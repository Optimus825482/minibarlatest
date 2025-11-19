"""
QR Kod Servisi
Oda QR kodlarının oluşturulması, doğrulanması ve yönetimi
"""

import qrcode
import qrcode.image.svg
import secrets
import random
from flask import request
from datetime import datetime
from models import db, Oda, QRKodOkutmaLog


class QRKodService:
    """QR kod oluşturma ve doğrulama servisi"""
    
    @staticmethod
    def generate_token():
        """
        Güvenli, benzersiz 6 haneli token oluştur
        Returns:
            str: 6 haneli sayısal token
        """
        return str(random.randint(100000, 999999))
    
    @staticmethod
    def generate_qr_url(token):
        """
        QR kod URL'i oluştur
        Args:
            token (str): Oda token'ı
        Returns:
            str: Tam QR kod URL'i
        """
        # Sistemin çalıştığı domain'i otomatik algıla
        if request:
            base_url = request.url_root.rstrip('/')
        else:
            # Request context yoksa (test ortamı)
            base_url = 'http://localhost:5000'
        
        return f"{base_url}/qr/{token}"
    
    @staticmethod
    def generate_qr_image(url):
        """
        QR kod görseli oluştur (SVG formatında - direkt HTML)
        Args:
            url (str): QR koda encode edilecek URL
        Returns:
            str: SVG HTML string (direkt embed edilebilir)
        """
        try:
            import re
            
            # QR kod oluştur - basit ve büyük (800x800)
            qr = qrcode.QRCode(
                version=1,  # Otomatik boyutlandırma
                error_correction=qrcode.constants.ERROR_CORRECT_L,  # En düşük hata düzeltme (%7) - daha basit
                box_size=2,  # Her kutu 2 birim - düşük yoğunluk
                border=0,  # Kenarsız - maksimum alan kullanımı
            )
            qr.add_data(url)
            qr.make(fit=True)
            
            # SVG factory ile görsel oluştur
            factory = qrcode.image.svg.SvgPathImage
            img = qr.make_image(image_factory=factory, fill_color="black", back_color="white")
            
            # SVG string'e çevir
            svg_str = img.to_string(encoding='unicode')
            
            # SVG tag'ini bul ve width/height ekle (800x800 büyük boyut)
            if '<svg' in svg_str and 'width=' not in svg_str:
                svg_str = svg_str.replace('<svg', '<svg width="800" height="800"', 1)
            elif '<svg' in svg_str:
                # Mevcut width/height varsa değiştir
                svg_str = re.sub(r'width="[^"]*"', 'width="800"', svg_str)
                svg_str = re.sub(r'height="[^"]*"', 'height="800"', svg_str)
            
            return svg_str
            
        except Exception as e:
            raise Exception(f"QR görsel oluşturma hatası: {str(e)}")
    
    @staticmethod
    def create_qr_for_oda(oda):
        """
        Oda için QR kod oluştur ve veritabanına kaydet
        Args:
            oda (Oda): Oda modeli instance
        Returns:
            dict: Token, URL ve görsel bilgileri
        """
        try:
            # Token oluştur
            token = QRKodService.generate_token()
            
            # URL oluştur
            url = QRKodService.generate_qr_url(token)
            
            # QR görsel oluştur
            qr_image = QRKodService.generate_qr_image(url)
            
            # Oda modelini güncelle
            oda.qr_kod_token = token
            oda.qr_kod_gorsel = qr_image
            oda.qr_kod_olusturma_tarihi = datetime.utcnow()
            
            return {
                'success': True,
                'token': token,
                'url': url,
                'image': qr_image,
                'oda_id': oda.id,
                'oda_no': oda.oda_no
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    @staticmethod
    def validate_token(token):
        """
        Token'ı doğrula ve oda bilgisini döndür
        Args:
            token (str): Doğrulanacak token (URL veya token string)
        Returns:
            Oda | None: Geçerli ise Oda instance, değilse None
        """
        try:
            # Eğer URL formatındaysa token'ı çıkar
            # Örnek: http://localhost:5014/qr/ABC123 -> ABC123
            if token.startswith('http://') or token.startswith('https://'):
                # URL'den token'ı çıkar
                parts = token.split('/qr/')
                if len(parts) == 2:
                    token = parts[1]
            
            # Önce basit format kontrol et: MINIBAR_ODA_{oda_id}_KAT_{kat_id}
            if token.startswith('MINIBAR_ODA_'):
                try:
                    # Token'ı parse et
                    parts = token.split('_')
                    if len(parts) >= 5 and parts[0] == 'MINIBAR' and parts[1] == 'ODA' and parts[3] == 'KAT':
                        oda_id = int(parts[2])
                        
                        # Oda'yı veritabanından getir
                        oda = Oda.query.filter_by(
                            id=oda_id,
                            aktif=True
                        ).first()
                        
                        if oda:
                            return oda
                except (ValueError, IndexError):
                    pass
            
            # Veritabanında token ara (güvenli token sistemi)
            oda = Oda.query.filter_by(
                qr_kod_token=token,
                aktif=True
            ).first()
            
            return oda
            
        except Exception:
            return None
    
    @staticmethod
    def log_qr_scan(oda_id, okutma_tipi, kullanici_id=None, basarili=True, hata_mesaji=None):
        """
        QR okutma logunu kaydet
        Args:
            oda_id (int): Oda ID
            okutma_tipi (str): 'kat_sorumlusu' veya 'misafir'
            kullanici_id (int, optional): Kullanıcı ID (kat sorumlusu için)
            basarili (bool): İşlem başarılı mı
            hata_mesaji (str, optional): Hata mesajı
        Returns:
            QRKodOkutmaLog: Oluşturulan log kaydı
        """
        try:
            log = QRKodOkutmaLog(
                oda_id=oda_id,
                kullanici_id=kullanici_id,
                okutma_tipi=okutma_tipi,
                ip_adresi=request.remote_addr if request else None,
                user_agent=request.headers.get('User-Agent', '') if request else '',
                basarili=basarili,
                hata_mesaji=hata_mesaji
            )
            db.session.add(log)
            db.session.commit()
            
            return log
            
        except Exception as e:
            db.session.rollback()
            raise Exception(f"QR log kaydetme hatası: {str(e)}")
    
    @staticmethod
    def regenerate_qr(oda):
        """
        Mevcut oda için QR kodu yeniden oluştur (eski token geçersiz olur)
        Args:
            oda (Oda): Oda modeli instance
        Returns:
            dict: Yeni token, URL ve görsel bilgileri
        """
        return QRKodService.create_qr_for_oda(oda)
    
    @staticmethod
    def get_qr_stats(oda_id=None):
        """
        QR okutma istatistiklerini getir
        Args:
            oda_id (int, optional): Belirli bir oda için filtrele
        Returns:
            dict: İstatistik bilgileri
        """
        try:
            query = QRKodOkutmaLog.query
            
            if oda_id:
                query = query.filter_by(oda_id=oda_id)
            
            toplam_okutma = query.count()
            basarili_okutma = query.filter_by(basarili=True).count()
            basarisiz_okutma = query.filter_by(basarili=False).count()
            
            kat_sorumlusu_okutma = query.filter_by(okutma_tipi='kat_sorumlusu').count()
            misafir_okutma = query.filter_by(okutma_tipi='misafir').count()
            
            return {
                'toplam_okutma': toplam_okutma,
                'basarili_okutma': basarili_okutma,
                'basarisiz_okutma': basarisiz_okutma,
                'kat_sorumlusu_okutma': kat_sorumlusu_okutma,
                'misafir_okutma': misafir_okutma,
                'basari_orani': round((basarili_okutma / toplam_okutma * 100), 2) if toplam_okutma > 0 else 0
            }
            
        except Exception as e:
            return {
                'error': str(e)
            }
