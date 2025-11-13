# Tedarikçi ve Satın Alma Modülü - Gereksinimler

## Giriş

Otel minibar yönetim sisteminde tedarikçi yönetimi ve satın alma süreçlerinin dijitalleştirilmesi için kapsamlı bir modül geliştirilmesi gerekmektedir. Mevcut sistemde tedarikçi veri modelleri bulunmakta ancak kullanıcı arayüzü ve satın alma süreç yönetimi eksiktir. Bu modül, stok yönetimi ile entegre çalışarak karlılık hesaplamalarının doğru yapılmasını sağlayacaktır.

## Sözlük (Glossary)

- **Sistem**: Otel Minibar Yönetim Sistemi
- **Tedarikçi**: Otele ürün tedarik eden firma
- **Satın Alma Siparişi**: Tedarikçiye verilen resmi sipariş belgesi
- **Teklif Talebi**: Tedarikçilerden fiyat teklifi alma süreci
- **Stok Girişi**: Satın alınan ürünlerin depoya fiziksel girişi
- **Minimum Stok Seviyesi**: Otomatik sipariş tetikleme eşiği
- **Tedarik Süresi**: Sipariş ile teslimat arası geçen süre
- **Sistem Yöneticisi**: Tüm otelleri yöneten üst düzey kullanıcı
- **Depo Sorumlusu**: Otel bazında stok ve satın alma yönetiminden sorumlu kullanıcı
- **Alış Fiyatı**: Tedarikçiden ürün satın alma maliyeti
- **Satış Fiyatı**: Misafire satılan ürün fiyatı
- **Kar Marjı**: Satış fiyatı ile alış fiyatı arasındaki fark yüzdesi

## Gereksinimler

### Gereksinim 1: Tedarikçi Tanımlama ve Yönetimi

**Kullanıcı Hikayesi:** Sistem yöneticisi olarak, tedarikçi bilgilerini sisteme ekleyip yönetebilmek istiyorum, böylece satın alma süreçlerinde doğru tedarikçi seçimi yapabilirim.

#### Kabul Kriterleri

1. WHEN Sistem_Yoneticisi tedarikçi ekleme formunu açtığında, THE Sistem SHALL tedarikçi adı, vergi numarası, telefon, email, adres ve ödeme koşulları alanlarını içeren formu gösterecektir
2. WHEN Sistem_Yoneticisi geçerli tedarikçi bilgilerini girip kaydet butonuna tıkladığında, THE Sistem SHALL tedarikçi kaydını veritabanına kaydedecek ve başarı mesajı gösterecektir
3. WHEN Sistem_Yoneticisi tedarikçi listesini görüntülediğinde, THE Sistem SHALL tüm aktif ve pasif tedarikçileri tablo formatında listeleyecektir
4. WHEN Sistem_Yoneticisi bir tedarikçiyi düzenleme moduna aldığında, THE Sistem SHALL mevcut tedarikçi bilgilerini form alanlarına dolduracak ve güncelleme imkanı sunacaktır
5. WHEN Sistem_Yoneticisi bir tedarikçiyi pasif yapmak istediğinde, THE Sistem SHALL tedarikçinin aktif siparişi olup olmadığını kontrol edecek ve uyarı verecektir

### Gereksinim 2: Ürün-Tedarikçi Fiyat Yönetimi

**Kullanıcı Hikayesi:** Depo sorumlusu olarak, her ürün için hangi tedarikçiden ne fiyata alabileceğimi görmek istiyorum, böylece en uygun maliyetli satın alma kararı verebilirim.

#### Kabul Kriterleri

1. WHEN Depo_Sorumlusu ürün-tedarikçi fiyat tanımlama sayfasını açtığında, THE Sistem SHALL ürün seçimi, tedarikçi seçimi, alış fiyatı, minimum sipariş miktarı ve geçerlilik tarihleri alanlarını içeren formu gösterecektir
2. WHEN Depo_Sorumlusu bir ürün için birden fazla tedarikçi fiyatı tanımladığında, THE Sistem SHALL her tedarikçi için ayrı kayıt oluşturacak ve fiyat karşılaştırma tablosu gösterecektir
3. WHEN Depo_Sorumlusu fiyat karşılaştırma tablosunu görüntülediğinde, THE Sistem SHALL en düşük fiyatlı tedarikçiyi yeşil renkle vurgulayacaktır
4. WHEN Depo_Sorumlusu bir tedarikçi fiyatını güncellemek istediğinde, THE Sistem SHALL eski fiyatı geçmiş kayıtlarına taşıyacak ve yeni fiyatı aktif edecektir
5. IF bir ürün için hiçbir aktif tedarikçi fiyatı yoksa, THEN THE Sistem SHALL satın alma siparişi oluşturulurken uyarı mesajı gösterecektir

### Gereksinim 3: Satın Alma Siparişi Oluşturma

**Kullanıcı Hikayesi:** Depo sorumlusu olarak, stok seviyesi düşen ürünler için satın alma siparişi oluşturmak istiyorum, böylece stok kesintisi yaşamadan tedarik sağlayabilirim.

#### Kabul Kriterleri

1. WHEN Depo_Sorumlusu satın alma siparişi oluşturma sayfasını açtığında, THE Sistem SHALL kritik stok seviyesinin altındaki ürünleri otomatik olarak önerecektir
2. WHEN Depo_Sorumlusu sipariş edilecek ürünleri seçtiğinde, THE Sistem SHALL her ürün için en uygun tedarikçiyi ve fiyatını otomatik olarak önerecektir
3. WHEN Depo_Sorumlusu sipariş miktarını girdiğinde, THE Sistem SHALL toplam tutarı, tahmini teslimat tarihini ve minimum sipariş miktarı uyarılarını gösterecektir
4. WHEN Depo_Sorumlusu siparişi onayladığında, THE Sistem SHALL sipariş kaydını "Beklemede" durumunda oluşturacak ve sipariş numarası üretecektir
5. WHEN sipariş oluşturulduğunda, THE Sistem SHALL ilgili tedarikçiye email bildirimi gönderecektir

### Gereksinim 4: Sipariş Takibi ve Durum Yönetimi

**Kullanıcı Hikayesi:** Depo sorumlusu olarak, verdiğim siparişlerin durumunu takip etmek istiyorum, böylece teslimat zamanını öngörebilir ve stok planlaması yapabilirim.

#### Kabul Kriterleri

1. WHEN Depo_Sorumlusu sipariş listesini görüntülediğinde, THE Sistem SHALL tüm siparişleri durum, tarih ve tedarikçi bilgileriyle birlikte listeleyecektir
2. WHEN Depo_Sorumlusu bir siparişin detayını açtığında, THE Sistem SHALL sipariş edilen ürünleri, miktarları, fiyatları ve durum geçmişini gösterecektir
3. WHEN Depo_Sorumlusu sipariş durumunu "Onaylandı" olarak güncellediğinde, THE Sistem SHALL tahmini teslimat tarihini hesaplayacak ve gösterecektir
4. WHEN Depo_Sorumlusu sipariş durumunu "Teslim Alındı" olarak işaretlediğinde, THE Sistem SHALL otomatik stok giriş formunu açacaktır
5. IF sipariş tahmini teslimat tarihini 2 gün geçtiyse, THEN THE Sistem SHALL depo sorumlusuna gecikme uyarısı gösterecektir

### Gereksinim 5: Stok Girişi ve Sipariş Entegrasyonu

**Kullanıcı Hikayesi:** Depo sorumlusu olarak, satın aldığım ürünleri stoka girerken sipariş bilgilerini otomatik doldurmak istiyorum, böylece manuel veri girişi hatalarını önleyebilirim.

#### Kabul Kriterleri

1. WHEN Depo_Sorumlusu "Teslim Alındı" durumundaki bir siparişten stok girişi yaptığında, THE Sistem SHALL sipariş edilen ürünleri ve miktarları otomatik olarak stok giriş formuna dolduracaktır
2. WHEN Depo_Sorumlusu stok girişini onayladığında, THE Sistem SHALL her ürün için UrunStok tablosunu güncelleyecek ve StokHareket kaydı oluşturacaktır
3. WHEN stok girişi tamamlandığında, THE Sistem SHALL ilgili siparişin durumunu "Tamamlandı" olarak işaretleyecektir
4. WHEN Depo_Sorumlusu kısmi teslimat girişi yaptığında, THE Sistem SHALL sipariş durumunu "Kısmi Teslim" olarak güncelleyecek ve kalan miktarı gösterecektir
5. WHEN stok girişi yapıldığında, THE Sistem SHALL ürünün birim maliyetini ve toplam stok değerini yeniden hesaplayacaktır

### Gereksinim 6: Tedarikçi Performans Takibi

**Kullanıcı Hikayesi:** Sistem yöneticisi olarak, tedarikçilerin performansını görmek istiyorum, böylece gelecekteki satın almalarda en güvenilir tedarikçileri seçebilirim.

#### Kabul Kriterleri

1. WHEN Sistem_Yoneticisi tedarikçi performans raporunu açtığında, THE Sistem SHALL her tedarikçi için ortalama teslimat süresi, zamanında teslimat oranı ve toplam sipariş sayısını gösterecektir
2. WHEN Sistem_Yoneticisi bir tedarikçinin detay raporunu görüntülediğinde, THE Sistem SHALL son 6 aydaki tüm siparişleri ve teslimat performansını grafik olarak gösterecektir
3. WHEN bir sipariş geç teslim edildiğinde, THE Sistem SHALL tedarikçinin zamanında teslimat oranını otomatik olarak güncelleyecektir
4. WHEN Sistem_Yoneticisi tedarikçi karşılaştırma raporunu açtığında, THE Sistem SHALL tüm tedarikçileri performans skoruna göre sıralayacaktır
5. IF bir tedarikçinin zamanında teslimat oranı yüzde 70'in altına düşerse, THEN THE Sistem SHALL sistem yöneticisine uyarı bildirimi gönderecektir

### Gereksinim 7: Otomatik Sipariş Önerisi

**Kullanıcı Hikayesi:** Depo sorumlusu olarak, stok seviyesi kritik seviyeye düşen ürünler için otomatik sipariş önerisi almak istiyorum, böylece stok takibini manuel yapmak zorunda kalmayacağım.

#### Kabul Kriterleri

1. WHEN Sistem günlük stok kontrolü yaptığında, THE Sistem SHALL mevcut stok seviyesi kritik seviyenin altında olan ürünleri tespit edecektir
2. WHEN kritik stok tespit edildiğinde, THE Sistem SHALL son 30 günlük tüketim ortalamasına göre sipariş miktarı önerecektir
3. WHEN Depo_Sorumlusu dashboard'unu açtığında, THE Sistem SHALL bekleyen sipariş önerilerini bildirim olarak gösterecektir
4. WHEN Depo_Sorumlusu sipariş önerisini onayladığında, THE Sistem SHALL önerilen ürünler ve miktarlarla otomatik sipariş formu oluşturacaktır
5. WHEN sipariş önerisi oluşturulduğunda, THE Sistem SHALL en uygun tedarikçiyi fiyat ve performans skoruna göre önerecektir

### Gereksinim 8: Fiyat Geçmişi ve Trend Analizi

**Kullanıcı Hikayesi:** Sistem yöneticisi olarak, ürün alış fiyatlarının zaman içindeki değişimini görmek istiyorum, böylece bütçe planlaması ve fiyat müzakereleri yapabilirim.

#### Kabul Kriterleri

1. WHEN Sistem_Yoneticisi fiyat geçmişi raporunu açtığında, THE Sistem SHALL seçilen ürün için tüm tedarikçilerin fiyat değişimlerini zaman çizelgesi olarak gösterecektir
2. WHEN Sistem_Yoneticisi bir ürünün fiyat trendini görüntülediğinde, THE Sistem SHALL son 12 aydaki ortalama fiyatı, en düşük fiyatı ve en yüksek fiyatı gösterecektir
3. WHEN bir tedarikçi fiyat güncellemesi yaptığında, THE Sistem SHALL fiyat değişim yüzdesini hesaplayacak ve UrunFiyatGecmisi tablosuna kaydedecektir
4. WHEN Sistem_Yoneticisi fiyat artış uyarısı ayarladığında, THE Sistem SHALL belirlenen yüzdenin üzerindeki fiyat artışlarında bildirim gönderecektir
5. WHEN fiyat karşılaştırma yapıldığında, THE Sistem SHALL aynı ürün için farklı tedarikçilerin fiyat değişim grafiklerini yan yana gösterecektir

### Gereksinim 9: Toplu Sipariş ve Excel İçe Aktarma

**Kullanıcı Hikayesi:** Depo sorumlusu olarak, çok sayıda ürün için toplu sipariş oluşturmak istiyorum, böylece her ürünü tek tek girmek zorunda kalmayacağım.

#### Kabul Kriterleri

1. WHEN Depo_Sorumlusu toplu sipariş sayfasını açtığında, THE Sistem SHALL Excel şablon dosyası indirme linki sunacaktır
2. WHEN Depo_Sorumlusu Excel dosyasını yüklediğinde, THE Sistem SHALL dosya formatını kontrol edecek ve hatalı satırları işaretleyecektir
3. WHEN Excel dosyası başarıyla yüklendiğinde, THE Sistem SHALL her ürün için tedarikçi ve fiyat bilgilerini otomatik eşleştirecektir
4. WHEN Depo_Sorumlusu toplu siparişi onayladığında, THE Sistem SHALL her tedarikçi için ayrı sipariş kaydı oluşturacaktır
5. IF Excel dosyasında tanımsız ürün veya tedarikçi varsa, THEN THE Sistem SHALL hata raporu gösterecek ve işlemi durduracaktır

### Gereksinim 10: Tedarikçi İletişim ve Belge Yönetimi

**Kullanıcı Hikayesi:** Depo sorumlusu olarak, tedarikçilerle yapılan yazışmaları ve belgeleri sisteme kaydetmek istiyorum, böylece geçmiş iletişim kayıtlarına kolayca erişebilirim.

#### Kabul Kriterleri

1. WHEN Depo_Sorumlusu tedarikçi detay sayfasını açtığında, THE Sistem SHALL iletişim geçmişi ve yüklenen belgeler bölümünü gösterecektir
2. WHEN Depo_Sorumlusu yeni iletişim kaydı eklediğinde, THE Sistem SHALL tarih, konu, açıklama ve ilgili sipariş bilgilerini kaydedecektir
3. WHEN Depo_Sorumlusu belge yüklediğinde, THE Sistem SHALL PDF, Excel ve resim formatlarını kabul edecek ve güvenli şekilde saklayacaktır
4. WHEN Depo_Sorumlusu sipariş detayından tedarikçi iletişim geçmişine erişmek istediğinde, THE Sistem SHALL ilgili siparişle ilişkili tüm iletişim kayıtlarını filtreleyecektir
5. WHEN belge yüklendiğinde, THE Sistem SHALL belge tipini (fatura, irsaliye, sözleşme) etiketleme imkanı sunacaktır
