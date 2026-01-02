"""
Zimmet Modelleri

PersonelZimmet, PersonelZimmetDetay ve şablon modelleri.
"""

from models.base import db, get_kktc_now


class PersonelZimmet(db.Model):
    """Personel zimmet tablosu - Kat sorumlusu zimmet başlık"""
    __tablename__ = 'personel_zimmet'
    
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    personel_id = db.Column(db.Integer, db.ForeignKey('kullanicilar.id'), nullable=False)
    otel_id = db.Column(db.Integer, db.ForeignKey('oteller.id', ondelete='SET NULL'), nullable=True)
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
    kritik_stok_seviyesi = db.Column(db.Integer, nullable=True)
    
    def __repr__(self):
        return f'<PersonelZimmetDetay #{self.id}>'


class ZimmetSablon(db.Model):
    """Zimmet şablonları - Önceden tanımlanmış ürün setleri"""
    __tablename__ = 'zimmet_sablonlari'
    
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    sablon_adi = db.Column(db.String(100), nullable=False)
    aciklama = db.Column(db.Text, nullable=True)
    olusturan_id = db.Column(db.Integer, db.ForeignKey('kullanicilar.id', ondelete='SET NULL'), nullable=True)
    otel_id = db.Column(db.Integer, db.ForeignKey('oteller.id', ondelete='CASCADE'), nullable=True)
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
    """Zimmet şablon detayları"""
    __tablename__ = 'zimmet_sablon_detaylari'
    
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    sablon_id = db.Column(db.Integer, db.ForeignKey('zimmet_sablonlari.id', ondelete='CASCADE'), nullable=False)
    urun_id = db.Column(db.Integer, db.ForeignKey('urunler.id', ondelete='CASCADE'), nullable=False)
    varsayilan_miktar = db.Column(db.Integer, nullable=False, default=1)
    
    # İlişkiler
    urun = db.relationship('Urun', backref='sablon_detaylari')
    
    __table_args__ = (
        db.Index('idx_zimmet_sablon_detay_sablon', 'sablon_id'),
        db.UniqueConstraint('sablon_id', 'urun_id', name='uq_sablon_urun'),
    )
    
    def __repr__(self):
        return f'<ZimmetSablonDetay sablon={self.sablon_id} urun={self.urun_id}>'
