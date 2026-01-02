"""
Minibar Modelleri

MinibarIslem, MinibarIslemDetay, MinibarDolumTalebi ve Kampanya modelleri.
"""

from sqlalchemy import Numeric
from models.base import db, get_kktc_now


class Kampanya(db.Model):
    """Kampanya tanımları tablosu"""
    __tablename__ = 'kampanyalar'
    
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    kampanya_adi = db.Column(db.String(200), nullable=False)
    aciklama = db.Column(db.Text)
    baslangic_tarihi = db.Column(db.DateTime(timezone=True), nullable=False)
    bitis_tarihi = db.Column(db.DateTime(timezone=True), nullable=False)
    indirim_orani = db.Column(Numeric(5, 2), nullable=True)
    indirim_tutari = db.Column(Numeric(10, 2), nullable=True)
    aktif = db.Column(db.Boolean, default=True)
    olusturma_tarihi = db.Column(db.DateTime(timezone=True), default=lambda: get_kktc_now())
    
    def __repr__(self):
        return f'<Kampanya {self.kampanya_adi}>'


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
    islem_tipi = db.Column(db.Enum(
        'ilk_dolum', 'yeniden_dolum', 'eksik_tamamlama', 'sayim', 
        'duzeltme', 'kontrol', 'doldurma', 'ek_dolum', 'setup_kontrol', 
        'ekstra_ekleme', 'ekstra_tuketim', 
        name='minibar_islem_tipi'
    ), nullable=False)
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
    ekstra_miktar = db.Column(db.Integer, default=0)
    setup_miktari = db.Column(db.Integer, default=0)
    zimmet_detay_id = db.Column(db.Integer, db.ForeignKey('personel_zimmet_detay.id'), nullable=True)
    
    # Fiyatlandırma ve Karlılık
    satis_fiyati = db.Column(Numeric(10, 2), nullable=True)
    alis_fiyati = db.Column(Numeric(10, 2), nullable=True)
    kar_tutari = db.Column(Numeric(10, 2), nullable=True)
    kar_orani = db.Column(Numeric(5, 2), nullable=True)
    bedelsiz = db.Column(db.Boolean, default=False)
    kampanya_id = db.Column(db.Integer, db.ForeignKey('kampanyalar.id'), nullable=True)
    
    # İlişkiler
    zimmet_detay = db.relationship('PersonelZimmetDetay', foreign_keys=[zimmet_detay_id])
    kampanya = db.relationship('Kampanya')
    
    def __repr__(self):
        return f'<MinibarIslemDetay #{self.id}>'


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
    durum = db.Column(db.Enum(
        'beklemede', 'onaylandi', 'reddedildi', 'tamamlandi', 'iptal', 
        name='dolum_talep_durum'
    ), default='beklemede', nullable=False)
    tamamlanma_tarihi = db.Column(db.DateTime(timezone=True), nullable=True)
    notlar = db.Column(db.Text, nullable=True)
    
    def __repr__(self):
        return f'<MinibarDolumTalebi #{self.id} - {self.durum}>'
