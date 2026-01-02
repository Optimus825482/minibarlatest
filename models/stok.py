"""
Stok Modelleri

Urun, UrunGrup, StokHareket, FIFO ve tedarik modelleri.
"""

from sqlalchemy import Numeric
from models.base import db, get_kktc_now
import enum


class AnaDepoTedarikDurum(str, enum.Enum):
    """Ana depo tedarik durumları"""
    AKTIF = 'aktif'
    IPTAL = 'iptal'


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
    urun_kodu = db.Column(db.String(50), unique=True, nullable=True)
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


class StokFifoKayit(db.Model):
    """FIFO kuralına göre stok takibi"""
    __tablename__ = 'stok_fifo_kayitlari'
    
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    otel_id = db.Column(db.Integer, db.ForeignKey('oteller.id', ondelete='CASCADE'), nullable=False)
    urun_id = db.Column(db.Integer, db.ForeignKey('urunler.id', ondelete='CASCADE'), nullable=False)
    tedarik_detay_id = db.Column(db.Integer, db.ForeignKey('ana_depo_tedarik_detaylari.id', ondelete='SET NULL'), nullable=True)
    
    giris_miktari = db.Column(db.Integer, nullable=False)
    kalan_miktar = db.Column(db.Integer, nullable=False)
    kullanilan_miktar = db.Column(db.Integer, default=0)
    
    giris_tarihi = db.Column(db.DateTime(timezone=True), default=lambda: get_kktc_now(), nullable=False)
    son_kullanim_tarihi = db.Column(db.DateTime(timezone=True), nullable=True)
    
    tukendi = db.Column(db.Boolean, default=False)
    
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
    """FIFO stok kullanım detayları"""
    __tablename__ = 'stok_fifo_kullanimlari'
    
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    fifo_kayit_id = db.Column(db.Integer, db.ForeignKey('stok_fifo_kayitlari.id', ondelete='CASCADE'), nullable=False)
    miktar = db.Column(db.Integer, nullable=False)
    islem_tipi = db.Column(db.String(50), nullable=False)
    referans_id = db.Column(db.Integer, nullable=True)
    islem_tarihi = db.Column(db.DateTime(timezone=True), default=lambda: get_kktc_now(), nullable=False)
    
    __table_args__ = (
        db.Index('idx_fifo_kullanim_kayit', 'fifo_kayit_id'),
        db.Index('idx_fifo_kullanim_tarih', 'islem_tarihi'),
        db.Index('idx_fifo_kullanim_tip', 'islem_tipi'),
    )
    
    def __repr__(self):
        return f'<StokFifoKullanim fifo={self.fifo_kayit_id} miktar={self.miktar}>'


class AnaDepoTedarik(db.Model):
    """Ana depodan yapılan tedarik işlemleri"""
    __tablename__ = 'ana_depo_tedarikleri'
    
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    tedarik_no = db.Column(db.String(50), unique=True, nullable=False)
    otel_id = db.Column(db.Integer, db.ForeignKey('oteller.id', ondelete='CASCADE'), nullable=False)
    depo_sorumlusu_id = db.Column(db.Integer, db.ForeignKey('kullanicilar.id', ondelete='SET NULL'), nullable=True)
    islem_tarihi = db.Column(db.DateTime(timezone=True), default=lambda: get_kktc_now(), nullable=False)
    toplam_urun_sayisi = db.Column(db.Integer, default=0)
    toplam_miktar = db.Column(db.Integer, default=0)
    aciklama = db.Column(db.Text, nullable=True)
    
    durum = db.Column(db.String(20), default='aktif')
    iptal_tarihi = db.Column(db.DateTime(timezone=True), nullable=True)
    iptal_eden_id = db.Column(db.Integer, db.ForeignKey('kullanicilar.id', ondelete='SET NULL'), nullable=True)
    iptal_nedeni = db.Column(db.Text, nullable=True)
    
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
        db.Index('idx_ana_depo_tedarik_durum', 'durum'),
    )
    
    def __repr__(self):
        return f'<AnaDepoTedarik #{self.id} - {self.tedarik_no}>'


class AnaDepoTedarikDetay(db.Model):
    """Ana depo tedarik detayları"""
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
        return f'<AnaDepoTedarikDetay tedarik={self.tedarik_id} urun={self.urun_id}>'


class OtelZimmetStok(db.Model):
    """Otel bazlı ortak zimmet deposu"""
    __tablename__ = 'otel_zimmet_stok'
    
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    otel_id = db.Column(db.Integer, db.ForeignKey('oteller.id', ondelete='CASCADE'), nullable=False)
    urun_id = db.Column(db.Integer, db.ForeignKey('urunler.id', ondelete='CASCADE'), nullable=False)
    toplam_miktar = db.Column(db.Integer, nullable=False, default=0)
    kullanilan_miktar = db.Column(db.Integer, nullable=False, default=0)
    kalan_miktar = db.Column(db.Integer, nullable=False, default=0)
    son_guncelleme = db.Column(db.DateTime(timezone=True), default=lambda: get_kktc_now())
    
    # İlişkiler
    otel = db.relationship('Otel', backref='zimmet_stoklari')
    urun = db.relationship('Urun', backref='otel_zimmet_stoklari')
    
    __table_args__ = (
        db.UniqueConstraint('otel_id', 'urun_id', name='uq_otel_zimmet_stok'),
        db.Index('idx_otel_zimmet_stok', 'otel_id', 'urun_id'),
    )
    
    def __repr__(self):
        return f'<OtelZimmetStok otel={self.otel_id} urun={self.urun_id}>'
