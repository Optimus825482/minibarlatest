"""
Log Modelleri

SistemLog, HataLog, AuditLog, SistemAyar ve OtomatikRapor modelleri.
"""

from sqlalchemy import Numeric
from sqlalchemy.dialects.postgresql import JSONB
from models.base import db, get_kktc_now


class SistemLog(db.Model):
    """Sistem log kayıtları tablosu"""
    __tablename__ = 'sistem_loglari'
    
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    kullanici_id = db.Column(db.Integer, db.ForeignKey('kullanicilar.id'))
    islem_tipi = db.Column(db.String(50), nullable=False)
    modul = db.Column(db.String(100), nullable=False)
    islem_detay = db.Column(JSONB, nullable=True)
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
    hata_tipi = db.Column(db.String(100), nullable=False)
    hata_mesaji = db.Column(db.Text, nullable=False)
    hata_detay = db.Column(db.Text)
    modul = db.Column(db.String(100))
    url = db.Column(db.String(500))
    method = db.Column(db.String(10))
    ip_adresi = db.Column(db.String(50))
    tarayici = db.Column(db.String(200))
    olusturma_tarihi = db.Column(db.DateTime(timezone=True), default=lambda: get_kktc_now(), nullable=False)
    cozuldu = db.Column(db.Boolean, default=False)
    cozum_notu = db.Column(db.Text)
    
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
    kullanici_id = db.Column(db.Integer, db.ForeignKey('kullanicilar.id'), nullable=True)
    kullanici_adi = db.Column(db.String(100), nullable=False)
    kullanici_rol = db.Column(db.String(50), nullable=False)
    
    # İşlem Detayları
    islem_tipi = db.Column(
        db.Enum('login', 'logout', 'create', 'update', 'delete', 'view', 'export', 'import', 'backup', 'restore', name='audit_islem_tipi'), 
        nullable=False
    )
    tablo_adi = db.Column(db.String(100), nullable=False)
    kayit_id = db.Column(db.Integer)
    
    # Veri Değişiklikleri
    eski_deger = db.Column(JSONB, nullable=True)
    yeni_deger = db.Column(JSONB, nullable=True)
    degisiklik_ozeti = db.Column(db.Text)
    
    # HTTP İstek Bilgileri
    http_method = db.Column(db.String(10))
    url = db.Column(db.String(500))
    endpoint = db.Column(db.String(200))
    
    # Ağ Bilgileri
    ip_adresi = db.Column(db.String(50))
    user_agent = db.Column(db.String(500))
    
    # Zaman Bilgisi
    islem_tarihi = db.Column(db.DateTime(timezone=True), default=lambda: get_kktc_now(), nullable=False)
    
    # Ek Bilgiler
    aciklama = db.Column(db.Text)
    basarili = db.Column(db.Boolean, default=True)
    hata_mesaji = db.Column(db.Text)
    
    # İlişki
    kullanici = db.relationship('Kullanici', foreign_keys=[kullanici_id], backref='audit_kayitlari')
    
    def __repr__(self):
        return f'<AuditLog {self.islem_tipi} - {self.tablo_adi} #{self.kayit_id}>'


class SistemAyar(db.Model):
    """Sistem ayarları tablosu"""
    __tablename__ = 'sistem_ayarlari'
    
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    anahtar = db.Column(db.String(100), unique=True, nullable=False)
    deger = db.Column(db.Text)
    aciklama = db.Column(db.Text)
    
    def __repr__(self):
        return f'<SistemAyar {self.anahtar}>'


class OtomatikRapor(db.Model):
    """Otomatik Oluşturulan Raporlar"""
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
    
    # Rapor İçeriği
    rapor_verisi = db.Column(JSONB, nullable=False)
    
    # Özet İstatistikler
    toplam_urun = db.Column(db.Integer)
    kritik_stok_sayisi = db.Column(db.Integer)
    toplam_deger = db.Column(Numeric(10, 2))
    
    # Ek Bilgiler
    olusturan = db.Column(db.String(100), default='Sistem')
    olusturma_tarihi = db.Column(db.DateTime(timezone=True), default=lambda: get_kktc_now(), nullable=False)
    
    def __repr__(self):
        return f'<OtomatikRapor {self.rapor_tipi} - {self.olusturma_tarihi}>'
