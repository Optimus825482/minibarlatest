"""
Doluluk Modelleri

MisafirKayit, DosyaYukleme ve QRKodOkutmaLog modelleri.
"""

from models.base import db, get_kktc_now


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
    giris_saati = db.Column(db.Time, nullable=True)
    cikis_tarihi = db.Column(db.Date, nullable=False, index=True)
    cikis_saati = db.Column(db.Time, nullable=True)
    
    # Durum Bilgileri
    durum = db.Column(db.String(20), default='aktif', nullable=False)
    kaynak = db.Column(db.String(50), default='excel', nullable=False)
    
    # Otel Bilgisi
    otel_id = db.Column(db.Integer, db.ForeignKey('oteller.id', ondelete='CASCADE'), nullable=True)
    
    # Dosya Yükleme Referansı
    dosya_yukleme_id = db.Column(db.Integer, db.ForeignKey('dosya_yuklemeleri.id', ondelete='SET NULL'), nullable=True)
    
    # Zaman Damgaları
    olusturma_tarihi = db.Column(db.DateTime(timezone=True), default=lambda: get_kktc_now(), nullable=False)
    guncelleme_tarihi = db.Column(db.DateTime(timezone=True), nullable=True)
    
    # İlişkiler
    oda = db.relationship('Oda', backref='misafir_kayitlari')
    otel = db.relationship('Otel', backref='misafir_kayitlari')
    dosya_yukleme = db.relationship('DosyaYukleme', backref='misafir_kayitlari')
    
    def __repr__(self):
        return f'<MisafirKayit #{self.id} - {self.islem_kodu}>'


class DosyaYukleme(db.Model):
    """Dosya yükleme kayıtları - Excel dosyaları için"""
    __tablename__ = 'dosya_yuklemeleri'
    __table_args__ = (
        db.Index('idx_dosya_yukleme_otel_tarih', 'otel_id', 'yukleme_tarihi'),
        db.Index('idx_dosya_yukleme_tip', 'dosya_tipi'),
    )
    
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    otel_id = db.Column(db.Integer, db.ForeignKey('oteller.id', ondelete='CASCADE'), nullable=False)
    yukleyen_id = db.Column(db.Integer, db.ForeignKey('kullanicilar.id', ondelete='SET NULL'), nullable=True)
    
    # Dosya Bilgileri
    dosya_adi = db.Column(db.String(255), nullable=False)
    dosya_tipi = db.Column(db.String(50), nullable=False)  # arrivals, departures, inhouse
    dosya_boyutu = db.Column(db.Integer, nullable=True)
    
    # İşlem Bilgileri
    yukleme_tarihi = db.Column(db.DateTime(timezone=True), default=lambda: get_kktc_now(), nullable=False)
    islem_tarihi = db.Column(db.Date, nullable=False)  # Hangi tarih için yüklendi
    
    # Sonuç Bilgileri
    toplam_kayit = db.Column(db.Integer, default=0, nullable=False)
    basarili_kayit = db.Column(db.Integer, default=0, nullable=False)
    hatali_kayit = db.Column(db.Integer, default=0, nullable=False)
    
    # Durum
    durum = db.Column(db.String(20), default='tamamlandi', nullable=False)
    hata_mesaji = db.Column(db.Text, nullable=True)
    
    # İlişkiler
    otel = db.relationship('Otel', backref='dosya_yuklemeleri')
    yukleyen = db.relationship('Kullanici', backref='dosya_yuklemeleri')
    
    def __repr__(self):
        return f'<DosyaYukleme #{self.id} - {self.dosya_tipi}>'


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
    
    # İlişkiler - backref yerine foreign_keys kullanarak çakışmayı önle
    # NOT: Oda modelinde zaten qr_okutma_loglari tanımlı olabilir
    
    def __repr__(self):
        return f'<QRKodOkutmaLog #{self.id} - {self.okutma_tipi}>'
