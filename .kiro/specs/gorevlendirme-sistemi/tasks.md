# Implementation Plan

## 1. Veritabanı Modelleri ve Migration

- [x] 1.1 Enum tipleri ve GunlukGorev modelini oluştur

  - GorevTipi ve GorevDurum enum'larını models.py'a ekle
  - GunlukGorev modelini oluştur (id, otel_id, personel_id, gorev_tarihi, gorev_tipi, durum, olusturma_tarihi, tamamlanma_tarihi, notlar)
  - İndeksler ve foreign key'leri tanımla
  - _Requirements: 1.1, 10.1_

- [x] 1.2 GorevDetay modelini oluştur

  - GorevDetay modelini oluştur (id, gorev_id, oda_id, misafir_kayit_id, durum, varis_saati, kontrol_zamani, dnd_sayisi, son_dnd_zamani, notlar)
  - GunlukGorev ile ilişkiyi tanımla
  - _Requirements: 2.1, 3.1_

- [x] 1.3 DNDKontrol modelini oluştur

  - DNDKontrol modelini oluştur (id, gorev_detay_id, kontrol_zamani, kontrol_eden_id, notlar)
  - GorevDetay ile ilişkiyi tanımla
  - _Requirements: 4.1, 4.2_

- [x] 1.4 YuklemeGorev modelini oluştur

  - YuklemeGorev modelini oluştur (id, otel_id, depo_sorumlusu_id, gorev_tarihi, dosya_tipi, durum, yukleme_zamani, dosya_yukleme_id)
  - DosyaYukleme ile ilişkiyi tanımla
  - _Requirements: 6.1, 6.2_

- [x] 1.5 GorevDurumLog modelini oluştur

  - GorevDurumLog modelini oluştur (id, gorev_detay_id, onceki_durum, yeni_durum, degisiklik_zamani, degistiren_id, aciklama)
  - GorevDetay ile ilişkiyi tanımla
  - _Requirements: 10.1_

- [x] 1.6 Alembic migration oluştur ve uygula

  - Migration dosyası oluştur
  - Veritabanına uygula
  - _Requirements: 1.1_

- [x]\* 1.7 Write property test for model serialization
  - **Property 9: Görev Durumu Log Round-Trip**
  - **Validates: Requirements 10.1, 10.3, 10.4**

## 2. GorevService Implementasyonu

- [x] 2.1 GorevService temel yapısını oluştur

  - utils/gorev_service.py dosyasını oluştur
  - GorevService sınıfını tanımla
  - _Requirements: 1.1_

- [x] 2.2 create_daily_tasks metodunu implement et

  - Günlük görevleri oluşturma mantığını yaz
  - In House ve Arrivals görevlerini ayrı oluştur
  - _Requirements: 1.1, 1.4_

- [x]\* 2.3 Write property test for task creation

  - **Property 1: Görev Oluşturma Tutarlılığı**
  - **Validates: Requirements 1.1**

- [x] 2.4 create_inhouse_tasks ve create_arrival_tasks metodlarını implement et

  - In House görevleri için MisafirKayit sorgusu
  - Arrivals görevleri için varış saati ile birlikte oluşturma
  - _Requirements: 2.1, 3.1_

- [x]\* 2.5 Write property test for task separation

  - **Property 2: In House ve Arrivals Ayrımı**
  - **Validates: Requirements 1.4, 2.1, 3.1**

- [x] 2.6 complete_task metodunu implement et

  - Görev durumunu completed olarak güncelle
  - Tamamlanma zamanını kaydet
  - GorevDurumLog kaydı oluştur
  - _Requirements: 2.2, 3.4, 10.1_

- [x]\* 2.7 Write property test for task completion

  - **Property 3: Görev Tamamlama Durumu**
  - **Validates: Requirements 2.2, 3.4**

- [x] 2.8 mark_dnd metodunu implement et

  - DND sayısını artır
  - DNDKontrol kaydı oluştur
  - 3 kez DND kontrolü yap ve otomatik tamamla
  - _Requirements: 2.3, 4.1, 4.2, 4.3_

- [x]\* 2.9 Write property test for DND marking

  - **Property 4: DND İşaretleme ve Listeleme**
  - **Validates: Requirements 2.3, 2.4**

- [x]\* 2.10 Write property test for DND 3-check rule

  - **Property 5: DND 3 Kontrol Kuralı**
  - **Validates: Requirements 4.3**

- [x] 2.11 calculate_countdown metodunu implement et

  - Varış saatine kalan süreyi hesapla
  - Saat, dakika, saniye olarak döndür
  - 15 dakika altı uyarı flag'i ekle
  - _Requirements: 3.2, 3.3_

- [x]\* 2.12 Write property test for countdown calculation

  - **Property 6: Geri Sayım Hesaplama**
  - **Validates: Requirements 3.2**

- [x] 2.13 get_pending_tasks, get_completed_tasks, get_dnd_tasks metodlarını implement et

  - Personel ve tarihe göre filtreleme
  - Durum bazlı sorgulama
  - _Requirements: 5.1, 5.2, 5.3_

- [x] 3. Checkpoint - Tüm testlerin geçtiğinden emin ol
  - Ensure all tests pass, ask the user if questions arise.

## 3. YuklemeGorevService Implementasyonu

- [x] 3.1 YuklemeGorevService temel yapısını oluştur

  - utils/yukleme_gorev_service.py dosyasını oluştur
  - YuklemeGorevService sınıfını tanımla
  - _Requirements: 6.1_

- [x] 3.2 create_daily_upload_tasks metodunu implement et

  - Her depo sorumlusu için In House ve Arrivals yükleme görevleri oluştur
  - Günlük otomatik çalışacak şekilde tasarla
  - _Requirements: 6.1_

- [x] 3.3 complete_upload_task metodunu implement et

  - Yükleme görevini tamamla
  - DosyaYukleme ile ilişkilendir
  - _Requirements: 6.2_

- [x]\* 3.4 Write property test for upload task completion

  - **Property 7: Yükleme Görevi Tamamlama**
  - **Validates: Requirements 6.2**

- [x] 3.5 get_pending_uploads ve get_upload_status metodlarını implement et

  - Bekleyen yükleme görevlerini getir
  - Yükleme durumunu sorgula
  - _Requirements: 6.3, 6.5_

- [x] 3.6 get_missing_uploads metodunu implement et

  - Tarih aralığında eksik yüklemeleri tespit et
  - İlgili depo sorumlularını listele
  - _Requirements: 9.4_

- [x]\* 3.7 Write property test for missing upload detection

  - **Property 8: Eksik Yükleme Tespiti**
  - **Validates: Requirements 9.4**

- [x] 3.8 get_upload_statistics metodunu implement et
  - Haftalık ve aylık yükleme oranlarını hesapla
  - _Requirements: 9.5_

## 4. BildirimService Implementasyonu

- [x] 4.1 BildirimService temel yapısını oluştur

  - utils/bildirim_service.py dosyasını oluştur
  - BildirimService sınıfını tanımla
  - _Requirements: 1.2_

- [x] 4.2 send_task_notification metodunu implement et

  - Görev bildirimi gönder
  - Bildirim tipine göre işle
  - _Requirements: 1.2, 1.3_

- [x] 4.3 send_dnd_incomplete_notification metodunu implement et

  - Tamamlanmayan DND bildirimi gönder
  - Oda numarası, ilk DND zamanı ve kontrol sayısını içer
  - _Requirements: 4.4, 4.5_

- [x] 4.4 send_upload_warning metodunu implement et

  - Yükleme uyarısı gönder
  - Depo sorumlusu ve sistem yöneticisine bildir
  - _Requirements: 6.3, 6.4_

- [x] 4.5 get_notifications metodunu implement et
  - Personel bildirimlerini getir
  - _Requirements: 1.2_

## 5. Routes Implementasyonu

- [x] 5.1 gorev_routes.py dosyasını oluştur

  - Blueprint tanımla
  - Route'ları register et
  - _Requirements: 1.3_

- [x] 5.2 Kat sorumlusu görev listesi route'larını implement et

  - GET /gorevler - Günlük görev listesi
  - GET /gorevler/inhouse - In House görevleri
  - GET /gorevler/arrivals - Arrivals görevleri
  - GET /gorevler/dnd - DND odaları listesi
  - _Requirements: 1.4, 2.1, 3.1, 2.4_

- [x] 5.3 Görev işlem route'larını implement et

  - POST /gorevler/<id>/tamamla - Görevi tamamla
  - POST /gorevler/<id>/dnd - DND olarak işaretle
  - _Requirements: 2.2, 2.3, 3.4_

- [x] 5.4 Depo sorumlusu route'larını implement et

  - GET /depo/gorevler - Yükleme görevleri
  - GET /depo/personel-gorevler - Personel görev durumları
  - GET /depo/gorev-raporlari - Görev raporları
  - _Requirements: 7.1, 7.2, 7.3_

- [x] 5.5 Sistem yöneticisi route'larını implement et

  - GET /sistem/gorev-ozeti - Otel geneli görev özeti
  - GET /sistem/yukleme-takip - Yükleme takip raporu
  - GET /sistem/dnd-bildirimleri - DND bildirimleri
  - _Requirements: 8.1, 8.2, 9.1, 9.2_

- [x] 5.6 API route'larını implement et

  - GET /api/gorevler/bekleyen - Bekleyen görev sayısı
  - GET /api/gorevler/countdown/<id> - Geri sayım bilgisi
  - POST /api/gorevler/bildirim-oku - Bildirimi okundu işaretle
  - _Requirements: 3.2, 1.2_

- [x] 6. Checkpoint - Tüm testlerin geçtiğinden emin ol
  - Ensure all tests pass, ask the user if questions arise.

## 6. Template'ler ve Dashboard Entegrasyonu

- [x] 6.1 Kat sorumlusu görev listesi template'ini oluştur

  - templates/kat_sorumlusu/gorev_listesi.html
  - In House ve Arrivals tabları
  - Geri sayım sayacı JavaScript
  - _Requirements: 1.4, 3.2, 3.3_

- [x] 6.2 Kat sorumlusu dashboard'una görev widget'ı ekle

  - Bekleyen görev sayısı
  - Tamamlanan görev sayısı
  - Bildirim alanı
  - _Requirements: 1.2, 5.1_

- [x]\* 6.3 Write property test for dashboard data consistency

  - **Property 10: Dashboard Veri Tutarlılığı**
  - **Validates: Requirements 5.1, 7.1, 8.1**

- [x] 6.4 DND odaları listesi template'ini oluştur

  - templates/kat_sorumlusu/dnd_listesi.html
  - DND kontrol geçmişi
  - Tekrar kontrol butonu
  - _Requirements: 2.4, 4.2_

- [x] 6.5 Depo sorumlusu dashboard'una görev widget'ı ekle

  - Yükleme görevleri durumu
  - Personel görev özeti
  - Eksik yükleme uyarısı
  - _Requirements: 6.3, 7.1_

- [x] 6.6 Sistem yöneticisi dashboard'una görev widget'ı ekle

  - Otel geneli görev özeti
  - Yükleme durumu özeti
  - DND bildirimleri
  - _Requirements: 8.1, 9.1_

- [x] 6.7 Görev raporları template'ini oluştur
  - templates/raporlar/gorev_raporlari.html
  - Tarih filtresi
  - Personel/kat/oda tipi bazlı istatistikler
  - _Requirements: 5.4, 7.3, 8.3_

## 7. Excel Yükleme Entegrasyonu

- [x] 7.1 ExcelProcessingService'e görev oluşturma hook'u ekle

  - Yükleme tamamlandığında GorevService.create_daily_tasks() çağır
  - YuklemeGorevService.complete_upload_task() çağır
  - _Requirements: 1.1, 6.2_

- [x] 7.2 Yükleme sonrası bildirim gönderimi ekle
  - Kat sorumlularına görev bildirimi gönder
  - _Requirements: 1.2_

## 8. Scheduled Tasks (Celery)

- [x] 8.1 Günlük yükleme görevi oluşturma task'ı ekle

  - Her gün 00:01'de çalışacak
  - Tüm depo sorumluları için yükleme görevleri oluştur
  - _Requirements: 6.1_

- [x] 8.2 DND tamamlanmayan görev kontrolü task'ı ekle

  - Her gün 23:59'da çalışacak
  - 3 kez kontrol edilmemiş DND odalarını tespit et
  - Bildirim gönder
  - _Requirements: 4.4_

- [x] 8.3 Eksik yükleme uyarısı task'ı ekle

  - Her gün 18:00'da çalışacak
  - Yükleme yapılmamış otelleri tespit et
  - Uyarı gönder
  - _Requirements: 6.3, 6.4_

- [x] 9. Final Checkpoint - Tüm testlerin geçtiğinden emin ol
  - Ensure all tests pass, ask the user if questions arise.
