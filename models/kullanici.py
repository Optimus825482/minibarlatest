"""
Kullanıcı Modelleri

Kullanici ve KullaniciOtel (çoklu otel ataması) modelleri.
"""

from werkzeug.security import generate_password_hash, check_password_hash
from models.base import db, get_kktc_now


class KullaniciOtel(db.Model):
    """Kullanıcı-Otel ilişki tablosu (Many-to-Many) - Depo sorumluları için"""
    __tablename__ = 'kullanici_otel'
    
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    kullanici_id = db.Column(db.Integer, db.ForeignKey('kullanicilar.id', ondelete='CASCADE'), nullable=False)
    otel_id = db.Column(db.Integer, db.ForeignKey('oteller.id', ondelete='CASCADE'), nullable=False)
    olusturma_tarihi = db.Column(db.DateTime(timezone=True), default=lambda: get_kktc_now())
    
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
    
    # Kat sorumlusu için tek otel ilişkisi
    otel_id = db.Column(db.Integer, db.ForeignKey('oteller.id', ondelete='SET NULL'), nullable=True)
    
    # Kat sorumlusunun bağlı olduğu depo sorumlusu
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
    
    # Otel ilişkileri
    otel = db.relationship('Otel', foreign_keys=[otel_id], backref='kat_sorumlu_kullanicilar')
    atanan_oteller = db.relationship('KullaniciOtel', backref='kullanici', lazy=True, cascade='all, delete-orphan')
    
    # Depo sorumlusu ilişkisi
    depo_sorumlusu = db.relationship('Kullanici', remote_side=[id], foreign_keys=[depo_sorumlusu_id], backref='bagli_kat_sorumlu')
    
    def sifre_belirle(self, sifre):
        """Şifreyi hashleyerek kaydet"""
        self.sifre_hash = generate_password_hash(sifre)
    
    def sifre_kontrol(self, sifre):
        """Şifre kontrolü"""
        return check_password_hash(self.sifre_hash, sifre)
    
    def __repr__(self):
        return f'<Kullanici {self.kullanici_adi} ({self.rol})>'
