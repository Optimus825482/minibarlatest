"""
Misafir Notları ve Metinleri İçin Otomatik Çeviri Servisi
Google Translate ücretsiz endpoint'i (fallback: orijinal metin) kullanarak
misafirlerin herhangi bir dilde yazdığı notları kat sorumlusuna Türkçe olarak gösterir.
"""

import json
import logging
import urllib.parse
import urllib.request
from typing import Dict, Any

logger = logging.getLogger(__name__)


def translate_to_turkish(text: str, timeout: float = 3.5) -> Dict[str, Any]:
    """
    Verilen metni otomatik dil algılama ile Türkçe'ye çevirir.

    Returns:
        dict: {
            'translated_text': str,
            'source_lang': str,
            'is_translated': bool
        }
    """
    cleaned = (text or "").strip()
    if not cleaned:
        return {
            "translated_text": "",
            "source_lang": "tr",
            "is_translated": False,
        }

    try:
        query = urllib.parse.quote(cleaned)
        url = (
            "https://translate.googleapis.com/translate_a/single"
            f"?client=gtx&sl=auto&tl=tr&dt=t&q={query}"
        )
        req = urllib.request.Request(
            url,
            headers={
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/122.0.0.0 Safari/537.36"
                )
            },
        )
        with urllib.request.urlopen(req, timeout=timeout) as response:
            raw = response.read().decode("utf-8", errors="replace")
            data = json.loads(raw)

        # data[0] çeviri parçalarını içerir: [[ceviri, orijinal, ...], ...]
        segments = data[0] if isinstance(data, list) and len(data) > 0 else []
        translated_parts = []
        if isinstance(segments, list):
            for seg in segments:
                if isinstance(seg, list) and len(seg) > 0 and seg[0]:
                    translated_parts.append(str(seg[0]))

        translated_text = "".join(translated_parts).strip() or cleaned
        source_lang = (
            str(data[2]).lower()
            if isinstance(data, list) and len(data) > 2 and data[2]
            else "auto"
        )

        is_translated = (
            source_lang != "tr"
            and translated_text.lower() != cleaned.lower()
        )

        return {
            "translated_text": translated_text,
            "source_lang": source_lang,
            "is_translated": is_translated,
        }
    except Exception as exc:
        logger.warning(f"Çeviri servisi hatası (orijinal metin kullanılacak): {exc}")
        return {
            "translated_text": cleaned,
            "source_lang": "auto",
            "is_translated": False,
        }


def format_guest_note_for_staff(text: str) -> str:
    """
    Misafir notunu kat sorumlusunun Türkçe okuyabileceği şekilde formatlar.
    Eğer not zaten Türkçe ise olduğu gibi döner; farklı bir dildeyse Türkçe çevirisini
    ana metin olarak yazar ve parantez içinde orijinal dili/metni ekler.
    """
    cleaned = (text or "").strip()
    if not cleaned:
        return ""

    result = translate_to_turkish(cleaned)
    if result.get("is_translated") and result.get("translated_text"):
        tr_text = result["translated_text"]
        lang_code = (result.get("source_lang") or "AUTO").upper()
        combined = f"{tr_text} (Orijinal [{lang_code}]: {cleaned})"
        return combined[:1000]

    return cleaned
