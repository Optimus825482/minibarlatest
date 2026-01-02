"""
Otel Modelleri

Otel, Kat, Oda, OdaTipi, Setup ve ilgili modeller.
"""

from models.base import db, get_kktc_now


# Many-to-Many ara tablo: OdaTipi <-> Setup (Otel bazlı)
oda_tipi_setup = db.Table('oda_tipi_setup',
    db.Column('otel_id', db.Integer, db.ForeignKey('oteller.id', ondelete='CASCADE'), primary_key=True),
    db.Column('oda_tipi_id', db.Integer, db.ForeignKey('oda_tipleri.id', ondelete='CASCADE'), primary_key=True),
    db.Column('setup_id', db.Integer, db.ForeignKey('setuplar.id', ondelete='CASCADE'), primary_key=True),
    db.Column('olusturma_tarihi', db.DateTime(timezone=True), default=lambda: get_kktc_now())
)


class Otel(db.Model):
    """Otel bilgileri tablosu"""
    __tablename__ = 'oteller'
    
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    ad = db.Column(db.String(200), nullable=False)
    adres = db.Column(db.Text)
    telefon = db.Column(db.String(20))
    email = db.Column(db.String(100))
    vergi_no = db.Column(db.String(50))
    logo = db.Column(db.Text, nullable=True)
    olusturma_tarihi = db.Column(db.DateTime(timezone=True), default=lambda: get_kktc_now())
    aktif = db.Column(db.Boolean, default=True)
    
    # İlk stok yükleme durumu
    ilk_stok_yuklendi = db.Column(db.Boolean, default=False)
    ilk_stok_yukleme_tarihi = db.Column(db.DateTime(timezone=True), nullable=True)
    ilk_stok_yukleyen_id = db.Column(db.Integer, db.ForeignKey('kullanicilar.id', ondelete='SET NULL'), nullable=True)
    
    # E-posta Bildirim Ayarları
    email_bildirim_aktif = db.Column(db.Boolean, default=False)
    email_uyari_aktif = db.Column(db.Boolean, default=False)
    email_rapor_aktif = db.Column(db.Boolean, default=False)
    email_sistem_aktif = db.Column(db.Boolean, default=False)
    
    # İlişkiler
    katlar = db.relationship('Kat', backref='otel', lazy=True, cascade='all, delete-orphan')
    kullanici_atamalari = db.relationship('KullaniciOtel', backref='otel', lazy=True, cascade='all, delete-orphan')
    
    def get_depo_sorumlu_sayisi(self):
        """Bu otele atanan depo sorumlusu sayısı"""
        try:
            from models.kullanici import KullaniciOtel, Kullanici
            return KullaniciOtel.query.join(Kullanici).filter(
                KullaniciOtel.otel_id == self.id,
                Kullanici.rol == 'depo_sorumlusu'
            ).count()
        except Exception:
            return 0
    
    def get_kat_sorumlu_sayisi(self):
        """Bu otele atanan kat sorumlusu sayısı"""
        try:
            from models.kullanici import Kullanici
            return Kullanici.query.filter(
                Kullanici.otel_id == self.id,
                Kullanici.rol == 'kat_sorumlusu'
            ).count()
        except Exception:
            return 0
    
    def __repr__(self):
        return f'<Otel {self.ad}>'


class Kat(db.Model):
    """Katlar tablosu"""
    __tablename__ = 'katlar'
    
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    otel_id = db.Column(db.Integer, db.ForeignKey('oteller.id'), nullable=False)
    kat_adi = db.Column(db.String(50), nullable=False)
    kat_no = db.Column(db.Integer, nullable=False)
    aciklama = db.Column(db.Text)
    aktif = db.Column(db.Boolean, default=True)
    olusturma_tarihi = db.Column(db.DateTime(timezone=True), default=lambda: get_kktc_now())
    
    # İlişkiler
    odalar = db.relationship('Oda', backref='kat', lazy=True, cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<Kat {self.kat_adi}>'


class OdaTipi(db.Model):
    """Oda tipleri tablosu"""
    __tablename__ = 'oda_tipleri'
    
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    ad = db.Column(db.String(100), nullable=False, unique=True)
    dolap_sayisi = db.Column(db.Integer, default=0)
    aktif = db.Column(db.Boolean, default=True)
    olusturma_tarihi = db.Column(db.DateTime(timezone=True), default=lambda: get_kktc_now())
    
    # Many-to-Many ilişki
    setuplar = db.relationship('Setup', secondary=oda_tipi_setup, backref=db.backref('oda_tipleri', lazy='dynamic'))
    
    def __repr__(self):
        return f'<OdaTipi {self.ad}>'


class Oda(db.Model):
    """Odalar tablosu"""
    __tablename__ = 'odalar'
    __table_args__ = (
        db.Index('idx_qr_token', 'qr_kod_token'),
    )
    
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    kat_id = db.Column(db.Integer, db.ForeignKey('katlar.id'), nullable=False)
    oda_no = db.Column(db.String(20), nullable=False, unique=True)
    oda_tipi_id = db.Column(db.Integer, db.ForeignKey('oda_tipleri.id'), nullable=True)
    kapasite = db.Column(db.Integer)
    aktif = db.Column(db.Boolean, default=True)
    olusturma_tarihi = db.Column(db.DateTime(timezone=True), default=lambda: get_kktc_now())
    
    # QR Kod Alanları
    qr_kod_token = db.Column(db.String(64), unique=True, nullable=True)
    qr_kod_gorsel = db.Column(db.Text, nullable=True)
    qr_kod_olusturma_tarihi = db.Column(db.DateTime(timezone=True), nullable=True)
    misafir_mesaji = db.Column(db.String(500), nullable=True)
    
    # İlişkiler
    oda_tipi_rel = db.relationship('OdaTipi', foreign_keys=[oda_tipi_id], backref='odalar')
    minibar_islemleri = db.relationship('MinibarIslem', backref='oda', lazy=True)
    dolum_talepleri = db.relationship('MinibarDolumTalebi', backref='oda', lazy=True)
    qr_okutma_loglari = db.relationship('QRKodOkutmaLog', backref='oda', lazy=True)
    
    @property
    def oda_tipi_adi(self):
        """Oda tipi adını döndür"""
        if self.oda_tipi_rel:
            return self.oda_tipi_rel.ad
        return None
    
    def __repr__(self):
        return f'<Oda {self.oda_no}>'


class Setup(db.Model):
    """Setup tanımları tablosu"""
    __tablename__ = 'setuplar'
    
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    ad = db.Column(db.String(100), nullable=False, unique=True)
    aciklama = db.Column(db.String(500))
    dolap_ici = db.Column(db.Boolean, default=True)
    aktif = db.Column(db.Boolean, default=True)
    olusturma_tarihi = db.Column(db.DateTime(timezone=True), default=lambda: get_kktc_now())
    
    # İlişkiler
    icerikler = db.relationship('SetupIcerik', backref='setup', lazy=True, cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<Setup {self.ad}>'


class SetupIcerik(db.Model):
    """Setup içerik tablosu"""
    __tablename__ = 'setup_icerik'
    
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    setup_id = db.Column(db.Integer, db.ForeignKey('setuplar.id'), nullable=False)
    urun_id = db.Column(db.Integer, db.ForeignKey('urunler.id'), nullable=False)
    adet = db.Column(db.Integer, nullable=False, default=1)
    olusturma_tarihi = db.Column(db.DateTime(timezone=True), default=lambda: get_kktc_now())
    
    # İlişkiler
    urun = db.relationship('Urun', backref='setup_icerikler')
    
    def __repr__(self):
        return f'<SetupIcerik Setup:{self.setup_id} Urun:{self.urun_id}>'
