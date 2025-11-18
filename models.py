from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timezone
from sqlalchemy import Numeric
from sqlalchemy.dialects.postgresql import JSONB
import enum

db = SQLAlchemy()

# PostgreSQL Only - MySQL support removed
JSONType = JSONB

# PostgreSQL ENUM Types
# Bu enum'lar hem MySQL hem PostgreSQL ile uyumlu çalışır
class KullaniciRol(str, enum.Enum):
    SISTEM_YONETICISI = 'sistem_yoneticisi'
    ADMIN = 'admin'
    DEPO_SORUMLUSU = 'depo_sorumlusu'
    KAT_SORUMLUSU = 'kat_sorumlusu'

class HareketTipi(str, enum.Enum):
    GIRIS = 'giris'
    CIKIS = 'cikis'
    DEVIR = 'devir'
    SAYIM = 'sayim'

class ZimmetDurum(str, enum.Enum):
    AKTIF = 'aktif'
    TAMAMLANDI = 'tamamlandi'
    IPTAL = 'iptal'

class MinibarIslemTipi(str, enum.Enum):
    ILK_DOLUM = 'ilk_dolum'
    YENIDEN_DOLUM = 'yeniden_dolum'
    EKSIK_TAMAMLAMA = 'eksik_tamamlama'
    SAYIM = 'sayim'
    DUZELTME = 'duzeltme'
    KONTROL = 'kontrol'
    DOLDURMA = 'doldurma'
    EK_DOLUM = 'ek_dolum'
    SETUP_KONTROL = 'setup_kontrol'
    EKSTRA_EKLEME = 'ekstra_ekleme'
    EKSTRA_TUKETIM = 'ekstra_tuketim'

class AuditIslemTipi(str, enum.Enum):
    CREATE = 'create'
    UPDATE = 'update'
    DELETE = 'delete'
    LOGIN = 'login'
    LOGOUT = 'logout'
    VIEW = 'view'
    EXPORT = 'export'
    IMPORT = 'import'

class RaporTipi(str, enum.Enum):
    GUNLUK_STOK = 'gunluk_stok'
    STOK_KONTROLU = 'stok_kontrolu'
    ZIMMET_OZETI = 'zimmet_ozeti'
    MINIBAR_TUKETIM = 'minibar_tuketim'

class DolumTalebiDurum(str, enum.Enum):
    BEKLEMEDE = 'beklemede'
    TAMAMLANDI = 'tamamlandi'
    IPTAL = 'iptal'

class QROkutmaTipi(str, enum.Enum):
    KAT_SORUMLUSU = 'kat_sorumlusu'
    MISAFIR = 'misafir'

class Otel(db.Model):
    """Otel bilgileri tablosu"""
    __tablename__ = 'oteller'
    
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    ad = db.Column(db.String(200), nullable=False)
    adres = db.Column(db.Text)
    telefon = db.Column(db.String(20))
    email = db.Column(db.String(100))
    vergi_no = db.Column(db.String(50))
    logo = db.Column(db.Text, nullable=True)  # Base64 encoded logo
    olusturma_tarihi = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    aktif = db.Column(db.Boolean, default=True)
    
    # İlişkiler
    katlar = db.relationship('Kat', backref='otel', lazy=True, cascade='all, delete-orphan')
    kullanici_atamalari = db.relationship('KullaniciOtel', backref='otel', lazy=True, cascade='all, delete-orphan')
    
    def get_depo_sorumlu_sayisi(self):
        """Bu otele atanan depo sorumlusu sayısı"""
        try:
            from models import KullaniciOtel, Kullanici
            return KullaniciOtel.query.join(Kullanici).filter(
                KullaniciOtel.otel_id == self.id,
                Kullanici.rol == 'depo_sorumlusu'
            ).count()
        except Exception as e:
            return 0
    
    def get_kat_sorumlu_sayisi(self):
        """Bu otele atanan kat sorumlusu sayısı"""
        try:
            from models import Kullanici
            return Kullanici.query.filter(
                Kullanici.otel_id == self.id,
                Kullanici.rol == 'kat_sorumlusu'
            ).count()
        except Exception as e:
            return 0
    
    def __repr__(self):
        return f'<Otel {self.ad}>'


class KullaniciOtel(db.Model):
    """Kullanıcı-Otel ilişki tablosu (Many-to-Many) - Depo sorumluları için"""
    __tablename__ = 'kullanici_otel'
    
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    kullanici_id = db.Column(db.Integer, db.ForeignKey('kullanicilar.id', ondelete='CASCADE'), nullable=False)
    otel_id = db.Column(db.Integer, db.ForeignKey('oteller.id', ondelete='CASCADE'), nullable=False)
    olusturma_tarihi = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    
    # NOT: 'otel' ilişkisi Otel modelinde backref ile tanımlı (satır 93)
    # Burada tekrar tanımlamaya gerek yok
    
    # Unique constraint - Aynı kullanıcı aynı otele birden fazla kez atanamaz
    __table_args__ = (
        db.UniqueConstraint('kullanici_id', 'otel_id', name='uq_kullanici_otel'),
        db.Index('idx_kullanici_otel', 'kullanici_id', 'otel_id'),
    )
    
    def __repr__(self):
        return f'<KullaniciOtel kullanici_id={self.kullanici_id} otel_id={self.otel_id}>'


class Kullanici(db.Model):
    """Kullanıcılar tablosu - Tüm roller"""
    __tablename__ = 'kullanicilar'
    
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    kullanici_adi = db.Column(db.String(50), unique=True, nullable=False)
    sifre_hash = db.Column(db.String(255), nullable=False)
    ad = db.Column(db.String(100), nullable=False)
    soyad = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100))
    telefon = db.Column(db.String(20))
    rol = db.Column(db.Enum('sistem_yoneticisi', 'admin', 'depo_sorumlusu', 'kat_sorumlusu', name='kullanici_rol'), nullable=False)
    aktif = db.Column(db.Boolean, default=True)
    olusturma_tarihi = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    son_giris = db.Column(db.DateTime(timezone=True))
    
    # YENİ: Kat sorumlusu için tek otel ilişkisi
    otel_id = db.Column(db.Integer, db.ForeignKey('oteller.id', ondelete='SET NULL'), nullable=True)
    
    # YENİ: Kat sorumlusunun bağlı olduğu depo sorumlusu
    depo_sorumlusu_id = db.Column(db.Integer, db.ForeignKey('kullanicilar.id', ondelete='SET NULL'), nullable=True)
    
    # İlişkiler
    zimmet_kayitlari = db.relationship('PersonelZimmet', 
                                       foreign_keys='PersonelZimmet.personel_id',
                                       backref='personel', 
                                       lazy=True)
    teslim_ettigi_zimmetler = db.relationship('PersonelZimmet',
                                              foreign_keys='PersonelZimmet.teslim_eden_id',
                                              lazy=True)
    minibar_islemleri = db.relationship('MinibarIslem', backref='personel', lazy=True)
    
    # YENİ: Otel ilişkileri
    otel = db.relationship('Otel', foreign_keys=[otel_id], backref='kat_sorumlu_kullanicilar')
    atanan_oteller = db.relationship('KullaniciOtel', backref='kullanici', lazy=True, cascade='all, delete-orphan')
    
    # YENİ: Depo sorumlusu ilişkisi
    depo_sorumlusu = db.relationship('Kullanici', remote_side=[id], foreign_keys=[depo_sorumlusu_id], backref='bagli_kat_sorumlu')
    
    def sifre_belirle(self, sifre):
        """Şifreyi hashleyerek kaydet"""
        self.sifre_hash = generate_password_hash(sifre)
    
    def sifre_kontrol(self, sifre):
        """Şifre kontrolü"""
        return check_password_hash(self.sifre_hash, sifre)
    
    def __repr__(self):
        return f'<Kullanici {self.kullanici_adi} ({self.rol})>'


class Kat(db.Model):
    """Katlar tablosu"""
    __tablename__ = 'katlar'
    
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    otel_id = db.Column(db.Integer, db.ForeignKey('oteller.id'), nullable=False)
    kat_adi = db.Column(db.String(50), nullable=False)
    kat_no = db.Column(db.Integer, nullable=False)
    aciklama = db.Column(db.Text)
    aktif = db.Column(db.Boolean, default=True)
    olusturma_tarihi = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    
    # İlişkiler
    odalar = db.relationship('Oda', backref='kat', lazy=True, cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<Kat {self.kat_adi}>'


class Setup(db.Model):
    """Setup tanımları tablosu"""
    __tablename__ = 'setuplar'
    
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    ad = db.Column(db.String(100), nullable=False, unique=True)  # MINI, MAXI
    aciklama = db.Column(db.String(500))
    dolap_ici = db.Column(db.Boolean, default=True)  # True: Dolap İçi, False: Dolap Dışı
    aktif = db.Column(db.Boolean, default=True)
    olusturma_tarihi = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    
    # İlişkiler
    icerikler = db.relationship('SetupIcerik', backref='setup', lazy=True, cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<Setup {self.ad}>'


class SetupIcerik(db.Model):
    """Setup içerik tablosu - Setup'a atanan ürünler"""
    __tablename__ = 'setup_icerik'
    
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    setup_id = db.Column(db.Integer, db.ForeignKey('setuplar.id'), nullable=False)
    urun_id = db.Column(db.Integer, db.ForeignKey('urunler.id'), nullable=False)
    adet = db.Column(db.Integer, nullable=False, default=1)
    olusturma_tarihi = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    
    # İlişkiler
    urun = db.relationship('Urun', backref='setup_icerikler')
    
    def __repr__(self):
        return f'<SetupIcerik Setup:{self.setup_id} Urun:{self.urun_id}>'


# Many-to-Many ara tablo: OdaTipi <-> Setup
oda_tipi_setup = db.Table('oda_tipi_setup',
    db.Column('oda_tipi_id', db.Integer, db.ForeignKey('oda_tipleri.id'), primary_key=True),
    db.Column('setup_id', db.Integer, db.ForeignKey('setuplar.id'), primary_key=True),
    db.Column('olusturma_tarihi', db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
)


class OdaTipi(db.Model):
    """Oda tipleri tablosu"""
    __tablename__ = 'oda_tipleri'
    
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    ad = db.Column(db.String(100), nullable=False, unique=True)
    dolap_sayisi = db.Column(db.Integer, default=0)
    aktif = db.Column(db.Boolean, default=True)
    olusturma_tarihi = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    
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
    oda_tipi_id = db.Column(db.Integer, db.ForeignKey('oda_tipleri.id'), nullable=True)  # Oda tipi referansı
    kapasite = db.Column(db.Integer)
    aktif = db.Column(db.Boolean, default=True)
    olusturma_tarihi = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    
    # QR Kod Alanları
    qr_kod_token = db.Column(db.String(64), unique=True, nullable=True)
    qr_kod_gorsel = db.Column(db.Text, nullable=True)  # Base64 encoded PNG
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


class UrunGrup(db.Model):
    """Ürün grupları tablosu"""
    __tablename__ = 'urun_gruplari'
    
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    grup_adi = db.Column(db.String(100), nullable=False, unique=True)
    aciklama = db.Column(db.Text)
    aktif = db.Column(db.Boolean, default=True)
    olusturma_tarihi = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    
    # İlişkiler
    urunler = db.relationship('Urun', backref='grup', lazy=True)
    
    def __repr__(self):
        return f'<UrunGrup {self.grup_adi}>'


class Urun(db.Model):
    """Ürünler tablosu"""
    __tablename__ = 'urunler'
    
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    grup_id = db.Column(db.Integer, db.ForeignKey('urun_gruplari.id'), nullable=False)
    urun_kodu = db.Column(db.String(50), unique=True, nullable=True)  # Excel için ürün kodu
    urun_adi = db.Column(db.String(200), nullable=False)
    barkod = db.Column(db.String(50), unique=True)
    birim = db.Column(db.String(20), default='Adet')
    kritik_stok_seviyesi = db.Column(db.Integer, default=10)
    aktif = db.Column(db.Boolean, default=True)
    olusturma_tarihi = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    
    # Fiyatlandırma Kolonları
    satis_fiyati = db.Column(Numeric(10, 2), nullable=True)
    alis_fiyati = db.Column(Numeric(10, 2), nullable=True)
    kar_tutari = db.Column(Numeric(10, 2), nullable=True)
    kar_orani = db.Column(Numeric(5, 2), nullable=True)
    
    # İlişkiler
    stok_hareketleri = db.relationship('StokHareket', backref='urun', lazy=True)
    zimmet_detaylari = db.relationship('PersonelZimmetDetay', backref='urun', lazy=True)
    minibar_detaylari = db.relationship('MinibarIslemDetay', backref='urun', lazy=True)
    
    def __repr__(self):
        return f'<Urun {self.urun_adi}>'


class StokHareket(db.Model):
    """Stok hareketleri tablosu - Depo giriş/çıkış"""
    __tablename__ = 'stok_hareketleri'
    
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    urun_id = db.Column(db.Integer, db.ForeignKey('urunler.id'), nullable=False)
    hareket_tipi = db.Column(db.Enum('giris', 'cikis', 'transfer', 'devir', 'sayim', 'fire', name='hareket_tipi'), nullable=False)
    miktar = db.Column(db.Integer, nullable=False)
    aciklama = db.Column(db.Text)
    islem_yapan_id = db.Column(db.Integer, db.ForeignKey('kullanicilar.id'))
    islem_tarihi = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    
    # İlişki
    islem_yapan = db.relationship('Kullanici', foreign_keys=[islem_yapan_id])
    
    def __repr__(self):
        return f'<StokHareket {self.hareket_tipi} - {self.miktar}>'


class PersonelZimmet(db.Model):
    """Personel zimmet tablosu - Kat sorumlusu zimmet başlık"""
    __tablename__ = 'personel_zimmet'
    
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    personel_id = db.Column(db.Integer, db.ForeignKey('kullanicilar.id'), nullable=False)
    zimmet_tarihi = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    iade_tarihi = db.Column(db.DateTime(timezone=True), nullable=True)
    teslim_eden_id = db.Column(db.Integer, db.ForeignKey('kullanicilar.id'))
    durum = db.Column(db.Enum('aktif', 'iade_edildi', 'iptal', name='zimmet_durum'), default='aktif')
    aciklama = db.Column(db.Text)
    
    # İlişkiler
    teslim_eden = db.relationship('Kullanici', 
                                  foreign_keys=[teslim_eden_id],
                                  overlaps="teslim_ettigi_zimmetler")
    detaylar = db.relationship('PersonelZimmetDetay', backref='zimmet', lazy=True, cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<PersonelZimmet #{self.id}>'


class PersonelZimmetDetay(db.Model):
    """Personel zimmet detay tablosu"""
    __tablename__ = 'personel_zimmet_detay'
    
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    zimmet_id = db.Column(db.Integer, db.ForeignKey('personel_zimmet.id'), nullable=False)
    urun_id = db.Column(db.Integer, db.ForeignKey('urunler.id'), nullable=False)
    miktar = db.Column(db.Integer, nullable=False)
    kullanilan_miktar = db.Column(db.Integer, default=0)
    kalan_miktar = db.Column(db.Integer)
    iade_edilen_miktar = db.Column(db.Integer, default=0)
    kritik_stok_seviyesi = db.Column(db.Integer, nullable=True)  # Kat sorumlusu tarafından belirlenen kritik seviye
    
    def __repr__(self):
        return f'<PersonelZimmetDetay #{self.id}>'


class MinibarIslem(db.Model):
    """Minibar işlemleri tablosu - Kontrol ve tüketim başlık"""
    __tablename__ = 'minibar_islemleri'
    __table_args__ = (
        db.Index('idx_oda_tarih', 'oda_id', 'islem_tarihi'),
        db.Index('idx_personel_tarih', 'personel_id', 'islem_tarihi'),
    )

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    oda_id = db.Column(db.Integer, db.ForeignKey('odalar.id'), nullable=False)
    personel_id = db.Column(db.Integer, db.ForeignKey('kullanicilar.id'), nullable=False)
    islem_tipi = db.Column(db.Enum('ilk_dolum', 'yeniden_dolum', 'eksik_tamamlama', 'sayim', 'duzeltme', 'kontrol', 'doldurma', 'ek_dolum', 'setup_kontrol', 'ekstra_ekleme', 'ekstra_tuketim', name='minibar_islem_tipi'), nullable=False)
    islem_tarihi = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    aciklama = db.Column(db.Text)
    
    # İlişkiler
    detaylar = db.relationship('MinibarIslemDetay', backref='islem', lazy=True, cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<MinibarIslem #{self.id} - {self.islem_tipi}>'


class MinibarIslemDetay(db.Model):
    """Minibar işlem detay tablosu"""
    __tablename__ = 'minibar_islem_detay'
    
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    islem_id = db.Column(db.Integer, db.ForeignKey('minibar_islemleri.id'), nullable=False)
    urun_id = db.Column(db.Integer, db.ForeignKey('urunler.id'), nullable=False)
    baslangic_stok = db.Column(db.Integer, default=0)
    bitis_stok = db.Column(db.Integer, default=0)
    tuketim = db.Column(db.Integer, default=0)
    eklenen_miktar = db.Column(db.Integer, default=0)
    ekstra_miktar = db.Column(db.Integer, default=0)  # Setup üstü eklenen miktar
    setup_miktari = db.Column(db.Integer, default=0)  # Setup'ta olması gereken miktar
    zimmet_detay_id = db.Column(db.Integer, db.ForeignKey('personel_zimmet_detay.id'), nullable=True)  # Hangi zimmetten kullanıldığı
    
    # Fiyatlandırma ve Karlılık Kolonları
    satis_fiyati = db.Column(Numeric(10, 2), nullable=True)
    alis_fiyati = db.Column(Numeric(10, 2), nullable=True)
    kar_tutari = db.Column(Numeric(10, 2), nullable=True)
    kar_orani = db.Column(Numeric(5, 2), nullable=True)  # Yüzde
    bedelsiz = db.Column(db.Boolean, default=False)
    kampanya_id = db.Column(db.Integer, db.ForeignKey('kampanyalar.id'), nullable=True)
    
    # İlişkiler
    zimmet_detay = db.relationship('PersonelZimmetDetay', foreign_keys=[zimmet_detay_id])
    kampanya = db.relationship('Kampanya')
    
    def __repr__(self):
        return f'<MinibarIslemDetay #{self.id}>'


class SistemAyar(db.Model):
    """Sistem ayarları tablosu"""
    __tablename__ = 'sistem_ayarlari'
    
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    anahtar = db.Column(db.String(100), unique=True, nullable=False)
    deger = db.Column(db.Text)
    aciklama = db.Column(db.Text)
    
    def __repr__(self):
        return f'<SistemAyar {self.anahtar}>'


class SistemLog(db.Model):
    """Sistem log kayıtları tablosu"""
    __tablename__ = 'sistem_loglari'
    
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    kullanici_id = db.Column(db.Integer, db.ForeignKey('kullanicilar.id'))
    islem_tipi = db.Column(db.String(50), nullable=False)  # giris, cikis, ekleme, guncelleme, silme, goruntuleme
    modul = db.Column(db.String(100), nullable=False)  # urun, stok, zimmet, oda, kat vb.
    islem_detay = db.Column(JSONB, nullable=True)  # İşlem detayları (JSONB formatında - PostgreSQL)
    ip_adresi = db.Column(db.String(50))
    tarayici = db.Column(db.String(200))
    islem_tarihi = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    
    # İlişki
    kullanici = db.relationship('Kullanici', foreign_keys=[kullanici_id], backref='log_kayitlari')
    
    def __repr__(self):
        return f'<SistemLog {self.islem_tipi} - {self.modul}>'


class HataLog(db.Model):
    """Hata log kayıtları tablosu"""
    __tablename__ = 'hata_loglari'
    
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    kullanici_id = db.Column(db.Integer, db.ForeignKey('kullanicilar.id'))
    hata_tipi = db.Column(db.String(100), nullable=False)  # Exception tipi
    hata_mesaji = db.Column(db.Text, nullable=False)  # Hata mesajı
    hata_detay = db.Column(db.Text)  # Stack trace ve detaylar
    modul = db.Column(db.String(100))  # Hangi modülde oluştu
    url = db.Column(db.String(500))  # Hangi URL'de oluştu
    method = db.Column(db.String(10))  # HTTP method (GET, POST, etc.)
    ip_adresi = db.Column(db.String(50))
    tarayici = db.Column(db.String(200))
    olusturma_tarihi = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    cozuldu = db.Column(db.Boolean, default=False)  # Hata çözüldü mü?
    cozum_notu = db.Column(db.Text)  # Çözüm notu
    
    # İlişki
    kullanici = db.relationship('Kullanici', foreign_keys=[kullanici_id], backref='hata_kayitlari')
    
    def __repr__(self):
        return f'<HataLog {self.hata_tipi} - {self.olusturma_tarihi}>'


class AuditLog(db.Model):
    """Audit Trail - Denetim İzi Kayıtları"""
    __tablename__ = 'audit_logs'
    __table_args__ = (
        db.Index('idx_tablo_kayit', 'tablo_adi', 'kayit_id'),
        db.Index('idx_kullanici_tarih', 'kullanici_id', 'islem_tarihi'),
        db.Index('idx_tarih', 'islem_tarihi'),
    )
    
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    
    # Kullanıcı ve İşlem Bilgileri
    kullanici_id = db.Column(db.Integer, db.ForeignKey('kullanicilar.id'), nullable=True)  # Nullable - sistem/script işlemleri için
    kullanici_adi = db.Column(db.String(100), nullable=False)  # Denormalize - kullanıcı silinse bile kayıt kalır
    kullanici_rol = db.Column(db.String(50), nullable=False)
    
    # İşlem Detayları
    islem_tipi = db.Column(
        db.Enum('login', 'logout', 'create', 'update', 'delete', 'view', 'export', 'import', 'backup', 'restore', name='audit_islem_tipi'), 
        nullable=False
    )
    tablo_adi = db.Column(db.String(100), nullable=False)  # Hangi tablo etkilendi
    kayit_id = db.Column(db.Integer)  # Etkilenen kayıt ID'si
    
    # Veri Değişiklikleri
    eski_deger = db.Column(JSONB, nullable=True)  # JSONB formatında eski değerler (PostgreSQL)
    yeni_deger = db.Column(JSONB, nullable=True)  # JSONB formatında yeni değerler (PostgreSQL)
    degisiklik_ozeti = db.Column(db.Text)  # Okunabilir değişiklik özeti
    
    # HTTP İstek Bilgileri
    http_method = db.Column(db.String(10))  # GET, POST, PUT, DELETE
    url = db.Column(db.String(500))  # İstek URL'i
    endpoint = db.Column(db.String(200))  # Flask endpoint adı
    
    # Ağ Bilgileri
    ip_adresi = db.Column(db.String(50))
    user_agent = db.Column(db.String(500))  # Tarayıcı bilgisi
    
    # Zaman Bilgisi
    islem_tarihi = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    
    # Ek Bilgiler
    aciklama = db.Column(db.Text)  # Ek açıklama
    basarili = db.Column(db.Boolean, default=True)  # İşlem başarılı mı?
    hata_mesaji = db.Column(db.Text)  # Hata varsa mesajı
    
    # İlişki
    kullanici = db.relationship('Kullanici', foreign_keys=[kullanici_id], backref='audit_kayitlari')
    
    def __repr__(self):
        return f'<AuditLog {self.islem_tipi} - {self.tablo_adi} #{self.kayit_id}>'


class OtomatikRapor(db.Model):
    """Otomatik Oluşturulan Raporlar (Günlük Stok Raporu vb.)"""
    __tablename__ = 'otomatik_raporlar'
    __table_args__ = (
        db.Index('idx_rapor_tipi_tarih', 'rapor_tipi', 'olusturma_tarihi'),
    )
    
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    
    # Rapor Bilgileri
    rapor_tipi = db.Column(
        db.Enum('gunluk', 'haftalik', 'aylik', name='rapor_tipi'),
        nullable=False
    )
    baslik = db.Column(db.String(200), nullable=False)
    aciklama = db.Column(db.Text)
    
    # Rapor İçeriği (JSONB formatında - PostgreSQL)
    rapor_verisi = db.Column(JSONB, nullable=False)  # JSONB
    
    # Özet İstatistikler (Hızlı erişim için)
    toplam_urun = db.Column(db.Integer)
    kritik_stok_sayisi = db.Column(db.Integer)
    toplam_deger = db.Column(Numeric(10, 2))
    
    # Ek Bilgiler
    olusturan = db.Column(db.String(100), default='Sistem')  # Sistem veya kullanıcı adı
    olusturma_tarihi = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    
    def __repr__(self):
        return f'<OtomatikRapor {self.rapor_tipi} - {self.olusturma_tarihi}>'



class MinibarDolumTalebi(db.Model):
    """Misafir dolum talepleri tablosu"""
    __tablename__ = 'minibar_dolum_talepleri'
    __table_args__ = (
        db.Index('idx_oda_durum', 'oda_id', 'durum'),
        db.Index('idx_talep_tarihi', 'talep_tarihi'),
    )
    
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    oda_id = db.Column(db.Integer, db.ForeignKey('odalar.id'), nullable=False)
    talep_tarihi = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    durum = db.Column(db.Enum('beklemede', 'onaylandi', 'reddedildi', 'tamamlandi', 'iptal', name='dolum_talep_durum'), default='beklemede', nullable=False)
    tamamlanma_tarihi = db.Column(db.DateTime(timezone=True), nullable=True)
    notlar = db.Column(db.Text, nullable=True)
    
    def __repr__(self):
        return f'<MinibarDolumTalebi #{self.id} - Oda {self.oda_id} - {self.durum}>'


class QRKodOkutmaLog(db.Model):
    """QR kod okutma geçmişi tablosu"""
    __tablename__ = 'qr_kod_okutma_loglari'
    __table_args__ = (
        db.Index('idx_qr_log_oda_tarih', 'oda_id', 'okutma_tarihi'),
        db.Index('idx_qr_log_kullanici_tarih', 'kullanici_id', 'okutma_tarihi'),
        db.Index('idx_qr_log_okutma_tipi', 'okutma_tipi'),
    )
    
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    oda_id = db.Column(db.Integer, db.ForeignKey('odalar.id'), nullable=False)
    kullanici_id = db.Column(db.Integer, db.ForeignKey('kullanicilar.id'), nullable=True)
    okutma_tarihi = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    okutma_tipi = db.Column(db.Enum('misafir_okutma', 'personel_kontrol', 'sistem_kontrol', name='qr_okutma_tipi'), nullable=False)
    ip_adresi = db.Column(db.String(50))
    user_agent = db.Column(db.String(500))
    basarili = db.Column(db.Boolean, default=True, nullable=False)
    hata_mesaji = db.Column(db.Text, nullable=True)
    
    # İlişkiler
    kullanici = db.relationship('Kullanici', backref='qr_okutma_loglari')
    
    def __repr__(self):
        return f'<QRKodOkutmaLog #{self.id} - {self.okutma_tipi} - {self.okutma_tarihi}>'


class MisafirKayit(db.Model):
    """Misafir kayıt tablosu - Excel'den yüklenen oda doluluk verileri"""
    __tablename__ = 'misafir_kayitlari'
    __table_args__ = (
        db.Index('idx_misafir_islem_kodu', 'islem_kodu'),
        db.Index('idx_misafir_oda_tarih', 'oda_id', 'giris_tarihi', 'cikis_tarihi'),
        db.Index('idx_misafir_giris', 'giris_tarihi'),
        db.Index('idx_misafir_cikis', 'cikis_tarihi'),
    )
    
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    oda_id = db.Column(db.Integer, db.ForeignKey('odalar.id'), nullable=False)
    islem_kodu = db.Column(db.String(50), nullable=False, index=True)
    
    # Misafir Bilgileri (İsim kaydedilmez - sadece sayı)
    misafir_sayisi = db.Column(db.Integer, nullable=False)
    
    # Tarih ve Saat Bilgileri
    giris_tarihi = db.Column(db.Date, nullable=False, index=True)
    giris_saati = db.Column(db.Time, nullable=True)  # Sadece ARRIVALS için (Arr.Time)
    cikis_tarihi = db.Column(db.Date, nullable=False, index=True)
    
    # Kayıt Tipi (Otomatik algılanır: in_house veya arrival)
    kayit_tipi = db.Column(db.Enum('in_house', 'arrival', name='misafir_kayit_tipi'), nullable=False)
    
    # Sistem Bilgileri
    olusturma_tarihi = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    olusturan_id = db.Column(db.Integer, db.ForeignKey('kullanicilar.id'))
    
    # İlişkiler
    oda = db.relationship('Oda', backref='misafir_kayitlari')
    olusturan = db.relationship('Kullanici', foreign_keys=[olusturan_id])
    
    def __repr__(self):
        return f'<MisafirKayit #{self.id} - Oda {self.oda_id} - {self.kayit_tipi}>'


class DosyaYukleme(db.Model):
    """Excel dosya yükleme kayıtları"""
    __tablename__ = 'dosya_yuklemeleri'
    __table_args__ = (
        db.Index('idx_dosya_islem_kodu', 'islem_kodu'),
        db.Index('idx_dosya_yukleme_tarihi', 'yukleme_tarihi'),
        db.Index('idx_dosya_silme_tarihi', 'silme_tarihi'),
    )
    
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    islem_kodu = db.Column(db.String(50), unique=True, nullable=False, index=True)
    
    # Dosya Bilgileri
    dosya_adi = db.Column(db.String(255), nullable=False)
    dosya_yolu = db.Column(db.String(500), nullable=False)
    dosya_tipi = db.Column(db.Enum('in_house', 'arrivals', name='dosya_tipi'), nullable=False)  # Otomatik algılanır
    dosya_boyutu = db.Column(db.Integer)  # bytes
    
    # İşlem Bilgileri
    yukleme_tarihi = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    silme_tarihi = db.Column(db.DateTime(timezone=True), nullable=True)  # Otomatik silme için
    durum = db.Column(db.Enum('yuklendi', 'isleniyor', 'tamamlandi', 'hata', 'silindi', name='yukleme_durum'), default='yuklendi', nullable=False)
    
    # İstatistikler
    toplam_satir = db.Column(db.Integer, default=0)
    basarili_satir = db.Column(db.Integer, default=0)
    hatali_satir = db.Column(db.Integer, default=0)
    hata_detaylari = db.Column(JSONB, nullable=True)  # Hata mesajları (JSONB formatında)
    
    # Kullanıcı Bilgileri
    yuklenen_kullanici_id = db.Column(db.Integer, db.ForeignKey('kullanicilar.id'))
    
    # İlişkiler
    yuklenen_kullanici = db.relationship('Kullanici', foreign_keys=[yuklenen_kullanici_id])
    
    def __repr__(self):
        return f'<DosyaYukleme #{self.id} - {self.islem_kodu} - {self.durum}>'


# ============================================
# MACHINE LEARNING MODELS
# ============================================

class MLMetricType(str, enum.Enum):
    """ML metrik tipleri"""
    STOK_SEVIYE = 'stok_seviye'
    TUKETIM_MIKTAR = 'tuketim_miktar'
    DOLUM_SURE = 'dolum_sure'
    STOK_BITIS_TAHMINI = 'stok_bitis_tahmini'
    # Phase 2 - Zimmet ve Doluluk
    ZIMMET_KULLANIM = 'zimmet_kullanim'      # Zimmet kullanım oranı
    ZIMMET_FIRE = 'zimmet_fire'              # Fire/kayıp oranı
    DOLULUK_ORAN = 'doluluk_oran'            # Otel doluluk oranı
    BOSTA_TUKETIM = 'bosta_tuketim'          # Boş odada tüketim
    # Phase 3 - QR & Talep Sistemi
    TALEP_YANIT_SURE = 'talep_yanit_sure'    # Talep yanıt süresi (dakika)
    TALEP_YOGUNLUK = 'talep_yogunluk'        # Oda/kat bazlı talep sayısı
    QR_OKUTMA_SIKLIK = 'qr_okutma_siklik'    # Personel QR okutma sıklığı
    # Phase 2.5 - QR ve Talep Sistemi
    TALEP_KARSILAMA_SURE = 'talep_karsilama_sure'    # Talep karşılama süresi (dakika)
    TALEP_SIKLIK = 'talep_siklik'                    # Oda bazlı talep sıklığı
    DOLUM_SAAT_DAGILIM = 'dolum_saat_dagilim'        # Dolum saati dağılımı
    QR_OKUTMA_PERFORMANS = 'qr_okutma_performans'    # QR okutma performansı

class MLAlertType(str, enum.Enum):
    """ML uyarı tipleri"""
    STOK_ANOMALI = 'stok_anomali'
    TUKETIM_ANOMALI = 'tuketim_anomali'
    DOLUM_GECIKME = 'dolum_gecikme'
    STOK_BITIS_UYARI = 'stok_bitis_uyari'
    # Phase 2 - Zimmet ve Doluluk
    ZIMMET_FIRE_YUKSEK = 'zimmet_fire_yuksek'        # Yüksek fire oranı
    BOSTA_TUKETIM_VAR = 'bosta_tuketim_var'          # Boş oda tüketim
    DOLUDA_TUKETIM_YOK = 'doluda_tuketim_yok'        # Dolu oda tüketim yok
    # Phase 3 - QR & Talep Sistemi
    TALEP_YANITLANMADI = 'talep_yanitlanmadi'        # Uzun süre yanıtlanmayan talep
    TALEP_YOGUNLUK_YUKSEK = 'talep_yogunluk_yuksek'  # Aşırı talep yoğunluğu
    QR_KULLANIM_DUSUK = 'qr_kullanim_dusuk'          # QR sistemi az kullanılıyor

class MLAlertSeverity(str, enum.Enum):
    """ML uyarı önem seviyeleri"""
    DUSUK = 'dusuk'
    ORTA = 'orta'
    YUKSEK = 'yuksek'
    KRITIK = 'kritik'

# ============================================
# FIYATLANDIRMA VE KARLILIK ENUM'LARI
# ============================================

class FiyatDegisiklikTipi(str, enum.Enum):
    """Fiyat değişiklik tipleri"""
    ALIS_FIYATI = 'alis_fiyati'
    SATIS_FIYATI = 'satis_fiyati'
    KAMPANYA = 'kampanya'

class IndirimTipi(str, enum.Enum):
    """İndirim tipleri"""
    YUZDE = 'yuzde'
    TUTAR = 'tutar'

class BedelsizLimitTipi(str, enum.Enum):
    """Bedelsiz limit tipleri"""
    MISAFIR = 'misafir'
    KAMPANYA = 'kampanya'
    PERSONEL = 'personel'

class DonemTipi(str, enum.Enum):
    """Dönem tipleri"""
    GUNLUK = 'gunluk'
    HAFTALIK = 'haftalik'
    AYLIK = 'aylik'

class KuralTipi(str, enum.Enum):
    """Fiyat güncelleme kural tipleri"""
    OTOMATIK_ARTIR = 'otomatik_artir'
    OTOMATIK_AZALT = 'otomatik_azalt'
    RAKIP_FIYAT = 'rakip_fiyat'

class SiparisDurum(str, enum.Enum):
    """Satın alma sipariş durumları"""
    BEKLEMEDE = 'beklemede'
    ONAYLANDI = 'onaylandi'
    TESLIM_ALINDI = 'teslim_alindi'
    KISMI_TESLIM = 'kismi_teslim'
    TAMAMLANDI = 'tamamlandi'
    IPTAL = 'iptal'

class DokumanTipi(str, enum.Enum):
    """Tedarikçi doküman tipleri"""
    FATURA = 'fatura'
    IRSALIYE = 'irsaliye'
    SOZLESME = 'sozlesme'
    DIGER = 'diger'


class MLMetric(db.Model):
    """ML metrik kayıtları - zaman serisi verileri"""
    __tablename__ = 'ml_metrics'
    __table_args__ = (
        db.Index('idx_ml_metrics_type_time', 'metric_type', 'timestamp'),
        db.Index('idx_ml_metrics_entity', 'entity_id'),
    )
    
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    metric_type = db.Column(
        db.Enum(
            'stok_seviye', 'tuketim_miktar', 'dolum_sure', 'stok_bitis_tahmini',
            'zimmet_kullanim', 'zimmet_fire', 'doluluk_oran', 'bosta_tuketim',
            'talep_yanit_sure', 'talep_yogunluk', 'qr_okutma_siklik', 'qr_okutma_performans',
            name='ml_metric_type'
        ),
        nullable=False
    )
    entity_id = db.Column(db.Integer, nullable=False)
    metric_value = db.Column(db.Float, nullable=False)
    timestamp = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    extra_data = db.Column(JSONB, nullable=True)  # Ek bilgiler (JSONB formatında)
    
    def __repr__(self):
        return f'<MLMetric {self.metric_type} - #{self.entity_id}>'


class MLModel(db.Model):
    """Eğitilmiş ML modelleri"""
    __tablename__ = 'ml_models'
    __table_args__ = (
        db.Index('idx_ml_models_type_active', 'model_type', 'metric_type', 'is_active'),
    )
    
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    model_type = db.Column(db.String(50), nullable=False)  # 'isolation_forest', 'z_score'
    metric_type = db.Column(db.String(50), nullable=False)
    model_data = db.Column(db.LargeBinary, nullable=True)  # Pickle serialized model (opsiyonel - dosya sisteminde ise NULL)
    model_path = db.Column(db.String(255), nullable=True)  # Dosya yolu (opsiyonel - DB'de ise NULL)
    parameters = db.Column(JSONB, nullable=True)  # Model parametreleri
    training_date = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    accuracy = db.Column(db.Float)
    precision = db.Column(db.Float)
    recall = db.Column(db.Float)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    
    # İlişkiler
    training_logs = db.relationship('MLTrainingLog', backref='model', lazy=True)
    
    def __repr__(self):
        return f'<MLModel {self.model_type} - {self.metric_type}>'


class MLAlert(db.Model):
    """ML uyarıları"""
    __tablename__ = 'ml_alerts'
    __table_args__ = (
        db.Index('idx_ml_alerts_severity_read', 'severity', 'is_read'),
        db.Index('idx_ml_alerts_created', 'created_at'),
        db.Index('idx_ml_alerts_entity', 'entity_id'),
    )
    
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    alert_type = db.Column(
        db.Enum(
            'stok_anomali', 'tuketim_anomali', 'dolum_gecikme', 'stok_bitis_uyari',
            'zimmet_fire_yuksek', 'bosta_tuketim_var', 'doluda_tuketim_yok',
            'talep_yanitlanmadi', 'talep_yogunluk_yuksek', 'qr_kullanim_dusuk',
            name='ml_alert_type'
        ),
        nullable=False
    )
    severity = db.Column(
        db.Enum('dusuk', 'orta', 'yuksek', 'kritik', name='ml_alert_severity'),
        nullable=False
    )
    entity_type = db.Column(db.String(50), nullable=True)  # 'urun', 'oda', 'kullanici'
    entity_id = db.Column(db.Integer, nullable=False)  # urun_id, oda_id, kullanici_id
    metric_value = db.Column(db.Float, nullable=False)
    expected_value = db.Column(db.Float)
    deviation_percent = db.Column(db.Float)
    message = db.Column(db.Text, nullable=False)
    suggested_action = db.Column(db.Text)
    created_at = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    is_read = db.Column(db.Boolean, default=False, nullable=False)
    is_false_positive = db.Column(db.Boolean, default=False, nullable=False)
    resolved_at = db.Column(db.DateTime(timezone=True), nullable=True)
    resolved_by_id = db.Column(db.Integer, db.ForeignKey('kullanicilar.id'), nullable=True)
    
    # İlişkiler
    resolved_by = db.relationship('Kullanici', foreign_keys=[resolved_by_id], backref='resolved_ml_alerts')
    
    def __repr__(self):
        return f'<MLAlert {self.alert_type} - {self.severity}>'


class MLTrainingLog(db.Model):
    """Model eğitim logları"""
    __tablename__ = 'ml_training_logs'
    __table_args__ = (
        db.Index('idx_ml_training_logs_date', 'training_start'),
    )
    
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    model_id = db.Column(db.Integer, db.ForeignKey('ml_models.id'), nullable=True)
    training_start = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    training_end = db.Column(db.DateTime(timezone=True), nullable=True)
    data_points = db.Column(db.Integer)
    success = db.Column(db.Boolean, default=False, nullable=False)
    error_message = db.Column(db.Text, nullable=True)
    metrics = db.Column(JSONB, nullable=True)  # Performans metrikleri (JSONB formatında)
    
    def __repr__(self):
        return f'<MLTrainingLog #{self.id} - {"Success" if self.success else "Failed"}>'


class MLFeature(db.Model):
    """Feature Engineering sonuçları - İşlenmiş feature'lar"""
    __tablename__ = 'ml_features'
    __table_args__ = (
        db.Index('idx_ml_features_type_entity', 'metric_type', 'entity_id'),
        db.Index('idx_ml_features_timestamp', 'timestamp'),
        db.Index('idx_ml_features_entity_time', 'entity_id', 'timestamp'),
    )
    
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    metric_type = db.Column(db.String(50), nullable=False)
    entity_id = db.Column(db.Integer, nullable=False)
    timestamp = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    
    # Statistical Features
    mean_value = db.Column(db.Float)
    std_value = db.Column(db.Float)
    min_value = db.Column(db.Float)
    max_value = db.Column(db.Float)
    median_value = db.Column(db.Float)
    q25_value = db.Column(db.Float)
    q75_value = db.Column(db.Float)
    
    # Trend Features
    trend_slope = db.Column(db.Float)
    trend_direction = db.Column(db.String(20))
    volatility = db.Column(db.Float)
    momentum = db.Column(db.Float)
    
    # Time Features
    hour_of_day = db.Column(db.Integer)
    day_of_week = db.Column(db.Integer)
    is_weekend = db.Column(db.Boolean)
    day_of_month = db.Column(db.Integer)
    
    # Domain Specific Features
    days_since_last_change = db.Column(db.Integer)
    change_frequency = db.Column(db.Float)
    avg_change_magnitude = db.Column(db.Float)
    zero_count = db.Column(db.Integer)
    
    # Lag Features
    lag_1 = db.Column(db.Float)
    lag_7 = db.Column(db.Float)
    lag_30 = db.Column(db.Float)
    
    # Rolling Features
    rolling_mean_7 = db.Column(db.Float)
    rolling_std_7 = db.Column(db.Float)
    rolling_mean_30 = db.Column(db.Float)
    rolling_std_30 = db.Column(db.Float)
    
    # Metadata
    feature_version = db.Column(db.String(20), default='1.0')
    extra_features = db.Column(JSONB, nullable=True)  # Ek feature'lar
    created_at = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    
    def __repr__(self):
        return f'<MLFeature {self.metric_type} - #{self.entity_id}>'


# ============================================
# DEVELOPER DASHBOARD MONITORING MODELS
# ============================================

class QueryLog(db.Model):
    """Database query performance log"""
    __tablename__ = 'query_logs'
    __table_args__ = (
        db.Index('idx_query_logs_time', 'execution_time'),
        db.Index('idx_query_logs_timestamp', 'timestamp'),
        db.Index('idx_query_logs_endpoint', 'endpoint'),
    )
    
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    query_text = db.Column(db.Text, nullable=False)
    execution_time = db.Column(db.Float, nullable=False)  # Saniye cinsinden
    timestamp = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    endpoint = db.Column(db.String(255))
    user_id = db.Column(db.Integer, db.ForeignKey('kullanicilar.id'))
    parameters = db.Column(JSONB)
    
    # İlişki
    user = db.relationship('Kullanici', foreign_keys=[user_id], backref='query_logs')
    
    def __repr__(self):
        return f'<QueryLog #{self.id} - {self.execution_time:.3f}s>'


class BackgroundJob(db.Model):
    """Background job tracking"""
    __tablename__ = 'background_jobs'
    __table_args__ = (
        db.Index('idx_background_jobs_status', 'status'),
        db.Index('idx_background_jobs_started', 'started_at'),
        db.Index('idx_background_jobs_job_id', 'job_id'),
    )
    
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    job_id = db.Column(db.String(255), unique=True, nullable=False)
    job_name = db.Column(db.String(255), nullable=False)
    status = db.Column(
        db.Enum('pending', 'running', 'completed', 'failed', 'cancelled', name='job_status'),
        nullable=False,
        default='pending'
    )
    started_at = db.Column(db.DateTime(timezone=True))
    completed_at = db.Column(db.DateTime(timezone=True))
    duration = db.Column(db.Float)  # Saniye cinsinden
    error_message = db.Column(db.Text)
    stack_trace = db.Column(db.Text)
    job_metadata = db.Column(JSONB)  # metadata yerine job_metadata
    created_at = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    
    def __repr__(self):
        return f'<BackgroundJob {self.job_name} - {self.status}>'


class BackupHistory(db.Model):
    """Database backup history"""
    __tablename__ = 'backup_history'
    __table_args__ = (
        db.Index('idx_backup_history_created', 'created_at'),
        db.Index('idx_backup_history_backup_id', 'backup_id'),
    )
    
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    backup_id = db.Column(db.String(255), unique=True, nullable=False)
    filename = db.Column(db.String(255), nullable=False)
    file_size = db.Column(db.BigInteger)  # Bytes
    description = db.Column(db.Text)
    created_at = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    created_by = db.Column(db.Integer, db.ForeignKey('kullanicilar.id'))
    status = db.Column(
        db.Enum('in_progress', 'completed', 'failed', name='backup_status'),
        nullable=False,
        default='in_progress'
    )
    restore_count = db.Column(db.Integer, default=0)
    
    # İlişki
    creator = db.relationship('Kullanici', foreign_keys=[created_by], backref='backups')
    
    def __repr__(self):
        return f'<BackupHistory {self.filename} - {self.status}>'


class ConfigAudit(db.Model):
    """Configuration file change audit"""
    __tablename__ = 'config_audit'
    __table_args__ = (
        db.Index('idx_config_audit_filename', 'filename'),
        db.Index('idx_config_audit_changed', 'changed_at'),
    )
    
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    filename = db.Column(db.String(255), nullable=False)
    old_content = db.Column(db.Text)
    new_content = db.Column(db.Text)
    changed_by = db.Column(db.Integer, db.ForeignKey('kullanicilar.id'))
    changed_at = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    change_reason = db.Column(db.Text)
    
    # İlişki
    changer = db.relationship('Kullanici', foreign_keys=[changed_by], backref='config_changes')
    
    def __repr__(self):
        return f'<ConfigAudit {self.filename} - {self.changed_at}>'


# ============================================
# FIYATLANDIRMA VE KARLILIK MODELLERI
# ============================================

class UrunStok(db.Model):
    """Ürün stok durumu - Gerçek zamanlı stok takibi"""
    __tablename__ = 'urun_stok'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    urun_id = db.Column(db.Integer, db.ForeignKey('urunler.id', ondelete='CASCADE'), nullable=False)
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
        try:
            if self.mevcut_stok <= self.kritik_stok_seviyesi:
                return 'kritik'
            elif self.mevcut_stok <= self.minimum_stok:
                return 'dusuk'
            elif self.mevcut_stok >= self.maksimum_stok:
                return 'fazla'
            return 'normal'
        except Exception as e:
            return 'bilinmiyor'

    def stok_guncelle(self, miktar, islem_tipi, kullanici_id):
        """Stok miktarını güncelle"""
        try:
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
            
            # Toplam değeri güncelle
            self.toplam_deger = self.mevcut_stok * self.birim_maliyet
        except Exception as e:
            raise Exception(f"Stok güncelleme hatası: {str(e)}")

    def __repr__(self):
        return f'<UrunStok urun_id={self.urun_id} otel_id={self.otel_id} mevcut={self.mevcut_stok}>'


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

    def __repr__(self):
        return f'<Kampanya {self.kampanya_adi}>'


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

    def __repr__(self):
        return f'<BedelsizLimit oda_id={self.oda_id} urun_id={self.urun_id}>'


class BedelsizKullanimLog(db.Model):
    """Bedelsiz kullanım log kayıtları"""
    __tablename__ = 'bedelsiz_kullanim_log'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    oda_id = db.Column(db.Integer, db.ForeignKey('odalar.id', ondelete='CASCADE'), nullable=False)
    urun_id = db.Column(db.Integer, db.ForeignKey('urunler.id', ondelete='CASCADE'), nullable=False)
    miktar = db.Column(db.Integer, nullable=False)
    islem_id = db.Column(db.Integer, db.ForeignKey('minibar_islemleri.id', ondelete='CASCADE'), nullable=False)
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

    def __repr__(self):
        return f'<BedelsizKullanimLog oda_id={self.oda_id} miktar={self.miktar}>'


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

    def __repr__(self):
        return f'<DonemselKarAnalizi otel_id={self.otel_id} donem={self.donem_tipi}>'


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

    def __repr__(self):
        return f'<FiyatGuncellemeKurali urun_id={self.urun_id} tip={self.kural_tipi}>'


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

    def __repr__(self):
        return f'<Tedarikci {self.tedarikci_adi}>'


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

    def __repr__(self):
        return f'<UrunTedarikciFiyat urun_id={self.urun_id} tedarikci_id={self.tedarikci_id}>'


class UrunFiyatGecmisi(db.Model):
    """Fiyat değişiklik geçmişi"""
    __tablename__ = 'urun_fiyat_gecmisi'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    urun_id = db.Column(db.Integer, db.ForeignKey('urunler.id', ondelete='CASCADE'), nullable=False)
    eski_fiyat = db.Column(Numeric(10, 2))
    yeni_fiyat = db.Column(Numeric(10, 2), nullable=False)
    degisiklik_tipi = db.Column(db.Enum(FiyatDegisiklikTipi, name='fiyat_degisiklik_tipi', native_enum=True, values_callable=lambda x: [e.value for e in x]), nullable=False)
    degisiklik_tarihi = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    degisiklik_sebebi = db.Column(db.Text)
    olusturan_id = db.Column(db.Integer, db.ForeignKey('kullanicilar.id'), nullable=False)

    # İlişkiler
    urun = db.relationship('Urun', backref='fiyat_gecmisi')
    olusturan = db.relationship('Kullanici')

    __table_args__ = (
        db.Index('idx_fiyat_gecmis_urun_tarih', 'urun_id', 'degisiklik_tarihi'),
    )

    def __repr__(self):
        return f'<UrunFiyatGecmisi urun_id={self.urun_id} tip={self.degisiklik_tipi}>'


class OdaTipiSatisFiyati(db.Model):
    """Oda tipi bazında satış fiyatları"""
    __tablename__ = 'oda_tipi_satis_fiyatlari'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    oda_tipi_id = db.Column(db.Integer, db.ForeignKey('oda_tipleri.id', ondelete='CASCADE'), nullable=False)  # Oda tipi ID
    urun_id = db.Column(db.Integer, db.ForeignKey('urunler.id', ondelete='CASCADE'), nullable=False)
    satis_fiyati = db.Column(Numeric(10, 2), nullable=False)
    baslangic_tarihi = db.Column(db.DateTime(timezone=True), nullable=False)
    bitis_tarihi = db.Column(db.DateTime(timezone=True), nullable=True)
    aktif = db.Column(db.Boolean, default=True)
    olusturma_tarihi = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    # İlişkiler
    oda_tipi_rel = db.relationship('OdaTipi', foreign_keys=[oda_tipi_id], backref='satis_fiyatlari')
    urun = db.relationship('Urun', backref='oda_tipi_fiyatlari')

    __table_args__ = (
        db.Index('idx_oda_tipi_urun_aktif', 'oda_tipi_id', 'urun_id', 'aktif'),
    )

    def __repr__(self):
        return f'<OdaTipiSatisFiyati oda_tipi_id={self.oda_tipi_id} urun_id={self.urun_id}>'


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

    def __repr__(self):
        return f'<SezonFiyatlandirma {self.sezon_adi}>'


# ============================================
# SATIN ALMA VE TEDARİKÇİ YÖNETİMİ MODELLERİ
# ============================================

class SatinAlmaSiparisi(db.Model):
    """Satın alma siparişi ana tablosu"""
    __tablename__ = 'satin_alma_siparisleri'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    siparis_no = db.Column(db.String(50), unique=True, nullable=False)
    tedarikci_id = db.Column(db.Integer, db.ForeignKey('tedarikciler.id', ondelete='RESTRICT'), nullable=True)
    otel_id = db.Column(db.Integer, db.ForeignKey('oteller.id', ondelete='CASCADE'), nullable=False)
    
    # Tarih Bilgileri
    siparis_tarihi = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    tahmini_teslimat_tarihi = db.Column(db.Date, nullable=False)
    gerceklesen_teslimat_tarihi = db.Column(db.Date, nullable=True)
    
    # Durum ve Tutar
    durum = db.Column(db.String(20), default='beklemede', nullable=False)
    toplam_tutar = db.Column(Numeric(12, 2), default=0, nullable=False)
    
    # Açıklama ve Notlar
    aciklama = db.Column(db.Text, nullable=True)
    
    # Kullanıcı Bilgileri
    olusturan_id = db.Column(db.Integer, db.ForeignKey('kullanicilar.id', ondelete='SET NULL'), nullable=True)
    onaylayan_id = db.Column(db.Integer, db.ForeignKey('kullanicilar.id', ondelete='SET NULL'), nullable=True)
    onay_tarihi = db.Column(db.DateTime(timezone=True), nullable=True)
    
    # Sistem Bilgileri
    olusturma_tarihi = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    guncelleme_tarihi = db.Column(db.DateTime(timezone=True), onupdate=lambda: datetime.now(timezone.utc))

    # İlişkiler
    tedarikci = db.relationship('Tedarikci', backref='siparisler')
    otel = db.relationship('Otel', backref='satin_alma_siparisleri')
    detaylar = db.relationship('SatinAlmaSiparisDetay', backref='siparis', lazy=True, cascade='all, delete-orphan')
    olusturan = db.relationship('Kullanici', foreign_keys=[olusturan_id], backref='olusturdugun_siparisler')
    onaylayan = db.relationship('Kullanici', foreign_keys=[onaylayan_id], backref='onayladigin_siparisler')

    __table_args__ = (
        db.Index('idx_siparis_durum_tarih', 'durum', 'siparis_tarihi'),
        db.Index('idx_siparis_tedarikci', 'tedarikci_id'),
        db.Index('idx_siparis_otel', 'otel_id'),
        db.Index('idx_siparis_no', 'siparis_no'),
    )

    def __repr__(self):
        return f'<SatinAlmaSiparisi {self.siparis_no} - {self.durum.value}>'


class SatinAlmaSiparisDetay(db.Model):
    """Sipariş detay satırları"""
    __tablename__ = 'satin_alma_siparis_detaylari'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    siparis_id = db.Column(db.Integer, db.ForeignKey('satin_alma_siparisleri.id', ondelete='CASCADE'), nullable=False)
    urun_id = db.Column(db.Integer, db.ForeignKey('urunler.id', ondelete='RESTRICT'), nullable=False)
    
    # Miktar ve Fiyat Bilgileri
    miktar = db.Column(db.Integer, nullable=False)
    birim_fiyat = db.Column(Numeric(10, 2), nullable=False)
    toplam_fiyat = db.Column(Numeric(12, 2), nullable=False)
    
    # Teslimat Bilgileri
    teslim_alinan_miktar = db.Column(db.Integer, default=0, nullable=False)
    
    # Sistem Bilgileri
    olusturma_tarihi = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

    # İlişkiler
    urun = db.relationship('Urun', backref='siparis_detaylari')

    __table_args__ = (
        db.Index('idx_siparis_detay_siparis', 'siparis_id'),
        db.Index('idx_siparis_detay_urun', 'urun_id'),
        db.CheckConstraint('miktar > 0', name='check_siparis_miktar_pozitif'),
        db.CheckConstraint('birim_fiyat >= 0', name='check_siparis_fiyat_pozitif'),
        db.CheckConstraint('teslim_alinan_miktar >= 0', name='check_teslim_miktar_pozitif'),
        db.CheckConstraint('teslim_alinan_miktar <= miktar', name='check_teslim_miktar_limit'),
    )

    def __repr__(self):
        return f'<SatinAlmaSiparisDetay siparis_id={self.siparis_id} urun_id={self.urun_id}>'


class SatinAlmaIslem(db.Model):
    """Direkt satın alma işlemleri (Sipariş olmadan stok girişi)"""
    __tablename__ = 'satin_alma_islemler'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    islem_no = db.Column(db.String(50), unique=True, nullable=False)
    tedarikci_id = db.Column(db.Integer, db.ForeignKey('tedarikciler.id', ondelete='RESTRICT'), nullable=False)
    otel_id = db.Column(db.Integer, db.ForeignKey('oteller.id', ondelete='CASCADE'), nullable=False)
    siparis_id = db.Column(db.Integer, db.ForeignKey('satin_alma_siparisleri.id', ondelete='SET NULL'), nullable=True)  # İlişkili sipariş (opsiyonel)
    
    # Fatura Bilgileri
    fatura_no = db.Column(db.String(100), nullable=True)
    fatura_tarihi = db.Column(db.Date, nullable=True)
    
    # Ödeme Bilgileri
    odeme_sekli = db.Column(db.String(50), nullable=True)  # nakit, kredi_karti, havale, cek
    odeme_durumu = db.Column(db.String(20), default='odenmedi', nullable=False)  # odendi, odenmedi, kismi
    
    # Tutar Bilgileri
    toplam_tutar = db.Column(Numeric(12, 2), default=0, nullable=False)
    kdv_tutari = db.Column(Numeric(12, 2), default=0, nullable=False)
    genel_toplam = db.Column(Numeric(12, 2), default=0, nullable=False)
    
    # Açıklama
    aciklama = db.Column(db.Text, nullable=True)
    
    # Kullanıcı Bilgileri
    olusturan_id = db.Column(db.Integer, db.ForeignKey('kullanicilar.id', ondelete='SET NULL'), nullable=True)
    
    # Sistem Bilgileri
    islem_tarihi = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    olusturma_tarihi = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    guncelleme_tarihi = db.Column(db.DateTime(timezone=True), onupdate=lambda: datetime.now(timezone.utc))

    # İlişkiler
    tedarikci = db.relationship('Tedarikci', backref='satin_alma_islemleri')
    otel = db.relationship('Otel', backref='satin_alma_islemleri')
    siparis = db.relationship('SatinAlmaSiparisi', backref='satin_alma_islemleri')
    detaylar = db.relationship('SatinAlmaIslemDetay', backref='islem', lazy=True, cascade='all, delete-orphan')
    olusturan = db.relationship('Kullanici', backref='satin_alma_islemleri')

    __table_args__ = (
        db.Index('idx_satin_alma_islem_tarih', 'islem_tarihi'),
        db.Index('idx_satin_alma_tedarikci', 'tedarikci_id'),
        db.Index('idx_satin_alma_otel', 'otel_id'),
        db.Index('idx_satin_alma_islem_no', 'islem_no'),
    )

    def __repr__(self):
        return f'<SatinAlmaIslem {self.islem_no}>'


class SatinAlmaIslemDetay(db.Model):
    """Satın alma işlem detay satırları"""
    __tablename__ = 'satin_alma_islem_detaylari'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    islem_id = db.Column(db.Integer, db.ForeignKey('satin_alma_islemler.id', ondelete='CASCADE'), nullable=False)
    urun_id = db.Column(db.Integer, db.ForeignKey('urunler.id', ondelete='RESTRICT'), nullable=False)
    
    # Miktar ve Fiyat Bilgileri
    miktar = db.Column(db.Integer, nullable=False)
    birim_fiyat = db.Column(Numeric(10, 2), nullable=False)
    kdv_orani = db.Column(Numeric(5, 2), default=0, nullable=False)
    kdv_tutari = db.Column(Numeric(10, 2), default=0, nullable=False)
    toplam_fiyat = db.Column(Numeric(12, 2), nullable=False)
    
    # Stok Hareket İlişkisi
    stok_hareket_id = db.Column(db.Integer, db.ForeignKey('stok_hareketleri.id', ondelete='SET NULL'), nullable=True)
    
    # Sistem Bilgileri
    olusturma_tarihi = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

    # İlişkiler
    urun = db.relationship('Urun', backref='satin_alma_detaylari')
    stok_hareket = db.relationship('StokHareket', backref='satin_alma_detay')

    __table_args__ = (
        db.Index('idx_satin_alma_detay_islem', 'islem_id'),
        db.Index('idx_satin_alma_detay_urun', 'urun_id'),
        db.CheckConstraint('miktar > 0', name='check_satin_alma_miktar_pozitif'),
        db.CheckConstraint('birim_fiyat >= 0', name='check_satin_alma_fiyat_pozitif'),
    )

    def __repr__(self):
        return f'<SatinAlmaIslemDetay islem_id={self.islem_id} urun_id={self.urun_id}>'


class TedarikciPerformans(db.Model):
    """Tedarikçi performans metrikleri"""
    __tablename__ = 'tedarikci_performans'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    tedarikci_id = db.Column(db.Integer, db.ForeignKey('tedarikciler.id', ondelete='CASCADE'), nullable=False)
    
    # Dönem Bilgileri
    donem_baslangic = db.Column(db.Date, nullable=False)
    donem_bitis = db.Column(db.Date, nullable=False)
    
    # Performans Metrikleri
    toplam_siparis_sayisi = db.Column(db.Integer, default=0, nullable=False)
    zamaninda_teslimat_sayisi = db.Column(db.Integer, default=0, nullable=False)
    ortalama_teslimat_suresi = db.Column(db.Integer, nullable=True)  # Gün cinsinden
    toplam_siparis_tutari = db.Column(Numeric(12, 2), default=0, nullable=False)
    performans_skoru = db.Column(Numeric(5, 2), nullable=True)  # 0-100 arası
    
    # Sistem Bilgileri
    olusturma_tarihi = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    guncelleme_tarihi = db.Column(db.DateTime(timezone=True), onupdate=lambda: datetime.now(timezone.utc))

    # İlişkiler
    tedarikci = db.relationship('Tedarikci', backref='performans_kayitlari')

    __table_args__ = (
        db.Index('idx_tedarikci_performans_tedarikci', 'tedarikci_id'),
        db.Index('idx_tedarikci_performans_donem', 'donem_baslangic', 'donem_bitis'),
        db.CheckConstraint('zamaninda_teslimat_sayisi <= toplam_siparis_sayisi', name='check_zamaninda_teslimat'),
        db.CheckConstraint('performans_skoru >= 0 AND performans_skoru <= 100', name='check_performans_skoru'),
    )

    def __repr__(self):
        return f'<TedarikciPerformans tedarikci_id={self.tedarikci_id} skor={self.performans_skoru}>'


class TedarikciIletisim(db.Model):
    """Tedarikçi iletişim kayıtları"""
    __tablename__ = 'tedarikci_iletisim'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    tedarikci_id = db.Column(db.Integer, db.ForeignKey('tedarikciler.id', ondelete='CASCADE'), nullable=False)
    siparis_id = db.Column(db.Integer, db.ForeignKey('satin_alma_siparisleri.id', ondelete='SET NULL'), nullable=True)
    
    # İletişim Bilgileri
    iletisim_tarihi = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    konu = db.Column(db.String(200), nullable=False)
    aciklama = db.Column(db.Text, nullable=False)
    
    # Kullanıcı Bilgileri
    kullanici_id = db.Column(db.Integer, db.ForeignKey('kullanicilar.id', ondelete='SET NULL'), nullable=True)
    
    # Sistem Bilgileri
    olusturma_tarihi = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

    # İlişkiler
    tedarikci = db.relationship('Tedarikci', backref='iletisim_kayitlari')
    siparis = db.relationship('SatinAlmaSiparisi', backref='iletisim_kayitlari')
    kullanici = db.relationship('Kullanici', backref='tedarikci_iletisimleri')

    __table_args__ = (
        db.Index('idx_tedarikci_iletisim_tedarikci', 'tedarikci_id'),
        db.Index('idx_tedarikci_iletisim_siparis', 'siparis_id'),
        db.Index('idx_tedarikci_iletisim_tarih', 'iletisim_tarihi'),
    )

    def __repr__(self):
        return f'<TedarikciIletisim tedarikci_id={self.tedarikci_id} konu={self.konu}>'


class TedarikciDokuman(db.Model):
    """Tedarikçi belge yönetimi"""
    __tablename__ = 'tedarikci_dokumanlar'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    tedarikci_id = db.Column(db.Integer, db.ForeignKey('tedarikciler.id', ondelete='CASCADE'), nullable=False)
    siparis_id = db.Column(db.Integer, db.ForeignKey('satin_alma_siparisleri.id', ondelete='SET NULL'), nullable=True)
    
    # Doküman Bilgileri
    dokuman_tipi = db.Column(db.Enum(DokumanTipi), nullable=False)
    dosya_adi = db.Column(db.String(255), nullable=False)
    dosya_yolu = db.Column(db.String(500), nullable=False)
    dosya_boyutu = db.Column(db.Integer, nullable=True)  # Bytes
    
    # Kullanıcı Bilgileri
    yuklenen_kullanici_id = db.Column(db.Integer, db.ForeignKey('kullanicilar.id', ondelete='SET NULL'), nullable=True)
    
    # Sistem Bilgileri
    yuklenme_tarihi = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

    # İlişkiler
    tedarikci = db.relationship('Tedarikci', backref='dokumanlar')
    siparis = db.relationship('SatinAlmaSiparisi', backref='dokumanlar')
    yuklenen_kullanici = db.relationship('Kullanici', backref='yuklenen_tedarikci_dokumanlari')

    __table_args__ = (
        db.Index('idx_tedarikci_dokuman_tedarikci', 'tedarikci_id'),
        db.Index('idx_tedarikci_dokuman_siparis', 'siparis_id'),
        db.Index('idx_tedarikci_dokuman_tipi', 'dokuman_tipi'),
        db.Index('idx_tedarikci_dokuman_tarih', 'yuklenme_tarihi'),
    )

    def __repr__(self):
        return f'<TedarikciDokuman tedarikci_id={self.tedarikci_id} tip={self.dokuman_tipi.value}>'
