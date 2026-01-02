"""
Email Modelleri

EmailAyarlari, EmailLog ve DolulukUyariLog modelleri.
"""

from models.base import db, get_kktc_now


class EmailAyarlari(db.Model):
    """E-posta ayarları tablosu"""
    __tablename__ = 'email_ayarlari'
    
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    otel_id = db.Column(db.Integer, db.ForeignKey('oteller.id', ondelete='CASCADE'), nullable=True)
    
    # SMTP Ayarları
    smtp_server = db.Column(db.String(200), nullable=True)
    smtp_port = db.Column(db.Integer, default=587)
    smtp_kullanici = db.Column(db.String(200), nullable=True)
    smtp_sifre = db.Column(db.String(500), nullable=True)  # Şifrelenmiş
    smtp_ssl = db.Column(db.Boolean, default=False)
    smtp_tls = db.Column(db.Boolean, default=True)
    
    # Gönderici Bilgileri
    gonderen_ad = db.Column(db.String(100), nullable=True)
    gonderen_email = db.Column(db.String(200), nullable=True)
    
    # Alıcı Listesi
    alici_listesi = db.Column(db.Text, nullable=True)  # Virgülle ayrılmış e-posta adresleri
    
    # Bildirim Ayarları
    kritik_stok_bildirimi = db.Column(db.Boolean, default=True)
    gunluk_rapor = db.Column(db.Boolean, default=False)
    haftalik_rapor = db.Column(db.Boolean, default=False)
    
    # Durum
    aktif = db.Column(db.Boolean, default=True)
    olusturma_tarihi = db.Column(db.DateTime(timezone=True), default=lambda: get_kktc_now())
    guncelleme_tarihi = db.Column(db.DateTime(timezone=True), nullable=True)
    
    # İlişkiler
    otel = db.relationship('Otel', backref='email_ayarlari')
    
    def __repr__(self):
        return f'<EmailAyarlari #{self.id}>'


class EmailLog(db.Model):
    """E-posta gönderim logları"""
    __tablename__ = 'email_loglari'
    __table_args__ = (
        db.Index('idx_email_log_tarih', 'gonderim_tarihi'),
        db.Index('idx_email_log_durum', 'durum'),
    )
    
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    otel_id = db.Column(db.Integer, db.ForeignKey('oteller.id', ondelete='SET NULL'), nullable=True)
    
    # E-posta Bilgileri
    alici = db.Column(db.String(500), nullable=False)
    konu = db.Column(db.String(500), nullable=False)
    icerik = db.Column(db.Text, nullable=True)
    email_tipi = db.Column(db.String(50), nullable=False)  # kritik_stok, rapor, sistem
    
    # Gönderim Bilgileri
    gonderim_tarihi = db.Column(db.DateTime(timezone=True), default=lambda: get_kktc_now(), nullable=False)
    durum = db.Column(db.String(20), default='beklemede', nullable=False)  # beklemede, gonderildi, hata
    
    # Hata Bilgileri
    hata_mesaji = db.Column(db.Text, nullable=True)
    deneme_sayisi = db.Column(db.Integer, default=0)
    
    # İlişkiler
    otel = db.relationship('Otel', backref='email_loglari')
    
    def __repr__(self):
        return f'<EmailLog #{self.id} - {self.durum}>'


class DolulukUyariLog(db.Model):
    """Doluluk uyarı logları - Eksik dosya yükleme bildirimleri"""
    __tablename__ = 'doluluk_uyari_loglari'
    __table_args__ = (
        db.Index('idx_doluluk_uyari_otel_tarih', 'otel_id', 'uyari_tarihi'),
    )
    
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    otel_id = db.Column(db.Integer, db.ForeignKey('oteller.id', ondelete='CASCADE'), nullable=False)
    
    # Uyarı Bilgileri
    uyari_tipi = db.Column(db.String(50), nullable=False)  # eksik_arrivals, eksik_departures, eksik_inhouse
    uyari_tarihi = db.Column(db.DateTime(timezone=True), default=lambda: get_kktc_now(), nullable=False)
    hedef_tarih = db.Column(db.Date, nullable=False)  # Hangi tarih için uyarı
    
    # Bildirim Durumu
    email_gonderildi = db.Column(db.Boolean, default=False)
    email_log_id = db.Column(db.Integer, db.ForeignKey('email_loglari.id', ondelete='SET NULL'), nullable=True)
    
    # Çözüm Durumu
    cozuldu = db.Column(db.Boolean, default=False)
    cozum_tarihi = db.Column(db.DateTime(timezone=True), nullable=True)
    
    # İlişkiler
    otel = db.relationship('Otel', backref='doluluk_uyari_loglari')
    email_log = db.relationship('EmailLog', backref='doluluk_uyarilari')
    
    def __repr__(self):
        return f'<DolulukUyariLog #{self.id} - {self.uyari_tipi}>'
