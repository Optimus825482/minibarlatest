"""
Input Validation and Sanitization
Güvenlik için input validasyonu ve temizleme
"""
import logging
import re
from typing import Any, Dict, List, Optional
import html
import bleach

logger = logging.getLogger(__name__)


class InputValidator:
    """Input validasyon ve sanitization servisi"""
    
    # SQL injection pattern'leri
    SQL_INJECTION_PATTERNS = [
        r"(\b(SELECT|INSERT|UPDATE|DELETE|DROP|CREATE|ALTER|EXEC|EXECUTE)\b)",
        r"(--|;|\/\*|\*\/)",
        r"(\bOR\b.*=.*)",
        r"(\bAND\b.*=.*)",
        r"('|\")(.*)(OR|AND)(.*)(=)(.*)",
    ]
    
    # XSS pattern'leri
    XSS_PATTERNS = [
        r"<script[^>]*>.*?</script>",
        r"javascript:",
        r"on\w+\s*=",
        r"<iframe",
        r"<object",
        r"<embed",
    ]
    
    @staticmethod
    def sanitize_string(value: str, max_length: int = 1000) -> str:
        """
        String'i temizle ve güvenli hale getir
        
        Args:
            value: Temizlenecek string
            max_length: Maksimum uzunluk
            
        Returns:
            str: Temizlenmiş string
        """
        try:
            if not isinstance(value, str):
                value = str(value)
            
            # HTML escape
            value = html.escape(value)
            
            # Uzunluk kontrolü
            if len(value) > max_length:
                value = value[:max_length]
                logger.warning(f"String kesildi: {max_length} karakter")
            
            # Whitespace temizle
            value = value.strip()
            
            return value
            
        except Exception as e:
            logger.error(f"String sanitization hatası: {str(e)}", exc_info=True)
            return ""
    
    @staticmethod
    def sanitize_html(value: str, allowed_tags: List[str] = None) -> str:
        """
        HTML içeriğini temizle
        
        Args:
            value: HTML içerik
            allowed_tags: İzin verilen HTML tag'leri
            
        Returns:
            str: Temizlenmiş HTML
        """
        try:
            if allowed_tags is None:
                allowed_tags = ['p', 'br', 'strong', 'em', 'u', 'a', 'ul', 'ol', 'li']
            
            # Bleach ile temizle
            clean_html = bleach.clean(
                value,
                tags=allowed_tags,
                attributes={'a': ['href', 'title']},
                strip=True
            )
            
            return clean_html
            
        except Exception as e:
            logger.error(f"HTML sanitization hatası: {str(e)}", exc_info=True)
            return html.escape(value)
    
    @staticmethod
    def check_sql_injection(value: str) -> bool:
        """
        SQL injection kontrolü
        
        Args:
            value: Kontrol edilecek string
            
        Returns:
            bool: SQL injection tespit edildi mi
        """
        try:
            value_upper = value.upper()
            
            for pattern in InputValidator.SQL_INJECTION_PATTERNS:
                if re.search(pattern, value_upper, re.IGNORECASE):
                    logger.warning(f"SQL injection tespit edildi: {pattern}")
                    return True
            
            return False
            
        except Exception as e:
            logger.error(f"SQL injection kontrolü hatası: {str(e)}", exc_info=True)
            return False
    
    @staticmethod
    def check_xss(value: str) -> bool:
        """
        XSS (Cross-Site Scripting) kontrolü
        
        Args:
            value: Kontrol edilecek string
            
        Returns:
            bool: XSS tespit edildi mi
        """
        try:
            for pattern in InputValidator.XSS_PATTERNS:
                if re.search(pattern, value, re.IGNORECASE):
                    logger.warning(f"XSS tespit edildi: {pattern}")
                    return True
            
            return False
            
        except Exception as e:
            logger.error(f"XSS kontrolü hatası: {str(e)}", exc_info=True)
            return False
    
    @staticmethod
    def validate_email(email: str) -> bool:
        """
        Email validasyonu
        
        Args:
            email: Email adresi
            
        Returns:
            bool: Geçerli mi
        """
        try:
            pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
            return bool(re.match(pattern, email))
        except Exception as e:
            logger.error(f"Email validasyon hatası: {str(e)}", exc_info=True)
            return False
    
    @staticmethod
    def validate_phone(phone: str) -> bool:
        """
        Telefon numarası validasyonu
        
        Args:
            phone: Telefon numarası
            
        Returns:
            bool: Geçerli mi
        """
        try:
            # Sadece rakam ve + - ( ) karakterlerine izin ver
            pattern = r'^[\d\s\-\+\(\)]+$'
            if not re.match(pattern, phone):
                return False
            
            # En az 10 rakam olmalı
            digits = re.sub(r'\D', '', phone)
            return len(digits) >= 10
            
        except Exception as e:
            logger.error(f"Phone validasyon hatası: {str(e)}", exc_info=True)
            return False
    
    @staticmethod
    def validate_integer(value: Any, min_val: int = None, max_val: int = None) -> bool:
        """
        Integer validasyonu
        
        Args:
            value: Değer
            min_val: Minimum değer
            max_val: Maksimum değer
            
        Returns:
            bool: Geçerli mi
        """
        try:
            int_val = int(value)
            
            if min_val is not None and int_val < min_val:
                return False
            
            if max_val is not None and int_val > max_val:
                return False
            
            return True
            
        except (ValueError, TypeError):
            return False
    
    @staticmethod
    def validate_dict(data: Dict, required_fields: List[str]) -> tuple[bool, Optional[str]]:
        """
        Dictionary validasyonu
        
        Args:
            data: Validate edilecek dict
            required_fields: Zorunlu alanlar
            
        Returns:
            tuple: (geçerli_mi, hata_mesajı)
        """
        try:
            if not isinstance(data, dict):
                return False, "Data must be a dictionary"
            
            for field in required_fields:
                if field not in data:
                    return False, f"Missing required field: {field}"
                
                if data[field] is None or data[field] == "":
                    return False, f"Field cannot be empty: {field}"
            
            return True, None
            
        except Exception as e:
            logger.error(f"Dict validasyon hatası: {str(e)}", exc_info=True)
            return False, str(e)
    
    @staticmethod
    def sanitize_filename(filename: str) -> str:
        """
        Dosya adını güvenli hale getir
        
        Args:
            filename: Dosya adı
            
        Returns:
            str: Güvenli dosya adı
        """
        try:
            # Tehlikeli karakterleri kaldır
            filename = re.sub(r'[^\w\s\-\.]', '', filename)
            
            # Path traversal önle
            filename = filename.replace('..', '')
            filename = filename.replace('/', '')
            filename = filename.replace('\\', '')
            
            # Uzunluk kontrolü
            if len(filename) > 255:
                name, ext = filename.rsplit('.', 1) if '.' in filename else (filename, '')
                filename = name[:250] + ('.' + ext if ext else '')
            
            return filename
            
        except Exception as e:
            logger.error(f"Filename sanitization hatası: {str(e)}", exc_info=True)
            return "file"


class FiyatValidation:
    """Fiyatlandırma sistemi için özel validasyon sınıfı"""
    
    @staticmethod
    def validate_fiyat(fiyat: Any, min_fiyat: float = 0.0, max_fiyat: float = 999999.99) -> tuple[bool, Optional[str]]:
        """
        Fiyat validasyonu - Negatif fiyat ve geçerlilik kontrolü
        
        Args:
            fiyat: Kontrol edilecek fiyat
            min_fiyat: Minimum kabul edilebilir fiyat (varsayılan: 0.0)
            max_fiyat: Maksimum kabul edilebilir fiyat (varsayılan: 999999.99)
            
        Returns:
            tuple: (geçerli_mi, hata_mesajı)
            
        Requirements: 2.1
        """
        try:
            # None kontrolü
            if fiyat is None:
                return False, "Fiyat boş olamaz"
            
            # Tip dönüşümü
            try:
                fiyat_float = float(fiyat)
            except (ValueError, TypeError):
                return False, "Fiyat geçerli bir sayı olmalıdır"
            
            # Negatif kontrol
            if fiyat_float < 0:
                logger.warning(f"Negatif fiyat tespit edildi: {fiyat_float}")
                return False, "Fiyat negatif olamaz"
            
            # Minimum kontrol
            if fiyat_float < min_fiyat:
                return False, f"Fiyat minimum {min_fiyat} TL olmalıdır"
            
            # Maksimum kontrol
            if fiyat_float > max_fiyat:
                return False, f"Fiyat maksimum {max_fiyat} TL olabilir"
            
            # Ondalık basamak kontrolü (max 2 basamak)
            fiyat_str = str(fiyat_float)
            if '.' in fiyat_str:
                decimal_places = len(fiyat_str.split('.')[1])
                if decimal_places > 2:
                    return False, "Fiyat en fazla 2 ondalık basamak içerebilir"
            
            return True, None
            
        except Exception as e:
            logger.error(f"Fiyat validasyon hatası: {str(e)}", exc_info=True)
            return False, f"Fiyat validasyon hatası: {str(e)}"
    
    @staticmethod
    def validate_kampanya(
        indirim_tipi: str,
        indirim_degeri: Any,
        min_siparis_miktari: int = None,
        max_kullanim_sayisi: int = None
    ) -> tuple[bool, Optional[str]]:
        """
        Kampanya validasyonu - İndirim oranı ve değer kontrolü
        
        Args:
            indirim_tipi: 'yuzde' veya 'tutar'
            indirim_degeri: İndirim değeri
            min_siparis_miktari: Minimum sipariş miktarı (opsiyonel)
            max_kullanim_sayisi: Maksimum kullanım sayısı (opsiyonel)
            
        Returns:
            tuple: (geçerli_mi, hata_mesajı)
            
        Requirements: 5.1
        """
        try:
            # İndirim tipi kontrolü
            if indirim_tipi not in ['yuzde', 'tutar']:
                return False, "İndirim tipi 'yuzde' veya 'tutar' olmalıdır"
            
            # İndirim değeri kontrolü
            try:
                indirim_float = float(indirim_degeri)
            except (ValueError, TypeError):
                return False, "İndirim değeri geçerli bir sayı olmalıdır"
            
            # Negatif kontrol
            if indirim_float < 0:
                logger.warning(f"Negatif indirim değeri tespit edildi: {indirim_float}")
                return False, "İndirim değeri negatif olamaz"
            
            # Sıfır kontrol
            if indirim_float == 0:
                return False, "İndirim değeri sıfırdan büyük olmalıdır"
            
            # Yüzde için özel kontrol
            if indirim_tipi == 'yuzde':
                if indirim_float > 100:
                    return False, "İndirim oranı %100'den fazla olamaz"
                if indirim_float < 1:
                    return False, "İndirim oranı en az %1 olmalıdır"
            
            # Tutar için özel kontrol
            if indirim_tipi == 'tutar':
                if indirim_float > 10000:
                    return False, "İndirim tutarı 10,000 TL'den fazla olamaz"
            
            # Minimum sipariş miktarı kontrolü
            if min_siparis_miktari is not None:
                if not isinstance(min_siparis_miktari, int) or min_siparis_miktari < 1:
                    return False, "Minimum sipariş miktarı pozitif bir tam sayı olmalıdır"
                if min_siparis_miktari > 1000:
                    return False, "Minimum sipariş miktarı 1000'den fazla olamaz"
            
            # Maksimum kullanım sayısı kontrolü
            if max_kullanim_sayisi is not None:
                if not isinstance(max_kullanim_sayisi, int) or max_kullanim_sayisi < 1:
                    return False, "Maksimum kullanım sayısı pozitif bir tam sayı olmalıdır"
                if max_kullanim_sayisi > 100000:
                    return False, "Maksimum kullanım sayısı 100,000'den fazla olamaz"
            
            return True, None
            
        except Exception as e:
            logger.error(f"Kampanya validasyon hatası: {str(e)}", exc_info=True)
            return False, f"Kampanya validasyon hatası: {str(e)}"
    
    @staticmethod
    def validate_bedelsiz_limit(
        max_miktar: int,
        kullanilan_miktar: int = 0,
        limit_tipi: str = None
    ) -> tuple[bool, Optional[str]]:
        """
        Bedelsiz limit validasyonu - Limit kontrolü
        
        Args:
            max_miktar: Maksimum bedelsiz miktar
            kullanilan_miktar: Kullanılan miktar (varsayılan: 0)
            limit_tipi: 'misafir', 'kampanya' veya 'personel' (opsiyonel)
            
        Returns:
            tuple: (geçerli_mi, hata_mesajı)
            
        Requirements: 6.1
        """
        try:
            # Maksimum miktar kontrolü
            if not isinstance(max_miktar, int):
                try:
                    max_miktar = int(max_miktar)
                except (ValueError, TypeError):
                    return False, "Maksimum miktar geçerli bir tam sayı olmalıdır"
            
            if max_miktar < 1:
                return False, "Maksimum miktar en az 1 olmalıdır"
            
            if max_miktar > 1000:
                return False, "Maksimum miktar 1000'den fazla olamaz"
            
            # Kullanılan miktar kontrolü
            if not isinstance(kullanilan_miktar, int):
                try:
                    kullanilan_miktar = int(kullanilan_miktar)
                except (ValueError, TypeError):
                    return False, "Kullanılan miktar geçerli bir tam sayı olmalıdır"
            
            if kullanilan_miktar < 0:
                logger.warning(f"Negatif kullanılan miktar tespit edildi: {kullanilan_miktar}")
                return False, "Kullanılan miktar negatif olamaz"
            
            # Kullanılan miktar, maksimum miktardan fazla olamaz
            if kullanilan_miktar > max_miktar:
                return False, f"Kullanılan miktar ({kullanilan_miktar}) maksimum miktardan ({max_miktar}) fazla olamaz"
            
            # Limit tipi kontrolü (opsiyonel)
            if limit_tipi is not None:
                valid_types = ['misafir', 'kampanya', 'personel']
                if limit_tipi not in valid_types:
                    return False, f"Limit tipi {', '.join(valid_types)} değerlerinden biri olmalıdır"
            
            return True, None
            
        except Exception as e:
            logger.error(f"Bedelsiz limit validasyon hatası: {str(e)}", exc_info=True)
            return False, f"Bedelsiz limit validasyon hatası: {str(e)}"
    
    @staticmethod
    def validate_tarih_araligi(baslangic_tarihi: Any, bitis_tarihi: Any) -> tuple[bool, Optional[str]]:
        """
        Tarih aralığı validasyonu
        
        Args:
            baslangic_tarihi: Başlangıç tarihi
            bitis_tarihi: Bitiş tarihi
            
        Returns:
            tuple: (geçerli_mi, hata_mesajı)
        """
        try:
            from datetime import datetime, timezone
            
            # None kontrolü
            if baslangic_tarihi is None:
                return False, "Başlangıç tarihi boş olamaz"
            
            # Datetime dönüşümü
            if isinstance(baslangic_tarihi, str):
                try:
                    baslangic_tarihi = datetime.fromisoformat(baslangic_tarihi.replace('Z', '+00:00'))
                except ValueError:
                    return False, "Başlangıç tarihi geçerli bir tarih formatında olmalıdır"
            
            if bitis_tarihi is not None:
                if isinstance(bitis_tarihi, str):
                    try:
                        bitis_tarihi = datetime.fromisoformat(bitis_tarihi.replace('Z', '+00:00'))
                    except ValueError:
                        return False, "Bitiş tarihi geçerli bir tarih formatında olmalıdır"
                
                # Bitiş tarihi başlangıçtan önce olamaz
                if bitis_tarihi < baslangic_tarihi:
                    return False, "Bitiş tarihi başlangıç tarihinden önce olamaz"
                
                # Tarih aralığı çok uzun olmamalı (max 5 yıl)
                from datetime import timedelta
                max_range = timedelta(days=365 * 5)
                if (bitis_tarihi - baslangic_tarihi) > max_range:
                    return False, "Tarih aralığı maksimum 5 yıl olabilir"
            
            return True, None
            
        except Exception as e:
            logger.error(f"Tarih aralığı validasyon hatası: {str(e)}", exc_info=True)
            return False, f"Tarih aralığı validasyon hatası: {str(e)}"
    
    @staticmethod
    def validate_oda_tipi(oda_tipi: str) -> tuple[bool, Optional[str]]:
        """
        Oda tipi validasyonu
        
        Args:
            oda_tipi: Oda tipi
            
        Returns:
            tuple: (geçerli_mi, hata_mesajı)
        """
        try:
            if not oda_tipi or not isinstance(oda_tipi, str):
                return False, "Oda tipi boş olamaz"
            
            # Güvenli string kontrolü
            oda_tipi = oda_tipi.strip()
            
            if len(oda_tipi) < 2:
                return False, "Oda tipi en az 2 karakter olmalıdır"
            
            if len(oda_tipi) > 100:
                return False, "Oda tipi maksimum 100 karakter olabilir"
            
            # SQL injection kontrolü
            if InputValidator.check_sql_injection(oda_tipi):
                return False, "Oda tipi geçersiz karakterler içeriyor"
            
            return True, None
            
        except Exception as e:
            logger.error(f"Oda tipi validasyon hatası: {str(e)}", exc_info=True)
            return False, f"Oda tipi validasyon hatası: {str(e)}"


# Global validator instance
_validator = InputValidator()
_fiyat_validator = FiyatValidation()


def get_validator() -> InputValidator:
    """
    Global validator instance'ını getir
    
    Returns:
        InputValidator: Validator instance
    """
    return _validator


def get_fiyat_validator() -> FiyatValidation:
    """
    Global fiyat validator instance'ını getir
    
    Returns:
        FiyatValidation: Fiyat validator instance
    """
    return _fiyat_validator
