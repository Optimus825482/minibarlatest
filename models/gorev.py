"""
Görev Modelleri

GunlukGorev, GorevDetay, DND ve kontrol kayıt modelleri.
"""

from models.base import db, get_kktc_now


class GunlukGorev(db.Model):
    """Günlük görev ana tablosu"""
    __tablename__ = 'gunluk_gorevler'
    
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    otel_id = db.Column(db.Integer, db.ForeignKey('oteller.id', ondelete='CASCADE'), nullable=False)
    personel_id = db.Column(db.Integer, db.ForeignKey('kullanicilar.id', ondelete='CASCADE'), nullable=False)
    gorev_tarihi = db.Column(db.Date, nullable=False)
    gorev_tipi = db.Column(db.Enum(
        'inhouse_kontrol', 'arrival_kontrol', 'departure_kontrol', 
        'inhouse_yukleme', 'arrivals_yukleme', 'departures_yukleme', 
        name='gorev_tipi_enum'
    ), nullable=False)
    durum = db.Column(db.Enum(
        'pending', 'in_progress', 'completed', 'dnd_pending', 'incomplete', 
        name='gorev_durum_enum'
    ), default='pending', nullable=False)
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
    )
    
    def __repr__(self):
        return f'<GunlukGorev #{self.id} - {self.gorev_tipi}>'


class GorevDetay(db.Model):
    """Görev detay tablosu - Her oda için ayrı görev detayı"""
    __tablename__ = 'gorev_detaylari'
    
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    gorev_id = db.Column(db.Integer, db.ForeignKey('gunluk_gorevler.id', ondelete='CASCADE'), nullable=False)
    oda_id = db.Column(db.Integer, db.ForeignKey('odalar.id', ondelete='CASCADE'), nullable=False)
    misafir_kayit_id = db.Column(db.Integer, db.ForeignKey('misafir_kayitlari.id', ondelete='SET NULL'), nullable=True)
    durum = db.Column(db.Enum(
        'pending', 'in_progress', 'completed', 'dnd_pending', 'incomplete', 
        name='gorev_durum_enum'
    ), default='pending', nullable=False)
    varis_saati = db.Column(db.Time, nullable=True)
    cikis_saati = db.Column(db.Time, nullable=True)
    oncelik_sirasi = db.Column(db.Integer, default=999, nullable=False)
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
        db.Index('idx_gorev_detay_oncelik', 'oncelik_sirasi'),
    )
    
    def __repr__(self):
        return f'<GorevDetay #{self.id} - Oda {self.oda_id}>'


class DNDKontrol(db.Model):
    """DND kontrol kayıtları - Eski görev bazlı sistem"""
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
        return f'<DNDKontrol #{self.id}>'


class GorevDurumLog(db.Model):
    """Görev durum değişiklik logları"""
    __tablename__ = 'gorev_durum_loglari'
    
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    gorev_detay_id = db.Column(db.Integer, db.ForeignKey('gorev_detaylari.id', ondelete='CASCADE'), nullable=False)
    onceki_durum = db.Column(db.Enum(
        'pending', 'in_progress', 'completed', 'dnd_pending', 'incomplete', 
        name='gorev_durum_enum'
    ), nullable=True)
    yeni_durum = db.Column(db.Enum(
        'pending', 'in_progress', 'completed', 'dnd_pending', 'incomplete', 
        name='gorev_durum_enum'
    ), nullable=False)
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
        return f'<GorevDurumLog #{self.id}>'


class YuklemeGorev(db.Model):
    """Yükleme görevleri - Depo sorumluları için"""
    __tablename__ = 'yukleme_gorevleri'
    
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    otel_id = db.Column(db.Integer, db.ForeignKey('oteller.id', ondelete='CASCADE'), nullable=False)
    depo_sorumlusu_id = db.Column(db.Integer, db.ForeignKey('kullanicilar.id', ondelete='CASCADE'), nullable=False)
    gorev_tarihi = db.Column(db.Date, nullable=False)
    dosya_tipi = db.Column(db.String(20), nullable=False)
    durum = db.Column(db.Enum(
        'pending', 'in_progress', 'completed', 'dnd_pending', 'incomplete', 
        name='gorev_durum_enum'
    ), default='pending', nullable=False)
    yukleme_zamani = db.Column(db.DateTime(timezone=True), nullable=True)
    dosya_yukleme_id = db.Column(db.Integer, db.ForeignKey('dosya_yuklemeleri.id', ondelete='SET NULL'), nullable=True)
    olusturma_tarihi = db.Column(db.DateTime(timezone=True), default=lambda: get_kktc_now(), nullable=False)
    
    # İlişkiler
    otel = db.relationship('Otel', backref='yukleme_gorevleri')
    depo_sorumlusu = db.relationship('Kullanici', backref='yukleme_gorevleri')
    dosya_yukleme = db.relationship('DosyaYukleme', backref='yukleme_gorevi')
    
    __table_args__ = (
        db.Index('idx_yukleme_gorev_otel_tarih', 'otel_id', 'gorev_tarihi'),
        db.Index('idx_yukleme_gorev_durum', 'durum'),
        db.UniqueConstraint('otel_id', 'gorev_tarihi', 'dosya_tipi', name='uq_yukleme_gorev'),
    )
    
    def __repr__(self):
        return f'<YuklemeGorev #{self.id} - {self.dosya_tipi}>'


class OdaKontrolKaydi(db.Model):
    """Oda kontrol kayıtları"""
    __tablename__ = 'oda_kontrol_kayitlari'
    
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    oda_id = db.Column(db.Integer, db.ForeignKey('odalar.id', ondelete='CASCADE'), nullable=False)
    personel_id = db.Column(db.Integer, db.ForeignKey('kullanicilar.id', ondelete='CASCADE'), nullable=False)
    kontrol_tarihi = db.Column(db.Date, nullable=False)
    baslangic_zamani = db.Column(db.DateTime(timezone=True), nullable=False)
    bitis_zamani = db.Column(db.DateTime(timezone=True), nullable=True)
    kontrol_tipi = db.Column(db.String(20), default='sarfiyat_yok', nullable=False)
    olusturma_tarihi = db.Column(db.DateTime(timezone=True), default=lambda: get_kktc_now(), nullable=False)
    
    # İlişkiler
    oda = db.relationship('Oda', backref='kontrol_kayitlari')
    personel = db.relationship('Kullanici', backref='oda_kontrol_kayitlari')
    
    __table_args__ = (
        db.Index('idx_oda_kontrol_oda_tarih', 'oda_id', 'kontrol_tarihi'),
        db.Index('idx_oda_kontrol_personel_tarih', 'personel_id', 'kontrol_tarihi'),
    )
    
    def __repr__(self):
        return f'<OdaKontrolKaydi #{self.id}>'


class OdaDNDKayit(db.Model):
    """Bağımsız DND kayıtları - Görev sisteminden bağımsız"""
    __tablename__ = 'oda_dnd_kayitlari'
    
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    oda_id = db.Column(db.Integer, db.ForeignKey('odalar.id', ondelete='CASCADE'), nullable=False)
    otel_id = db.Column(db.Integer, db.ForeignKey('oteller.id', ondelete='CASCADE'), nullable=False)
    kayit_tarihi = db.Column(db.Date, nullable=False)
    dnd_sayisi = db.Column(db.Integer, default=0, nullable=False)
    ilk_dnd_zamani = db.Column(db.DateTime(timezone=True), nullable=True)
    son_dnd_zamani = db.Column(db.DateTime(timezone=True), nullable=True)
    durum = db.Column(db.String(20), default='aktif', nullable=False)
    gorev_detay_id = db.Column(db.Integer, db.ForeignKey('gorev_detaylari.id', ondelete='SET NULL'), nullable=True)
    olusturma_tarihi = db.Column(db.DateTime(timezone=True), default=lambda: get_kktc_now(), nullable=False)
    guncelleme_tarihi = db.Column(db.DateTime(timezone=True), nullable=True)
    
    # İlişkiler
    oda = db.relationship('Oda', backref='dnd_kayitlari')
    otel = db.relationship('Otel', backref='dnd_kayitlari')
    gorev_detay = db.relationship('GorevDetay', backref='dnd_kayit')
    kontroller = db.relationship('OdaDNDKontrol', backref='dnd_kayit', lazy='dynamic', cascade='all, delete-orphan')
    
    __table_args__ = (
        db.UniqueConstraint('oda_id', 'kayit_tarihi', name='uq_oda_dnd_tarih'),
        db.Index('idx_oda_dnd_oda_tarih', 'oda_id', 'kayit_tarihi'),
        db.Index('idx_oda_dnd_otel_tarih', 'otel_id', 'kayit_tarihi'),
        db.Index('idx_oda_dnd_durum', 'durum'),
    )
    
    @property
    def min_kontrol_tamamlandi(self):
        """Minimum 3 kontrol yapıldı mı?"""
        return self.dnd_sayisi >= 3
    
    def __repr__(self):
        return f'<OdaDNDKayit #{self.id} - {self.dnd_sayisi}/3>'


class OdaDNDKontrol(db.Model):
    """DND kontrol detayları"""
    __tablename__ = 'oda_dnd_kontrolleri'
    
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    dnd_kayit_id = db.Column(db.Integer, db.ForeignKey('oda_dnd_kayitlari.id', ondelete='CASCADE'), nullable=False)
    kontrol_no = db.Column(db.Integer, nullable=False)
    kontrol_eden_id = db.Column(db.Integer, db.ForeignKey('kullanicilar.id', ondelete='SET NULL'), nullable=True)
    kontrol_zamani = db.Column(db.DateTime(timezone=True), default=lambda: get_kktc_now(), nullable=False)
    notlar = db.Column(db.Text, nullable=True)
    
    # İlişkiler
    kontrol_eden = db.relationship('Kullanici', backref='dnd_kontrol_kayitlari')
    
    __table_args__ = (
        db.Index('idx_dnd_kontrol_kayit', 'dnd_kayit_id'),
        db.Index('idx_dnd_kontrol_zaman', 'kontrol_zamani'),
    )
    
    def __repr__(self):
        return f'<OdaDNDKontrol #{self.id} - Kontrol #{self.kontrol_no}>'
