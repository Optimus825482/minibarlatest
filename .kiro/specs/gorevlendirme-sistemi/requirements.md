# Requirements Document

## Introduction

Bu doküman, Minibar Takip Sistemi için günlük görevlendirme sisteminin gereksinimlerini tanımlar. Sistem, günlük doluluk bilgileri (In House ve Arrivals) yüklendikten sonra kat sorumluları için otomatik minibar kontrol görevleri oluşturur. Görevler, In House (kalmaya devam eden) ve Arrivals (o gün giriş yapacak) odalar için ayrı ayrı listelenir. Arrivals görevlerinde misafir varış saatine özel geri sayım sayacı bulunur. DND (Do Not Disturb) durumundaki odalar için özel takip mekanizması içerir.

## Glossary

- **Görevlendirme Sistemi**: Günlük doluluk verilerine göre otomatik minibar kontrol görevleri oluşturan sistem
- **In House**: Otelde kalmaya devam eden misafirler ve odaları
- **Arrivals**: O gün giriş yapacak misafirler ve odaları
- **DND (Do Not Disturb)**: Rahatsız Etmeyin durumu - misafirin odaya girilmesini istemediği durum
- **Görev Durumu**: Görevin mevcut durumu (pending, in_progress, completed, dnd_pending)
- **Geri Sayım Sayacı**: Arrivals görevlerinde misafir varışına kalan süreyi gösteren sayaç
- **Kat Sorumlusu**: Minibar kontrollerini yapan personel
- **Depo Sorumlusu**: Kat sorumlularını yöneten ve raporları takip eden personel
- **Sistem Yöneticisi**: Tüm sistemi yöneten ve raporlara erişen personel
- **Doluluk Yükleme Görevi**: Depo sorumlusunun günlük olarak In House ve Arrivals verilerini sisteme yüklemesi görevi
- **Yükleme Takip Sistemi**: Doluluk verilerinin yüklenme durumunu izleyen ve raporlayan sistem

## Requirements

### Requirement 1

**User Story:** As a kat sorumlusu, I want to see my daily task list automatically generated after occupancy data is uploaded, so that I can efficiently plan my minibar control activities.

#### Acceptance Criteria

1. WHEN günlük doluluk verileri (In House veya Arrivals) sisteme yüklenip kaydedildiğinde THEN Görevlendirme Sistemi SHALL ilgili kat sorumluları için otomatik görev listesi oluşturmalıdır
2. WHEN görev listesi oluşturulduğunda THEN Görevlendirme Sistemi SHALL kat sorumlusu dashboard'unda bildirim göstermelidir
3. WHEN kat sorumlusu bildirime tıkladığında THEN Görevlendirme Sistemi SHALL görev detayları sayfasına yönlendirmelidir
4. WHEN görev listesi görüntülendiğinde THEN Görevlendirme Sistemi SHALL In House ve Arrivals görevlerini ayrı listeler halinde göstermelidir

### Requirement 2

**User Story:** As a kat sorumlusu, I want to see In House room tasks separately, so that I can perform minibar controls for guests who are staying.

#### Acceptance Criteria

1. WHEN In House görev listesi görüntülendiğinde THEN Görevlendirme Sistemi SHALL kalmaya devam eden odaları oda numarası, kat bilgisi ve misafir sayısı ile listelemelidir
2. WHEN bir In House oda için minibar kontrolü yapıldığında THEN Görevlendirme Sistemi SHALL görev durumunu "completed" olarak güncellemeli ve eksik ürünlerin tamamlanmasını kaydetmelidir
3. WHEN In House görev listesinde bir oda DND durumunda olduğunda THEN Görevlendirme Sistemi SHALL kat sorumlusunun odayı DND olarak işaretlemesine izin vermelidir
4. WHEN bir oda DND olarak işaretlendiğinde THEN Görevlendirme Sistemi SHALL odayı görev listesinden çıkarmadan ayrı bir DND listesinde de göstermelidir

### Requirement 3

**User Story:** As a kat sorumlusu, I want to see Arrivals room tasks with countdown timers, so that I can complete pre-arrival controls before guests arrive.

#### Acceptance Criteria

1. WHEN Arrivals görev listesi görüntülendiğinde THEN Görevlendirme Sistemi SHALL o gün giriş yapacak odaları varış saati, oda numarası ve kat bilgisi ile listelemelidir
2. WHEN bir Arrivals görevi görüntülendiğinde THEN Görevlendirme Sistemi SHALL misafir varış saatine kalan süreyi geri sayım sayacı ile göstermelidir
3. WHEN varış saatine 15 dakikadan az kaldığında THEN Görevlendirme Sistemi SHALL geri sayım sayacını kırmızı renkte ve yanıp söner şekilde göstermelidir
4. WHEN Arrivals kontrolü tamamlandığında THEN Görevlendirme Sistemi SHALL görev durumunu "completed" olarak güncellemeli ve kontrol zamanını kaydetmelidir
5. WHILE geri sayım sayacı aktifken THEN Görevlendirme Sistemi SHALL sayacı her saniye güncellemeli ve kontrol yapılana kadar aktif tutmalıdır

### Requirement 4

**User Story:** As a kat sorumlusu, I want to manage DND rooms with multiple check attempts, so that I can properly document rooms that remain inaccessible throughout the day.

#### Acceptance Criteria

1. WHEN bir oda ilk kez DND olarak işaretlendiğinde THEN Görevlendirme Sistemi SHALL DND kayıt zamanını ve kontrol eden personeli kaydetmelidir
2. WHEN bir DND odası için tekrar kontrol yapıldığında THEN Görevlendirme Sistemi SHALL yeni kontrol kaydı eklemeye ve DND durumunu güncellemeye izin vermelidir
3. WHEN bir DND odası gün içinde en az 3 kez (ilk + 2 ek) DND olarak işaretlendiğinde THEN Görevlendirme Sistemi SHALL görevi "completed" olarak işaretlemelidir
4. WHEN gün sonunda bir DND odası 3 kez kontrol edilmemişse THEN Görevlendirme Sistemi SHALL ertesi gün kat sorumlusu ve sistem yöneticisine yapılmayan görev bildirimi göndermelidir
5. WHEN DND bildirimi gönderildiğinde THEN Görevlendirme Sistemi SHALL oda numarası, ilk DND kayıt zamanı ve toplam kontrol sayısını içermelidir

### Requirement 5

**User Story:** As a kat sorumlusu, I want to see my completed and incomplete tasks on my dashboard, so that I can track my daily performance.

#### Acceptance Criteria

1. WHEN kat sorumlusu dashboard'u görüntülendiğinde THEN Görevlendirme Sistemi SHALL günlük tamamlanan ve tamamlanmayan görev sayılarını göstermelidir
2. WHEN tamamlanan görevler görüntülendiğinde THEN Görevlendirme Sistemi SHALL görev tipi, oda numarası ve tamamlanma zamanını listelemelidir
3. WHEN tamamlanmayan görevler görüntülendiğinde THEN Görevlendirme Sistemi SHALL görev tipi, oda numarası ve bekleyen süreyi listelemelidir
4. WHEN raporlar bölümüne erişildiğinde THEN Görevlendirme Sistemi SHALL geçmişe dönük görev raporlarını tarih filtresi ile göstermelidir

### Requirement 6

**User Story:** As a depo sorumlusu, I want to have a daily task to upload In House and Arrivals data, so that the system can generate tasks for floor supervisors.

#### Acceptance Criteria

1. WHEN her gün başladığında THEN Görevlendirme Sistemi SHALL depo sorumlusu için "In House Yükle" ve "Arrivals Yükle" görevlerini otomatik oluşturmalıdır
2. WHEN In House veya Arrivals dosyası yüklendiğinde THEN Görevlendirme Sistemi SHALL ilgili yükleme görevini "completed" olarak işaretlemelidir
3. WHEN günlük doluluk yükleme görevi tamamlanmadığında THEN Görevlendirme Sistemi SHALL depo sorumlusu dashboard'unda uyarı bildirimi göstermelidir
4. WHEN günlük doluluk yükleme görevi tamamlanmadığında THEN Görevlendirme Sistemi SHALL sistem yöneticisi dashboard'unda da uyarı bildirimi göstermelidir
5. WHEN yükleme durumu sorgulandığında THEN Görevlendirme Sistemi SHALL yükleme tarihi, yükleyen personel ve dosya tipi bilgilerini döndürmelidir

### Requirement 7

**User Story:** As a depo sorumlusu, I want to see task completion status of my floor supervisors, so that I can monitor their performance and workload.

#### Acceptance Criteria

1. WHEN depo sorumlusu dashboard'u görüntülendiğinde THEN Görevlendirme Sistemi SHALL bağlı kat sorumlularının günlük tamamlanan ve tamamlanmayan görev sayılarını göstermelidir
2. WHEN görev detayları görüntülendiğinde THEN Görevlendirme Sistemi SHALL tamamlayan personel bilgisi, oda numarası ve tamamlanma zamanını göstermelidir
3. WHEN tarih filtresi uygulandığında THEN Görevlendirme Sistemi SHALL seçilen tarih aralığındaki görev raporlarını göstermelidir

### Requirement 8

**User Story:** As a sistem yöneticisi, I want to see all task reports across the hotel, so that I can monitor overall operational efficiency.

#### Acceptance Criteria

1. WHEN sistem yöneticisi dashboard'u görüntülendiğinde THEN Görevlendirme Sistemi SHALL tüm otelin günlük tamamlanan ve tamamlanmayan görev özetini göstermelidir
2. WHEN detaylı rapor görüntülendiğinde THEN Görevlendirme Sistemi SHALL personel bazlı, kat bazlı ve oda tipi bazlı görev istatistiklerini göstermelidir
3. WHEN tarih filtresi uygulandığında THEN Görevlendirme Sistemi SHALL geçmişe dönük raporları filtreleyerek göstermelidir
4. WHEN DND bildirimleri görüntülendiğinde THEN Görevlendirme Sistemi SHALL tamamlanmayan DND görevlerinin detaylarını göstermelidir

### Requirement 9

**User Story:** As a sistem yöneticisi, I want to track daily occupancy upload status, so that I can ensure data is uploaded consistently.

#### Acceptance Criteria

1. WHEN sistem yöneticisi dashboard'u görüntülendiğinde THEN Görevlendirme Sistemi SHALL günlük doluluk yükleme durumunu (In House ve Arrivals ayrı ayrı) göstermelidir
2. WHEN doluluk yükleme takip raporu görüntülendiğinde THEN Görevlendirme Sistemi SHALL tarih, otel, yükleyen personel, dosya tipi ve yükleme zamanını listelemelidir
3. WHEN tarih filtresi uygulandığında THEN Görevlendirme Sistemi SHALL seçilen tarih aralığındaki yükleme geçmişini göstermelidir
4. WHEN yükleme yapılmayan günler sorgulandığında THEN Görevlendirme Sistemi SHALL eksik yükleme günlerini ve ilgili depo sorumlularını listelemelidir
5. WHEN yükleme istatistikleri görüntülendiğinde THEN Görevlendirme Sistemi SHALL haftalık ve aylık yükleme oranlarını göstermelidir

### Requirement 10

**User Story:** As a sistem, I want to track task status changes, so that accurate reporting and audit trails are maintained.

#### Acceptance Criteria

1. WHEN bir görev durumu değiştiğinde THEN Görevlendirme Sistemi SHALL değişiklik zamanı, önceki durum, yeni durum ve işlemi yapan personeli kaydetmelidir
2. WHEN minibar kontrolü kaydedildiğinde THEN Görevlendirme Sistemi SHALL kontrol edilen ürünler, eksik ürünler ve tamamlanan ürünleri kaydetmelidir
3. WHEN görev verileri sorgulandığında THEN Görevlendirme Sistemi SHALL JSON formatında serialize edilebilir veri döndürmelidir
4. WHEN görev verileri parse edildiğinde THEN Görevlendirme Sistemi SHALL JSON formatından deserialize edilen veriyi orijinal veri ile eşleşecek şekilde döndürmelidir
