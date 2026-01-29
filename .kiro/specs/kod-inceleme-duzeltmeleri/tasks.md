# Implementation Plan: Kod İnceleme Düzeltmeleri

## Overview

Bu plan, KOD_INCELEME_RAPORU_2026.md'de tespit edilen güvenlik açıkları ve kod kalitesi sorunlarının düzeltilmesi için adım adım görevleri içerir. Görevler öncelik sırasına göre (Kritik → Yüksek → Orta) sıralanmıştır.

## Tasks

- [x] 1. Kritik Güvenlik Düzeltmeleri

  - [x] 1.1 Developer şifresini environment variable'a taşı
    - `routes/developer_routes.py` dosyasında hardcoded şifreyi kaldır
    - `os.getenv('DEVELOPER_PASSWORD_HASH')` ile environment variable'dan oku
    - `werkzeug.security.check_password_hash` ile şifre doğrulama yap
    - `.env.example` dosyasına örnek hash ekle
    - _Requirements: 1.1, 1.2, 1.3, 1.4_
  - [x]\* 1.2 Write property test for password hash verification ✅
    - **Property 1: Password Hash Verification**
    - **Validates: Requirements 1.2**
    - _Implemented in: tests/test_kod_inceleme_properties.py_
  - [x] 1.3 SQL injection koruması için whitelist ekle
    - `utils/rollback_manager.py` dosyasında ALLOWED_TABLES listesi oluştur
    - `validate_table_name()` fonksiyonu ekle
    - TRUNCATE işleminden önce whitelist kontrolü yap
    - _Requirements: 2.1, 2.2_
  - [x]\* 1.4 Write property test for SQL table whitelist validation ✅
    - **Property 2: SQL Table Whitelist Validation**
    - **Validates: Requirements 2.1, 2.2**
    - _Implemented in: tests/test_kod_inceleme_properties.py_
  - [x] 1.5 Query analyzer'da SQL injection koruması ekle
    - `utils/monitoring/query_analyzer.py` dosyasında ALLOWED_QUERY_PREFIXES listesi oluştur
    - `validate_query_for_explain()` fonksiyonu ekle
    - explain_query çağrısından önce prefix kontrolü yap
    - _Requirements: 2.3, 2.4_
  - [x]\* 1.6 Write property test for query prefix validation ✅
    - **Property 3: Query Prefix Validation**
    - **Validates: Requirements 2.3, 2.4**
    - _Implemented in: tests/test_kod_inceleme_properties.py_

- [x] 2. Checkpoint - Kritik güvenlik düzeltmelerini doğrula

  - Tüm testlerin geçtiğinden emin ol
  - Kullanıcıya soru varsa sor

- [x] 3. XSS Güvenlik Düzeltmeleri

  - [x] 3.1 DOMPurify kütüphanesini projeye ekle
    - `static/js/vendor/purify.min.js` dosyasını oluştur (CDN'den indir)
    - `templates/base.html` dosyasına script tag ekle
    - _Requirements: 3.2_
  - [x] 3.2 JavaScript dosyalarında innerHTML kullanımlarını güvenli hale getir
    - `static/js/toast.js` dosyasını güncelle
    - `static/js/table-search-filter.js` dosyasını güncelle
    - `static/js/oda_kontrol.js` dosyasını güncelle
    - `static/js/bildirim_manager.js` dosyasını güncelle
    - Tüm innerHTML kullanımlarını DOMPurify.sanitize() ile sar
    - _Requirements: 3.1, 3.3, 3.4_

- [x] 4. Yüksek Seviye Düzeltmeler

  - [x] 4.1 JSON validation helper fonksiyonu ekle
    - `utils/helpers.py` dosyasına `get_json_or_error()` fonksiyonu ekle
    - _Requirements: 4.1, 4.2_
  - [x] 4.2 Route dosyalarında JSON null kontrolü ekle
    - `routes/gorev_routes.py` dosyasını güncelle
    - `routes/depo_routes.py` dosyasını güncelle
    - `routes/fiyatlandirma_routes.py` dosyasını güncelle
    - _Requirements: 4.3_
  - [x]\* 4.3 Write property test for JSON validation response ✅
    - **Property 4: JSON Validation Response**
    - **Validates: Requirements 4.1, 4.2**
    - _Implemented in: tests/test_kod_inceleme_properties.py_
  - [x] 4.4 N+1 query optimizasyonu yap
    - `routes/developer_routes.py` dosyasında `get_product_stats()` fonksiyonunu optimize et
    - Döngü içindeki sorguları tek sorguda toplu veri çekecek şekilde değiştir
    - _Requirements: 5.1, 5.2, 5.3_
  - [x]\* 4.5 Write property test for optimized query performance ✅
    - **Property 6: Optimized Query Performance**
    - **Validates: Requirements 5.1, 5.3**
    - _Implemented in: tests/test_kod_inceleme_properties.py_
  - [x] 4.6 Duplicate kod temizliği yap
    - `utils/excel_service.py` dosyasında duplicate `basarili_satir += 1` satırını kaldır (satır 259)
    - _Requirements: 6.1, 6.2_

- [x] 5. Checkpoint - Yüksek seviye düzeltmeleri doğrula

  - Tüm testlerin geçtiğinden emin ol
  - Kullanıcıya soru varsa sor

- [x] 6. Orta Seviye Düzeltmeler

  - [x] 6.1 Magic numbers düzeltmesi yap
    - `static/js/bildirim_manager.js` dosyasında NOTIFICATION_TIMEOUT_MS sabiti tanımla
    - `routes/developer_routes.py` dosyasında limit değerleri için sabitler tanımla
    - _Requirements: 7.1, 7.2, 7.3_
  - [x] 6.2 Error response helper fonksiyonu ekle
    - `utils/helpers.py` dosyasına `error_response()` fonksiyonu ekle
    - `utils/helpers.py` dosyasına `success_response()` fonksiyonu ekle
    - _Requirements: 8.1, 8.2_
  - [x] 6.3 Route dosyalarında hata response formatını standartlaştır
    - Tutarsız hata formatlarını `error_response()` ile değiştir
    - _Requirements: 8.3_
  - [x]\* 6.4 Write property test for error response format consistency ✅
    - **Property 5: Error Response Format Consistency**
    - **Validates: Requirements 8.1, 8.2**
    - _Implemented in: tests/test_kod_inceleme_properties.py_
  - [x] 6.5 Logging tutarlılığını sağla
    - `print()` çağrılarını `logger` çağrılarına dönüştür
    - Hata durumlarında `logger.error()` kullan
    - Bilgi loglarında `logger.info()` kullan
    - Debug loglarında `logger.debug()` kullan
    - Uyarı loglarında `logger.warning()` kullan
    - _Requirements: 9.1, 9.2, 9.3, 9.4_
    - _Düzeltilen dosyalar: routes/**init**.py, routes/error_handlers.py, routes/restore_routes.py, routes/restore_routes_v2.py, routes/rapor_routes.py, routes/gorev_routes.py, routes/kat_sorumlusu_routes.py, routes/sistem_yoneticisi_routes.py, routes/dashboard_routes.py, routes/doluluk_routes.py, routes/api_routes.py_

- [x] 7. Final Checkpoint - Tüm düzeltmeleri doğrula
  - Tüm zorunlu görevler tamamlandı
  - Logging tutarlılığı sağlandı (print → logger dönüşümü)
  - Error response formatları standartlaştırıldı
  - Kod kalitesi iyileştirildi
  - Opsiyonel property testleri (hypothesis ile) kullanıcı tarafından istendiğinde yazılabilir

## Notes

- Görevler `*` ile işaretlenenler opsiyonel test görevleridir
- Her görev belirli requirements'lara referans verir
- Checkpoint'ler incremental doğrulama sağlar
- Property testleri hypothesis kütüphanesi ile yazıldı (20 iterasyon/test, hız optimizasyonu)
- Unit testler pytest ile yazılacak
- Property testleri: `python -m pytest tests/test_kod_inceleme_properties.py -v`
