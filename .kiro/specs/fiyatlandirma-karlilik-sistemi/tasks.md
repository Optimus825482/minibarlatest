# Fiyatlandırma ve Karlılık Hesaplama Sistemi - İmplementasyon Görevleri

## Faz 1: Veritabanı ve Model Altyapısı

- [x] 1. Veritabanı Kontrolü ve Eksik Tabloların Oluşturulması

  - Mevcut fiyatlandırma tablolarını kontrol et (tedarikciler, urun_tedarikci_fiyatlari, urun_fiyat_gecmisi, oda_tipi_satis_fiyatlari, sezon_fiyatlandirma zaten var)
  - Eksik tabloları tespit et ve migration script hazırla
  - _Requirements: 1.1, 2.1, 3.1, 4.1, 5.1, 6.1, 7.1, 21.1_

- [x] 1.1 UrunStok Tablosu Oluşturma

  - UrunStok modelini models.py'ye ekle (mevcut_stok, minimum_stok, maksimum_stok, kritik_stok_seviyesi, birim_maliyet, toplam_deger, stok_devir_hizi)
  - Otel bazlı stok izolasyonu için otel_id foreign key ekle
  - Index'leri oluştur (idx_urun_stok_otel, idx_urun_stok_kritik)
  - _Requirements: 21.1, 21.2, 21.3, 21.8_

- [x] 1.2 Kampanya ve Bedelsiz Tablolarını Kontrol ve Güncelleme

  - Kampanya tablosunu kontrol et (kampanyalar tablosu var, eksik kolonları ekle)
  - BedelsizLimit tablosunu kontrol et (bedelsiz_limitler tablosu var, eksik kolonları ekle)
  - BedelsizKullanimLog tablosunu kontrol et (bedelsiz_kullanim_log tablosu var)
  - _Requirements: 5.1, 5.2, 6.1, 6.2_

- [x] 1.3 Karlılık ve Analiz Tablolarını Kontrol

  - DonemselKarAnalizi tablosunu kontrol et (donemsel_kar_analizi tablosu var)
  - FiyatGuncellemeKurali tablosunu kontrol et (fiyat_guncelleme_kurallari tablosu var)
  - ROI hesaplama tablosunu kontrol et (roi_hesaplamalari tablosu var)
  - _Requirements: 8.1, 10.1, 15.1_

- [x] 1.4 MinibarIslemDetay Tablosuna Fiyat Kolonları Ekleme

  - satis_fiyati, alis_fiyati, kar_tutari, kar_orani, bedelsiz, kampanya_id kolonlarını ekle
  - Mevcut kayıtlar için NULL değerlere izin ver
  - Migration script'i hazırla
  - _Requirements: 7.1, 7.2, 7.3, 7.4_

- [x] 1.5 Model Enum'larını Güncelleme

  - FiyatDegisiklikTipi, IndirimTipi, BedelsizLimitTipi, DonemTipi, KuralTipi enum'larını models.py'ye ekle
  - PostgreSQL ENUM tiplerini oluştur
  - _Requirements: 2.1, 5.1, 6.1, 8.1, 15.1_

## Faz 2: Servis Katmanı Geliştirme

- [x] 2. FiyatYonetimServisi Oluşturma

  - utils/fiyatlandirma_servisler.py dosyasını oluştur
  - FiyatYonetimServisi sınıfını implement et
  - _Requirements: 2.1, 3.1, 4.1_

- [x] 2.1 Dinamik Fiyat Hesaplama Fonksiyonu

  - dinamik_fiyat_hesapla() metodunu yaz (alış fiyatı + oda tipi + sezon + kampanya + bedelsiz)
  - Çok katmanlı fiyat hesaplama algoritması
  - Try-catch blokları ile hata yönetimi
  - _Requirements: 2.2, 3.2, 4.2, 5.2, 6.2_

- [x] 2.2 Tedarikçi Fiyat Yönetimi Fonksiyonları

  - guncel_alis_fiyati_getir() metodu
  - en_uygun_tedarikci_bul() metodu
  - fiyat_guncelle() metodu
  - _Requirements: 1.1, 1.2, 2.1, 2.2_

- [x] 2.3 Oda Tipi ve Sezon Fiyat Fonksiyonları

  - oda_tipi_fiyati_getir() metodu
  - sezon_carpani_uygula() metodu
  - _Requirements: 3.1, 3.2, 4.1, 4.2_

- [x] 3. KampanyaServisi Oluşturma

  - KampanyaServisi sınıfını implement et
  - kampanya_olustur(), kampanya_uygula(), kampanya_kullanim_guncelle() metodları
  - _Requirements: 5.1, 5.2, 5.3, 5.4, 5.5_

- [x] 4. BedelsizServisi Oluşturma

  - BedelsizServisi sınıfını implement et
  - limit_kontrol(), limit_kullan(), limit_tanimla() metodları
  - _Requirements: 6.1, 6.2, 6.3, 6.4, 6.5_

- [x] 5. KarHesaplamaServisi Oluşturma

  - KarHesaplamaServisi sınıfını implement et
  - gercek_zamanli_kar_hesapla(), donemsel_kar_analizi(), urun_karliligi_analizi(), oda_karliligi_analizi(), roi_hesapla() metodları
  - _Requirements: 7.1, 7.2, 7.3, 8.1, 8.2, 9.1, 9.2, 10.1, 10.2_

- [x] 6. StokYonetimServisi Oluşturma

  - StokYonetimServisi sınıfını implement et
  - stok_durumu_getir(), kritik_stoklar_getir(), stok_sayim_yap(), stok_devir_raporu(), stok_deger_raporu() metodları
  - _Requirements: 21.1, 21.2, 21.3, 21.4, 21.5, 21.9, 21.10_

- [x] 7. MLEntegrasyonServisi Oluşturma

  - MLEntegrasyonServisi sınıfını implement et
  - gelir_anomali_tespit(), karlilik_anomali_tespit(), trend_analizi() metodları
  - Mevcut ML sistemi ile entegrasyon
  - _Requirements: 13.1, 13.2, 13.3, 14.1, 14.2_

## Faz 3: API Endpoint'leri

- [x] 8. Fiyat Yönetimi API Route'ları

  - routes/fiyatlandirma_routes.py dosyasını oluştur
  - Blueprint tanımla
  - _Requirements: 2.1, 3.1, 4.1, 5.1_

- [x] 8.1 Temel Fiyat API'leri

  - GET /api/v1/fiyat/urun/<urun_id> - Ürün fiyat bilgileri
  - POST /api/v1/fiyat/urun/<urun_id>/guncelle - Fiyat güncelleme
  - GET /api/v1/fiyat/tedarikci/<tedarikci_id> - Tedarikçi fiyatları
  - POST /api/v1/fiyat/dinamik-hesapla - Dinamik fiyat hesaplama
  - _Requirements: 2.1, 2.2, 2.3_

- [x] 8.2 Kampanya API'leri

  - POST /api/v1/fiyat/kampanya - Kampanya oluşturma
  - GET /api/v1/fiyat/kampanya/<kampanya_id> - Kampanya detayı
  - PUT /api/v1/fiyat/kampanya/<kampanya_id> - Kampanya güncelleme
  - DELETE /api/v1/fiyat/kampanya/<kampanya_id> - Kampanya silme
  - _Requirements: 5.1, 5.2, 5.3_

- [x] 9. Karlılık API Route'ları

  - routes/karlilik_routes.py dosyasını oluştur
  - Blueprint tanımla
  - _Requirements: 7.1, 8.1, 9.1, 10.1_

- [x] 9.1 Karlılık Hesaplama API'leri

  - GET /api/v1/kar/urun/<urun_id> - Ürün karlılık bilgisi
  - GET /api/v1/kar/oda/<oda_id> - Oda karlılık bilgisi
  - GET /api/v1/kar/donemsel - Dönemsel kar raporu
  - POST /api/v1/kar/hesapla - Gerçek zamanlı kar hesaplama
  - _Requirements: 7.1, 7.2, 8.1, 8.2, 9.1_

- [x] 9.2 ROI ve Analiz API'leri

  - GET /api/v1/kar/roi/<urun_id> - ROI hesaplama
  - GET /api/v1/kar/analitik - Karlılık analitikleri
  - GET /api/v1/kar/trend - Trend analizi
  - _Requirements: 10.1, 10.2, 10.3, 12.1_

- [x] 10. Stok Yönetimi API Route'ları

  - routes/stok_routes.py dosyasını oluştur
  - Blueprint tanımla
  - _Requirements: 21.1, 21.2, 21.3_

- [x] 10.1 Stok Durumu API'leri

  - GET /api/v1/stok/durum/<urun_id> - Stok durumu
  - GET /api/v1/stok/kritik - Kritik stoklar
  - POST /api/v1/stok/sayim - Stok sayımı
  - GET /api/v1/stok/devir-raporu - Stok devir raporu
  - GET /api/v1/stok/deger-raporu - Stok değer raporu
  - _Requirements: 21.1, 21.2, 21.3, 21.4, 21.9, 21.10_

## Faz 4: Frontend Geliştirme

- [x] 11. Karlılık Dashboard UI

  - templates/admin/karlilik_dashboard.html oluştur
  - Özet kartlar (Günlük Kar, Aylık Kar, Kar Marjı, ROI)
  - Chart.js ile trend grafikleri
  - DataTables ile en karlı ürünler tablosu
  - _Requirements: 17.1, 17.2, 17.3_

- [x] 12. Fiyat Yönetimi UI

  - templates/admin/urun_fiyat_yonetimi.html oluştur
  - Fiyat güncelleme formu
  - Tedarikçi seçimi
  - Fiyat geçmişi tablosu
  - _Requirements: 2.1, 2.2, 16.1, 16.2_

- [x] 13. Kampanya Yönetimi UI

  - templates/admin/kampanya_yonetimi.html oluştur
  - Kampanya oluşturma formu
  - Aktif kampanyalar tablosu
  - Kampanya performans metrikleri
  - _Requirements: 5.1, 5.2, 5.3_

- [x] 14. Bedelsiz Limit Yönetimi UI

  - templates/admin/bedelsiz_limit_yonetimi.html oluştur
  - Limit tanımlama formu
  - Oda bazlı limit listesi
  - Kullanım takibi
  - _Requirements: 6.1, 6.2, 6.3_

- [x] 15. JavaScript Modülleri

  - static/js/fiyatlandirma.js oluştur
  - FiyatlandirmaManager sınıfı
  - KarlilikManager sınıfı
  - Chart.js entegrasyonu
  - DataTables entegrasyonu
  - _Requirements: 17.1, 17.2, 17.3, 17.4_

## Faz 5: Performans ve Optimizasyon

- [x] 16. Redis Cache Entegrasyonu

  - Flask-Caching konfigürasyonu
  - FiyatCache sınıfı oluştur
  - Fiyat hesaplama cache (1 saat)
  - Kar analizi cache (30 dakika)
  - Cache invalidation stratejisi
  - _Requirements: 18.1, 18.2, 18.3, 18.5_

- [x] 17. Celery Asenkron İşlemler

  - Celery konfigürasyonu
  - donemsel_kar_hesapla_async() task
  - tuketim_trendi_guncelle_async() task
  - stok_devir_guncelle_async() task
  - _Requirements: 18.4_

- [x] 18. Database Optimizasyonu

  - Index'leri kontrol et ve optimize et
  - Query performansını test et
  - Connection pooling ayarları
  - _Requirements: 18.1, 18.2_

## Faz 6: Güvenlik ve Yetkilendirme

- [x] 19. Rol Bazlı Erişim Kontrolü

  - role_required decorator'ı implement et
  - Her API endpoint'ine yetki kontrolü ekle
  - Sistem Yöneticisi: Tüm erişim
  - Admin: Tüm erişim
  - Depo Sorumlusu: Tedarikçi fiyatları
  - Kat Sorumlusu: Sadece görüntüleme
  - _Requirements: 19.1, 19.2, 19.3, 19.4_

- [ ] 20. Audit Trail Entegrasyonu

  - log_fiyat_degisiklik() fonksiyonu
  - Tüm fiyat değişikliklerini AuditLog'a kaydet
  - UrunFiyatGecmisi tablosuna kaydet
  - _Requirements: 16.1, 16.2, 16.3, 19.5_

-

- [x] 21. Input Validasyonu

  - FiyatValidation sınıfı oluştur
  - validate_fiyat() - Negatif fiyat kontrolü
  - validate_kampanya() - İndirim oranı kontrolü
  - validate_bedelsiz_limit() - Limit kontrolü
  - _Requirements: 2.1, 5.1, 6.1_

## -az 7: Veri Migrasyonu

- [x] 22. Migration Script Hazırlama

  - migrations/add_fiyatlandirma_sistemi.py oluştur
  - upgrade() fonksiyonu - Yeni tabloları oluştur
  - downgrade() fonksiyonu - Rollback
  - _Requirements: 20.1, 20.2, 20.3_

- [x] 23. Mevcut Verilere Fiyat Atama

  - Tüm ürünlere varsayılan alış fiyatı ata
  - Varsayılan tedarikçi oluştur
  - UrunStok kayıtları oluştur
  - _Requirements: 20.1, 20.2, 21.1_

- [ ] 24. Tarihsel Fiyat Hesaplama
  - Geçmiş MinibarIslemDetay kayıtlarına fiyat hesapla
  - Kar tutarı ve kar oranı hesapla
  - _Requirements: 20.2_

## Faz 8: Test ve Dokümantasyon

- [x] 25. Unit Testler

  - tests/test_fiyatlandirma.py oluştur
  - FiyatYonetimServisi testleri
  - KarHesaplamaServisi testleri
  - KampanyaServisi testleri
  - BedelsizServisi testleri
  - StokYonetimServisi testleri
  - _Requirements: Tüm servisler_

- [x] 26. Integration Testler

  - API endpoint testleri
  - Database entegrasyon testleri
  - Cache testleri
  - _Requirements: Tüm API'ler_

- [ ] 27. API Dokümantasyonu

  - OpenAPI/Swagger dokümantasyonu
  - Endpoint açıklamaları
  - Request/Response örnekleri
  - _Requirements: Tüm API'ler_

- [ ] 28. Kullanıcı Dokümantasyonu
  - Fiyatlandırma sistemi kullanım kılavuzu
  - Kampanya yönetimi rehberi
  - Karlılık analizi rehberi
  - _Requirements: Tüm özellikler_
