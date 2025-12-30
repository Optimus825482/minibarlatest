from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timezone
from sqlalchemy import Numeric
from sqlalchemy.dialects.postgresql import JSONB
import enum
import pytz

db = SQLAlchemy()

# KKTC Timezone (Kıbrıs - Europe/Nicosia)
KKTC_TZ = pytz.timezone('Europe/Nicosia')


def get_kktc_now():
    """Kıbrıs saat diliminde şu anki zamanı döndürür."""
    return datetime.now(KKTC_TZ)

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
    olusturma_tarihi = db.Column(db.DateTime(timezone=True), default=lambda: get_kktc_now())
    aktif = db.Column(db.Boolean, default=True)
    
    # İlk stok yükleme durumu - Her otel için 1 kez kullanılabilir
    ilk_stok_yuklendi = db.Column(db.Boolean, default=False)
    ilk_stok_yukleme_tarihi = db.Column(db.DateTime(timezone=True), nullable=True)
    ilk_stok_yukleyen_id = db.Column(db.Integer, db.ForeignKey('kullanicilar.id', ondelete='SET NULL'), nullable=True)
    
    # E-posta Bildirim Ayarları - Otel bazında açılıp kapatılabilir
    email_bildirim_aktif = db.Column(db.Boolean, default=False)  # Varsayılan kapalı
    email_uyari_aktif = db.Column(db.Boolean, default=False)  # Uyarı e-postaları
    email_rapor_aktif = db.Column(db.Boolean, default=False)  # Rapor e-postaları
    email_sistem_aktif = db.Column(db.Boolean, default=False)  # Sistem bildirimleri
    
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
    olusturma_tarihi = db.Column(db.DateTime(timezone=True), default=lambda: get_kktc_now())
    
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
    olusturma_tarihi = db.Column(db.DateTime(timezone=True), default=lambda: get_kktc_now())
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
    olusturma_tarihi = db.Column(db.DateTime(timezone=True), default=lambda: get_kktc_now())
    
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
    olusturma_tarihi = db.Column(db.DateTime(timezone=True), default=lambda: get_kktc_now())
    
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
    olusturma_tarihi = db.Column(db.DateTime(timezone=True), default=lambda: get_kktc_now())
    
    # İlişkiler
    urun = db.relationship('Urun', backref='setup_icerikler')
    
    def __repr__(self):
        return f'<SetupIcerik Setup:{self.setup_id} Urun:{self.urun_id}>'


# Many-to-Many ara tablo: OdaTipi <-> Setup (Otel bazlı)
oda_tipi_setup = db.Table('oda_tipi_setup',
    db.Column('otel_id', db.Integer, db.ForeignKey('oteller.id', ondelete='CASCADE'), primary_key=True),
    db.Column('oda_tipi_id', db.Integer, db.ForeignKey('oda_tipleri.id', ondelete='CASCADE'), primary_key=True),
    db.Column('setup_id', db.Integer, db.ForeignKey('setuplar.id', ondelete='CASCADE'), primary_key=True),
    db.Column('olusturma_tarihi', db.DateTime(timezone=True), default=lambda: get_kktc_now())
)


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
    oda_tipi_id = db.Column(db.Integer, db.ForeignKey('oda_tipleri.id'), nullable=True)  # Oda tipi referansı
    kapasite = db.Column(db.Integer)
    aktif = db.Column(db.Boolean, default=True)
    olusturma_tarihi = db.Column(db.DateTime(timezone=True), default=lambda: get_kktc_now())
    
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
    olusturma_tarihi = db.Column(db.DateTime(timezone=True), default=lambda: get_kktc_now())
    
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
    olusturma_tarihi = db.Column(db.DateTime(timezone=True), default=lambda: get_kktc_now())
    
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
    islem_tarihi = db.Column(db.DateTime(timezone=True), default=lambda: get_kktc_now())
    
    # İlişki
    islem_yapan = db.relationship('Kullanici', foreign_keys=[islem_yapan_id])
    
    def __repr__(self):
        return f'<StokHareket {self.hareket_tipi} - {self.miktar}>'


class PersonelZimmet(db.Model):
    """Personel zimmet tablosu - Kat sorumlusu zimmet başlık"""
    __tablename__ = 'personel_zimmet'
    
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    personel_id = db.Column(db.Integer, db.ForeignKey('kullanicilar.id'), nullable=False)
    otel_id = db.Column(db.Integer, db.ForeignKey('oteller.id', ondelete='SET NULL'), nullable=True)  # Otel bazlı filtreleme
    zimmet_tarihi = db.Column(db.DateTime(timezone=True), default=lambda: get_kktc_now())
    iade_tarihi = db.Column(db.DateTime(timezone=True), nullable=True)
    teslim_eden_id = db.Column(db.Integer, db.ForeignKey('kullanicilar.id'))
    durum = db.Column(db.Enum('aktif', 'iade_edildi', 'iptal', name='zimmet_durum'), default='aktif')
    aciklama = db.Column(db.Text)
    
    # İlişkiler
    otel = db.relationship('Otel', foreign_keys=[otel_id], backref='zimmetler')
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
    islem_tarihi = db.Column(db.DateTime(timezone=True), default=lambda: get_kktc_now())
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
    islem_tarihi = db.Column(db.DateTime(timezone=True), default=lambda: get_kktc_now(), nullable=False)
    
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
    olusturma_tarihi = db.Column(db.DateTime(timezone=True), default=lambda: get_kktc_now(), nullable=False)
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
    islem_tarihi = db.Column(db.DateTime(timezone=True), default=lambda: get_kktc_now(), nullable=False)
    
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
    olusturma_tarihi = db.Column(db.DateTime(timezone=True), default=lambda: get_kktc_now(), nullable=False)
    
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
    talep_tarihi = db.Column(db.DateTime(timezone=True), default=lambda: get_kktc_now(), nullable=False)
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
    okutma_tarihi = db.Column(db.DateTime(timezone=True), default=lambda: get_kktc_now(), nullable=False)
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
    cikis_saati = db.Column(db.Time, nullable=True)  # Sadece DEPARTURES için (Dep.Time)
    
    # Kayıt Tipi (Otomatik algılanır: in_house, arrival veya departure)
    kayit_tipi = db.Column(db.String(20), nullable=False)  # in_house, arrival, departure
    
    # Sistem Bilgileri
    olusturma_tarihi = db.Column(db.DateTime(timezone=True), default=lambda: get_kktc_now(), nullable=False)
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
        db.Index('idx_dosya_otel_id', 'otel_id'),
    )
    
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    islem_kodu = db.Column(db.String(50), unique=True, nullable=False, index=True)
    
    # Otel Bilgisi - Hangi otele ait olduğu
    otel_id = db.Column(db.Integer, db.ForeignKey('oteller.id', ondelete='CASCADE'), nullable=True)
    
    # Dosya Bilgileri
    dosya_adi = db.Column(db.String(255), nullable=False)
    dosya_yolu = db.Column(db.String(500), nullable=False)
    dosya_tipi = db.Column(db.String(20), nullable=False)  # in_house, arrivals, departures
    dosya_boyutu = db.Column(db.Integer)  # bytes
    
    # İşlem Bilgileri
    yukleme_tarihi = db.Column(db.DateTime(timezone=True), default=lambda: get_kktc_now(), nullable=False)
    silme_tarihi = db.Column(db.DateTime(timezone=True), nullable=True)  # Otomatik silme için
    durum = db.Column(db.String(20), default='yuklendi', nullable=False)  # yuklendi, isleniyor, tamamlandi, hata, silindi
    
    # İstatistikler
    toplam_satir = db.Column(db.Integer, default=0)
    basarili_satir = db.Column(db.Integer, default=0)
    hatali_satir = db.Column(db.Integer, default=0)
    hata_detaylari = db.Column(JSONB, nullable=True)  # Hata mesajları (JSONB formatında)
    
    # Kullanıcı Bilgileri
    yuklenen_kullanici_id = db.Column(db.Integer, db.ForeignKey('kullanicilar.id'))
    
    # İlişkiler
    yuklenen_kullanici = db.relationship('Kullanici', foreign_keys=[yuklenen_kullanici_id])
    otel = db.relationship('Otel', backref='dosya_yuklemeleri')
    
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
    timestamp = db.Column(db.DateTime(timezone=True), default=lambda: get_kktc_now(), nullable=False)
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
    training_date = db.Column(db.DateTime(timezone=True), default=lambda: get_kktc_now(), nullable=False)
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
    created_at = db.Column(db.DateTime(timezone=True), default=lambda: get_kktc_now(), nullable=False)
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
    training_start = db.Column(db.DateTime(timezone=True), default=lambda: get_kktc_now(), nullable=False)
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
    timestamp = db.Column(db.DateTime(timezone=True), default=lambda: get_kktc_now(), nullable=False)
    
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
    created_at = db.Column(db.DateTime(timezone=True), default=lambda: get_kktc_now(), nullable=False)
    
    def __repr__(self):
        return f'<MLFeature {self.metric_type} - #{self.entity_id}>'


class MLPerformanceLog(db.Model):
    """ML Model işlem performans logları"""
    __tablename__ = 'ml_performance_logs'
    __table_args__ = (
        db.Index('idx_ml_perf_operation', 'operation'),
        db.Index('idx_ml_perf_timestamp', 'timestamp'),
        db.Index('idx_ml_perf_success', 'success'),
    )
    
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    operation = db.Column(db.String(50), nullable=False)  # 'model_save', 'model_load'
    model_type = db.Column(db.String(50), nullable=False)
    metric_type = db.Column(db.String(50), nullable=False)
    duration_ms = db.Column(db.Float, nullable=False)
    file_size_mb = db.Column(db.Float)
    success = db.Column(db.Boolean, default=True)
    error_message = db.Column(db.Text)
    timestamp = db.Column(db.DateTime(timezone=True), default=lambda: get_kktc_now(), nullable=False)
    
    def __repr__(self):
        return f'<MLPerformanceLog {self.operation} - {self.model_type}>'


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
    timestamp = db.Column(db.DateTime(timezone=True), default=lambda: get_kktc_now(), nullable=False)
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
    created_at = db.Column(db.DateTime(timezone=True), default=lambda: get_kktc_now(), nullable=False)
    
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
    created_at = db.Column(db.DateTime(timezone=True), default=lambda: get_kktc_now(), nullable=False)
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
    changed_at = db.Column(db.DateTime(timezone=True), default=lambda: get_kktc_now(), nullable=False)
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
    son_guncelleme_tarihi = db.Column(db.DateTime(timezone=True), default=lambda: get_kktc_now())
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
                self.son_giris_tarihi = get_kktc_now()
            elif islem_tipi in ['cikis', 'fire']:
                self.mevcut_stok -= miktar
                self.son_cikis_tarihi = get_kktc_now()
                self.son_30gun_cikis += miktar
            elif islem_tipi == 'sayim':
                self.sayim_farki = self.mevcut_stok - miktar
                self.mevcut_stok = miktar
                self.son_sayim_tarihi = get_kktc_now()
                self.son_sayim_miktari = miktar

            self.son_guncelleme_tarihi = get_kktc_now()
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
    olusturma_tarihi = db.Column(db.DateTime(timezone=True), default=lambda: get_kktc_now())
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
    olusturma_tarihi = db.Column(db.DateTime(timezone=True), default=lambda: get_kktc_now())

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
    kullanilma_tarihi = db.Column(db.DateTime(timezone=True), default=lambda: get_kktc_now())
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
    olusturma_tarihi = db.Column(db.DateTime(timezone=True), default=lambda: get_kktc_now())

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
    olusturma_tarihi = db.Column(db.DateTime(timezone=True), default=lambda: get_kktc_now())

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
    olusturma_tarihi = db.Column(db.DateTime(timezone=True), default=lambda: get_kktc_now())
    guncelleme_tarihi = db.Column(db.DateTime(timezone=True), onupdate=lambda: get_kktc_now())

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
    olusturma_tarihi = db.Column(db.DateTime(timezone=True), default=lambda: get_kktc_now())
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
    degisiklik_tarihi = db.Column(db.DateTime(timezone=True), default=lambda: get_kktc_now())
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
    olusturma_tarihi = db.Column(db.DateTime(timezone=True), default=lambda: get_kktc_now())

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
    olusturma_tarihi = db.Column(db.DateTime(timezone=True), default=lambda: get_kktc_now())

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
    siparis_tarihi = db.Column(db.DateTime(timezone=True), default=lambda: get_kktc_now(), nullable=False)
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
    olusturma_tarihi = db.Column(db.DateTime(timezone=True), default=lambda: get_kktc_now(), nullable=False)
    guncelleme_tarihi = db.Column(db.DateTime(timezone=True), onupdate=lambda: get_kktc_now())

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
    olusturma_tarihi = db.Column(db.DateTime(timezone=True), default=lambda: get_kktc_now(), nullable=False)

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
    
    # Durum ve İptal Bilgileri
    durum = db.Column(db.String(20), default='aktif', nullable=False)  # aktif, iptal
    iptal_tarihi = db.Column(db.DateTime(timezone=True), nullable=True)
    iptal_eden_id = db.Column(db.Integer, db.ForeignKey('kullanicilar.id', ondelete='SET NULL'), nullable=True)
    iptal_aciklama = db.Column(db.Text, nullable=True)
    
    # Kullanıcı Bilgileri
    olusturan_id = db.Column(db.Integer, db.ForeignKey('kullanicilar.id', ondelete='SET NULL'), nullable=True)
    
    # Sistem Bilgileri
    islem_tarihi = db.Column(db.DateTime(timezone=True), default=lambda: get_kktc_now(), nullable=False)
    olusturma_tarihi = db.Column(db.DateTime(timezone=True), default=lambda: get_kktc_now(), nullable=False)
    guncelleme_tarihi = db.Column(db.DateTime(timezone=True), onupdate=lambda: get_kktc_now())

    # İlişkiler
    tedarikci = db.relationship('Tedarikci', backref='satin_alma_islemleri')
    otel = db.relationship('Otel', backref='satin_alma_islemleri')
    siparis = db.relationship('SatinAlmaSiparisi', backref='satin_alma_islemleri')
    detaylar = db.relationship('SatinAlmaIslemDetay', backref='islem', lazy=True, cascade='all, delete-orphan')
    olusturan = db.relationship('Kullanici', foreign_keys=[olusturan_id], backref='olusturdugun_satin_alma_islemleri')
    iptal_eden = db.relationship('Kullanici', foreign_keys=[iptal_eden_id], backref='iptal_ettigi_satin_alma_islemleri')

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
    olusturma_tarihi = db.Column(db.DateTime(timezone=True), default=lambda: get_kktc_now(), nullable=False)

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
    olusturma_tarihi = db.Column(db.DateTime(timezone=True), default=lambda: get_kktc_now(), nullable=False)
    guncelleme_tarihi = db.Column(db.DateTime(timezone=True), onupdate=lambda: get_kktc_now())

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
    iletisim_tarihi = db.Column(db.DateTime(timezone=True), default=lambda: get_kktc_now(), nullable=False)
    konu = db.Column(db.String(200), nullable=False)
    aciklama = db.Column(db.Text, nullable=False)
    
    # Kullanıcı Bilgileri
    kullanici_id = db.Column(db.Integer, db.ForeignKey('kullanicilar.id', ondelete='SET NULL'), nullable=True)
    
    # Sistem Bilgileri
    olusturma_tarihi = db.Column(db.DateTime(timezone=True), default=lambda: get_kktc_now(), nullable=False)

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
    yuklenme_tarihi = db.Column(db.DateTime(timezone=True), default=lambda: get_kktc_now(), nullable=False)

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


# ============================================
# KAT SORUMLUSU SİPARİŞ TALEPLERİ
# ============================================

class KatSorumlusuSiparisTalebi(db.Model):
    """Kat sorumlusunun depodan talep ettiği siparişler"""
    __tablename__ = 'kat_sorumlusu_siparis_talepleri'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    talep_no = db.Column(db.String(50), unique=True, nullable=False)
    
    # Kullanıcı Bilgileri
    kat_sorumlusu_id = db.Column(db.Integer, db.ForeignKey('kullanicilar.id', ondelete='CASCADE'), nullable=False)
    depo_sorumlusu_id = db.Column(db.Integer, db.ForeignKey('kullanicilar.id', ondelete='SET NULL'), nullable=True)
    
    # Tarih Bilgileri
    talep_tarihi = db.Column(db.DateTime(timezone=True), default=lambda: get_kktc_now(), nullable=False)
    onay_tarihi = db.Column(db.DateTime(timezone=True), nullable=True)
    teslim_tarihi = db.Column(db.DateTime(timezone=True), nullable=True)
    
    # Durum: beklemede, onaylandi, hazirlaniyor, teslim_edildi, iptal
    durum = db.Column(db.String(20), default='beklemede', nullable=False)
    
    # Açıklama
    aciklama = db.Column(db.Text, nullable=True)
    red_nedeni = db.Column(db.Text, nullable=True)
    
    # Sistem Bilgileri
    olusturma_tarihi = db.Column(db.DateTime(timezone=True), default=lambda: get_kktc_now(), nullable=False)
    guncelleme_tarihi = db.Column(db.DateTime(timezone=True), onupdate=lambda: get_kktc_now())

    # İlişkiler
    kat_sorumlusu = db.relationship('Kullanici', foreign_keys=[kat_sorumlusu_id], backref='siparis_talepleri')
    depo_sorumlusu = db.relationship('Kullanici', foreign_keys=[depo_sorumlusu_id], backref='islenen_talepler')
    detaylar = db.relationship('KatSorumlusuSiparisTalepDetay', backref='talep', lazy=True, cascade='all, delete-orphan')

    __table_args__ = (
        db.Index('idx_talep_durum_tarih', 'durum', 'talep_tarihi'),
        db.Index('idx_talep_kat_sorumlusu', 'kat_sorumlusu_id'),
        db.Index('idx_talep_depo_sorumlusu', 'depo_sorumlusu_id'),
        db.Index('idx_talep_no', 'talep_no'),
    )

    def __repr__(self):
        return f'<KatSorumlusuSiparisTalebi {self.talep_no} - {self.durum}>'


class KatSorumlusuSiparisTalepDetay(db.Model):
    """Sipariş talep detay satırları"""
    __tablename__ = 'kat_sorumlusu_siparis_talep_detaylari'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    talep_id = db.Column(db.Integer, db.ForeignKey('kat_sorumlusu_siparis_talepleri.id', ondelete='CASCADE'), nullable=False)
    urun_id = db.Column(db.Integer, db.ForeignKey('urunler.id', ondelete='RESTRICT'), nullable=False)
    
    # Miktar Bilgileri
    talep_miktari = db.Column(db.Integer, nullable=False)
    onaylanan_miktar = db.Column(db.Integer, default=0, nullable=False)
    teslim_edilen_miktar = db.Column(db.Integer, default=0, nullable=False)
    
    # Aciliyet: normal, acil
    aciliyet = db.Column(db.String(10), default='normal', nullable=False)
    
    # Sistem Bilgileri
    olusturma_tarihi = db.Column(db.DateTime(timezone=True), default=lambda: get_kktc_now(), nullable=False)

    # İlişkiler
    urun = db.relationship('Urun', backref='talep_detaylari')

    __table_args__ = (
        db.Index('idx_talep_detay_talep', 'talep_id'),
        db.Index('idx_talep_detay_urun', 'urun_id'),
        db.CheckConstraint('talep_miktari > 0', name='check_talep_miktar_pozitif'),
        db.CheckConstraint('onaylanan_miktar >= 0', name='check_onaylanan_miktar_pozitif'),
        db.CheckConstraint('teslim_edilen_miktar >= 0', name='check_teslim_miktar_pozitif'),
        db.CheckConstraint('teslim_edilen_miktar <= onaylanan_miktar', name='check_teslim_onay_limit'),
    )

    def __repr__(self):
        return f'<KatSorumlusuSiparisTalepDetay talep_id={self.talep_id} urun_id={self.urun_id}>'


# ============================================
# GÖREVLENDİRME SİSTEMİ MODELLERİ
# ============================================

class GorevTipi(str, enum.Enum):
    """Görev tipleri"""
    INHOUSE_KONTROL = 'inhouse_kontrol'
    ARRIVAL_KONTROL = 'arrival_kontrol'
    DEPARTURE_KONTROL = 'departure_kontrol'
    INHOUSE_YUKLEME = 'inhouse_yukleme'
    ARRIVALS_YUKLEME = 'arrivals_yukleme'
    DEPARTURES_YUKLEME = 'departures_yukleme'


class GorevDurum(str, enum.Enum):
    """Görev durumları"""
    PENDING = 'pending'
    IN_PROGRESS = 'in_progress'
    COMPLETED = 'completed'
    DND_PENDING = 'dnd_pending'
    INCOMPLETE = 'incomplete'


class GunlukGorev(db.Model):
    """Günlük görev ana tablosu - Kat sorumluları için minibar kontrol görevleri"""
    __tablename__ = 'gunluk_gorevler'
    
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    otel_id = db.Column(db.Integer, db.ForeignKey('oteller.id', ondelete='CASCADE'), nullable=False)
    personel_id = db.Column(db.Integer, db.ForeignKey('kullanicilar.id', ondelete='CASCADE'), nullable=False)
    gorev_tarihi = db.Column(db.Date, nullable=False)
    gorev_tipi = db.Column(
        db.Enum('inhouse_kontrol', 'arrival_kontrol', 'departure_kontrol', 'inhouse_yukleme', 'arrivals_yukleme', 'departures_yukleme', name='gorev_tipi_enum'),
        nullable=False
    )
    durum = db.Column(
        db.Enum('pending', 'in_progress', 'completed', 'dnd_pending', 'incomplete', name='gorev_durum_enum'),
        default='pending',
        nullable=False
    )
    olusturma_tarihi = db.Column(db.DateTime(timezone=True), default=lambda: get_kktc_now(), nullable=False)
    tamamlanma_tarihi = db.Column(db.DateTime(timezone=True), nullable=True)
    notlar = db.Column(db.Text, nullable=True)
    
    # İlişkiler
    otel = db.relationship('Otel', backref='gunluk_gorevler')
    personel = db.relationship('Kullanici', backref='gunluk_gorevler')
    detaylar = db.relationship('GorevDetay', backref='gorev', lazy=True, cascade='all, delete-orphan')
    
    __table_args__ = (
        db.Index('idx_gunluk_gorev_otel_tarih', 'otel_id', 'gorev_tarihi'),
        db.Index('idx_gunluk_gorev_personel_tarih', 'personel_id', 'gorev_tarihi'),
        db.Index('idx_gunluk_gorev_durum', 'durum'),
        db.Index('idx_gunluk_gorev_tipi', 'gorev_tipi'),
    )
    
    def __repr__(self):
        return f'<GunlukGorev #{self.id} - {self.gorev_tipi} - {self.durum}>'


class GorevDetay(db.Model):
    """Görev detay tablosu - Her oda için ayrı görev detayı"""
    __tablename__ = 'gorev_detaylari'
    
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    gorev_id = db.Column(db.Integer, db.ForeignKey('gunluk_gorevler.id', ondelete='CASCADE'), nullable=False)
    oda_id = db.Column(db.Integer, db.ForeignKey('odalar.id', ondelete='CASCADE'), nullable=False)
    misafir_kayit_id = db.Column(db.Integer, db.ForeignKey('misafir_kayitlari.id', ondelete='SET NULL'), nullable=True)
    durum = db.Column(
        db.Enum('pending', 'in_progress', 'completed', 'dnd_pending', 'incomplete', name='gorev_durum_enum'),
        default='pending',
        nullable=False
    )
    varis_saati = db.Column(db.Time, nullable=True)  # Arrivals için varış saati
    cikis_saati = db.Column(db.Time, nullable=True)  # Departures için çıkış saati
    oncelik_sirasi = db.Column(db.Integer, default=999, nullable=False)  # Görev öncelik sırası
    kontrol_zamani = db.Column(db.DateTime(timezone=True), nullable=True)
    dnd_sayisi = db.Column(db.Integer, default=0, nullable=False)
    son_dnd_zamani = db.Column(db.DateTime(timezone=True), nullable=True)
    notlar = db.Column(db.Text, nullable=True)
    
    # İlişkiler
    oda = db.relationship('Oda', backref='gorev_detaylari')
    misafir_kayit = db.relationship('MisafirKayit', backref='gorev_detaylari')
    dnd_kontroller = db.relationship('DNDKontrol', backref='gorev_detay', lazy=True, cascade='all, delete-orphan')
    durum_loglari = db.relationship('GorevDurumLog', backref='gorev_detay', lazy=True, cascade='all, delete-orphan')
    
    __table_args__ = (
        db.Index('idx_gorev_detay_gorev', 'gorev_id'),
        db.Index('idx_gorev_detay_oda', 'oda_id'),
        db.Index('idx_gorev_detay_durum', 'durum'),
        db.Index('idx_gorev_detay_dnd', 'dnd_sayisi'),
        db.Index('idx_gorev_detay_oncelik', 'oncelik_sirasi'),
    )
    
    def __repr__(self):
        return f'<GorevDetay #{self.id} - Oda {self.oda_id} - {self.durum}>'


class DNDKontrol(db.Model):
    """DND kontrol kayıtları - Her DND işaretlemesi için ayrı kayıt"""
    __tablename__ = 'dnd_kontroller'
    
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    gorev_detay_id = db.Column(db.Integer, db.ForeignKey('gorev_detaylari.id', ondelete='CASCADE'), nullable=False)
    kontrol_zamani = db.Column(db.DateTime(timezone=True), default=lambda: get_kktc_now(), nullable=False)
    kontrol_eden_id = db.Column(db.Integer, db.ForeignKey('kullanicilar.id', ondelete='SET NULL'), nullable=True)
    notlar = db.Column(db.Text, nullable=True)
    
    # İlişkiler
    kontrol_eden = db.relationship('Kullanici', backref='dnd_kontrolleri')
    
    __table_args__ = (
        db.Index('idx_dnd_kontrol_gorev_detay', 'gorev_detay_id'),
        db.Index('idx_dnd_kontrol_zaman', 'kontrol_zamani'),
    )
    
    def __repr__(self):
        return f'<DNDKontrol #{self.id} - GorevDetay {self.gorev_detay_id}>'


class YuklemeGorev(db.Model):
    """Yükleme görevleri - Depo sorumluları için günlük doluluk yükleme görevleri"""
    __tablename__ = 'yukleme_gorevleri'
    
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    otel_id = db.Column(db.Integer, db.ForeignKey('oteller.id', ondelete='CASCADE'), nullable=False)
    depo_sorumlusu_id = db.Column(db.Integer, db.ForeignKey('kullanicilar.id', ondelete='CASCADE'), nullable=False)
    gorev_tarihi = db.Column(db.Date, nullable=False)
    dosya_tipi = db.Column(db.String(20), nullable=False)  # 'inhouse' veya 'arrivals'
    durum = db.Column(
        db.Enum('pending', 'in_progress', 'completed', 'dnd_pending', 'incomplete', name='gorev_durum_enum'),
        default='pending',
        nullable=False
    )
    yukleme_zamani = db.Column(db.DateTime(timezone=True), nullable=True)
    dosya_yukleme_id = db.Column(db.Integer, db.ForeignKey('dosya_yuklemeleri.id', ondelete='SET NULL'), nullable=True)
    olusturma_tarihi = db.Column(db.DateTime(timezone=True), default=lambda: get_kktc_now(), nullable=False)
    
    # İlişkiler
    otel = db.relationship('Otel', backref='yukleme_gorevleri')
    depo_sorumlusu = db.relationship('Kullanici', backref='yukleme_gorevleri')
    dosya_yukleme = db.relationship('DosyaYukleme', backref='yukleme_gorevi')
    
    __table_args__ = (
        db.Index('idx_yukleme_gorev_otel_tarih', 'otel_id', 'gorev_tarihi'),
        db.Index('idx_yukleme_gorev_depo_sorumlusu', 'depo_sorumlusu_id'),
        db.Index('idx_yukleme_gorev_durum', 'durum'),
        db.UniqueConstraint('otel_id', 'gorev_tarihi', 'dosya_tipi', name='uq_yukleme_gorev_otel_tarih_tip'),
    )
    
    def __repr__(self):
        return f'<YuklemeGorev #{self.id} - {self.dosya_tipi} - {self.durum}>'


class GorevDurumLog(db.Model):
    """Görev durum değişiklik logları - Audit trail için"""
    __tablename__ = 'gorev_durum_loglari'
    
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    gorev_detay_id = db.Column(db.Integer, db.ForeignKey('gorev_detaylari.id', ondelete='CASCADE'), nullable=False)
    onceki_durum = db.Column(
        db.Enum('pending', 'in_progress', 'completed', 'dnd_pending', 'incomplete', name='gorev_durum_enum'),
        nullable=True
    )
    yeni_durum = db.Column(
        db.Enum('pending', 'in_progress', 'completed', 'dnd_pending', 'incomplete', name='gorev_durum_enum'),
        nullable=False
    )
    degisiklik_zamani = db.Column(db.DateTime(timezone=True), default=lambda: get_kktc_now(), nullable=False)
    degistiren_id = db.Column(db.Integer, db.ForeignKey('kullanicilar.id', ondelete='SET NULL'), nullable=True)
    aciklama = db.Column(db.Text, nullable=True)
    
    # İlişkiler
    degistiren = db.relationship('Kullanici', backref='gorev_durum_degisiklikleri')
    
    __table_args__ = (
        db.Index('idx_gorev_durum_log_detay', 'gorev_detay_id'),
        db.Index('idx_gorev_durum_log_zaman', 'degisiklik_zamani'),
    )
    
    def __repr__(self):
        return f'<GorevDurumLog #{self.id} - {self.onceki_durum} -> {self.yeni_durum}>'


# ============================================
# ODA KONTROL KAYITLARI
# ============================================

class OdaKontrolKaydi(db.Model):
    """Oda kontrol kayıtları - Kat sorumlusunun oda kontrolü başlangıç ve bitiş zamanları"""
    __tablename__ = 'oda_kontrol_kayitlari'
    
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    oda_id = db.Column(db.Integer, db.ForeignKey('odalar.id', ondelete='CASCADE'), nullable=False)
    personel_id = db.Column(db.Integer, db.ForeignKey('kullanicilar.id', ondelete='CASCADE'), nullable=False)
    kontrol_tarihi = db.Column(db.Date, nullable=False)
    
    # Zaman bilgileri
    baslangic_zamani = db.Column(db.DateTime(timezone=True), nullable=False)
    bitis_zamani = db.Column(db.DateTime(timezone=True), nullable=True)
    
    # Kontrol tipi: sarfiyat_yok, urun_eklendi
    kontrol_tipi = db.Column(db.String(20), default='sarfiyat_yok', nullable=False)
    
    # Sistem bilgileri
    olusturma_tarihi = db.Column(db.DateTime(timezone=True), default=lambda: get_kktc_now(), nullable=False)
    
    # İlişkiler
    oda = db.relationship('Oda', backref='kontrol_kayitlari')
    personel = db.relationship('Kullanici', backref='oda_kontrol_kayitlari')
    
    __table_args__ = (
        db.Index('idx_oda_kontrol_oda_tarih', 'oda_id', 'kontrol_tarihi'),
        db.Index('idx_oda_kontrol_personel_tarih', 'personel_id', 'kontrol_tarihi'),
        db.Index('idx_oda_kontrol_bitis', 'bitis_zamani'),
    )
    
    def __repr__(self):
        return f'<OdaKontrolKaydi #{self.id} - Oda {self.oda_id} - {self.kontrol_tipi}>'


# ============================================
# EMAIL SİSTEMİ MODELLERİ
# ============================================

class EmailAyarlari(db.Model):
    """Email SMTP ayarları tablosu"""
    __tablename__ = 'email_ayarlari'
    
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    smtp_server = db.Column(db.String(255), nullable=False)
    smtp_port = db.Column(db.Integer, nullable=False, default=587)
    smtp_username = db.Column(db.String(255), nullable=False)
    smtp_password = db.Column(db.String(500), nullable=False)  # Şifrelenmiş saklanmalı
    smtp_use_tls = db.Column(db.Boolean, default=True)
    smtp_use_ssl = db.Column(db.Boolean, default=False)
    sender_email = db.Column(db.String(255), nullable=False)
    sender_name = db.Column(db.String(255), default='Minibar Takip Sistemi')
    aktif = db.Column(db.Boolean, default=True)
    olusturma_tarihi = db.Column(db.DateTime(timezone=True), default=lambda: get_kktc_now())
    guncelleme_tarihi = db.Column(db.DateTime(timezone=True), onupdate=lambda: get_kktc_now())
    guncelleyen_id = db.Column(db.Integer, db.ForeignKey('kullanicilar.id', ondelete='SET NULL'), nullable=True)
    
    # İlişkiler
    guncelleyen = db.relationship('Kullanici', foreign_keys=[guncelleyen_id], backref='email_ayar_guncellemeleri')
    
    def __repr__(self):
        return f'<EmailAyarlari {self.smtp_server}:{self.smtp_port}>'


class EmailLog(db.Model):
    """Gönderilen email kayıtları tablosu"""
    __tablename__ = 'email_loglari'
    
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    alici_email = db.Column(db.String(255), nullable=False)
    alici_kullanici_id = db.Column(db.Integer, db.ForeignKey('kullanicilar.id', ondelete='SET NULL'), nullable=True)
    konu = db.Column(db.String(500), nullable=False)
    icerik = db.Column(db.Text, nullable=False)
    email_tipi = db.Column(db.String(50), nullable=False)  # uyari, bilgi, sistem
    durum = db.Column(db.String(20), default='gonderildi')  # gonderildi, hata, beklemede
    hata_mesaji = db.Column(db.Text, nullable=True)
    gonderim_tarihi = db.Column(db.DateTime(timezone=True), default=lambda: get_kktc_now())
    okundu = db.Column(db.Boolean, default=False)
    okunma_tarihi = db.Column(db.DateTime(timezone=True), nullable=True)
    tracking_id = db.Column(db.String(100), unique=True, nullable=True)
    ilgili_tablo = db.Column(db.String(100), nullable=True)
    ilgili_kayit_id = db.Column(db.Integer, nullable=True)
    ek_bilgiler = db.Column(JSONB, nullable=True)
    
    # İlişkiler
    alici_kullanici = db.relationship('Kullanici', foreign_keys=[alici_kullanici_id], backref='alinan_emailler')
    
    __table_args__ = (
        db.Index('idx_email_log_alici', 'alici_email'),
        db.Index('idx_email_log_tarih', 'gonderim_tarihi'),
        db.Index('idx_email_log_tipi', 'email_tipi'),
        db.Index('idx_email_log_durum', 'durum'),
        db.Index('idx_email_log_tracking', 'tracking_id'),
    )
    
    def __repr__(self):
        return f'<EmailLog #{self.id} - {self.alici_email} - {self.durum}>'


class DolulukUyariLog(db.Model):
    """Günlük doluluk uyarı kayıtları tablosu"""
    __tablename__ = 'doluluk_uyari_loglari'
    
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    otel_id = db.Column(db.Integer, db.ForeignKey('oteller.id', ondelete='CASCADE'), nullable=False)
    depo_sorumlusu_id = db.Column(db.Integer, db.ForeignKey('kullanicilar.id', ondelete='CASCADE'), nullable=False)
    uyari_tarihi = db.Column(db.Date, nullable=False)
    uyari_tipi = db.Column(db.String(50), nullable=False)  # inhouse_eksik, arrivals_eksik, her_ikisi_eksik
    email_gonderildi = db.Column(db.Boolean, default=False)
    email_log_id = db.Column(db.Integer, db.ForeignKey('email_loglari.id', ondelete='SET NULL'), nullable=True)
    sistem_yoneticisi_bilgilendirildi = db.Column(db.Boolean, default=False)
    olusturma_tarihi = db.Column(db.DateTime(timezone=True), default=lambda: get_kktc_now())
    
    # İlişkiler
    otel = db.relationship('Otel', backref='doluluk_uyarilari')
    depo_sorumlusu = db.relationship('Kullanici', foreign_keys=[depo_sorumlusu_id], backref='doluluk_uyarilari')
    email_log = db.relationship('EmailLog', backref='doluluk_uyari')
    
    __table_args__ = (
        db.Index('idx_doluluk_uyari_tarih', 'uyari_tarihi'),
        db.Index('idx_doluluk_uyari_otel', 'otel_id', 'uyari_tarihi'),
    )
    
    def __repr__(self):
        return f'<DolulukUyariLog #{self.id} - Otel {self.otel_id} - {self.uyari_tarihi}>'


# ============================================
# ZİMMET ŞABLON SİSTEMİ
# ==========================


# ============================================
# ZİMMET ŞABLON SİSTEMİ
# ============================================

class ZimmetSablon(db.Model):
    """Zimmet şablonları - Önceden tanımlanmış ürün setleri"""
    __tablename__ = 'zimmet_sablonlari'
    
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    sablon_adi = db.Column(db.String(100), nullable=False)
    aciklama = db.Column(db.Text, nullable=True)
    olusturan_id = db.Column(db.Integer, db.ForeignKey('kullanicilar.id', ondelete='SET NULL'), nullable=True)
    otel_id = db.Column(db.Integer, db.ForeignKey('oteller.id', ondelete='CASCADE'), nullable=True)  # NULL ise tüm oteller için geçerli
    aktif = db.Column(db.Boolean, default=True)
    olusturma_tarihi = db.Column(db.DateTime(timezone=True), default=lambda: get_kktc_now())
    guncelleme_tarihi = db.Column(db.DateTime(timezone=True), onupdate=lambda: get_kktc_now())
    
    # İlişkiler
    olusturan = db.relationship('Kullanici', backref='zimmet_sablonlari')
    otel = db.relationship('Otel', backref='zimmet_sablonlari')
    detaylar = db.relationship('ZimmetSablonDetay', backref='sablon', lazy=True, cascade='all, delete-orphan')
    
    __table_args__ = (
        db.Index('idx_zimmet_sablon_otel', 'otel_id'),
        db.Index('idx_zimmet_sablon_aktif', 'aktif'),
    )
    
    def __repr__(self):
        return f'<ZimmetSablon #{self.id} - {self.sablon_adi}>'


class ZimmetSablonDetay(db.Model):
    """Zimmet şablon detayları - Şablondaki ürünler ve miktarlar"""
    __tablename__ = 'zimmet_sablon_detaylari'
    
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    sablon_id = db.Column(db.Integer, db.ForeignKey('zimmet_sablonlari.id', ondelete='CASCADE'), nullable=False)
    urun_id = db.Column(db.Integer, db.ForeignKey('urunler.id', ondelete='CASCADE'), nullable=False)
    varsayilan_miktar = db.Column(db.Integer, nullable=False, default=1)
    
    # İlişkiler
    urun = db.relationship('Urun', backref='sablon_detaylari')
    
    __table_args__ = (
        db.Index('idx_zimmet_sablon_detay_sablon', 'sablon_id'),
        db.Index('idx_zimmet_sablon_detay_urun', 'urun_id'),
        db.UniqueConstraint('sablon_id', 'urun_id', name='uq_sablon_urun'),
    )
    
    def __repr__(self):
        return f'<ZimmetSablonDetay sablon={self.sablon_id} urun={self.urun_id}>'


# ============================================
# ANA DEPO TEDARİK SİSTEMİ
# ============================================

class AnaDepoTedarikDurum(str, enum.Enum):
    """Ana depo tedarik durumları"""
    AKTIF = 'aktif'
    IPTAL = 'iptal'


class AnaDepoTedarik(db.Model):
    """Ana depodan yapılan tedarik işlemleri - Başlık tablosu"""
    __tablename__ = 'ana_depo_tedarikleri'
    
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    tedarik_no = db.Column(db.String(50), unique=True, nullable=False)  # ADT-20251205-001 formatında
    otel_id = db.Column(db.Integer, db.ForeignKey('oteller.id', ondelete='CASCADE'), nullable=False)
    depo_sorumlusu_id = db.Column(db.Integer, db.ForeignKey('kullanicilar.id', ondelete='SET NULL'), nullable=True)
    islem_tarihi = db.Column(db.DateTime(timezone=True), default=lambda: get_kktc_now(), nullable=False)
    toplam_urun_sayisi = db.Column(db.Integer, default=0)
    toplam_miktar = db.Column(db.Integer, default=0)
    aciklama = db.Column(db.Text, nullable=True)
    
    # Durum ve iptal bilgileri
    durum = db.Column(db.String(20), default='aktif')  # aktif, iptal
    iptal_tarihi = db.Column(db.DateTime(timezone=True), nullable=True)
    iptal_eden_id = db.Column(db.Integer, db.ForeignKey('kullanicilar.id', ondelete='SET NULL'), nullable=True)
    iptal_nedeni = db.Column(db.Text, nullable=True)
    
    # Sistem yöneticisi bildirimi
    sistem_yoneticisi_goruldu = db.Column(db.Boolean, default=False)
    gorulme_tarihi = db.Column(db.DateTime(timezone=True), nullable=True)
    
    # İlişkiler
    otel = db.relationship('Otel', backref='ana_depo_tedarikleri')
    depo_sorumlusu = db.relationship('Kullanici', foreign_keys=[depo_sorumlusu_id], backref='ana_depo_tedarikleri')
    iptal_eden = db.relationship('Kullanici', foreign_keys=[iptal_eden_id])
    detaylar = db.relationship('AnaDepoTedarikDetay', backref='tedarik', lazy=True, cascade='all, delete-orphan')
    
    __table_args__ = (
        db.Index('idx_ana_depo_tedarik_tarih', 'islem_tarihi'),
        db.Index('idx_ana_depo_tedarik_otel', 'otel_id'),
        db.Index('idx_ana_depo_tedarik_depo_sorumlusu', 'depo_sorumlusu_id'),
        db.Index('idx_ana_depo_tedarik_goruldu', 'sistem_yoneticisi_goruldu'),
        db.Index('idx_ana_depo_tedarik_durum', 'durum'),
    )
    
    def ayni_gun_mu(self):
        """İşlem bugün mü yapıldı?"""
        bugun = get_kktc_now().date()
        return self.islem_tarihi.date() == bugun
    
    def iptal_edilebilir_mi(self, kullanici_rol, kullanici_id):
        """
        İşlem iptal edilebilir mi kontrol et
        
        Kurallar:
        - Zaten iptal edilmişse iptal edilemez
        - Depo sorumlusu sadece kendi işlemlerini iptal edebilir
        - Aynı gün kuralı kaldırıldı - zimmet kullanılmadıysa her zaman iptal edilebilir
        """
        if self.durum == 'iptal':
            return False, "Bu işlem zaten iptal edilmiş."
        
        # Depo sorumlusu sadece kendi işlemlerini iptal edebilir
        if kullanici_rol == 'depo_sorumlusu':
            if self.depo_sorumlusu_id != kullanici_id:
                return False, "Sadece kendi işlemlerinizi iptal edebilirsiniz."
        
        return True, None
    
    def __repr__(self):
        return f'<AnaDepoTedarik #{self.id} - {self.tedarik_no}>'


class AnaDepoTedarikDetay(db.Model):
    """Ana depo tedarik detayları - Çekilen ürünler"""
    __tablename__ = 'ana_depo_tedarik_detaylari'
    
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    tedarik_id = db.Column(db.Integer, db.ForeignKey('ana_depo_tedarikleri.id', ondelete='CASCADE'), nullable=False)
    urun_id = db.Column(db.Integer, db.ForeignKey('urunler.id', ondelete='CASCADE'), nullable=False)
    miktar = db.Column(db.Integer, nullable=False)
    created_at = db.Column(db.DateTime(timezone=True), default=lambda: get_kktc_now(), nullable=True)
    
    # İlişkiler
    urun = db.relationship('Urun', backref='ana_depo_tedarik_detaylari')
    fifo_kayitlari = db.relationship('StokFifoKayit', backref='tedarik_detay', lazy=True)
    
    __table_args__ = (
        db.Index('idx_ana_depo_tedarik_detay_tedarik', 'tedarik_id'),
        db.Index('idx_ana_depo_tedarik_detay_urun', 'urun_id'),
    )
    
    def __repr__(self):
        return f'<AnaDepoTedarikDetay tedarik={self.tedarik_id} urun={self.urun_id} miktar={self.miktar}>'


# ============================================
# FIFO STOK TAKİP SİSTEMİ
# ============================================

class StokFifoKayit(db.Model):
    """FIFO kuralına göre stok takibi - Her tedarik partisi ayrı takip edilir"""
    __tablename__ = 'stok_fifo_kayitlari'
    
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    otel_id = db.Column(db.Integer, db.ForeignKey('oteller.id', ondelete='CASCADE'), nullable=False)
    urun_id = db.Column(db.Integer, db.ForeignKey('urunler.id', ondelete='CASCADE'), nullable=False)
    tedarik_detay_id = db.Column(db.Integer, db.ForeignKey('ana_depo_tedarik_detaylari.id', ondelete='SET NULL'), nullable=True)
    
    # Miktar bilgileri
    giris_miktari = db.Column(db.Integer, nullable=False)  # Tedarik edilen miktar
    kalan_miktar = db.Column(db.Integer, nullable=False)   # Kullanılmayan miktar
    kullanilan_miktar = db.Column(db.Integer, default=0)   # Kullanılan miktar
    
    # Tarih bilgileri
    giris_tarihi = db.Column(db.DateTime(timezone=True), default=lambda: get_kktc_now(), nullable=False)
    son_kullanim_tarihi = db.Column(db.DateTime(timezone=True), nullable=True)
    
    # Durum
    tukendi = db.Column(db.Boolean, default=False)  # Parti tamamen kullanıldı mı?
    
    # İlişkiler
    otel = db.relationship('Otel', backref='fifo_kayitlari')
    urun = db.relationship('Urun', backref='fifo_kayitlari')
    kullanim_detaylari = db.relationship('StokFifoKullanim', backref='fifo_kayit', lazy=True, cascade='all, delete-orphan')
    
    __table_args__ = (
        db.Index('idx_fifo_otel_urun', 'otel_id', 'urun_id'),
        db.Index('idx_fifo_giris_tarihi', 'giris_tarihi'),
        db.Index('idx_fifo_tukendi', 'tukendi'),
        db.Index('idx_fifo_kalan', 'kalan_miktar'),
    )
    
    def kullan(self, miktar, islem_tipi, referans_id=None):
        """FIFO kaydından miktar kullan"""
        if miktar > self.kalan_miktar:
            raise ValueError(f"Yetersiz stok. Kalan: {self.kalan_miktar}, İstenen: {miktar}")
        
        self.kalan_miktar -= miktar
        self.kullanilan_miktar += miktar
        self.son_kullanim_tarihi = get_kktc_now()
        
        if self.kalan_miktar == 0:
            self.tukendi = True
        
        # Kullanım kaydı oluştur
        kullanim = StokFifoKullanim(
            fifo_kayit_id=self.id,
            miktar=miktar,
            islem_tipi=islem_tipi,
            referans_id=referans_id
        )
        db.session.add(kullanim)
        
        return kullanim
    
    def __repr__(self):
        return f'<StokFifoKayit urun={self.urun_id} kalan={self.kalan_miktar}/{self.giris_miktari}>'


class StokFifoKullanim(db.Model):
    """FIFO stok kullanım detayları - Hangi parti ne zaman nerede kullanıldı"""
    __tablename__ = 'stok_fifo_kullanimlari'
    
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    fifo_kayit_id = db.Column(db.Integer, db.ForeignKey('stok_fifo_kayitlari.id', ondelete='CASCADE'), nullable=False)
    miktar = db.Column(db.Integer, nullable=False)
    islem_tipi = db.Column(db.String(50), nullable=False)  # zimmet, minibar_dolum, setup_kontrol, iade, iptal
    referans_id = db.Column(db.Integer, nullable=True)  # İlgili işlemin ID'si
    islem_tarihi = db.Column(db.DateTime(timezone=True), default=lambda: get_kktc_now(), nullable=False)
    
    __table_args__ = (
        db.Index('idx_fifo_kullanim_kayit', 'fifo_kayit_id'),
        db.Index('idx_fifo_kullanim_tarih', 'islem_tarihi'),
        db.Index('idx_fifo_kullanim_tip', 'islem_tipi'),
    )
    
    def __repr__(self):
        return f'<StokFifoKullanim fifo={self.fifo_kayit_id} miktar={self.miktar} tip={self.islem_tipi}>'


# ============================================================================
# OTEL BAZLI ZİMMET STOK SİSTEMİ
# ============================================================================

class OtelZimmetStok(db.Model):
    """
    Otel bazlı ortak zimmet deposu
    
    Tüm kat sorumluları aynı otelin ortak zimmet deposundan kullanır.
    Bu tablo otel bazında toplam zimmet stoğunu tutar.
    """
    __tablename__ = 'otel_zimmet_stok'
    
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    otel_id = db.Column(db.Integer, db.ForeignKey('oteller.id', ondelete='CASCADE'), nullable=False)
    urun_id = db.Column(db.Integer, db.ForeignKey('urunler.id', ondelete='CASCADE'), nullable=False)
    toplam_miktar = db.Column(db.Integer, nullable=False, default=0)
    kullanilan_miktar = db.Column(db.Integer, nullable=False, default=0)
    kalan_miktar = db.Column(db.Integer, nullable=False, default=0)
    kritik_stok_seviyesi = db.Column(db.Integer, default=50)
    son_guncelleme = db.Column(db.DateTime(timezone=True), default=lambda: get_kktc_now())
    olusturma_tarihi = db.Column(db.DateTime(timezone=True), default=lambda: get_kktc_now())
    
    # Unique constraint
    __table_args__ = (
        db.UniqueConstraint('otel_id', 'urun_id', name='uq_otel_urun_zimmet'),
        db.Index('idx_otel_zimmet_stok_otel', 'otel_id'),
        db.Index('idx_otel_zimmet_stok_urun', 'urun_id'),
        db.Index('idx_otel_zimmet_stok_kalan', 'kalan_miktar'),
    )
    
    # İlişkiler
    otel = db.relationship('Otel', backref=db.backref('zimmet_stoklari', lazy='dynamic'))
    urun = db.relationship('Urun', backref=db.backref('otel_zimmet_stoklari', lazy='dynamic'))
    kullanimlar = db.relationship('PersonelZimmetKullanim', backref='otel_zimmet_stok', lazy='dynamic')
    
    @property
    def kullanim_yuzdesi(self):
        """Kullanım yüzdesini hesapla"""
        if self.toplam_miktar == 0:
            return 0
        return round((self.kullanilan_miktar / self.toplam_miktar) * 100, 1)
    
    @property
    def stok_durumu(self):
        """Stok durumunu belirle: kritik, dikkat, normal"""
        if self.kalan_miktar == 0:
            return 'stokout'
        elif self.kalan_miktar <= self.kritik_stok_seviyesi:
            return 'kritik'
        elif self.kalan_miktar <= self.kritik_stok_seviyesi * 1.5:
            return 'dikkat'
        return 'normal'
    
    def stok_ekle(self, miktar):
        """Depoya stok ekle"""
        self.toplam_miktar += miktar
        self.kalan_miktar += miktar
        self.son_guncelleme = get_kktc_now()
    
    def stok_kullan(self, miktar, personel_id=None, islem_tipi='minibar_kullanim', referans_id=None, aciklama=None):
        """
        Depodan stok kullan ve kullanım kaydı oluştur
        
        Args:
            miktar: Kullanılacak miktar
            personel_id: Kullanan personel ID
            islem_tipi: İşlem tipi (minibar_kullanim, iade, duzeltme)
            referans_id: İlgili işlem ID (MinibarIslem ID vb.)
            aciklama: Açıklama
            
        Returns:
            PersonelZimmetKullanim: Oluşturulan kullanım kaydı
            
        Raises:
            ValueError: Yetersiz stok durumunda
        """
        if self.kalan_miktar < miktar:
            raise ValueError(f"Yetersiz zimmet stoğu. Mevcut: {self.kalan_miktar}, İstenen: {miktar}")
        
        self.kullanilan_miktar += miktar
        self.kalan_miktar -= miktar
        self.son_guncelleme = get_kktc_now()
        
        # Kullanım kaydı oluştur
        kullanim = PersonelZimmetKullanim(
            otel_zimmet_stok_id=self.id,
            personel_id=personel_id,
            urun_id=self.urun_id,
            kullanilan_miktar=miktar,
            islem_tipi=islem_tipi,
            referans_islem_id=referans_id,
            aciklama=aciklama
        )
        db.session.add(kullanim)
        
        return kullanim
    
    def __repr__(self):
        return f'<OtelZimmetStok otel={self.otel_id} urun={self.urun_id} kalan={self.kalan_miktar}>'


class PersonelZimmetKullanim(db.Model):
    """
    Personel bazlı zimmet kullanım takibi
    
    Her personelin otel zimmet deposundan ne kadar kullandığını takip eder.
    Raporlama ve analiz için kullanılır.
    """
    __tablename__ = 'personel_zimmet_kullanim'
    
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    otel_zimmet_stok_id = db.Column(db.Integer, db.ForeignKey('otel_zimmet_stok.id', ondelete='CASCADE'), nullable=False)
    personel_id = db.Column(db.Integer, db.ForeignKey('kullanicilar.id', ondelete='CASCADE'), nullable=False)
    urun_id = db.Column(db.Integer, db.ForeignKey('urunler.id', ondelete='CASCADE'), nullable=False)
    kullanilan_miktar = db.Column(db.Integer, nullable=False, default=0)
    islem_tarihi = db.Column(db.DateTime(timezone=True), default=lambda: get_kktc_now())
    islem_tipi = db.Column(db.String(50), default='minibar_kullanim')  # minibar_kullanim, iade, duzeltme
    referans_islem_id = db.Column(db.Integer, nullable=True)  # MinibarIslem ID referansı
    aciklama = db.Column(db.Text)
    olusturan_id = db.Column(db.Integer, db.ForeignKey('kullanicilar.id'), nullable=True)
    
    __table_args__ = (
        db.Index('idx_pzk_otel_zimmet', 'otel_zimmet_stok_id'),
        db.Index('idx_pzk_personel', 'personel_id'),
        db.Index('idx_pzk_urun', 'urun_id'),
        db.Index('idx_pzk_tarih', 'islem_tarihi'),
    )
    
    # İlişkiler
    personel = db.relationship('Kullanici', foreign_keys=[personel_id], backref='zimmet_kullanimlari')
    urun = db.relationship('Urun', backref='zimmet_kullanimlari')
    olusturan = db.relationship('Kullanici', foreign_keys=[olusturan_id])
    
    def __repr__(self):
        return f'<PersonelZimmetKullanim personel={self.personel_id} urun={self.urun_id} miktar={self.kullanilan_miktar}>'
