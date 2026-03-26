"""
KKTC Timezone Yardımcı Modülü

Tüm sistemde tutarlı timezone yönetimi için merkezi kaynak.
Daha önce 29+ dosyaya dağılmış olan KKTC_TZ ve get_kktc_now
tanımlarının tek yetkili kaynağı burasıdır.

Kullanım:
    from utils.timezone import KKTC_TZ, get_kktc_now, get_kktc_today
    from utils.timezone import utc_to_kktc, kktc_to_utc
"""

import pytz
from datetime import datetime, timezone as stdlib_timezone

# KKTC Timezone (Kıbrıs - Europe/Nicosia)
KKTC_TZ = pytz.timezone('Europe/Nicosia')


def get_kktc_now() -> datetime:
    """
    Kıbrıs saat diliminde şu anki zamanı döndürür.
    Tüm sistemde saat kaydı için bu fonksiyon kullanılmalıdır.

    Returns:
        datetime: KKTC timezone'unda şu anki zaman
    """
    return datetime.now(KKTC_TZ)


def get_kktc_today():
    """
    Kıbrıs saat diliminde bugünün tarihini döndürür.

    Returns:
        date: KKTC timezone'unda bugünün tarihi
    """
    return datetime.now(KKTC_TZ).date()


def utc_to_kktc(utc_datetime):
    """
    UTC datetime'ı KKTC timezone'una çevirir.

    Args:
        utc_datetime: UTC timezone'unda datetime

    Returns:
        datetime | None: KKTC timezone'unda datetime
    """
    if utc_datetime is None:
        return None
    if utc_datetime.tzinfo is None:
        utc_datetime = utc_datetime.replace(tzinfo=stdlib_timezone.utc)
    return utc_datetime.astimezone(KKTC_TZ)


def kktc_to_utc(kktc_datetime):
    """
    KKTC datetime'ı UTC timezone'una çevirir.

    Args:
        kktc_datetime: KKTC timezone'unda datetime

    Returns:
        datetime | None: UTC timezone'unda datetime
    """
    if kktc_datetime is None:
        return None
    if kktc_datetime.tzinfo is None:
        kktc_datetime = KKTC_TZ.localize(kktc_datetime)
    return kktc_datetime.astimezone(stdlib_timezone.utc)
