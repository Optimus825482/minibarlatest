# Fiyatlandırma ve Karlılık Hesaplama Sistemi - Tasarım Dokümanı

## Genel Bakış

Bu tasarım dokümanı, mini bar stok takip sistemine eklenecek fiyatlandırma ve karlılık hesaplama modülünün teknik mimarisini tanımlar. Sistem, mevcut Flask/SQLAlchemy altyapısı üzerine inşa edilecek ve PostgreSQL veritabanı kullanacaktır.

### Temel Prensipler

- **Modüler Mimari**: Mevcut sistemle uyumlu, bağımsız modüller
- **Geriye Dönük Uyumluluk**: Mevcut veri ve işlevsellik korunacak
- **Performans**: Redis cache ve asenkron işlemler
- **Güvenlik**: Rol bazlı erişim kontrolü ve audit trail
- **Ölçeklenebilirlik**: Multi-otel yapısına uygun tasarım

## Mimari Genel Bakış

```
┌─────────────────────────────────────────────────────────────┐
│                    Presentation Layer                        │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │  Dashboard   │  │  Fiyat UI    │  │  Rapor UI    │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│                      API Layer (Flask)                       │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │ Fiyat API    │  │ Karlılık API │  │  ML API      │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│                     Service Layer                            │
│  ┌──────────────────┐  ┌──────────────────┐                │
│  │ FiyatYonetim     │  │ KarHesaplama     │                │
│  │ Servisi          │  │ Servisi          │                │
│  └──────────────────┘  └──────────────────┘                │
│  ┌──────────────────┐  ┌──────────────────┐                │
│  │ Kampanya         │  │ ML Entegrasyon   │                │
│  │ Servisi          │  │ Servisi          │                │
│  └──────────────────┘  └──────────────────┘                │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│                     Data Layer                               │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │ PostgreSQL   │  │ Redis Cache  │  │ Celery Queue │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
└─────────────────────────────────────────────────────────────┘
```

## Veri Modeli Tasarımı

### Yeni Tablolar

#### 1. Tedarikci (Tedarikçi Yönetimi)

```python
class Tedarikci(db.Model):
    """Tedarikçi bilgileri"""
    __tablename__ = 'tedarikciler'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    tedarikci_adi = db.Column(db.String(200), nullable=False)
    iletisim_bilgileri = db.Column(JSONB, nullable=True)  # {telefon, email, adres}
    vergi_no = db.Column(db.String(50))
    aktif = db.Column(db.Boolean, default=True)
    olusturma_tarihi = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    guncelleme_tarihi = db.Column(db.DateTime(timezone=True), onupdate=lambda: datetime.now(timezone.utc))

    # İlişkiler
    urun_fiyatlari = db.relationship('UrunTedarikciFiyat', backref='tedarikci', lazy=True)

    __table_args__ = (
        db.Index('idx_tedarikci_aktif', 'aktif'),
    )
```

#### 2. UrunTedarikciFiyat (Ürün-Tedarikçi Fiyat İlişkisi)

```python
class UrunTedarikciFiyat(db.Model):
    """Ürün bazında tedarikçi fiyatları"""
    __tablename__ = 'urun_tedarikci_fiyatlari'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    urun_id = db.Column(db.Integer, db.ForeignKey('urunler.id', ondelete='CASCADE'), nullable=False)
    tedarikci_id = db.Column(db.Integer, db.ForeignKey('tedarikciler.id', ondelete='CASCADE'), nullable=False)
    alis_fiyati = db.Column(Numeric(10, 2), nullable=False)
    minimum_miktar = db.Column(db.Integer, default=1)
    baslangic_tarihi = db.Column(db.DateTime(timezone=True), nullable=False)
    bitis_tarihi = db.Column(db.DateTime(timezone=True), nullable=True)
    aktif = db.Column(db.Boolean, default=True)
    olusturma_tarihi = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    olusturan_id = db.Column(db.Integer, db.ForeignKey('kullanicilar.id'), nullable=False)

    # İlişkiler
    urun = db.relationship('Urun', backref='tedarikci_fiyatlari')
    olusturan = db.relationship('Kullanici')

    __table_args__ = (
        db.Index('idx_urun_tedarikci_aktif', 'urun_id', 'tedarikci_id', 'aktif'),
        db.Index('idx_urun_fiyat_tarih', 'urun_id', 'baslangic_tarihi', 'bitis_tarihi'),
    )
```

#### 3. UrunFiyatGecmisi (Fiyat Değişiklik Geçmişi)

```python
class FiyatDegisiklikTipi(str, enum.Enum):
    ALIS_FIYATI = 'alis_fiyati'
    SATIS_FIYATI = 'satis_fiyati'
    KAMPANYA = 'kampanya'

class UrunFiyatGecmisi(db.Model):
    """Fiyat değişiklik geçmişi"""
    __tablename__ = 'urun_fiyat_gecmisi'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    urun_id = db.Column(db.Integer, db.ForeignKey('urunler.id', ondelete='CASCADE'), nullable=False)
    eski_fiyat = db.Column(Numeric(10, 2))
    yeni_fiyat = db.Column(Numeric(10, 2), nullable=False)
    degisiklik_tipi = db.Column(db.Enum(FiyatDegisiklikTipi), nullable=False)
    degisiklik_tarihi = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    degisiklik_sebebi = db.Column(db.Text)
    olusturan_id = db.Column(db.Integer, db.ForeignKey('kullanicilar.id'), nullable=False)

    # İlişkiler
    urun = db.relationship('Urun', backref='fiyat_gecmisi')
    olusturan = db.relationship('Kullanici')

    __table_args__ = (
        db.Index('idx_fiyat_gecmis_urun_tarih', 'urun_id', 'degisiklik_tarihi'),
    )
```

#### 4. OdaTipiSatisFiyati (Oda Tipi Bazlı Fiyatlandırma)

```python
class OdaTipiSatisFiyati(db.Model):
    """Oda tipi bazında satış fiyatları"""
    __tablename__ = 'oda_tipi_satis_fiyatlari'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    oda_tipi = db.Column(db.String(100), nullable=False)  # Standard, Deluxe, Suite
    urun_id = db.Column(db.Integer, db.ForeignKey('urunler.id', ondelete='CASCADE'), nullable=False)
    satis_fiyati = db.Column(Numeric(10, 2), nullable=False)
    baslangic_tarihi = db.Column(db.DateTime(timezone=True), nullable=False)
    bitis_tarihi = db.Column(db.DateTime(timezone=True), nullable=True)
    aktif = db.Column(db.Boolean, default=True)
    olusturma_tarihi = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    # İlişkiler
    urun = db.relationship('Urun', backref='oda_tipi_fiyatlari')

    __table_args__ = (
        db.Index('idx_oda_tipi_urun_aktif', 'oda_tipi', 'urun_id', 'aktif'),
    )
```

#### 5. SezonFiyatlandirma (Sezonluk Fiyat Çarpanları)

```python
class SezonFiyatlandirma(db.Model):
    """Sezonluk fiyat çarpanları"""
    __tablename__ = 'sezon_fiyatlandirma'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    sezon_adi = db.Column(db.String(100), nullable=False)  # Yaz, Kış, Bayram
    baslangic_tarihi = db.Column(db.Date, nullable=False)
    bitis_tarihi = db.Column(db.Date, nullable=False)
    urun_id = db.Column(db.Integer, db.ForeignKey('urunler.id', ondelete='CASCADE'), nullable=True)
    fiyat_carpani = db.Column(Numeric(4, 2), default=1.0)  # 0.50 - 3.00 arası
    aktif = db.Column(db.Boolean, default=True)
    olusturma_tarihi = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    # İlişkiler
    urun = db.relationship('Urun', backref='sezon_fiyatlari')

    __table_args__ = (
        db.Index('idx_sezon_tarih_aktif', 'baslangic_tarihi', 'bitis_tarihi', 'aktif'),
    )
```

#### 6. Kampanya (Promosyon ve İndirim Yönetimi)

```python
class IndirimTipi(str, enum.Enum):
    YUZDE = 'yuzde'
    TUTAR = 'tutar'

class Kampanya(db.Model):
    """Kampanya ve promosyon yönetimi"""
    __tablename__ = 'kampanyalar'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    kampanya_adi = db.Column(db.String(200), nullable=False)
    baslangic_tarihi = db.Column(db.DateTime(timezone=True), nullable=False)
    bitis_tarihi = db.Column(db.DateTime(timezone=True), nullable=False)
    urun_id = db.Column(db.Integer, db.ForeignKey('urunler.id', ondelete='CASCADE'), nullable=True)
    indirim_tipi = db.Column(db.Enum(IndirimTipi), nullable=False)
    indirim_degeri = db.Column(Numeric(10, 2), nullable=False)
    min_siparis_miktari = db.Column(db.Integer, default=1)
    max_kullanim_sayisi = db.Column(db.Integer, nullable=True)
    kullanilan_sayisi = db.Column(db.Integer, default=0)
    aktif = db.Column(db.Boolean, default=True)
    olusturma_tarihi = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    olusturan_id = db.Column(db.Integer, db.ForeignKey('kullanicilar.id'), nullable=False)

    # İlişkiler
    urun = db.relationship('Urun', backref='kampanyalar')
    olusturan = db.relationship('Kullanici')

    __table_args__ = (
        db.Index('idx_kampanya_aktif_tarih', 'aktif', 'baslangic_tarihi', 'bitis_tarihi'),
    )
```

#### 7. BedelsizLimit (Bedelsiz Tüketim Limitleri)

```python
class BedelsizLimitTipi(str, enum.Enum):
    MISAFIR = 'misafir'
    KAMPANYA = 'kampanya'
    PERSONEL = 'personel'

class BedelsizLimit(db.Model):
    """Bedelsiz tüketim limitleri"""
    __tablename__ = 'bedelsiz_limitler'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    oda_id = db.Column(db.Integer, db.ForeignKey('odalar.id', ondelete='CASCADE'), nullable=False)
    urun_id = db.Column(db.Integer, db.ForeignKey('urunler.id', ondelete='CASCADE'), nullable=False)
    max_miktar = db.Column(db.Integer, nullable=False)
    kullanilan_miktar = db.Column(db.Integer, default=0)
    baslangic_tarihi = db.Column(db.DateTime(timezone=True), nullable=False)
    bitis_tarihi = db.Column(db.DateTime(timezone=True), nullable=True)
    limit_tipi = db.Column(db.Enum(BedelsizLimitTipi), nullable=False)
    kampanya_id = db.Column(db.Integer, db.ForeignKey('kampanyalar.id', ondelete='SET NULL'), nullable=True)
    aktif = db.Column(db.Boolean, default=True)
    olusturma_tarihi = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    # İlişkiler
    oda = db.relationship('Oda', backref='bedelsiz_limitler')
    urun = db.relationship('Urun', backref='bedelsiz_limitler')
    kampanya = db.relationship('Kampanya', backref='bedelsiz_limitler')

    __table_args__ = (
        db.Index('idx_bedelsiz_oda_aktif', 'oda_id', 'aktif'),
    )
```

#### 8. BedelsizKullanimLog (Bedelsiz Kullanım Kayıtları)

```python
class BedelsizKullanimLog(db.Model):
    """Bedelsiz kullanım log kayıtları"""
    __tablename__ = 'bedelsiz_kullanim_log'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    oda_id = db.Column(db.Integer, db.ForeignKey('odalar.id', ondelete='CASCADE'), nullable=False)
    urun_id = db.Column(db.Integer, db.ForeignKey('urunler.id', ondelete='CASCADE'), nullable=False)
    miktar = db.Column(db.Integer, nullable=False)
    islem_id = db.Column(db.Integer, db.ForeignKey('minibar_islemler.id', ondelete='CASCADE'), nullable=False)
    kullanilma_tarihi = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    limit_id = db.Column(db.Integer, db.ForeignKey('bedelsiz_limitler.id', ondelete='SET NULL'), nullable=True)

    # İlişkiler
    oda = db.relationship('Oda')
    urun = db.relationship('Urun')
    islem = db.relationship('MinibarIslem')
    limit = db.relationship('BedelsizLimit')

    __table_args__ = (
        db.Index('idx_bedelsiz_log_tarih', 'kullanilma_tarihi'),
    )
```

#### 9. DonemselKarAnalizi (Dönemsel Karlılık Raporları)

```python
class DonemTipi(str, enum.Enum):
    GUNLUK = 'gunluk'
    HAFTALIK = 'haftalik'
    AYLIK = 'aylik'

class DonemselKarAnalizi(db.Model):
    """Dönemsel kar analiz raporları"""
    __tablename__ = 'donemsel_kar_analizi'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    otel_id = db.Column(db.Integer, db.ForeignKey('oteller.id', ondelete='CASCADE'), nullable=False)
    donem_tipi = db.Column(db.Enum(DonemTipi), nullable=False)
    baslangic_tarihi = db.Column(db.Date, nullable=False)
    bitis_tarihi = db.Column(db.Date, nullable=False)
    toplam_gelir = db.Column(Numeric(12, 2), default=0)
    toplam_maliyet = db.Column(Numeric(12, 2), default=0)
    net_kar = db.Column(Numeric(12, 2), default=0)
    kar_marji = db.Column(Numeric(5, 2), default=0)  # Yüzde
    analiz_verisi = db.Column(JSONB, nullable=True)  # Detaylı analiz verileri
    olusturma_tarihi = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    # İlişkiler
    otel = db.relationship('Otel', backref='kar_analizleri')

    __table_args__ = (
        db.Index('idx_kar_analiz_otel_donem', 'otel_id', 'donem_tipi', 'baslangic_tarihi'),
    )
```

#### 10. FiyatGuncellemeKurali (Otomatik Fiyat Güncelleme)

```python
class KuralTipi(str, enum.Enum):
    OTOMATIK_ARTIR = 'otomatik_artir'
    OTOMATIK_AZALT = 'otomatik_azalt'
    RAKIP_FIYAT = 'rakip_fiyat'

class FiyatGuncellemeKurali(db.Model):
    """Otomatik fiyat güncelleme kuralları"""
    __tablename__ = 'fiyat_guncelleme_kurallari'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    urun_id = db.Column(db.Integer, db.ForeignKey('urunler.id', ondelete='CASCADE'), nullable=True)
    kural_tipi = db.Column(db.Enum(KuralTipi), nullable=False)
    artirma_orani = db.Column(Numeric(5, 2), nullable=True)  # Yüzde
    azaltma_orani = db.Column(Numeric(5, 2), nullable=True)  # Yüzde
    min_fiyat = db.Column(Numeric(10, 2), nullable=True)
    max_fiyat = db.Column(Numeric(10, 2), nullable=True)
    aktif = db.Column(db.Boolean, default=True)
    son_uygulama = db.Column(db.DateTime(timezone=True), nullable=True)
    olusturma_tarihi = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    # İlişkiler
    urun = db.relationship('Urun', backref='fiyat_kurallari')

    __table_args__ = (
        db.Index('idx_fiyat_kural_aktif', 'aktif'),
    )
```

### Mevcut Tablolara Eklemeler

#### MinibarIslemDetay Tablosu Güncellemeleri

```python
# Mevcut MinibarIslemDetay modeline eklenecek kolonlar:
class MinibarIslemDetay(db.Model):
    # ... mevcut kolonlar ...

    # YENİ KOLONLAR
    satis_fiyati = db.Column(Numeric(10, 2), nullable=True)
    alis_fiyati = db.Column(Numeric(10, 2), nullable=True)
    kar_tutari = db.Column(Numeric(10, 2), nullable=True)
    kar_orani = db.Column(Numeric(5, 2), nullable=True)  # Yüzde
    bedelsiz = db.Column(db.Boolean, default=False)
    kampanya_id = db.Column(db.Integer, db.ForeignKey('kampanyalar.id'), nullable=True)

    # YENİ İLİŞKİ
    kampanya = db.relationship('Kampanya')
```

## Servis Katmanı Tasarımı

### 1. FiyatYonetimServisi

```python
class FiyatYonetimServisi:
    """Fiyat yönetimi ve hesaplama servisi"""

    @staticmethod
    def dinamik_fiyat_hesapla(urun_id, oda_id=None, tarih=None, miktar=1):
        """
        Çok katmanlı dinamik fiyat hesaplama

        Args:
            urun_id: Ürün ID
            oda_id: Oda ID (oda tipi için)
            tarih: Fiyat hesaplama tarihi
            miktar: Tüketim miktarı

        Returns:
            dict: {
                'alis_fiyati': Decimal,
                'satis_fiyati': Decimal,
                'kar_tutari': Decimal,
                'kar_orani': float,
                'bedelsiz': bool,
                'uygulanan_kampanya': str
            }
        """
        pass

    @staticmethod
    def guncel_alis_fiyati_getir(urun_id, tedarikci_id=None):
        """Güncel alış fiyatını getir"""
        pass

    @staticmethod
    def oda_tipi_fiyati_getir(urun_id, oda_tipi, tarih=None):
        """Oda tipi bazlı satış fiyatını getir"""
        pass

    @staticmethod
    def sezon_carpani_uygula(fiyat, urun_id, tarih):
        """Sezon çarpanını uygula"""
        pass

    @staticmethod
    def kampanya_uygula(fiyat, urun_id, miktar, tarih):
        """Kampanya indirimini uygula"""
        pass

    @staticmethod
    def bedelsiz_kontrol(oda_id, urun_id, miktar):
        """Bedelsiz limit kontrolü"""
        pass
```

### 2. KarHesaplamaServisi

```python
class KarHesaplamaServisi:
    """Karlılık hesaplama ve analiz servisi"""

    @staticmethod
    def gercek_zamanli_kar_hesapla(islem_detay_listesi):
        """
        Gerçek zamanlı kar/zarar hesaplama

        Args:
            islem_detay_listesi: MinibarIslemDetay listesi

        Returns:
            dict: {
                'toplam_gelir': Decimal,
                'toplam_maliyet': Decimal,
                'net_kar': Decimal,
                'kar_marji': float,
                'islem_sayisi': int
            }
        """
        pass

    @staticmethod
    def donemsel_kar_analizi(otel_id, baslangic, bitis, donem_tipi='gunluk'):
        """Dönemsel karlılık analizi"""
        pass

    @staticmethod
    def urun_karliligi_analizi(urun_id, tarih_araligi=None):
        """Ürün bazlı karlılık analizi"""
        pass

    @staticmethod
    def oda_karliligi_analizi(oda_id, tarih_araligi=None):
        """Oda bazlı karlılık analizi"""
        pass

    @staticmethod
    def roi_hesapla(urun_id, baslangic, bitis):
        """ROI hesaplama"""
        pass
```

### 3. KampanyaServisi

```python
class KampanyaServisi:
    """Kampanya yönetim servisi"""

    @staticmethod
    def kampanya_olustur(kampanya_data):
        """Yeni kampanya oluştur"""
        pass

    @staticmethod
    def kampanya_uygula(kampanya_id, fiyat, miktar):
        """Kampanya indirimini hesapla"""
        pass

    @staticmethod
    def kampanya_kullanim_guncelle(kampanya_id):
        """Kampanya kullanım sayısını artır"""
        pass

    @staticmethod
    def aktif_kampanyalar_getir(urun_id=None, tarih=None):
        """Aktif kampanyaları getir"""
        pass
```

### 4. BedelsizServisi

```python
class BedelsizServisi:
    """Bedelsiz limit yönetim servisi"""

    @staticmethod
    def limit_kontrol(oda_id, urun_id, miktar):
        """
        Bedelsiz limit kontrolü

        Returns:
            tuple: (bedelsiz_miktar, ucretli_miktar)
        """
        pass

    @staticmethod
    def limit_kullan(oda_id, urun_id, miktar, islem_id):
        """Bedelsiz limiti kullan ve log'la"""
        pass

    @staticmethod
    def limit_tanimla(oda_id, urun_id, max_miktar, limit_tipi, **kwargs):
        """Yeni bedelsiz limit tanımla"""
        pass
```

### 5. MLEntegrasyonServisi

```python
class MLEntegrasyonServisi:
    """ML sistemi entegrasyon servisi"""

    @staticmethod
    def gelir_anomali_tespit(otel_id, tarih_araligi):
        """Gelir anomalilerini tespit et"""
        pass

    @staticmethod
    def karlilik_anomali_tespit(otel_id, tarih_araligi):
        """Karlılık anomalilerini tespit et"""
        pass

    @staticmethod
    def trend_analizi(urun_id, donem='aylik'):
        """Ürün trend analizi"""
        pass
```

## API Endpoint Tasarımı

### Fiyat Yönetimi API'leri

```python
# routes/fiyatlandirma_routes.py

@fiyatlandirma_bp.route('/api/v1/fiyat/urun/<int:urun_id>', methods=['GET'])
@login_required
def get_urun_fiyat(urun_id):
    """Ürün fiyat bilgilerini getir"""
    pass

@fiyatlandirma_bp.route('/api/v1/fiyat/urun/<int:urun_id>/guncelle', methods=['POST'])
@login_required
@role_required(['sistem_yoneticisi', 'admin', 'depo_sorumlusu'])
def update_urun_fiyat(urun_id):
    """Ürün fiyatını güncelle"""
    pass

@fiyatlandirma_bp.route('/api/v1/fiyat/tedarikci/<int:tedarikci_id>', methods=['GET'])
@login_required
def get_tedarikci_fiyatlari(tedarikci_id):
    """Tedarikçi fiyatlarını getir"""
    pass

@fiyatlandirma_bp.route('/api/v1/fiyat/kampanya', methods=['POST'])
@login_required
@role_required(['sistem_yoneticisi', 'admin'])
def create_kampanya():
    """Yeni kampanya oluştur"""
    pass

@fiyatlandirma_bp.route('/api/v1/fiyat/dinamik-hesapla', methods=['POST'])
@login_required
def hesapla_dinamik_fiyat():
    """Dinamik fiyat hesapla"""
    pass
```

### Karlılık API'leri

```python
@karlilik_bp.route('/api/v1/kar/urun/<int:urun_id>', methods=['GET'])
@login_required
def get_urun_karlilik(urun_id):
    """Ürün karlılık bilgisi"""
    pass

@karlilik_bp.route('/api/v1/kar/donemsel', methods=['GET'])
@login_required
def get_donemsel_kar():
    """Dönemsel kar raporu"""
    pass

@karlilik_bp.route('/api/v1/kar/roi/<int:urun_id>', methods=['GET'])
@login_required
def get_urun_roi(urun_id):
    """Ürün ROI hesaplama"""
    pass

@karlilik_bp.route('/api/v1/kar/hesapla', methods=['POST'])
@login_required
def hesapla_kar():
    """Gerçek zamanlı kar hesaplama"""
    pass
```

## Frontend Tasarımı

### Dashboard Bileşenleri

#### 1. Karlılık Dashboard (karlilik_dashboard.html)

```html
<!-- Özet Kartlar -->
<div class="grid grid-cols-4 gap-4">
  <div class="card">
    <h3>Günlük Kar</h3>
    <p class="text-2xl" id="gunluk-kar">₺0</p>
  </div>
  <div class="card">
    <h3>Aylık Kar</h3>
    <p class="text-2xl" id="aylik-kar">₺0</p>
  </div>
  <div class="card">
    <h3>Kar Marjı</h3>
    <p class="text-2xl" id="kar-marji">%0</p>
  </div>
  <div class="card">
    <h3>ROI</h3>
    <p class="text-2xl" id="roi">%0</p>
  </div>
</div>

<!-- Trend Grafikleri -->
<div class="mt-6">
  <canvas id="kar-trend-chart"></canvas>
</div>

<!-- En Karlı Ürünler -->
<div class="mt-6">
  <table id="karli-urunler-table" class="datatable">
    <!-- DataTables ile doldurulacak -->
  </table>
</div>
```

#### 2. Fiyat Yönetimi (urun_fiyat_yonetimi.html)

```html
<!-- Fiyat Güncelleme Formu -->
<form id="fiyat-guncelle-form">
  <div class="form-group">
    <label>Ürün</label>
    <select name="urun_id" required></select>
  </div>
  <div class="form-group">
    <label>Tedarikçi</label>
    <select name="tedarikci_id" required></select>
  </div>
  <div class="form-group">
    <label>Alış Fiyatı</label>
    <input type="number" name="alis_fiyati" step="0.01" required />
  </div>
  <div class="form-group">
    <label>Satış Fiyatı</label>
    <input type="number" name="satis_fiyati" step="0.01" required />
  </div>
  <button type="submit">Güncelle</button>
</form>

<!-- Fiyat Geçmişi -->
<div class="mt-6">
  <h3>Fiyat Geçmişi</h3>
  <table id="fiyat-gecmis-table" class="datatable"></table>
</div>
```

#### 3. Kampanya Yönetimi (kampanya_yonetimi.html)

```html
<!-- Kampanya Oluşturma -->
<form id="kampanya-form">
  <div class="form-group">
    <label>Kampanya Adı</label>
    <input type="text" name="kampanya_adi" required />
  </div>
  <div class="form-group">
    <label>İndirim Tipi</label>
    <select name="indirim_tipi" required>
      <option value="yuzde">Yüzde</option>
      <option value="tutar">Tutar</option>
    </select>
  </div>
  <div class="form-group">
    <label>İndirim Değeri</label>
    <input type="number" name="indirim_degeri" step="0.01" required />
  </div>
  <div class="form-group">
    <label>Başlangıç Tarihi</label>
    <input type="datetime-local" name="baslangic_tarihi" required />
  </div>
  <div class="form-group">
    <label>Bitiş Tarihi</label>
    <input type="datetime-local" name="bitis_tarihi" required />
  </div>
  <button type="submit">Kampanya Oluştur</button>
</form>

<!-- Aktif Kampanyalar -->
<div class="mt-6">
  <h3>Aktif Kampanyalar</h3>
  <table id="kampanya-table" class="datatable"></table>
</div>
```

### JavaScript Modülleri

```javascript
// static/js/fiyatlandirma.js

class FiyatlandirmaManager {
  constructor() {
    this.apiBase = "/api/v1/fiyat";
  }

  async hesaplaVeGuncelleFiyat(urunId, odaId, miktar) {
    const response = await fetch(`${this.apiBase}/dinamik-hesapla`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ urun_id: urunId, oda_id: odaId, miktar: miktar }),
    });
    return await response.json();
  }

  async updateUrunFiyat(urunId, fiyatData) {
    const response = await fetch(`${this.apiBase}/urun/${urunId}/guncelle`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(fiyatData),
    });
    return await response.json();
  }
}

class KarlilikManager {
  constructor() {
    this.apiBase = "/api/v1/kar";
  }

  async loadUrunKarlilik(urunId, baslangic, bitis) {
    const response = await fetch(
      `${this.apiBase}/urun/${urunId}?baslangic=${baslangic}&bitis=${bitis}`
    );
    return await response.json();
  }

  async loadDonemselKar(otelId, donemTipi, baslangic, bitis) {
    const response = await fetch(
      `${this.apiBase}/donemsel?otel_id=${otelId}&donem=${donemTipi}&baslangic=${baslangic}&bitis=${bitis}`
    );
    return await response.json();
  }

  renderKarTrendChart(data) {
    const ctx = document.getElementById("kar-trend-chart").getContext("2d");
    new Chart(ctx, {
      type: "line",
      data: {
        labels: data.labels,
        datasets: [
          {
            label: "Net Kar",
            data: data.values,
            borderColor: "rgb(75, 192, 192)",
            tension: 0.1,
          },
        ],
      },
    });
  }
}
```

## Performans Optimizasyonu

### Redis Cache Stratejisi

```python
from flask_caching import Cache

cache = Cache(config={
    'CACHE_TYPE': 'redis',
    'CACHE_REDIS_URL': 'redis://localhost:6379/0',
    'CACHE_DEFAULT_TIMEOUT': 3600
})

class FiyatCache:
    @staticmethod
    @cache.memoize(timeout=3600)  # 1 saat
    def get_urun_fiyat(urun_id, oda_tipi, tarih):
        """Ürün fiyatını cache'den getir"""
        return FiyatYonetimServisi.dinamik_fiyat_hesapla(urun_id, oda_tipi, tarih)

    @staticmethod
    @cache.memoize(timeout=1800)  # 30 dakika
    def get_kar_analizi(otel_id, baslangic, bitis):
        """Kar analizini cache'den getir"""
        return KarHesaplamaServisi.donemsel_kar_analizi(otel_id, baslangic, bitis)

    @staticmethod
    def invalidate_urun_fiyat(urun_id):
        """Ürün fiyat cache'ini temizle"""
        cache.delete_memoized(FiyatCache.get_urun_fiyat, urun_id)
```

### Celery Asenkron İşlemler

```python
from celery import Celery

celery = Celery('minibar_takip', broker='redis://localhost:6379/1')

@celery.task
def donemsel_kar_hesapla_async(otel_id, baslangic, bitis):
    """Dönemsel kar hesaplama - asenkron"""
    try:
        sonuc = KarHesaplamaServisi.donemsel_kar_analizi(otel_id, baslangic, bitis)
        # Sonucu veritabanına kaydet
        analiz = DonemselKarAnalizi(**sonuc)
        db.session.add(analiz)
        db.session.commit()
        return {'status': 'success', 'analiz_id': analiz.id}
    except Exception as e:
        return {'status': 'error', 'message': str(e)}

@celery.task
def tuketim_trendi_guncelle_async():
    """Tüketim trendi güncelleme - asenkron"""
    pass
```

## Güvenlik ve Yetkilendirme

### Rol Bazlı Erişim Kontrolü

```python
from functools import wraps
from flask import abort
from flask_login import current_user

def role_required(roles):
    """Rol bazlı erişim kontrolü decorator"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated:
                abort(401)
            if current_user.rol not in roles:
                abort(403)
            return f(*args, **kwargs)
        return decorated_function
    return decorator

# Kullanım
@fiyatlandirma_bp.route('/api/v1/fiyat/urun/<int:urun_id>/guncelle', methods=['POST'])
@login_required
@role_required(['sistem_yoneticisi', 'admin', 'depo_sorumlusu'])
def update_urun_fiyat(urun_id):
    pass
```

### Audit Trail Entegrasyonu

```python
def log_fiyat_degisiklik(urun_id, eski_fiyat, yeni_fiyat, degisiklik_tipi, sebep):
    """Fiyat değişikliğini logla"""
    gecmis = UrunFiyatGecmisi(
        urun_id=urun_id,
        eski_fiyat=eski_fiyat,
        yeni_fiyat=yeni_fiyat,
        degisiklik_tipi=degisiklik_tipi,
        degisiklik_sebebi=sebep,
        olusturan_id=current_user.id
    )
    db.session.add(gecmis)

    # Audit log'a da kaydet
    audit_log = AuditLog(
        kullanici_id=current_user.id,
        kullanici_adi=current_user.kullanici_adi,
        kullanici_rol=current_user.rol,
        islem_tipi='update',
        tablo_adi='urun_fiyat',
        kayit_id=urun_id,
        eski_deger={'fiyat': float(eski_fiyat)},
        yeni_deger={'fiyat': float(yeni_fiyat)},
        degisiklik_ozeti=f"Fiyat {eski_fiyat} -> {yeni_fiyat}"
    )
    db.session.add(audit_log)
    db.session.commit()
```

## Veri Migrasyonu Stratejisi

### Migration Script Yapısı

```python
# migrations/add_fiyatlandirma_sistemi.py

def upgrade():
    """Fiyatlandırma sistemini ekle"""

    # 1. Yeni tabloları oluştur
    create_new_tables()

    # 2. Mevcut tablolara kolonlar ekle
    add_columns_to_existing_tables()

    # 3. Index'leri oluştur
    create_indexes()

    # 4. Varsayılan verileri ekle
    insert_default_data()

    # 5. Mevcut verilere fiyat ata
    migrate_existing_data()

def downgrade():
    """Rollback işlemi"""

    # 1. Eklenen kolonları kaldır
    remove_added_columns()

    # 2. Yeni tabloları sil
    drop_new_tables()
```

### Veri Migrasyonu Adımları

```python
def migrate_existing_data():
    """Mevcut verilere fiyat bilgisi ekle"""

    # 1. Tüm ürünlere varsayılan alış fiyatı ata
    urunler = Urun.query.all()
    for urun in urunler:
        varsayilan_fiyat = UrunTedarikciFiyat(
            urun_id=urun.id,
            tedarikci_id=1,  # Varsayılan tedarikçi
            alis_fiyati=10.00,  # Varsayılan fiyat
            baslangic_tarihi=datetime.now(timezone.utc),
            aktif=True,
            olusturan_id=1  # Sistem kullanıcısı
        )
        db.session.add(varsayilan_fiyat)

    # 2. Geçmiş işlemlere tarihsel fiyat hesapla
    islemler = MinibarIslemDetay.query.filter(
        MinibarIslemDetay.satis_fiyati.is_(None)
    ).all()

    for islem in islemler:
        # Tarihsel fiyat hesaplama mantığı
        islem.alis_fiyati = 10.00
        islem.satis_fiyati = 15.00
        islem.kar_tutari = 5.00
        islem.kar_orani = 33.33

    db.session.commit()
```

## Test Stratejisi

### Unit Test Örnekleri

```python
# tests/test_fiyatlandirma.py

class TestFiyatYonetimServisi(unittest.TestCase):

    def test_dinamik_fiyat_hesaplama(self):
        """Dinamik fiyat hesaplama testi"""
        sonuc = FiyatYonetimServisi.dinamik_fiyat_hesapla(
            urun_id=1,
            oda_id=1,
            tarih=datetime.now(),
            miktar=2
        )
        self.assertIsNotNone(sonuc['satis_fiyati'])
        self.assertGreater(sonuc['satis_fiyati'], sonuc['alis_fiyati'])

    def test_kampanya_uygulama(self):
        """Kampanya uygulama testi"""
        fiyat = Decimal('100.00')
        indirimli = KampanyaServisi.kampanya_uygula(
            kampanya_id=1,
            fiyat=fiyat,
            miktar=2
        )
        self.assertLess(indirimli, fiyat)

    def test_bedelsiz_limit_kontrolu(self):
        """Bedelsiz limit kontrolü testi"""
        bedelsiz, ucretli = BedelsizServisi.limit_kontrol(
            oda_id=1,
            urun_id=1,
            miktar=5
        )
        self.assertEqual(bedelsiz + ucretli, 5)
```

## Hata Yönetimi

### Exception Handling

```python
class FiyatlandirmaException(Exception):
    """Fiyatlandırma sistemi genel exception"""
    pass

class FiyatBulunamadiException(FiyatlandirmaException):
    """Fiyat bulunamadı exception"""
    pass

class BedelsizLimitAsimException(FiyatlandirmaException):
    """Bedelsiz limit aşımı exception"""
    pass

# Kullanım
try:
    fiyat = FiyatYonetimServisi.dinamik_fiyat_hesapla(urun_id, oda_id)
except FiyatBulunamadiException as e:
    logger.error(f"Fiyat bulunamadı: {e}")
    return jsonify({'error': 'Fiyat bilgisi bulunamadı'}), 404
except Exception as e:
    logger.error(f"Beklenmeyen hata: {e}")
    return jsonify({'error': 'Sistem hatası'}), 500
```

## Monitoring ve Logging

```python
import logging

logger = logging.getLogger('fiyatlandirma')

def log_fiyat_hesaplama(urun_id, sonuc):
    """Fiyat hesaplama logla"""
    logger.info(f"Fiyat hesaplandı - Ürün: {urun_id}, Sonuç: {sonuc}")

def log_kar_analizi(otel_id, kar_marji):
    """Kar analizi logla"""
    logger.info(f"Kar analizi - Otel: {otel_id}, Marj: {kar_marji}%")
```

---

## Sonuç

Bu tasarım dokümanı, fiyatlandırma ve karlılık hesaplama sisteminin tüm teknik detaylarını içermektedir. Sistem:

- **10 yeni tablo** ile veri modeli genişletilmiştir
- **5 ana servis sınıfı** ile iş mantığı organize edilmiştir
- **RESTful API** yapısı ile frontend entegrasyonu sağlanmıştır
- **Redis cache** ve **Celery** ile performans optimize edilmiştir
- **Rol bazlı erişim** ve **audit trail** ile güvenlik sağlanmıştır
- **Kapsamlı test stratejisi** ile kalite garanti edilmiştir

Sistem, mevcut mini bar stok takip altyapısı ile tam uyumlu çalışacak şekilde tasarlanmıştır.

## Ek: Ürün Stok Takip Tablosu

### UrunStok Tablosu

```python
class UrunStok(db.Model):
    """Ürün stok durumu - Gerçek zamanlı stok takibi"""
    __tablename__ = 'urun_stok'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    urun_id = db.Column(db.Integer, db.ForeignKey('urunler.id', ondelete='CASCADE'), nullable=False, unique=True)
    otel_id = db.Column(db.Integer, db.ForeignKey('oteller.id', ondelete='CASCADE'), nullable=False)

    # Stok Bilgileri
    mevcut_stok = db.Column(db.Integer, default=0, nullable=False)
    minimum_stok = db.Column(db.Integer, default=10, nullable=False)
    maksimum_stok = db.Column(db.Integer, default=1000, nullable=False)
    kritik_stok_seviyesi = db.Column(db.Integer, default=5, nullable=False)

    # Değer Bilgileri
    birim_maliyet = db.Column(Numeric(10, 2), default=0)  # Ortalama alış fiyatı
    toplam_deger = db.Column(Numeric(12, 2), default=0)  # mevcut_stok × birim_maliyet

    # Stok Devir Bilgileri
    son_30gun_cikis = db.Column(db.Integer, default=0)  # Son 30 günde çıkan miktar
    stok_devir_hizi = db.Column(Numeric(5, 2), default=0)  # Aylık devir hızı

    # Güncelleme Bilgileri
    son_giris_tarihi = db.Column(db.DateTime(timezone=True), nullable=True)
    son_cikis_tarihi = db.Column(db.DateTime(timezone=True), nullable=True)
    son_guncelleme_tarihi = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    son_guncelleyen_id = db.Column(db.Integer, db.ForeignKey('kullanicilar.id'), nullable=True)

    # Sayım Bilgileri
    son_sayim_tarihi = db.Column(db.DateTime(timezone=True), nullable=True)
    son_sayim_miktari = db.Column(db.Integer, nullable=True)
    sayim_farki = db.Column(db.Integer, default=0)  # Beklenen - Gerçek

    # İlişkiler
    urun = db.relationship('Urun', backref=db.backref('stok', uselist=False))
    otel = db.relationship('Otel', backref='urun_stoklari')
    son_guncelleyen = db.relationship('Kullanici')

    __table_args__ = (
        db.Index('idx_urun_stok_otel', 'otel_id', 'urun_id'),
        db.Index('idx_urun_stok_kritik', 'mevcut_stok', 'kritik_stok_seviyesi'),
        db.CheckConstraint('mevcut_stok >= 0', name='check_stok_pozitif'),
        db.CheckConstraint('minimum_stok >= 0', name='check_min_stok_pozitif'),
    )

    def stok_durumu(self):
        """Stok durumunu döndür"""
        if self.mevcut_stok <= self.kritik_stok_seviyesi:
            return 'kritik'
        elif self.mevcut_stok <= self.minimum_stok:
            return 'dusuk'
        elif self.mevcut_stok >= self.maksimum_stok:
            return 'fazla'
        return 'normal'

    def stok_guncelle(self, miktar, islem_tipi, kullanici_id):
        """Stok miktarını güncelle"""
        if islem_tipi in ['giris', 'devir']:
            self.mevcut_stok += miktar
            self.son_giris_tarihi = datetime.now(timezone.utc)
        elif islem_tipi in ['cikis', 'fire']:
            self.mevcut_stok -= miktar
            self.son_cikis_tarihi = datetime.now(timezone.utc)
            self.son_30gun_cikis += miktar
        elif islem_tipi == 'sayim':
            self.sayim_farki = self.mevcut_stok - miktar
            self.mevcut_stok = miktar
            self.son_sayim_tarihi = datetime.now(timezone.utc)
            self.son_sayim_miktari = miktar

        self.son_guncelleme_tarihi = datetime.now(timezone.utc)
        self.son_guncelleyen_id = kullanici_id
        self.toplam_deger = self.mevcut_stok * (self.birim_maliyet or 0)

        # Stok devir hızını hesapla (aylık)
        if self.mevcut_stok > 0:
            self.stok_devir_hizi = self.son_30gun_cikis / self.mevcut_stok
```

### StokHareket Tablosu Güncellemesi

```python
# Mevcut StokHareket modeline trigger ekle
class StokHareket(db.Model):
    # ... mevcut kolonlar ...

    def after_insert_listener(mapper, connection, target):
        """Stok hareketi sonrası UrunStok'u güncelle"""
        urun_stok = UrunStok.query.filter_by(urun_id=target.urun_id).first()
        if urun_stok:
            urun_stok.stok_guncelle(
                miktar=target.miktar,
                islem_tipi=target.hareket_tipi,
                kullanici_id=target.islem_yapan_id
            )
            db.session.commit()

# SQLAlchemy event listener
from sqlalchemy import event
event.listen(StokHareket, 'after_insert', StokHareket.after_insert_listener)
```

### StokYonetimServisi

```python
class StokYonetimServisi:
    """Stok yönetim servisi"""

    @staticmethod
    def stok_durumu_getir(urun_id, otel_id):
        """Ürün stok durumunu getir"""
        stok = UrunStok.query.filter_by(
            urun_id=urun_id,
            otel_id=otel_id
        ).first()

        if not stok:
            return None

        return {
            'mevcut_stok': stok.mevcut_stok,
            'durum': stok.stok_durumu(),
            'toplam_deger': float(stok.toplam_deger),
            'stok_devir_hizi': float(stok.stok_devir_hizi),
            'son_guncelleme': stok.son_guncelleme_tarihi
        }

    @staticmethod
    def kritik_stoklar_getir(otel_id):
        """Kritik seviyedeki stokları getir"""
        return UrunStok.query.filter(
            UrunStok.otel_id == otel_id,
            UrunStok.mevcut_stok <= UrunStok.kritik_stok_seviyesi
        ).all()

    @staticmethod
    def stok_sayim_yap(urun_id, otel_id, sayilan_miktar, kullanici_id):
        """Stok sayımı yap ve farkı hesapla"""
        stok = UrunStok.query.filter_by(
            urun_id=urun_id,
            otel_id=otel_id
        ).first()

        if not stok:
            raise Exception("Stok kaydı bulunamadı")

        onceki_miktar = stok.mevcut_stok
        stok.stok_guncelle(sayilan_miktar, 'sayim', kullanici_id)

        # Fark varsa StokHareket'e kaydet
        if stok.sayim_farki != 0:
            hareket = StokHareket(
                urun_id=urun_id,
                hareket_tipi='sayim',
                miktar=abs(stok.sayim_farki),
                aciklama=f"Sayım farkı: Beklenen {onceki_miktar}, Sayılan {sayilan_miktar}",
                islem_yapan_id=kullanici_id
            )
            db.session.add(hareket)

        db.session.commit()
        return stok.sayim_farki

    @staticmethod
    def stok_devir_raporu(otel_id, baslangic, bitis):
        """Stok devir hızı raporu"""
        stoklar = UrunStok.query.filter_by(otel_id=otel_id).all()

        rapor = []
        for stok in stoklar:
            # Dönem içindeki çıkışları hesapla
            cikislar = db.session.query(
                db.func.sum(StokHareket.miktar)
            ).filter(
                StokHareket.urun_id == stok.urun_id,
                StokHareket.hareket_tipi == 'cikis',
                StokHareket.islem_tarihi.between(baslangic, bitis)
            ).scalar() or 0

            # Ortalama stok
            ortalama_stok = stok.mevcut_stok  # Basitleştirilmiş

            # Devir hızı
            devir_hizi = cikislar / ortalama_stok if ortalama_stok > 0 else 0

            rapor.append({
                'urun': stok.urun.urun_adi,
                'cikis': cikislar,
                'ortalama_stok': ortalama_stok,
                'devir_hizi': devir_hizi,
                'durum': 'hizli' if devir_hizi > 2 else 'yavas' if devir_hizi < 0.5 else 'normal'
            })

        return rapor

    @staticmethod
    def stok_deger_raporu(otel_id):
        """Toplam stok değeri raporu"""
        toplam = db.session.query(
            db.func.sum(UrunStok.toplam_deger)
        ).filter(
            UrunStok.otel_id == otel_id
        ).scalar() or 0

        kategori_bazli = db.session.query(
            UrunGrup.grup_adi,
            db.func.sum(UrunStok.toplam_deger).label('toplam')
        ).join(
            Urun, Urun.grup_id == UrunGrup.id
        ).join(
            UrunStok, UrunStok.urun_id == Urun.id
        ).filter(
            UrunStok.otel_id == otel_id
        ).group_by(
            UrunGrup.grup_adi
        ).all()

        return {
            'toplam_deger': float(toplam),
            'kategori_bazli': [
                {'kategori': k, 'deger': float(d)}
                for k, d in kategori_bazli
            ]
        }
```

### API Endpoint'leri

```python
@stok_bp.route('/api/v1/stok/durum/<int:urun_id>', methods=['GET'])
@login_required
def get_stok_durum(urun_id):
    """Ürün stok durumunu getir"""
    otel_id = request.args.get('otel_id', type=int)
    stok = StokYonetimServisi.stok_durumu_getir(urun_id, otel_id)
    return jsonify(stok)

@stok_bp.route('/api/v1/stok/kritik', methods=['GET'])
@login_required
def get_kritik_stoklar():
    """Kritik stokları getir"""
    otel_id = request.args.get('otel_id', type=int)
    stoklar = StokYonetimServisi.kritik_stoklar_getir(otel_id)
    return jsonify([{
        'urun_id': s.urun_id,
        'urun_adi': s.urun.urun_adi,
        'mevcut_stok': s.mevcut_stok,
        'kritik_seviye': s.kritik_stok_seviyesi
    } for s in stoklar])

@stok_bp.route('/api/v1/stok/sayim', methods=['POST'])
@login_required
@role_required(['sistem_yoneticisi', 'admin', 'depo_sorumlusu'])
def stok_sayim():
    """Stok sayımı yap"""
    data = request.get_json()
    fark = StokYonetimServisi.stok_sayim_yap(
        urun_id=data['urun_id'],
        otel_id=data['otel_id'],
        sayilan_miktar=data['miktar'],
        kullanici_id=current_user.id
    )
    return jsonify({'fark': fark, 'message': 'Sayım tamamlandı'})

@stok_bp.route('/api/v1/stok/devir-raporu', methods=['GET'])
@login_required
def get_devir_raporu():
    """Stok devir raporu"""
    otel_id = request.args.get('otel_id', type=int)
    baslangic = request.args.get('baslangic')
    bitis = request.args.get('bitis')
    rapor = StokYonetimServisi.stok_devir_raporu(otel_id, baslangic, bitis)
    return jsonify(rapor)

@stok_bp.route('/api/v1/stok/deger-raporu', methods=['GET'])
@login_required
def get_deger_raporu():
    """Stok değer raporu"""
    otel_id = request.args.get('otel_id', type=int)
    rapor = StokYonetimServisi.stok_deger_raporu(otel_id)
    return jsonify(rapor)
```

### Migration Script Eklentisi

```python
def create_urun_stok_table():
    """UrunStok tablosunu oluştur"""
    op.create_table(
        'urun_stok',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('urun_id', sa.Integer(), sa.ForeignKey('urunler.id'), nullable=False),
        sa.Column('otel_id', sa.Integer(), sa.ForeignKey('oteller.id'), nullable=False),
        sa.Column('mevcut_stok', sa.Integer(), default=0, nullable=False),
        sa.Column('minimum_stok', sa.Integer(), default=10, nullable=False),
        sa.Column('maksimum_stok', sa.Integer(), default=1000, nullable=False),
        sa.Column('kritik_stok_seviyesi', sa.Integer(), default=5, nullable=False),
        sa.Column('birim_maliyet', sa.Numeric(10, 2), default=0),
        sa.Column('toplam_deger', sa.Numeric(12, 2), default=0),
        sa.Column('son_30gun_cikis', sa.Integer(), default=0),
        sa.Column('stok_devir_hizi', sa.Numeric(5, 2), default=0),
        sa.Column('son_giris_tarihi', sa.DateTime(timezone=True)),
        sa.Column('son_cikis_tarihi', sa.DateTime(timezone=True)),
        sa.Column('son_guncelleme_tarihi', sa.DateTime(timezone=True)),
        sa.Column('son_guncelleyen_id', sa.Integer(), sa.ForeignKey('kullanicilar.id')),
        sa.Column('son_sayim_tarihi', sa.DateTime(timezone=True)),
        sa.Column('son_sayim_miktari', sa.Integer()),
        sa.Column('sayim_farki', sa.Integer(), default=0),
    )

    # Index'ler
    op.create_index('idx_urun_stok_otel', 'urun_stok', ['otel_id', 'urun_id'])
    op.create_index('idx_urun_stok_kritik', 'urun_stok', ['mevcut_stok', 'kritik_stok_seviyesi'])

def populate_urun_stok():
    """Mevcut ürünler için stok kayıtları oluştur"""
    # Tüm ürünler için başlangıç stok kaydı oluştur
    urunler = Urun.query.all()
    for urun in urunler:
        # Her otel için ayrı stok kaydı
        oteller = Otel.query.filter_by(aktif=True).all()
        for otel in oteller:
            stok = UrunStok(
                urun_id=urun.id,
                otel_id=otel.id,
                mevcut_stok=0,
                minimum_stok=urun.kritik_stok_seviyesi or 10,
                kritik_stok_seviyesi=urun.kritik_stok_seviyesi or 5
            )
            db.session.add(stok)

    db.session.commit()
```

Bu ekleme ile artık:

- ✅ Ürün stokları ayrı tabloda tutulacak
- ✅ Gerçek zamanlı stok güncellemesi olacak
- ✅ Stok devir hızı hesaplanacak
- ✅ Kritik stok uyarıları verilecek
- ✅ Stok değer raporları oluşturulacak
- ✅ Stok sayım ve fark analizi yapılacak
