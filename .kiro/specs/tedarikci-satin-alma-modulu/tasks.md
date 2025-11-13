# Tedarikçi ve Satın Alma Modülü - İmplementasyon Planı

## Genel Bakış

Bu plan, tedarikçi yönetimi ve satın alma modülünün adım adım implementasyonunu içerir. Her task, önceki task'lerin üzerine inşa edilir ve tüm kod entegre edilmiş şekilde çalışır durumda olacaktır.

## Task Listesi

- [x] 1. Veri modelleri ve enum'ları oluştur

  - Yeni veri modellerini models.py'ye ekle
  - Enum sınıflarını tanımla (SiparisDurum, DokumanTipi)
  - Veritabanı ilişkilerini kur
  - _Gereksinimler: 1.1, 2.1, 3.1, 4.1, 10.1_

- [x] 1.1 SatinAlmaSiparisi ve SatinAlmaSiparisDetay modellerini ekle

  - SatinAlmaSiparisi model sınıfını oluştur
  - SatinAlmaSiparisDetay model sınıfını oluştur
  - İlişkileri ve indeksleri tanımla
  - _Gereksinimler: 3.1, 3.2, 4.1_

- [x] 1.2 TedarikciPerformans, TedarikciIletisim ve TedarikciDokuman modellerini ekle

  - TedarikciPerformans model sınıfını oluştur
  - TedarikciIletisim model sınıfını oluştur
  - TedarikciDokuman model sınıfını oluştur
  - _Gereksinimler: 6.1, 10.1, 10.2_

- [x] 1.3 Migration script'i oluştur ve çalıştır

  - Alembic migration dosyası oluştur
  - Migration'ı test et
  - Veritabanını güncelle
  - _Gereksinimler: Tüm veri modelleri_

- [ ] 2. Tedarikçi yönetim servislerini oluştur

  - utils/tedarikci_servisleri.py dosyasını oluştur
  - TedarikciServisi sınıfını implement et
  - Tedarikçi CRUD operasyonlarını ekle
  - Performans hesaplama fonksiyonlarını ekle
  - _Gereksinimler: 1.1, 1.2, 1.3, 6.1, 6.2_

- [x] 2.1 Tedarikçi CRUD operasyonlarını implement et

  - tedarikci_olustur() metodunu yaz
  - tedarikci_guncelle() metodunu yaz
  - tedarikci_listele() metodunu yaz
  - tedarikci_sil() metodunu yaz (soft delete)
  - _Gereksinimler: 1.1, 1.2, 1.3_

- [x] 2.2 Tedarikçi performans hesaplama fonksiyonlarını ekle

  - tedarikci_performans_hesapla() metodunu yaz
  - performans_skoru_hesapla() yardımcı fonksiyonunu yaz
  - zamaninda_teslimat_orani_hesapla() fonksiyonunu yaz
  - _Gereksinimler: 6.1, 6.2, 6.3_

- [x] 2.3 En uygun tedarikçi bulma algoritmasını implement et

  - en_uygun_tedarikci_bul() metodunu yaz
  - Fiyat ve performans skorunu birleştiren algoritma
  - _Gereksinimler: 2.2, 7.5_

- [x] 3. Satın alma yönetim servislerini oluştur

  - utils/satin_alma_servisleri.py dosyasını oluştur
  - SatinAlmaServisi sınıfını implement et
  - Sipariş CRUD operasyonlarını ekle
  - Otomatik sipariş önerisi algoritmasını ekle
  - _Gereksinimler: 3.1, 3.2, 4.1, 7.1_

- [x] 3.1 Sipariş oluşturma ve yönetim fonksiyonlarını implement et

  - siparis_olustur() metodunu yaz
  - siparis_no_uret() yardımcı fonksiyonunu yaz
  - siparis_durum_guncelle() metodunu yaz
  - siparis_listele() metodunu yaz
  - _Gereksinimler: 3.1, 3.2, 3.3, 4.1_

- [x] 3.2 Otomatik sipariş önerisi algoritmasını implement et

  - otomatik_siparis_onerisi_olustur() metodunu yaz
  - Kritik stok seviyesi kontrolü
  - Son 30 günlük tüketim analizi
  - Önerilen miktar hesaplama
  - _Gereksinimler: 7.1, 7.2, 7.3_

- [x] 3.3 Stok giriş entegrasyonu fonksiyonlarını implement et

  - stok_giris_olustur() metodunu yaz
  - Sipariş ile stok girişi bağlantısı
  - Birim maliyet güncelleme
  - Kısmi teslimat desteği
  - _Gereksinimler: 5.1, 5.2, 5.3, 5.4_

- [x] 3.4 Geciken sipariş kontrolü ve bildirim fonksiyonlarını ekle

  - geciken_siparisler_kontrol() metodunu yaz
  - Tahmini teslimat tarihi kontrolü
  - Bildirim tetikleme
  - _Gereksinimler: 4.5, 6.3_

- [x] 4. Form sınıflarını oluştur

  - forms.py dosyasına yeni formları ekle
  - Validasyon kurallarını tanımla
  - _Gereksinimler: 1.1, 2.1, 3.1, 10.1_

- [x] 4.1 Tedarikçi yönetim formlarını oluştur

  - TedarikciForm sınıfını yaz
  - UrunTedarikciFiyatForm sınıfını yaz
  - TedarikciIletisimForm sınıfını yaz
  - _Gereksinimler: 1.1, 2.1, 10.1_

- [x] 4.2 Satın alma formlarını oluştur

  - SatinAlmaSiparisForm sınıfını yaz
  - SiparisStokGirisForm sınıfını yaz
  - Dinamik ürün satırları için JavaScript desteği
  - _Gereksinimler: 3.1, 5.1_

- [x] 5. Sistem yöneticisi route'larını oluştur

  - routes/sistem_yoneticisi_routes.py dosyasını güncelle
  - Tedarikçi yönetim endpoint'lerini ekle
  - Fiyat yönetim endpoint'lerini ekle
  - _Gereksinimler: 1.1, 2.1, 2.2, 8.1_

- [x] 5.1 Tedarikçi CRUD route'larını implement et

  - /tedarikci-yonetimi route'unu ekle (GET, POST)
  - /tedarikci-duzenle/<id> route'unu ekle (GET, POST)
  - /tedarikci-pasif-yap/<id> route'unu ekle (POST)
  - /tedarikci-aktif-yap/<id> route'unu ekle (POST)
  - _Gereksinimler: 1.1, 1.2, 1.3, 1.4_

- [x] 5.2 Ürün-tedarikçi fiyat yönetim route'larını implement et

  - /urun-tedarikci-fiyat route'unu ekle (GET, POST)
  - /fiyat-karsilastirma/<urun_id> route'unu ekle (GET)
  - /fiyat-guncelle/<id> route'unu ekle (POST)
  - _Gereksinimler: 2.1, 2.2, 2.3, 8.1_

- [x] 5.3 Tedarikçi performans route'larını implement et

  - /tedarikci-performans/<id> route'unu ekle (GET)
  - /tedarikci-performans-raporu route'unu ekle (GET)
  - _Gereksinimler: 6.1, 6.2, 6.4_

- [x] 6. Depo sorumlusu route'larını oluştur

  - routes/depo_sorumlusu_routes.py dosyasını güncelle
  - Satın alma sipariş endpoint'lerini ekle
  - Stok giriş entegrasyon endpoint'lerini ekle
  - _Gereksinimler: 3.1, 4.1, 5.1, 7.1_

- [x] 6.1 Satın alma sipariş route'larını implement et

  - /satin-alma-siparis route'unu ekle (GET, POST)
  - /siparis-listesi route'unu ekle (GET)
  - /siparis-detay/<id> route'unu ekle (GET)
  - /siparis-durum-guncelle/<id> route'unu ekle (POST)
  - _Gereksinimler: 3.1, 3.2, 3.3, 4.1, 4.2_

- [x] 6.2 Stok giriş entegrasyon route'larını implement et

  - /siparis-stok-giris/<id> route'unu ekle (GET, POST)
  - Sipariş bilgilerini otomatik form doldurma
  - Stok güncelleme entegrasyonu
  - _Gereksinimler: 5.1, 5.2, 5.3, 5.4_

- [x] 6.3 Otomatik sipariş önerileri route'larını implement et

  - /otomatik-siparis-onerileri route'unu ekle (GET)
  - /siparis-onerisi-onayla route'unu ekle (POST)
  - _Gereksinimler: 7.1, 7.2, 7.3, 7.4_

- [x] 6.4 Tedarikçi iletişim ve belge yönetimi route'larını implement et

  - /tedarikci-iletisim/<id> route'unu ekle (GET, POST)
  - /tedarikci-dokuman-yukle route'unu ekle (POST)
  - /tedarikci-dokuman-indir/<id> route'unu ekle (GET)
  - _Gereksinimler: 10.1, 10.2, 10.3, 10.4_

- [x] 7. Sistem yöneticisi template'lerini oluştur

  - templates/sistem_yoneticisi/ klasörüne yeni template'ler ekle
  - Tedarikçi yönetim sayfalarını oluştur
  - Fiyat yönetim sayfalarını oluştur
  - _Gereksinimler: 1.1, 2.1, 6.1, 8.1_

- [x] 7.1 Tedarikçi yönetim template'lerini oluştur

  - tedarikci_yonetimi.html (liste + form)
  - tedarikci_duzenle.html
  - tedarikci_performans.html
  - _Gereksinimler: 1.1, 1.2, 1.3, 6.1_

- [x] 7.2 Fiyat yönetim template'lerini oluştur

  - urun_tedarikci_fiyat.html
  - fiyat_karsilastirma.html
  - _Gereksinimler: 2.1, 2.2, 2.3_

- [x] 8. Depo sorumlusu template'lerini oluştur

  - templates/depo_sorumlusu/ klasörüne yeni template'ler ekle
  - Satın alma sipariş sayfalarını oluştur
  - Stok giriş sayfalarını oluştur
  - _Gereksinimler: 3.1, 4.1, 5.1, 7.1_

- [x] 8.1 Satın alma sipariş template'lerini oluştur

  - satin_alma_siparis.html (form)
  - siparis_listesi.html
  - siparis_detay.html
  - _Gereksinimler: 3.1, 3.2, 3.3, 4.1_

- [x] 8.2 Stok giriş entegrasyon template'lerini oluştur

  - siparis_stok_giris.html
  - Otomatik form doldurma JavaScript'i
  - _Gereksinimler: 5.1, 5.2, 5.3_

- [x] 8.3 Otomatik sipariş önerileri template'ini oluştur

  - otomatik_siparis_onerileri.html
  - Öneri kartları ve onaylama butonları
  - _Gereksinimler: 7.1, 7.2, 7.3_

- [x] 8.4 Tedarikçi iletişim ve belge yönetimi template'lerini oluştur

  - tedarikci_iletisim.html
  - Belge yükleme ve listeleme arayüzü
  - _Gereksinimler: 10.1, 10.2, 10.3_

- [x] 9. Email bildirim sistemini entegre et

  - utils/email_servisi.py dosyasını güncelle
  - Sipariş bildirimi email template'i oluştur
  - Gecikme uyarısı email template'i oluştur
  - _Gereksinimler: 3.5, 4.5, 6.5_

- [x] 9.1 Email servis fonksiyonlarını implement et

  - siparis_bildirimi_gonder() metodunu yaz
  - gecikme_uyarisi_gonder() metodunu yaz
  - Email template'lerini oluştur
  - _Gereksinimler: 3.5, 4.5_

- [x] 10. Dashboard bildirimlerini ekle

  - Dashboard'a kritik stok uyarıları ekle
  - Geciken sipariş bildirimleri ekle
  - Onay bekleyen sipariş sayacı ekle
  - _Gereksinimler: 7.3, 4.5_

- [x] 10.1 Dashboard bildirim fonksiyonlarını implement et

  - get_dashboard_bildirimleri() fonksiyonunu yaz
  - Sistem yöneticisi dashboard'unu güncelle
  - Depo sorumlusu dashboard'unu güncelle
  - _Gereksinimler: 7.3, 4.5_

- [x] 11. Raporlama fonksiyonlarını implement et

  - Tedarikçi performans raporu
  - Satın alma özet raporu
  - Fiyat trend analizi raporu
  - _Gereksinimler: 6.1, 6.2, 8.1, 8.2_

- [x] 11.1 Tedarikçi performans raporu fonksiyonlarını yaz

  - tedarikci_performans_raporu() fonksiyonunu implement et
  - Grafik ve tablo görselleştirmeleri
  - _Gereksinimler: 6.1, 6.2, 6.4_

- [x] 11.2 Satın alma özet raporu fonksiyonlarını yaz

  - satin_alma_ozet_raporu() fonksiyonunu implement et
  - Tedarikçi ve ürün bazında analizler
  - _Gereksinimler: 8.1, 8.2_

- [x] 12. Excel içe/dışa aktarma fonksiyonlarını implement et

  - Toplu sipariş Excel yükleme
  - Excel şablon oluşturma
  - Rapor Excel export
  - _Gereksinimler: 9.1, 9.2, 9.3_

- [x] 12.1 Toplu sipariş Excel yükleme fonksiyonlarını yaz

  - toplu_siparis_yukle() fonksiyonunu implement et
  - Excel validasyon ve parsing
  - Hata raporlama
  - _Gereksinimler: 9.1, 9.2, 9.3, 9.4, 9.5_

-

- [x] 13. Güvenlik ve yetkilendirme kontrollerini ekle

  - Rol bazlı erişim kontrollerini test et
  - Otel bazlı veri izolasyonunu doğrula
  - CSRF korumasını test et
  - _Gereksinimler: Tüm route'lar_

- [x] 13.1 Güvenlik testlerini yaz ve çalıştır

  - Yetkilendirme testleri
  - Input validasyon testleri
  - Dosya yükleme güvenlik testleri
  - _Gereksinimler: Tüm modül_

- [x] 14. Performans optimizasyonlarını uygula

  - Veritabanı indekslerini ekle
  - Sorgu optimizasyonlarını yap
  - Cache mekanizmalarını entegre et
  - _Gereksinimler: Tüm modül_

- [x] 14.1 Veritabanı optimizasyonlarını uygula

  - İndeksleri ekle ve test et
  - Eager loading optimizasyonları
  - Pagination implementasyonu
  - _Gereksinimler: Tüm veri modelleri_

- [x] 14.2 Cache mekanizmalarını entegre et

  - Tedarikçi performans cache'i
  - Fiyat karşılaştırma cache'i
  - Cache invalidation stratejisi
  - _Gereksinimler: Performans kritik fonksiyonlar_

- [ ]\* 15. Test suite'ini oluştur ve çalıştır

  - Birim testleri yaz
  - Entegrasyon testleri yaz
  - UI testleri yaz
  - _Gereksinimler: Tüm modül_

- [ ]\* 15.1 Birim testlerini yaz

  - TedarikciServisi testleri
  - SatinAlmaServisi testleri
  - Form validasyon testleri
  - _Gereksinimler: Servis katmanı_

- [ ]\* 15.2 Entegrasyon testlerini yaz

  - Sipariş -> Stok giriş akış testi
  - Fiyatlandırma entegrasyon testi
  - Otomatik sipariş önerisi akış testi
  - _Gereksinimler: Tüm modül_

- [ ] 16. Dokümantasyon ve kullanım kılavuzu oluştur

  - Kullanıcı kılavuzu yaz
  - API dokümantasyonu oluştur
  - Sistem yöneticisi için kurulum kılavuzu
  - _Gereksinimler: Tüm modül_

- [ ] 16.1 Kullanıcı kılavuzunu yaz
  - Tedarikçi yönetimi kılavuzu
  - Satın alma süreçleri kılavuzu
  - Raporlama kılavuzu
  - _Gereksinimler: Tüm modül_
