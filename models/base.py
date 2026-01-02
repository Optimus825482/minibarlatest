"""
Base Model Modülü

SQLAlchemy instance, enum tanımları ve yardımcı fonksiyonlar.
Tüm diğer model modülleri bu dosyadan import yapar.
"""

from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from sqlalchemy.dialects.postgresql import JSONB
import enum
import pytz

# SQLAlchemy instance - Tüm modeller bunu kullanır
db = SQLAlchemy()

# KKTC Timezone (Kıbrıs - Europe/Nicosia)
KKTC_TZ = pytz.timezone('Europe/Nicosia')

# PostgreSQL JSONB type
JSONType = JSONB


def get_kktc_now():
    """Kıbrıs saat diliminde şu anki zamanı döndürür."""
    return datetime.now(KKTC_TZ)


# ============================================
# ENUM TANIMLARI
# ============================================

class KullaniciRol(str, enum.Enum):
    """Kullanıcı rolleri"""
    SISTEM_YONETICISI = 'sistem_yoneticisi'
    ADMIN = 'admin'
    DEPO_SORUMLUSU = 'depo_sorumlusu'
    KAT_SORUMLUSU = 'kat_sorumlusu'


class HareketTipi(str, enum.Enum):
    """Stok hareket tipleri"""
    GIRIS = 'giris'
    CIKIS = 'cikis'
    DEVIR = 'devir'
    SAYIM = 'sayim'


class ZimmetDurum(str, enum.Enum):
    """Zimmet durumları"""
    AKTIF = 'aktif'
    TAMAMLANDI = 'tamamlandi'
    IPTAL = 'iptal'


class MinibarIslemTipi(str, enum.Enum):
    """Minibar işlem tipleri"""
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
    """Audit log işlem tipleri"""
    CREATE = 'create'
    UPDATE = 'update'
    DELETE = 'delete'
    LOGIN = 'login'
    LOGOUT = 'logout'
    VIEW = 'view'
    EXPORT = 'export'
    IMPORT = 'import'


class RaporTipi(str, enum.Enum):
    """Rapor tipleri"""
    GUNLUK_STOK = 'gunluk_stok'
    STOK_KONTROLU = 'stok_kontrolu'
    ZIMMET_OZETI = 'zimmet_ozeti'
    MINIBAR_TUKETIM = 'minibar_tuketim'


class DolumTalebiDurum(str, enum.Enum):
    """Dolum talebi durumları"""
    BEKLEMEDE = 'beklemede'
    TAMAMLANDI = 'tamamlandi'
    IPTAL = 'iptal'


class QROkutmaTipi(str, enum.Enum):
    """QR okutma tipleri"""
    KAT_SORUMLUSU = 'kat_sorumlusu'
    MISAFIR = 'misafir'


class GorevDurum(str, enum.Enum):
    """Görev durumları"""
    PENDING = 'pending'
    IN_PROGRESS = 'in_progress'
    COMPLETED = 'completed'
    DND_PENDING = 'dnd_pending'
    INCOMPLETE = 'incomplete'
