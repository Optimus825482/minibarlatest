# Fiyatlandırma ve Karlılık Hesaplama Sistemi - Gereksinimler

## Giriş

Mini bar stok takip sistemine kapsamlı fiyatlandırma yönetimi ve karlılık analizi yetenekleri ekleyen modül. Sistem, tedarikçi bazlı alış fiyatları, dinamik satış fiyatları, kampanya yönetimi, bedelsiz tanımlama ve gerçek zamanlı karlılık hesaplamaları sağlayacak.

## Sözlük

- **Sistem**: Mini Bar Stok Takip Sistemi
- **Tedarikçi**: Ürün temin edilen firma
- **Alış Fiyatı**: Tedarikçiden ürün alım maliyeti
- **Satış Fiyatı**: Misafire satış bedeli
- **Oda Tipi**: Standard, Deluxe, Suite gibi oda kategorileri
- **Kampanya**: İndirim veya promosyon tanımı
- **Bedelsiz**: Ücretsiz tüketim limiti
- **Karlılık**: Satış fiyatı ile alış fiyatı arasındaki fark
- **ROI**: Yatırım getirisi (Return on Investment)
- **Sezon**: Fiyatlandırma dönemleri (Yaz, Kış, Bayram vb.)
- **ML Sistemi**: Machine Learning anomali tespit sistemi
- **Zimmet**: Personel stok sorumluluğu

---

## Gereksinimler

### Gereksinim 1: Tedarikçi Yönetimi

**Kullanıcı Hikayesi:** Sistem Yöneticisi olarak, ürünleri temin ettiğim tedarikçileri yönetebilmek istiyorum, böylece fiyat karşılaştırması yapabilir ve en uygun tedarikçiyi seçebilirim.

#### Kabul Kriterleri

1. WHEN Sistem Yöneticisi yeni tedarikçi ekler, THE Sistem SHALL tedarikçi bilgilerini (ad, iletişim, adres) veritabanına kaydetmek
2. WHEN Sistem Yöneticisi tedarikçi listesini görüntüler, THE Sistem SHALL tüm aktif tedarikçileri alfabetik sırada listelemek
3. WHEN Sistem Yöneticisi tedarikçi bilgilerini günceller, THE Sistem SHALL değişiklikleri audit log'a kaydetmek
4. WHEN Sistem Yöneticisi tedarikçiyi pasif yapar, THE Sistem SHALL tedarikçiye ait aktif fiyatları da pasif duruma getirmek
5. THE Sistem SHALL her tedarikçi için iletişim bilgilerini JSON formatında saklamak

### Gereksinim 2: Ürün Alış Fiyatı Yönetimi

**Kullanıcı Hikayesi:** Depo Sorumlusu olarak, her ürün için tedarikçi bazlı alış fiyatlarını tanımlayabilmek istiyorum, böylece maliyet takibi yapabilir ve karlılık hesaplayabilirim.

#### Kabul Kriterleri

1. WHEN Depo Sorumlusu ürüne alış fiyatı tanımlar, THE Sistem SHALL fiyatı tedarikçi ile ilişkilendirerek kaydetmek
2. WHEN Depo Sorumlusu fiyat günceller, THE Sistem SHALL eski fiyatı geçmişe taşımak ve yeni fiyatı aktif etmek
3. WHEN Depo Sorumlusu fiyat geçmişini görüntüler, THE Sistem SHALL tüm fiyat değişikliklerini tarih sırasıyla listelemek
4. THE Sistem SHALL her fiyat değişikliği için değişiklik sebebini ve yapan kullanıcıyı kaydetmek
5. WHEN birden fazla tedarikçi fiyatı varsa, THE Sistem SHALL en düşük fiyatlı tedarikciyi öneride bulunmak

### Gereksinim 3: Dinamik Satış Fiyatı Sistemi

**Kullanıcı Hikayesi:** Admin olarak, farklı oda tiplerine göre farklı satış fiyatları belirleyebilmek istiyorum, böylece oda kategorisine göre karlılık optimize edebilirim.

#### Kabul Kriterleri

1. WHEN Admin oda tipi için satış fiyatı tanımlar, THE Sistem SHALL fiyatı ürün ve oda tipi ile ilişkilendirerek kaydetmek
2. WHEN misafir tüketim yapar, THE Sistem SHALL odanın tipine göre doğru satış fiyatını uygulamak
3. THE Sistem SHALL Standard, Deluxe ve Suite oda tipleri için farklı fiyat çarpanlarını desteklemek
4. WHEN oda tipi fiyatı tanımlı değilse, THE Sistem SHALL varsayılan satış fiyatını kullanmak
5. WHEN Admin fiyat geçerlilik tarihi belirler, THE Sistem SHALL sadece geçerli tarih aralığındaki fiyatları uygulamak

### Gereksinim 4: Sezonluk Fiyatlandırma

**Kullanıcı Hikayesi:** Admin olarak, sezonlara göre fiyat çarpanları belirleyebilmek istiyorum, böylece yoğun dönemlerde karlılığı artırabilirim.

#### Kabul Kriterleri

1. WHEN Admin sezon tanımlar, THE Sistem SHALL sezon adı, başlangıç ve bitiş tarihlerini kaydetmek
2. WHEN Admin sezon için fiyat çarpanı belirler, THE Sistem SHALL çarpanı 0.5 ile 3.0 arasında kabul etmek
3. WHEN tüketim tarihi sezon içindeyse, THE Sistem SHALL satış fiyatına sezon çarpanını uygulamak
4. WHEN birden fazla sezon çakışırsa, THE Sistem SHALL en yüksek çarpanlı sezonu öncelikli kullanmak
5. THE Sistem SHALL sezon dışı dönemlerde normal fiyatları uygulamak

### Gereksinim 5: Kampanya Yönetimi

**Kullanıcı Hikayesi:** Admin olarak, promosyon kampanyaları oluşturabilmek istiyorum, böylece satışları artırabilir ve müşteri memnuniyetini sağlayabilirim.

#### Kabul Kriterleri

1. WHEN Admin kampanya oluşturur, THE Sistem SHALL kampanya adı, tarih aralığı ve indirim bilgilerini kaydetmek
2. THE Sistem SHALL yüzde ve tutar bazlı indirim tiplerini desteklemek
3. WHEN kampanya minimum sipariş miktarı içeriyorsa, THE Sistem SHALL sadece koşul sağlandığında indirimi uygulamak
4. WHEN kampanya kullanım limiti dolduğunda, THE Sistem SHALL kampanyayı otomatik pasif duruma getirmek
5. WHEN tüketimde kampanya uygulanır, THE Sistem SHALL kampanya ID'sini işlem detayına kaydetmek

### Gereksinim 6: Bedelsiz Limit Sistemi

**Kullanıcı Hikayesi:** Admin olarak, odalara bedelsiz tüketim limitleri tanımlayabilmek istiyorum, böylece VIP misafirlere özel hizmet sunabilir ve kampanya yönetebilirim.

#### Kabul Kriterleri

1. WHEN Admin odaya bedelsiz limit tanımlar, THE Sistem SHALL ürün, miktar ve geçerlilik tarihlerini kaydetmek
2. THE Sistem SHALL misafir, kampanya ve personel bazlı limit tiplerini desteklemek
3. WHEN misafir bedelsiz limit dahilinde tüketim yapar, THE Sistem SHALL kullanılan miktarı limitten düşmek
4. WHEN bedelsiz limit aşılırsa, THE Sistem SHALL aşan miktarı normal fiyattan hesaplamak
5. THE Sistem SHALL her bedelsiz kullanımı log tablosuna kaydetmek

### Gereksinim 7: Gerçek Zamanlı Karlılık Hesaplama

**Kullanıcı Hikayesi:** Admin olarak, her işlemde gerçek zamanlı kar/zarar görebilmek istiyorum, böylece anlık finansal durumu takip edebilirim.

#### Kabul Kriterleri

1. WHEN tüketim işlemi kaydedilir, THE Sistem SHALL alış ve satış fiyatlarını kullanarak kar tutarını hesaplamak
2. THE Sistem SHALL kar oranını yüzde olarak hesaplayıp kaydetmek
3. WHEN işlem bedelsiz ise, THE Sistem SHALL kar tutarını negatif olarak kaydetmek
4. THE Sistem SHALL her işlem detayına alış fiyatı, satış fiyatı, kar tutarı ve kar oranı alanlarını eklemek
5. WHEN kampanya uygulanırsa, THE Sistem SHALL indirimli fiyat üzerinden karlılık hesaplamak

### Gereksinim 8: Dönemsel Kar Analizi

**Kullanıcı Hikayesi:** Admin olarak, günlük, haftalık ve aylık kar raporları görebilmek istiyorum, böylece performans trendlerini analiz edebilirim.

#### Kabul Kriterleri

1. WHEN Admin dönemsel rapor talep eder, THE Sistem SHALL seçilen tarih aralığı için toplam gelir, maliyet ve net karı hesaplamak
2. THE Sistem SHALL kar marjını yüzde olarak hesaplayıp göstermek
3. THE Sistem SHALL günlük, haftalık ve aylık dönem tiplerini desteklemek
4. WHEN rapor oluşturulur, THE Sistem SHALL sonuçları veritabanına kaydetmek
5. THE Sistem SHALL analiz verilerini JSON formatında detaylı olarak saklamak

### Gereksinim 9: Ürün Bazlı Karlılık Analizi

**Kullanıcı Hikayesi:** Admin olarak, hangi ürünlerin daha karlı olduğunu görebilmek istiyorum, böylece stok ve fiyat stratejilerimi optimize edebilirim.

#### Kabul Kriterleri

1. WHEN Admin ürün karlılığı sorgular, THE Sistem SHALL ürünün toplam satış, maliyet ve kar bilgilerini hesaplamak
2. THE Sistem SHALL ürün bazlı kar marjını yüzde olarak göstermek
3. WHEN tarih aralığı belirtilirse, THE Sistem SHALL sadece o dönemdeki verileri kullanmak
4. THE Sistem SHALL en karlı ve en az karlı ürünleri sıralı listelemek
5. THE Sistem SHALL ürün trend analizini grafik olarak göstermek

### Gereksinim 10: ROI Hesaplama

**Kullanıcı Hikayesi:** Admin olarak, ürün ve kategori bazında yatırım getirisini görebilmek istiyorum, böylece hangi ürünlere yatırım yapacağıma karar verebilirim.

#### Kabul Kriterleri

1. WHEN Admin ROI hesaplama talep eder, THE Sistem SHALL toplam yatırım ve toplam geliri kullanarak ROI'yi hesaplamak
2. THE Sistem SHALL ROI'yi yüzde olarak göstermek
3. THE Sistem SHALL ürün, kategori ve otel bazında ROI hesaplamayı desteklemek
4. WHEN ROI negatifse, THE Sistem SHALL zarar durumunu açıkça belirtmek
5. THE Sistem SHALL ROI trendini zaman içinde grafik olarak göstermek

### Gereksinim 11: Tüketim Kalıbı Analizi

**Kullanıcı Hikayesi:** Admin olarak, ürün tüketim kalıplarını görebilmek istiyorum, böylece stok planlaması ve fiyatlandırma stratejisi geliştirebilirim.

#### Kabul Kriterleri

1. THE Sistem SHALL ürün bazında hangi günlerde daha çok tüketildiğini analiz etmek
2. THE Sistem SHALL saat aralıklarına göre tüketim dağılımını göstermek
3. THE Sistem SHALL oda tiplerine göre tüketim farklılıklarını analiz etmek
4. THE Sistem SHALL mevsimsel değişimleri yüzde olarak hesaplamak
5. THE Sistem SHALL tüketim kalıplarını JSON formatında saklamak

### Gereksinim 12: Ürün Trend Analizi

**Kullanıcı Hikayesi:** Admin olarak, ürün popülaritesi trendlerini görebilmek istiyorum, böylece yükselen ve düşen ürünleri tespit edebilirim.

#### Kabul Kriterleri

1. THE Sistem SHALL haftalık, aylık ve yıllık trend analizlerini desteklemek
2. WHEN trend analizi yapılır, THE Sistem SHALL önceki dönemle karşılaştırma yaparak değişim oranını hesaplamak
3. THE Sistem SHALL trend yönünü (yükselen, düşen, sabit) otomatik belirlemek
4. THE Sistem SHALL tüketim miktarı ve değerini ayrı ayrı analiz etmek
5. THE Sistem SHALL trend verilerini grafik olarak görselleştirmek

### Gereksinim 13: ML Sistemi Entegrasyonu - Gelir Anomalileri

**Kullanıcı Hikayesi:** Sistem Yöneticisi olarak, gelir anomalilerini otomatik tespit edebilmek istiyorum, böylece olağandışı durumları hızlıca fark edip müdahale edebilirim.

#### Kabul Kriterleri

1. THE Sistem SHALL oda bazlı gelir anomalilerini Z-Score algoritması ile tespit etmek
2. THE Sistem SHALL ürün bazlı gelir anomalilerini Isolation Forest algoritması ile analiz etmek
3. WHEN anomali tespit edildiğinde, THE Sistem SHALL uyarı seviyesini (Düşük, Orta, Yüksek, Kritik) belirlemek
4. THE Sistem SHALL anomali tespit sonuçlarını ml_alerts tablosuna kaydetmek
5. THE Sistem SHALL gelir anomalilerini dashboard'da görsel olarak göstermek

### Gereksinim 14: ML Sistemi Entegrasyonu - Karlılık Anomalileri

**Kullanıcı Hikayesi:** Sistem Yöneticisi olarak, karlılık anomalilerini otomatik tespit edebilmek istiyorum, böylece kar marjı düşüşlerini erken fark edebilirim.

#### Kabul Kriterleri

1. THE Sistem SHALL oda bazlı karlılık anomalilerini gerçek zamanlı izlemek
2. WHEN kar marjı beklenenden düşükse, THE Sistem SHALL kritik seviye uyarısı oluşturmak
3. THE Sistem SHALL ortalama sepet değeri anomalilerini tespit etmek
4. THE Sistem SHALL anomali tespit için son 30 günlük veriyi baseline olarak kullanmak
5. THE Sistem SHALL her anomali için öneride bulunmak (fiyat artırma, maliyet düşürme vb.)

### Gereksinim 15: Otomatik Fiyat Güncelleme Kuralları

**Kullanıcı Hikayesi:** Admin olarak, otomatik fiyat güncelleme kuralları tanımlayabilmek istiyorum, böylece manuel müdahale olmadan fiyatlar optimize edilebilsin.

#### Kabul Kriterleri

1. WHEN Admin otomatik kural tanımlar, THE Sistem SHALL kural tipini (otomatik_artir, otomatik_azalt, rakip_fiyat) kaydetmek
2. THE Sistem SHALL artırma ve azaltma oranlarını yüzde olarak desteklemek
3. WHEN kural aktifse, THE Sistem SHALL belirlenen periyotta otomatik fiyat güncellemesi yapmak
4. THE Sistem SHALL minimum ve maksimum fiyat sınırlarını kontrol etmek
5. THE Sistem SHALL her otomatik güncellemeyi audit log'a kaydetmek

### Gereksinim 16: Fiyat Geçmişi ve Audit Trail

**Kullanıcı Hikayesi:** Sistem Yöneticisi olarak, tüm fiyat değişikliklerinin geçmişini görebilmek istiyorum, böylece şeffaflık sağlayabilir ve hataları tespit edebilirim.

#### Kabul Kriterleri

1. WHEN fiyat değişikliği yapılır, THE Sistem SHALL eski ve yeni fiyatı geçmiş tablosuna kaydetmek
2. THE Sistem SHALL değişiklik tipini (alış_fiyatı, satış_fiyatı, kampanya) belirtmek
3. THE Sistem SHALL değişiklik sebebini ve yapan kullanıcıyı kaydetmek
4. THE Sistem SHALL fiyat geçmişini tarih sırasıyla filtrelenebilir şekilde listelemek
5. THE Sistem SHALL fiyat değişiklik trendlerini grafik olarak göstermek

### Gereksinim 17: Dashboard ve Raporlama

**Kullanıcı Hikayesi:** Admin olarak, tüm fiyatlandırma ve karlılık verilerini tek bir dashboard'da görebilmek istiyorum, böylece hızlı kararlar alabilirim.

#### Kabul Kriterleri

1. THE Sistem SHALL güncel kar/zarar durumunu özet kartlarda göstermek
2. THE Sistem SHALL en karlı ve en az karlı ürünleri listelemek
3. THE Sistem SHALL aktif kampanyaları ve kullanım oranlarını göstermek
4. THE Sistem SHALL trend grafiklerini Chart.js ile görselleştirmek
5. THE Sistem SHALL tüm raporları Excel formatında export edebilmek

### Gereksinim 18: Performans ve Optimizasyon

**Kullanıcı Hikayesi:** Sistem Yöneticisi olarak, fiyatlandırma hesaplamalarının hızlı çalışmasını istiyorum, böylece kullanıcı deneyimi olumsuz etkilenmesin.

#### Kabul Kriterleri

1. THE Sistem SHALL fiyat hesaplama işlemlerini 500ms altında tamamlamak
2. THE Sistem SHALL sık kullanılan fiyat verilerini Redis cache'de saklamak
3. THE Sistem SHALL veritabanı sorgularını optimize edilmiş indexler ile hızlandırmak
4. THE Sistem SHALL ağır analiz işlemlerini Celery ile asenkron çalıştırmak
5. THE Sistem SHALL cache hit oranını %95 üzerinde tutmak

### Gereksinim 19: Güvenlik ve Yetkilendirme

**Kullanıcı Hikayesi:** Sistem Yöneticisi olarak, fiyat yönetimi yetkilerini rol bazlı kontrol edebilmek istiyorum, böylece yetkisiz erişimleri engelleyebilirim.

#### Kabul Kriterleri

1. THE Sistem SHALL Sistem Yöneticisi rolüne tüm fiyat işlemlerine erişim vermek
2. THE Sistem SHALL Admin rolüne kampanya ve oda tipi fiyatlarına erişim vermek
3. THE Sistem SHALL Depo Sorumlusu rolüne sadece tedarikçi fiyatlarına erişim vermek
4. THE Sistem SHALL Kat Sorumlusu rolüne sadece görüntüleme yetkisi vermek
5. THE Sistem SHALL tüm fiyat değişikliklerini audit log'a kaydetmek

### Gereksinim 20: Veri Migrasyonu ve Geriye Dönük Uyumluluk

**Kullanıcı Hikayesi:** Sistem Yöneticisi olarak, mevcut verilerin yeni sisteme sorunsuz geçişini istiyorum, böylece veri kaybı yaşamadan sistemi güncelleyebilirim.

#### Kabul Kriterleri

1. THE Sistem SHALL mevcut ürünlere varsayılan alış ve satış fiyatları atamak
2. THE Sistem SHALL geçmiş işlemlere tarihsel fiyat hesaplaması yapmak
3. THE Sistem SHALL migration işlemini rollback edebilme yeteneğine sahip olmak
4. THE Sistem SHALL migration öncesi tam veritabanı yedeği almak
5. THE Sistem SHALL migration sonrası veri bütünlüğü kontrolü yapmak

### Gereksinim 21: Ürün Stok Takip Tablosu

**Kullanıcı Hikayesi:** Depo Sorumlusu olarak, her ürünün güncel stok miktarını ayrı bir tabloda görebilmek istiyorum, böylece stok durumunu hızlıca sorgulayabilir ve kritik stok seviyelerini takip edebilirim.

#### Kabul Kriterleri

1. THE Sistem SHALL her ürün için güncel stok miktarını ayrı bir tabloda saklamak
2. WHEN stok hareketi gerçekleştiğinde, THE Sistem SHALL stok tablosunu otomatik güncellemek
3. THE Sistem SHALL ürün bazında minimum stok seviyesi, maksimum stok seviyesi ve mevcut stok bilgilerini tutmak
4. WHEN stok kritik seviyenin altına düştüğünde, THE Sistem SHALL otomatik uyarı oluşturmak
5. THE Sistem SHALL stok değerini (miktar × alış fiyatı) hesaplayarak saklamak
6. THE Sistem SHALL son stok güncelleme tarihini ve güncelleyen kullanıcıyı kaydetmek
7. WHEN stok sorgulanır, THE Sistem SHALL 100ms altında yanıt vermek (performans)
8. THE Sistem SHALL otel bazında stok izolasyonu sağlamak
9. THE Sistem SHALL stok sayım işlemlerinde fark analizi yapabilmek
10. THE Sistem SHALL stok devir hızını hesaplayıp raporlayabilmek
