# Setup Bazlı Minibar Kontrol Sistemi - Implementation Plan

## Genel Bakış

Bu implementation plan, setup bazlı minibar kontrol sistemini adım adım kodlayarak oluşturur. Her task, bir önceki task'ın üzerine inşa edilir ve sonunda tam çalışan bir sistem elde edilir.

## Task Listesi

- [x] 1. Veritabanı değişikliklerini uygula

  - Migration script'i oluştur ve çalıştır
  - Yeni enum değerlerini ekle (setup_kontrol, ekstra_ekleme, ekstra_tuketim)
  - Ekstra_miktar kolonunu ekle (eğer minibar_zimmet_detay tablosu varsa)
  - Index'leri oluştur
  - _Requirements: 1.1, 2.1, 3.1, 5.1_

- [x] 2. Servis katmanını oluştur

- [x] 2.1 minibar_servisleri.py dosyasını oluştur

  - `oda_setup_durumu_getir()` fonksiyonunu yaz
  - `tuketim_hesapla()` fonksiyonunu yaz
  - `zimmet_stok_kontrol()` fonksiyonunu yaz
  - `zimmet_stok_dusu()` fonksiyonunu yaz
  - `minibar_stok_guncelle()` fonksiyonunu yaz
  - `tuketim_kaydet()` fonksiyonunu yaz
  - _Requirements: 1.1, 2.1, 3.1, 4.1, 5.1, 6.1_

- [x] 2.2 Custom exception sınıflarını oluştur

  - `ZimmetStokYetersizError` exception'ını yaz
  - `OdaTipiNotFoundError` exception'ını yaz
  - `SetupNotFoundError` exception'ını yaz
  - _Requirements: 9.1_

- [x] 3. Backend API endpoint'lerini oluştur

- [x] 3.1 Oda setup durumu endpoint'i

  - `GET /api/kat-sorumlusu/oda-setup/<oda_id>` route'unu yaz
  - Oda tipini bul ve setup'ları getir
  - Her setup için ürünleri ve durumları hesapla
  - Kat sorumlusu zimmet stoklarını getir
  - JSON response döndür
  - Try-catch blokları ekle
  - _Requirements: 1.1, 1.2, 1.3, 2.1, 2.2, 2.3_

- [x] 3.2 Ürün ekleme endpoint'i

  - `POST /api/kat-sorumlusu/urun-ekle` route'unu yaz
  - Request validasyonu yap
  - Zimmet stok kontrolü yap
  - Transaction başlat
  - Tüketim hesapla ve kaydet
  - Zimmet stoğundan düş
  - Minibar stok güncelle
  - MinibarIslem ve MinibarIslemDetay kayıtları oluştur
  - Audit log kaydet
  - Transaction commit et
  - Try-catch blokları ekle
  - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5, 3.6, 4.1, 4.2, 4.3, 4.4, 9.1_

- [x] 3.3 Ekstra ürün ekleme endpoint'i

  - `POST /api/kat-sorumlusu/ekstra-ekle` route'unu yaz
  - Request validasyonu yap
  - Zimmet stok kontrolü yap
  - Transaction başlat
  - Zimmet stoğundan düş
  - Minibar stok güncelle (ekstra_miktar alanını güncelle)
  - MinibarIslem ve MinibarIslemDetay kayıtları oluştur (tuketim=0)
  - Audit log kaydet
  - Transaction commit et
  - Try-catch blokları ekle
  - _Requirements: 5.1, 5.2, 5.3, 5.4, 5.5, 5.6, 5.7, 5.8, 9.1_

- [x] 3.4 Ekstra sıfırlama endpoint'i

  - `POST /api/kat-sorumlusu/ekstra-sifirla` route'unu yaz
  - Request validasyonu yap
  - Transaction başlat
  - Ekstra miktarı tüketim olarak kaydet
  - Minibar stok güncelle (ekstra_miktar=0)
  - MinibarIslem ve MinibarIslemDetay kayıtları oluştur
  - Audit log kaydet
  - Transaction commit et
  - Try-catch blokları ekle
  - _Requirements: 6.1, 6.2, 6.3, 6.4, 6.5, 6.6, 6.7, 9.1_

- [x] 4. Frontend template'ini oluştur

- [x] 4.1 minibar_kontrol.html template'ini oluştur

  - Base template'i extend et
  - Oda seçim alanını oluştur (QR tarama + Manuel dropdown)
  - Setup accordion yapısını oluştur
  - Ürün tablosu template'ini oluştur
  - Durum renklendirmesi için CSS class'ları ekle
  - Responsive tasarım için media query'ler ekle
  - _Requirements: 1.1, 1.2, 1.3, 1.4, 2.1, 2.2, 2.3, 8.1, 8.2, 8.3_

- [x] 4.2 Modal template'lerini oluştur

  - Ürün ekleme modalını oluştur
  - Ekstra ekleme modalını oluştur
  - Ekstra sıfırlama onay modalını oluştur
  - Modal'lar için CSS stilleri ekle
  - Mobil uyumlu modal tasarımı yap
  - _Requirements: 3.1, 3.2, 3.3, 5.1, 5.2, 5.3, 6.1, 6.2, 6.3, 8.4, 8.5_

- [x] 5. Frontend JavaScript'i oluştur

- [x] 5.1 minibar_kontrol.js dosyasını oluştur

  - `odaSecildi()` fonksiyonunu yaz
  - `setupListesiYukle()` fonksiyonunu yaz
  - `accordionAc()` ve `accordionKapat()` fonksiyonlarını yaz
  - `durumRengiGetir()` fonksiyonunu yaz
  - `toastGoster()` fonksiyonunu yaz
  - _Requirements: 1.1, 1.2, 1.5, 2.1, 2.2, 8.6, 8.7_

- [x] 5.2 Modal yönetim fonksiyonlarını yaz

  - `urunEkleModalAc()` fonksiyonunu yaz
  - `ekstraEkleModalAc()` fonksiyonunu yaz
  - `ekstraSifirlaModalAc()` fonksiyonunu yaz
  - Modal kapatma fonksiyonlarını yaz
  - _Requirements: 3.1, 3.2, 5.1, 5.2, 6.1, 6.2_

- [x] 5.3 API çağrı fonksiyonlarını yaz

  - `urunEkle()` async fonksiyonunu yaz
  - `ekstraEkle()` async fonksiyonunu yaz
  - `ekstraSifirla()` async fonksiyonunu yaz
  - Hata yönetimi ve toast mesajları ekle
  - Loading state yönetimi ekle
  - _Requirements: 3.4, 3.5, 3.6, 5.5, 5.6, 5.7, 6.5, 6.6, 6.7, 8.6_

- [x] 6. Eski sistem fonksiyonlarını kaldır

- [x] 6.1 İlk dolum ve ek dolum route'larını kaldır

  - kat_sorumlusu_routes.py'den ilgili route'ları sil
  - depo_sorumlusu_routes.py'den ilgili route'ları sil
  - sistem_yoneticisi_routes.py'den ilgili route'ları sil
  - _Requirements: 7.1, 7.2, 7.3_

- [x] 6.2 İlk dolum ve ek dolum template'lerini kaldır

  - templates/kat_sorumlusu/ilk_dolum.html dosyasını sil
  - templates/kat_sorumlusu/ek_dolum.html dosyasını sil
  - templates/depo*sorumlusu/ilk_dolum*\*.html dosyalarını sil
  - templates/sistem*yoneticisi/ilk_dolum*\*.html dosyalarını sil
  - _Requirements: 7.4_

- [x] 6.3 İlk dolum ve ek dolum JavaScript dosyalarını kaldır

  - static/js/ilk_dolum.js dosyasını sil (varsa)
  - static/js/ek_dolum.js dosyasını sil (varsa)
  - İlgili JavaScript fonksiyonlarını diğer dosyalardan temizle
  - _Requirements: 7.5_

- [x] 6.4 Sidebar menülerini güncelle

  - Kat sorumlusu sidebar'ından "İlk Dolum" ve "Ek Dolum" menülerini kaldır
  - Depo sorumlusu sidebar'ından ilgili menüleri kaldır
  - Sistem yöneticisi sidebar'ından ilgili menüleri kaldır
  - "Minibar Kontrol" menüsünü tek giriş noktası olarak bırak
  - _Requirements: 7.1, 7.2, 7.6, 7.7_

- [x] 7. Güvenlik ve yetkilendirme ekle

- [x] 7.1 Route decorator'larını ekle

  - Tüm endpoint'lere @login_required ekle
  - Tüm endpoint'lere @role_required('kat_sorumlusu') ekle
  - Rate limiting ekle (@limiter.limit("60/minute"))
  - _Requirements: 9.1, 9.2, 9.7_

- [x] 7.2 Input validasyonu ekle

  - `validate_urun_ekle_request()` fonksiyonunu yaz
  - `validate_ekstra_ekle_request()` fonksiyonunu yaz
  - `validate_ekstra_sifirla_request()` fonksiyonunu yaz
  - Her endpoint'te validasyon çağır
  - _Requirements: 9.2_

- [x] 7.3 Audit trail kayıtlarını ekle

  - Her işlem sonrası audit_create() çağır
  - İşlem detaylarını JSONB formatında kaydet
  - Kullanıcı, tarih ve işlem tipi bilgilerini ekle
  - _Requirements: 9.5_

- [ ]\* 8. Test suite'ini oluştur
- [ ]\* 8.1 Unit testleri yaz

  - test_minibar_servisleri.py dosyasını oluştur
  - Servis fonksiyonları için unit testler yaz
  - Mock objeler kullan
  - _Requirements: Tüm gereksinimler_

- [ ]\* 8.2 Integration testleri yaz

  - test_minibar_kontrol_integration.py dosyasını oluştur
  - End-to-end akış testleri yaz
  - Veritabanı transaction testleri yaz
  - Hata senaryoları testleri yaz
  - _Requirements: Tüm gereksinimler_

- [ ]\* 8.3 Performance testleri yaz

  - Setup listeleme performans testi yaz (< 2 saniye)
  - Ürün ekleme performans testi yaz (< 1 saniye)
  - Load testing senaryoları oluştur
  - _Requirements: Başarı Kriterleri 1, 2_

- [x] 9. Deployment ve dokümantasyon

- [x] 9.1 Migration script'lerini hazırla

  - add_setup_kontrol_enum.py migration'ını oluştur
  - add_ekstra_miktar_column.py migration'ını oluştur (eğer gerekiyorsa)
  - remove_old_dolum_functions.py migration'ını oluştur
  - Migration sırasını dokümante et
  - _Requirements: 7.1, 7.2, 7.3, 7.4, 7.5_

- [x] 9.2 Rollback planını hazırla

  - Eski sisteme dönüş adımlarını dokümante et
  - Backup stratejisi oluştur
  - Rollback script'i yaz
  - _Requirements: Başarı Kriteri 3_

- [x] 9.3 Kullanıcı dokümantasyonu oluştur

  - SETUP_BAZLI_MINIBAR_KONTROL.md dosyası oluştur
  - Kullanım kılavuzu yaz
  - Ekran görüntüleri ekle
  - Sık sorulan sorular bölümü ekle
  - _Requirements: Tüm gereksinimler_

- [ ] 10. Sistem entegrasyonu ve test
- [ ] 10.1 Geliştirme ortamında test et

  - Tüm fonksiyonları manuel test et
  - Farklı oda tipleri ile test et
  - Farklı setup'lar ile test et
  - Hata senaryolarını test et
  - _Requirements: Tüm gereksinimler_

- [ ] 10.2 Mobil cihazlarda test et

  - Tablet'te test et
  - Telefonda test et
  - Farklı ekran boyutlarında test et
  - Touch event'leri test et
  - _Requirements: 8.1, 8.2, 8.3, 8.4, 8.5_

- [ ] 10.3 Production deployment
  - Migration'ları production'da çalıştır
  - Yeni kodu deploy et
  - Eski fonksiyonları devre dışı bırak
  - Monitoring ve alerting kur
  - _Requirements: Başarı Kriteri 3, 4_

## Notlar

- Her task tamamlandığında ilgili checkbox işaretlenmelidir
- Task'lar sırayla yapılmalıdır (bağımlılıklar var)
- Test task'ları (\*) opsiyoneldir ancak önerilir
- Her task için commit yapılması önerilir
- Hata durumunda rollback planı uygulanmalıdır

## Bağımlılıklar

```
1 → 2 → 3 → 4 → 5 → 6 → 7 → 8 → 9 → 10
    ↓   ↓   ↓   ↓
    2.1 3.1 4.1 5.1
    2.2 3.2 4.2 5.2
        3.3     5.3
        3.4
```

## Tahmini Süre

- Task 1: 1 saat
- Task 2: 3 saat
- Task 3: 4 saat
- Task 4: 3 saat
- Task 5: 3 saat
- Task 6: 2 saat
- Task 7: 2 saat
- Task 8: 4 saat (opsiyonel)
- Task 9: 2 saat
- Task 10: 3 saat

**Toplam: 23-27 saat**
