# Setup Bazlı Minibar Kontrol Sistemi - Gereksinimler

## Giriş

Bu sistem, minibar kontrol ve dolum işlemlerini tamamen yeniden yapılandırır. Artık her oda tipinin setup'ları (dolap içi/dışı) tanımlı olduğuna göre, kat sorumlusu oda seçtiğinde o odanın setup'larına göre otomatik olarak bulunması gereken ürünler ve miktarlar listelenir. İlk dolum, ek dolum gibi kavramlar kaldırılır; bunların yerine setup-bazlı kontrol ve tüketim takibi gelir.

## Sözlük

- **Sistem**: Minibar Takip Sistemi
- **Kat Sorumlusu**: Otelde belirli bir kattan sorumlu olan ve minibar kontrol işlemlerini yöneten personel
- **Oda Tipi**: Odaların kategorisi (örn: Standart, Deluxe, Suite)
- **Setup**: Bir oda tipine tanımlı ürün grubu (dolap içi veya dolap dışı)
- **Dolap İçi Setup**: Minibar dolabının içinde bulunması gereken ürünler ve miktarları
- **Dolap Dışı Setup**: Minibar dolabının dışında (oda içinde) bulunması gereken ürünler ve miktarları
- **Setup Miktarı**: Bir setup'ta tanımlı olan standart ürün miktarı
- **Tüketim**: Setup miktarından eksik olan miktar (setup miktarı - mevcut miktar)
- **Ekstra Miktar**: Setup miktarının üzerinde odaya eklenen ürün miktarı
- **Kat Sorumlusu Stoğu**: Kat sorumlusunun zimmetinde olan ürün stoğu
- **Accordion**: Açılır-kapanır liste yapısı

## Gereksinimler

### Gereksinim 1: Oda Seçimi ve Setup Listeleme

**Kullanıcı Hikayesi:** Kat sorumlusu olarak, minibar kontrolünde oda seçtiğimde o odanın oda tipine göre tüm setup'larını accordion yapısında görmek istiyorum, böylece hangi ürünlerin bulunması gerektiğini hızlıca görebilirim.

#### Kabul Kriterleri

1. WHEN Kat Sorumlusu minibar kontrol sayfasında bir oda seçtiğinde, THE Sistem SHALL seçilen odanın oda tipini belirler
2. WHEN Sistem oda tipini belirlediğinde, THE Sistem SHALL o oda tipine tanımlı tüm setup'ları (dolap içi ve dolap dışı) accordion yapısında listeler
3. THE Sistem SHALL her setup için setup adını, dolap sayısını ve toplam ürün çeşit sayısını accordion başlığında gösterir
4. WHILE accordion kapalıyken, THE Sistem SHALL sadece setup başlık bilgilerini gösterir
5. WHEN Kat Sorumlusu bir accordion'a tıkladığında, THE Sistem SHALL o setup'ın içeriğini (ürünler ve miktarlar) açarak gösterir

### Gereksinim 2: Setup İçeriği Görüntüleme

**Kullanıcı Hikayesi:** Kat sorumlusu olarak, bir setup'a tıkladığımda o setup'taki tüm ürünleri, bulunması gereken miktarları ve mevcut durumu görmek istiyorum, böylece hangi ürünlerin eksik olduğunu anlayabilirim.

#### Kabul Kriterleri

1. WHEN Kat Sorumlusu bir setup accordion'ını açtığında, THE Sistem SHALL o setup'taki tüm ürünleri tablo formatında listeler
2. THE Sistem SHALL her ürün için şu bilgileri gösterir: ürün adı, birim, setup miktarı, mevcut miktar, durum
3. THE Sistem SHALL mevcut miktarı setup miktarı ile karşılaştırarak durum gösterir (Tam, Eksik, Fazla)
4. WHERE mevcut miktar setup miktarından azsa, THE Sistem SHALL o satırı sarı renkle vurgular ve "Eksik" durumu gösterir
5. WHERE mevcut miktar setup miktarından fazlaysa, THE Sistem SHALL o satırı mavi renkle vurgular ve "Ekstra Var" durumu gösterir
6. WHERE mevcut miktar setup miktarına eşitse, THE Sistem SHALL o satırı yeşil renkle vurgular ve "Tam" durumu gösterir

### Gereksinim 3: Ürün Ekleme İşlemi

**Kullanıcı Hikayesi:** Kat sorumlusu olarak, eksik olan bir ürünün yanındaki "Ekle" butonuna tıklayarak o ürünü setup miktarına tamamlamak istiyorum, böylece minibar'ı standart duruma getirebilirim.

#### Kabul Kriterleri

1. WHEN Kat Sorumlusu bir ürünün yanındaki "Ekle" butonuna tıkladığında, THE Sistem SHALL ürün ekleme modalını açar
2. THE Sistem SHALL modal içinde ürün adını, birimini, setup miktarını ve mevcut miktarı gösterir
3. THE Sistem SHALL modal içinde "Eklenecek Miktar" için sayısal input alanı sunar
4. THE Sistem SHALL modal içinde Kat Sorumlusunun zimmetindeki o ürünün stok miktarını gösterir
5. THE Sistem SHALL modal içinde "İptal" ve "Kaydet" butonlarını gösterir
6. WHEN Kat Sorumlusu eklenecek miktarı girip "Kaydet"e bastığında, THE Sistem SHALL zimmet stoğundan girilen miktarı düşer
7. THE Sistem SHALL eksik miktarı (setup miktarı - mevcut miktar) tüketim olarak kaydeder
8. THE Sistem SHALL odanın o ürün için mevcut miktarını setup miktarına eşitler
9. IF eklenecek miktar zimmet stoğundan fazlaysa, THEN THE Sistem SHALL "Zimmetinizde yeterli stok bulunmamaktadır" hata mesajı gösterir

### Gereksinim 4: Tüketim Hesaplama ve Kaydetme

**Kullanıcı Hikayesi:** Kat sorumlusu olarak, ürün eklediğimde sistemin otomatik olarak tüketimi hesaplamasını ve kaydetmesini istiyorum, böylece misafir faturasına doğru yansıtılır.

#### Kabul Kriterleri

1. WHEN Kat Sorumlusu ürün ekleme işlemini tamamladığında, THE Sistem SHALL tüketim miktarını hesaplar (setup miktarı - önceki mevcut miktar)
2. THE Sistem SHALL hesaplanan tüketimi minibar_tuketim tablosuna kaydeder
3. THE Sistem SHALL tüketim kaydında şu bilgileri saklar: oda_id, urun_id, miktar, tarih, kat_sorumlusu_id
4. THE Sistem SHALL tüketim kaydını o odanın aktif rezervasyonuna bağlar
5. WHERE tüketim miktarı sıfırdan büyükse, THE Sistem SHALL bu tüketimi misafir faturasına yansıtır
6. THE Sistem SHALL işlem sonrası başarı mesajı gösterir ve setup listesini günceller

### Gereksinim 5: Ekstra Ürün Ekleme

**Kullanıcı Hikayesi:** Kat sorumlusu olarak, misafir talebi üzerine setup miktarının üzerinde ürün eklemek istiyorum, böylece misafir ihtiyaçlarını karşılayabilirim.

#### Kabul Kriterleri

1. WHEN Kat Sorumlusu bir ürünün yanındaki "Ekstra" butonuna tıkladığında, THE Sistem SHALL ekstra ürün ekleme modalını açar
2. THE Sistem SHALL modal içinde ürün adını, birimini, setup miktarını ve mevcut miktarı gösterir
3. THE Sistem SHALL modal içinde "Ekstra Eklenecek Miktar" için sayısal input alanı sunar
4. THE Sistem SHALL modal içinde Kat Sorumlusunun zimmetindeki o ürünün stok miktarını gösterir
5. WHEN Kat Sorumlusu ekstra miktarı girip "Kaydet"e bastığında, THE Sistem SHALL zimmet stoğundan girilen miktarı düşer
6. THE Sistem SHALL ekstra miktarı tüketim olarak KAYDETMEZ
7. THE Sistem SHALL ekstra miktarı o ürün için geçici olarak saklar (ekstra_miktar alanında)
8. THE Sistem SHALL odanın o ürün için mevcut miktarını (setup miktarı + ekstra miktar) olarak günceller
9. THE Sistem SHALL bir sonraki kontrolde ekstra miktarı görünür şekilde gösterir

### Gereksinim 6: Ekstra Ürün Tüketimi ve Sıfırlama

**Kullanıcı Hikayesi:** Kat sorumlusu olarak, bir önceki kontrolde ekstra eklenen ürünlerin tüketilip tüketilmediğini görmek ve tüketildiyse sıfırlamak istiyorum, böylece ekstra ürünler de doğru şekilde faturalandırılır.

#### Kabul Kriterleri

1. WHEN Kat Sorumlusu bir setup'ı açtığında ve o üründe ekstra miktar varsa, THE Sistem SHALL ekstra miktarı ayrı bir sütunda gösterir
2. THE Sistem SHALL ekstra miktarı olan ürünlerin yanında "Sıfırla" butonu gösterir
3. WHEN Kat Sorumlusu "Sıfırla" butonuna tıkladığında, THE Sistem SHALL onay modalı açar
4. THE Sistem SHALL onay modalında "Ekstra [X] adet [Ürün Adı] tüketildi mi?" sorusunu gösterir
5. WHEN Kat Sorumlusu onayladığında, THE Sistem SHALL ekstra miktarı tüketim olarak kaydeder
6. THE Sistem SHALL ekstra_miktar alanını sıfırlar
7. THE Sistem SHALL odanın o ürün için mevcut miktarını setup miktarına geri döndürür
8. WHERE ekstra miktar sıfırlanmazsa, THE Sistem SHALL bir sonraki kontrolde yine ekstra miktarı gösterir

### Gereksinim 7: Eski Sistem Fonksiyonlarının Kaldırılması

**Kullanıcı Hikayesi:** Sistem yöneticisi olarak, artık kullanılmayan ilk dolum ve ek dolum fonksiyonlarının sistemden kaldırılmasını istiyorum, böylece sistem daha sade ve anlaşılır olur.

#### Kabul Kriterleri

1. THE Sistem SHALL "İlk Dolum" menü öğesini Kat Sorumlusu, Depo Sorumlusu ve Sistem Yöneticisi panellerinden kaldırır
2. THE Sistem SHALL "Ek Dolum" ile ilgili tüm menü öğelerini ve sayfaları kaldırır
3. THE Sistem SHALL ilk_dolum ve ek_dolum ile ilgili route'ları kaldırır
4. THE Sistem SHALL ilk_dolum ve ek_dolum ile ilgili template dosyalarını kaldırır
5. THE Sistem SHALL ilk_dolum ve ek_dolum ile ilgili JavaScript fonksiyonlarını kaldırır
6. WHERE veritabanında ilk_dolum ve ek_dolum kayıtları varsa, THE Sistem SHALL bu kayıtları korur (geçmiş veri için)
7. THE Sistem SHALL minibar kontrol sayfasını tek giriş noktası olarak kullanır

### Gereksinim 8: Responsive Tasarım ve Kullanıcı Deneyimi

**Kullanıcı Hikayesi:** Kat sorumlusu olarak, minibar kontrol sayfasını mobil cihazlarda da rahatça kullanmak istiyorum, böylece odada kontrol yaparken tablet veya telefonumdan işlem yapabilirim.

#### Kabul Kriterleri

1. THE Sistem SHALL minibar kontrol sayfasını responsive tasarım ile oluşturur
2. WHERE ekran genişliği 768px'den küçükse, THE Sistem SHALL accordion'ları tam genişlikte gösterir
3. WHERE ekran genişliği 768px'den küçükse, THE Sistem SHALL tablo sütunlarını dikey düzende gösterir
4. THE Sistem SHALL butonları dokunmatik ekranlar için yeterli boyutta (minimum 44x44px) oluşturur
5. THE Sistem SHALL modal pencerelerini mobil ekranlarda tam ekran olarak gösterir
6. THE Sistem SHALL yükleme durumlarında loading spinner gösterir
7. THE Sistem SHALL tüm işlemlerde kullanıcıya görsel geri bildirim (toast mesajları) verir

### Gereksinim 9: Güvenlik ve Yetkilendirme

**Kullanıcı Hikayesi:** Sistem yöneticisi olarak, minibar kontrol işlemlerinin sadece yetkili personel tarafından yapılmasını istiyorum, böylece sistem güvenliği sağlanır.

#### Kabul Kriterleri

1. THE Sistem SHALL tüm minibar kontrol route'larını @login_required decorator ile korur
2. THE Sistem SHALL minibar kontrol sayfasına sadece "Kat Sorumlusu" rolündeki kullanıcıların erişmesine izin verir
3. THE Sistem SHALL her işlemde CSRF token kontrolü yapar
4. THE Sistem SHALL her işlemi audit_trail tablosuna kaydeder
5. THE Sistem SHALL zimmet stok kontrollerini transaction içinde yapar
6. IF yetkisiz erişim denemesi olursa, THEN THE Sistem SHALL 403 Forbidden hatası döner ve girişimi loglar
7. THE Sistem SHALL rate limiting uygular (dakikada maksimum 60 istek)

### Gereksinim 10: Raporlama ve İzleme

**Kullanıcı Hikayesi:** Sistem yöneticisi olarak, minibar kontrol işlemlerini ve tüketim istatistiklerini raporlayabilmek istiyorum, böylece sistem performansını ve ürün tüketimlerini analiz edebilirim.

#### Kabul Kriterleri

1. THE Sistem SHALL her minibar kontrol işlemini tarih, saat, kat sorumlusu ve oda bilgileriyle kaydeder
2. THE Sistem SHALL günlük, haftalık ve aylık tüketim raporları oluşturur
3. THE Sistem SHALL en çok tüketilen ürünleri listeler
4. THE Sistem SHALL oda tiplerine göre tüketim karşılaştırması yapar
5. THE Sistem SHALL kat sorumlularının performans istatistiklerini gösterir
6. WHERE Sistem Yöneticisi rapor sayfasını açtığında, THE Sistem SHALL grafik ve tablo formatında verileri gösterir
7. THE Sistem SHALL raporları Excel ve PDF formatında dışa aktarma imkanı sunar

## Teknik Notlar

### Veritabanı Değişiklikleri

Yeni alan eklenecek:

```python
# minibar_zimmet_detay tablosuna
ekstra_miktar = db.Column(db.Integer, default=0)  # Setup üstü eklenen miktar
```

### API Endpoint'leri

```
GET /api/kat-sorumlusu/oda-setup/<oda_id>
POST /api/kat-sorumlusu/urun-ekle
POST /api/kat-sorumlusu/ekstra-ekle
POST /api/kat-sorumlusu/ekstra-sifirla
```

### Kaldırılacak Dosyalar

- templates/kat_sorumlusu/ilk_dolum.html
- templates/kat_sorumlusu/ek_dolum.html
- templates/depo*sorumlusu/ilk_dolum*\*.html
- templates/sistem*yoneticisi/ilk_dolum*\*.html
- İlgili route fonksiyonları
- İlgili JavaScript dosyaları

## Başarı Kriterleri

1. Kat sorumlusu oda seçtiğinde setup'lar 2 saniyeden kısa sürede listelenir
2. Ürün ekleme işlemi 1 saniyeden kısa sürede tamamlanır
3. Sistem %99.9 uptime sağlar
4. Tüm işlemler audit trail'e kaydedilir
5. Mobil cihazlarda sorunsuz çalışır
6. Eski ilk dolum/ek dolum fonksiyonları tamamen kaldırılır
