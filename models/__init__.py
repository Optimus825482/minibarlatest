"""
Modüler Model Yapısı

Bu paket, models.py dosyasını mantıksal modüllere böler.
Geriye dönük uyumluluk için tüm modeller buradan export edilir.

NOT: Şu an için models.py ana kaynak olarak kullanılıyor.
Modüler dosyalar (otel.py, kullanici.py vb.) gelecekte taşınacak.
"""

# Ana models.py'den tüm modelleri import et
import sys
import os

# models.py'yi doğrudan import et
_models_py_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'models.py')

if os.path.exists(_models_py_path):
    import importlib.util
    _spec = importlib.util.spec_from_file_location("models_main", _models_py_path)
    _models_main = importlib.util.module_from_spec(_spec)
    _spec.loader.exec_module(_models_main)
    
    # Base exports
    db = _models_main.db
    get_kktc_now = _models_main.get_kktc_now
    KKTC_TZ = _models_main.KKTC_TZ
    JSONType = _models_main.JSONType
    
    # Enum'lar
    KullaniciRol = _models_main.KullaniciRol
    HareketTipi = _models_main.HareketTipi
    ZimmetDurum = _models_main.ZimmetDurum
    MinibarIslemTipi = _models_main.MinibarIslemTipi
    AuditIslemTipi = _models_main.AuditIslemTipi
    RaporTipi = _models_main.RaporTipi
    DolumTalebiDurum = _models_main.DolumTalebiDurum
    QROkutmaTipi = _models_main.QROkutmaTipi
    GorevDurum = _models_main.GorevDurum
    SiparisDurum = _models_main.SiparisDurum
    DokumanTipi = _models_main.DokumanTipi
    FiyatDegisiklikTipi = _models_main.FiyatDegisiklikTipi
    IndirimTipi = _models_main.IndirimTipi
    BedelsizLimitTipi = _models_main.BedelsizLimitTipi
    DonemTipi = _models_main.DonemTipi
    KuralTipi = _models_main.KuralTipi
    MLMetricType = _models_main.MLMetricType
    MLAlertType = _models_main.MLAlertType
    MLAlertSeverity = _models_main.MLAlertSeverity
    
    # Otel modelleri
    Otel = _models_main.Otel
    Kat = _models_main.Kat
    Oda = _models_main.Oda
    OdaTipi = _models_main.OdaTipi
    Setup = _models_main.Setup
    SetupIcerik = _models_main.SetupIcerik
    oda_tipi_setup = _models_main.oda_tipi_setup
    
    # Kullanıcı modelleri
    Kullanici = _models_main.Kullanici
    KullaniciOtel = _models_main.KullaniciOtel
    
    # Stok modelleri
    UrunGrup = _models_main.UrunGrup
    Urun = _models_main.Urun
    StokHareket = _models_main.StokHareket
    StokFifoKayit = _models_main.StokFifoKayit
    StokFifoKullanim = _models_main.StokFifoKullanim
    AnaDepoTedarik = _models_main.AnaDepoTedarik
    AnaDepoTedarikDetay = _models_main.AnaDepoTedarikDetay
    OtelZimmetStok = _models_main.OtelZimmetStok
    UrunStok = _models_main.UrunStok
    OdaTipiSatisFiyati = _models_main.OdaTipiSatisFiyati
    
    # Zimmet modelleri
    PersonelZimmet = _models_main.PersonelZimmet
    PersonelZimmetDetay = _models_main.PersonelZimmetDetay
    ZimmetSablon = _models_main.ZimmetSablon
    ZimmetSablonDetay = _models_main.ZimmetSablonDetay
    PersonelZimmetKullanim = _models_main.PersonelZimmetKullanim
    
    # Minibar modelleri
    MinibarIslem = _models_main.MinibarIslem
    MinibarIslemDetay = _models_main.MinibarIslemDetay
    MinibarDolumTalebi = _models_main.MinibarDolumTalebi
    Kampanya = _models_main.Kampanya
    
    # Görev modelleri
    GunlukGorev = _models_main.GunlukGorev
    GorevDetay = _models_main.GorevDetay
    GorevDurumLog = _models_main.GorevDurumLog
    YuklemeGorev = _models_main.YuklemeGorev
    DNDKontrol = _models_main.DNDKontrol
    OdaDNDKayit = _models_main.OdaDNDKayit
    OdaDNDKontrol = _models_main.OdaDNDKontrol
    OdaKontrolKaydi = _models_main.OdaKontrolKaydi
    
    # Doluluk modelleri
    MisafirKayit = _models_main.MisafirKayit
    DosyaYukleme = _models_main.DosyaYukleme
    QRKodOkutmaLog = _models_main.QRKodOkutmaLog
    
    # Log modelleri
    SistemLog = _models_main.SistemLog
    HataLog = _models_main.HataLog
    AuditLog = _models_main.AuditLog
    SistemAyar = _models_main.SistemAyar
    OtomatikRapor = _models_main.OtomatikRapor
    
    # Email modelleri
    EmailAyarlari = _models_main.EmailAyarlari
    EmailLog = _models_main.EmailLog
    DolulukUyariLog = _models_main.DolulukUyariLog
    
    # Tedarikçi modelleri
    Tedarikci = _models_main.Tedarikci
    UrunTedarikciFiyat = _models_main.UrunTedarikciFiyat
    TedarikciPerformans = _models_main.TedarikciPerformans
    TedarikciIletisim = _models_main.TedarikciIletisim
    TedarikciDokuman = _models_main.TedarikciDokuman
    
    # Satın Alma modelleri
    SatinAlmaSiparisi = _models_main.SatinAlmaSiparisi
    SatinAlmaSiparisDetay = _models_main.SatinAlmaSiparisDetay
    SatinAlmaIslem = _models_main.SatinAlmaIslem
    SatinAlmaIslemDetay = _models_main.SatinAlmaIslemDetay
    KatSorumlusuSiparisTalebi = _models_main.KatSorumlusuSiparisTalebi
    KatSorumlusuSiparisTalepDetay = _models_main.KatSorumlusuSiparisTalepDetay
    
    # ML modelleri
    MLModel = _models_main.MLModel
    MLMetric = _models_main.MLMetric
    MLAlert = _models_main.MLAlert
    MLTrainingLog = _models_main.MLTrainingLog
    MLFeature = _models_main.MLFeature
    MLPerformanceLog = _models_main.MLPerformanceLog
    
    # Fiyatlandırma modelleri
    FiyatDegisiklikLog = getattr(_models_main, 'FiyatDegisiklikLog', None)
    KarlilikAnalizi = getattr(_models_main, 'KarlilikAnalizi', None)
    SezonFiyatlandirma = _models_main.SezonFiyatlandirma
    BedelsizLimit = _models_main.BedelsizLimit
    BedelsizKullanimLog = _models_main.BedelsizKullanimLog
    DonemselKarAnalizi = _models_main.DonemselKarAnalizi
    UrunFiyatGecmisi = _models_main.UrunFiyatGecmisi
    
    # Developer/Sistem modelleri
    QueryLog = _models_main.QueryLog
    BackupHistory = _models_main.BackupHistory
    ConfigAudit = _models_main.ConfigAudit
    BackgroundJob = _models_main.BackgroundJob

# Tüm modelleri __all__ ile export et
__all__ = [
    # Base
    'db', 'get_kktc_now', 'KKTC_TZ', 'JSONType',
    # Enum'lar
    'KullaniciRol', 'HareketTipi', 'ZimmetDurum', 'MinibarIslemTipi',
    'AuditIslemTipi', 'RaporTipi', 'DolumTalebiDurum', 'QROkutmaTipi',
    'GorevDurum', 'SiparisDurum', 'DokumanTipi', 'FiyatDegisiklikTipi',
    'IndirimTipi', 'BedelsizLimitTipi', 'DonemTipi', 'KuralTipi',
    'MLMetricType', 'MLAlertType', 'MLAlertSeverity',
    # Otel
    'Otel', 'Kat', 'Oda', 'OdaTipi', 'Setup', 'SetupIcerik', 'oda_tipi_setup',
    # Kullanıcı
    'Kullanici', 'KullaniciOtel',
    # Stok
    'UrunGrup', 'Urun', 'StokHareket', 'StokFifoKayit', 'StokFifoKullanim',
    'AnaDepoTedarik', 'AnaDepoTedarikDetay', 'OtelZimmetStok', 'UrunStok', 'OdaTipiSatisFiyati',
    # Zimmet
    'PersonelZimmet', 'PersonelZimmetDetay', 'ZimmetSablon', 'ZimmetSablonDetay', 'PersonelZimmetKullanim',
    # Minibar
    'MinibarIslem', 'MinibarIslemDetay', 'MinibarDolumTalebi', 'Kampanya',
    # Görev
    'GunlukGorev', 'GorevDetay', 'GorevDurumLog', 'YuklemeGorev',
    'DNDKontrol', 'OdaDNDKayit', 'OdaDNDKontrol', 'OdaKontrolKaydi',
    # Doluluk
    'MisafirKayit', 'DosyaYukleme', 'QRKodOkutmaLog',
    # Log
    'SistemLog', 'HataLog', 'AuditLog', 'SistemAyar', 'OtomatikRapor',
    # Email
    'EmailAyarlari', 'EmailLog', 'DolulukUyariLog',
    # Tedarikçi
    'Tedarikci', 'UrunTedarikciFiyat', 'TedarikciPerformans', 'TedarikciIletisim', 'TedarikciDokuman',
    # Satın Alma
    'SatinAlmaSiparisi', 'SatinAlmaSiparisDetay', 'SatinAlmaIslem', 'SatinAlmaIslemDetay',
    'KatSorumlusuSiparisTalebi', 'KatSorumlusuSiparisTalepDetay',
    # ML
    'MLModel', 'MLMetric', 'MLAlert', 'MLTrainingLog', 'MLFeature', 'MLPerformanceLog',
    # Fiyatlandırma
    'FiyatDegisiklikLog', 'KarlilikAnalizi', 'SezonFiyatlandirma',
    'BedelsizLimit', 'BedelsizKullanimLog', 'DonemselKarAnalizi', 'UrunFiyatGecmisi',
    # Developer/Sistem
    'QueryLog', 'BackupHistory', 'ConfigAudit', 'BackgroundJob',
]
