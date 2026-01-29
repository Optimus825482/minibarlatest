# Requirements Document

## Introduction

Bu spec, KOD_INCELEME_RAPORU_2026.md dosyasında tespit edilen güvenlik açıkları ve kod kalitesi sorunlarının düzeltilmesini kapsar. Öncelik sırasına göre kritik güvenlik açıkları, yüksek seviye bulgular ve orta seviye iyileştirmeler ele alınacaktır.

## Glossary

- **System**: Otel Minibar Yönetim Sistemi
- **Developer_Panel**: Geliştirici yönetim paneli
- **XSS**: Cross-Site Scripting saldırısı
- **SQL_Injection**: SQL enjeksiyon saldırısı
- **DOMPurify**: JavaScript HTML sanitization kütüphanesi
- **Environment_Variable**: Sistem ortam değişkeni
- **Whitelist**: İzin verilen değerler listesi
- **N_Plus_1_Query**: Döngü içinde tekrarlı veritabanı sorgusu problemi

## Requirements

### Requirement 1: Hardcoded Şifre Güvenlik Açığı

**User Story:** As a sistem yöneticisi, I want developer şifresinin güvenli şekilde saklanmasını, so that kaynak koda erişen kişiler panele yetkisiz erişim sağlayamasın.

#### Acceptance Criteria

1. WHEN developer_routes.py dosyası yüklendiğinde, THE System SHALL developer şifresini environment variable'dan okumalı
2. WHEN şifre doğrulaması yapıldığında, THE System SHALL werkzeug.security.check_password_hash fonksiyonunu kullanmalı
3. IF DEVELOPER_PASSWORD_HASH environment variable tanımlı değilse, THEN THE System SHALL developer paneline erişimi engellemeli
4. THE System SHALL hardcoded şifre içermemeli

### Requirement 2: SQL Injection Koruması

**User Story:** As a güvenlik uzmanı, I want dinamik tablo adlarının whitelist ile kontrol edilmesini, so that SQL injection saldırıları engellensin.

#### Acceptance Criteria

1. WHEN rollback_manager.py'de TRUNCATE işlemi yapıldığında, THE System SHALL tablo adını ALLOWED_TABLES whitelist'inde kontrol etmeli
2. IF tablo adı whitelist'te yoksa, THEN THE System SHALL ValueError exception fırlatmalı
3. WHEN query_analyzer.py'de explain_query çağrıldığında, THE System SHALL sadece SELECT ve WITH ile başlayan sorguları kabul etmeli
4. IF query SELECT veya WITH ile başlamıyorsa, THEN THE System SHALL hata mesajı döndürmeli

### Requirement 3: XSS Güvenlik Açıkları

**User Story:** As a kullanıcı, I want tarayıcımda kötü niyetli JavaScript kodlarının çalışmamasını, so that hesabım ve verilerim güvende olsun.

#### Acceptance Criteria

1. WHEN JavaScript dosyalarında innerHTML kullanıldığında, THE System SHALL DOMPurify ile sanitization yapmalı
2. THE System SHALL DOMPurify kütüphanesini static/js/vendor/ klasörüne eklemeli
3. WHEN kullanıcı girdisi DOM'a eklendiğinde, THE System SHALL textContent veya DOMPurify.sanitize() kullanmalı
4. THE System SHALL oda_kontrol.js, bildirim_manager.js, toast.js, table-search-filter.js dosyalarını güncellemeli

### Requirement 4: Request JSON Null Kontrolü

**User Story:** As a API kullanıcısı, I want geçersiz JSON gönderimlerinde anlamlı hata mesajları almak, so that sorunları hızlıca çözebilmem.

#### Acceptance Criteria

1. WHEN request.get_json() çağrıldığında, THE System SHALL None kontrolü yapmalı
2. IF data None ise, THEN THE System SHALL {'success': False, 'error': 'Geçersiz JSON verisi'} ve 400 status code döndürmeli
3. THE System SHALL gorev_routes.py, depo_routes.py, fiyatlandirma_routes.py dosyalarını güncellemeli

### Requirement 5: N+1 Query Optimizasyonu

**User Story:** As a sistem yöneticisi, I want veritabanı sorgularının optimize edilmesini, so that sistem performansı artırılsın.

#### Acceptance Criteria

1. WHEN developer_routes.py'de get_product_stats() çağrıldığında, THE System SHALL tek sorguda toplu veri çekmeli
2. THE System SHALL döngü içinde tekrarlı sorgu yerine JOIN veya subquery kullanmalı
3. WHEN stok hareketleri sorgulandığında, THE System SHALL func.sum ve case ifadeleri ile tek sorguda sonuç döndürmeli

### Requirement 6: Duplicate Kod Temizliği

**User Story:** As a geliştirici, I want kod tekrarlarının temizlenmesini, so that bakım kolaylaşsın ve hatalar azalsın.

#### Acceptance Criteria

1. WHEN excel_service.py incelendiğinde, THE System SHALL duplicate `basarili_satir += 1` satırını kaldırmalı
2. THE System SHALL kod tekrarı içermemeli

### Requirement 7: Magic Numbers Düzeltmesi

**User Story:** As a geliştirici, I want sabit değerlerin anlamlı isimlerle tanımlanmasını, so that kodun okunabilirliği artsın.

#### Acceptance Criteria

1. WHEN bildirim_manager.js'de timeout kullanıldığında, THE System SHALL NOTIFICATION_TIMEOUT_MS sabiti kullanmalı
2. WHEN developer_routes.py'de limit değerleri kullanıldığında, THE System SHALL anlamlı sabit isimleri kullanmalı
3. THE System SHALL tüm magic number'ları const/constant olarak tanımlamalı

### Requirement 8: Hata Response Standardizasyonu

**User Story:** As a API kullanıcısı, I want tutarlı hata response formatı almak, so that hata yönetimini kolayca yapabilmem.

#### Acceptance Criteria

1. THE System SHALL tüm hata response'larında aynı formatı kullanmalı: {'success': False, 'error': message, 'status_code': code}
2. WHEN hata oluştuğunda, THE System SHALL error_response() helper fonksiyonunu kullanmalı
3. THE System SHALL tutarsız hata formatlarını standart formata dönüştürmeli

### Requirement 9: Logging Tutarlılığı

**User Story:** As a sistem yöneticisi, I want tutarlı log formatı kullanılmasını, so that sorunları kolayca takip edebileyim.

#### Acceptance Criteria

1. THE System SHALL print() yerine logger kullanmalı
2. WHEN hata loglanacağında, THE System SHALL logger.error() kullanmalı
3. WHEN bilgi loglanacağında, THE System SHALL logger.info() kullanmalı
4. THE System SHALL tüm print() çağrılarını logger çağrılarına dönüştürmeli
