"""
Email Gönderim Servisi

Bu modül sistem genelinde email gönderimi için kullanılır.
- SMTP ayarları veritabanından okunur
- Gönderilen tüm emailler loglanır
- Okundu takibi desteklenir
"""

import smtplib
import uuid
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List

logger = logging.getLogger(__name__)


class EmailService:
    """Email gönderim servisi"""
    
    @staticmethod
    def get_email_settings() -> Optional[Dict[str, Any]]:
        """
        Aktif email ayarlarını veritabanından al
        
        Returns:
            dict: Email ayarları veya None
        """
        try:
            from models import db, EmailAyarlari
            
            ayarlar = EmailAyarlari.query.filter_by(aktif=True).first()
            if not ayarlar:
                logger.warning("Aktif email ayarları bulunamadı")
                return None
            
            return {
                'smtp_server': ayarlar.smtp_server,
                'smtp_port': ayarlar.smtp_port,
                'smtp_username': ayarlar.smtp_username,
                'smtp_password': ayarlar.smtp_password,
                'smtp_use_tls': ayarlar.smtp_use_tls,
                'smtp_use_ssl': ayarlar.smtp_use_ssl,
                'sender_email': ayarlar.sender_email,
                'sender_name': ayarlar.sender_name
            }
        except Exception as e:
            logger.error(f"Email ayarları alınırken hata: {str(e)}")
            return None
    
    @staticmethod
    def send_email(
        to_email: str,
        subject: str,
        body: str,
        email_tipi: str = 'sistem',
        kullanici_id: Optional[int] = None,
        ilgili_tablo: Optional[str] = None,
        ilgili_kayit_id: Optional[int] = None,
        ek_bilgiler: Optional[Dict] = None,
        html_body: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Email gönder ve logla
        
        Args:
            to_email: Alıcı email adresi
            subject: Email konusu
            body: Email içeriği (plain text)
            email_tipi: Email tipi (uyari, bilgi, sistem)
            kullanici_id: Alıcı kullanıcı ID (opsiyonel)
            ilgili_tablo: İlişkili tablo adı (opsiyonel)
            ilgili_kayit_id: İlişkili kayıt ID (opsiyonel)
            ek_bilgiler: Ek metadata (opsiyonel)
            html_body: HTML içerik (opsiyonel)
        
        Returns:
            dict: {success: bool, message: str, email_log_id: int}
        """
        try:
            from models import db, EmailLog
            
            # Email ayarlarını al
            settings = EmailService.get_email_settings()
            if not settings:
                return {
                    'success': False,
                    'message': 'Email ayarları yapılandırılmamış',
                    'email_log_id': None
                }
            
            # Tracking ID oluştur (okundu takibi için)
            tracking_id = str(uuid.uuid4())
            
            # Email oluştur
            msg = MIMEMultipart('alternative')
            msg['Subject'] = subject
            msg['From'] = f"{settings['sender_name']} <{settings['sender_email']}>"
            msg['To'] = to_email
            msg['X-Tracking-ID'] = tracking_id
            
            # Plain text part
            text_part = MIMEText(body, 'plain', 'utf-8')
            msg.attach(text_part)
            
            # HTML part (varsa)
            if html_body:
                # Okundu takibi için tracking pixel ekle
                tracking_pixel = f'<img src="{{BASE_URL}}/api/email-tracking/{tracking_id}" width="1" height="1" style="display:none;" />'
                html_with_tracking = html_body + tracking_pixel
                html_part = MIMEText(html_with_tracking, 'html', 'utf-8')
                msg.attach(html_part)
            
            # SMTP bağlantısı ve gönderim
            durum = 'gonderildi'
            hata_mesaji = None
            
            try:
                if settings['smtp_use_ssl']:
                    server = smtplib.SMTP_SSL(settings['smtp_server'], settings['smtp_port'])
                else:
                    server = smtplib.SMTP(settings['smtp_server'], settings['smtp_port'])
                    if settings['smtp_use_tls']:
                        server.starttls()
                
                server.login(settings['smtp_username'], settings['smtp_password'])
                server.sendmail(settings['sender_email'], to_email, msg.as_string())
                server.quit()
                
                logger.info(f"Email gönderildi: {to_email} - {subject}")
                
            except smtplib.SMTPException as smtp_error:
                durum = 'hata'
                hata_mesaji = str(smtp_error)
                logger.error(f"SMTP hatası: {hata_mesaji}")
            except Exception as e:
                durum = 'hata'
                hata_mesaji = str(e)
                logger.error(f"Email gönderim hatası: {hata_mesaji}")
            
            # Email log kaydı oluştur
            email_log = EmailLog(
                alici_email=to_email,
                alici_kullanici_id=kullanici_id,
                konu=subject,
                icerik=body,
                email_tipi=email_tipi,
                durum=durum,
                hata_mesaji=hata_mesaji,
                tracking_id=tracking_id,
                ilgili_tablo=ilgili_tablo,
                ilgili_kayit_id=ilgili_kayit_id,
                ek_bilgiler=ek_bilgiler
            )
            db.session.add(email_log)
            db.session.commit()
            
            return {
                'success': durum == 'gonderildi',
                'message': 'Email başarıyla gönderildi' if durum == 'gonderildi' else f'Email gönderilemedi: {hata_mesaji}',
                'email_log_id': email_log.id,
                'tracking_id': tracking_id
            }
            
        except Exception as e:
            logger.error(f"Email servisi hatası: {str(e)}")
            return {
                'success': False,
                'message': f'Sistem hatası: {str(e)}',
                'email_log_id': None
            }
    
    @staticmethod
    def send_bulk_email(
        recipients: List[Dict[str, Any]],
        subject: str,
        body: str,
        email_tipi: str = 'sistem',
        html_body: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Toplu email gönder
        
        Args:
            recipients: [{email: str, kullanici_id: int (optional)}]
            subject: Email konusu
            body: Email içeriği
            email_tipi: Email tipi
            html_body: HTML içerik (opsiyonel)
        
        Returns:
            dict: {success: int, failed: int, results: list}
        """
        results = []
        success_count = 0
        failed_count = 0
        
        for recipient in recipients:
            result = EmailService.send_email(
                to_email=recipient['email'],
                subject=subject,
                body=body,
                email_tipi=email_tipi,
                kullanici_id=recipient.get('kullanici_id'),
                html_body=html_body
            )
            
            results.append({
                'email': recipient['email'],
                'success': result['success'],
                'message': result['message']
            })
            
            if result['success']:
                success_count += 1
            else:
                failed_count += 1
        
        return {
            'success': success_count,
            'failed': failed_count,
            'results': results
        }
    
    @staticmethod
    def mark_as_read(tracking_id: str) -> bool:
        """
        Email'i okundu olarak işaretle
        
        Args:
            tracking_id: Email tracking ID
        
        Returns:
            bool: Başarılı mı
        """
        try:
            from models import db, EmailLog
            
            email_log = EmailLog.query.filter_by(tracking_id=tracking_id).first()
            if email_log and not email_log.okundu:
                email_log.okundu = True
                email_log.okunma_tarihi = datetime.now(timezone.utc)
                db.session.commit()
                logger.info(f"Email okundu olarak işaretlendi: {tracking_id}")
                return True
            return False
        except Exception as e:
            logger.error(f"Email okundu işaretleme hatası: {str(e)}")
            return False
    
    @staticmethod
    def test_connection() -> Dict[str, Any]:
        """
        SMTP bağlantısını test et
        
        Returns:
            dict: {success: bool, message: str}
        """
        try:
            settings = EmailService.get_email_settings()
            if not settings:
                return {
                    'success': False,
                    'message': 'Email ayarları yapılandırılmamış'
                }
            
            if settings['smtp_use_ssl']:
                server = smtplib.SMTP_SSL(settings['smtp_server'], settings['smtp_port'], timeout=10)
            else:
                server = smtplib.SMTP(settings['smtp_server'], settings['smtp_port'], timeout=10)
                if settings['smtp_use_tls']:
                    server.starttls()
            
            server.login(settings['smtp_username'], settings['smtp_password'])
            server.quit()
            
            return {
                'success': True,
                'message': 'SMTP bağlantısı başarılı'
            }
            
        except smtplib.SMTPAuthenticationError:
            return {
                'success': False,
                'message': 'Kimlik doğrulama hatası - Kullanıcı adı veya şifre yanlış'
            }
        except smtplib.SMTPConnectError:
            return {
                'success': False,
                'message': 'Sunucuya bağlanılamadı - Sunucu adresi veya port yanlış'
            }
        except Exception as e:
            return {
                'success': False,
                'message': f'Bağlantı hatası: {str(e)}'
            }


class DolulukUyariService:
    """Günlük doluluk uyarı servisi"""
    
    @staticmethod
    def check_and_send_warnings(target_hour: int = 10) -> Dict[str, Any]:
        """
        KKTC saatiyle belirtilen saatte doluluk yüklemesi yapılmamış otelleri kontrol et
        ve uyarı gönder
        
        Args:
            target_hour: Kontrol saati (KKTC saati, varsayılan 10:00)
        
        Returns:
            dict: {warnings_sent: int, details: list}
        """
        try:
            from models import db, Otel, Kullanici, KullaniciOtel, YuklemeGorev, DolulukUyariLog
            from datetime import date
            import pytz
            
            # KKTC timezone (UTC+2)
            kktc_tz = pytz.timezone('Europe/Nicosia')
            now_kktc = datetime.now(kktc_tz)
            bugun = date.today()
            
            logger.info(f"Doluluk uyarı kontrolü başladı - KKTC Saati: {now_kktc.strftime('%H:%M')}")
            
            warnings_sent = 0
            details = []
            
            # Tüm aktif otelleri al
            oteller = Otel.query.filter_by(aktif=True).all()
            
            for otel in oteller:
                # Bu otel için bugünkü yükleme görevlerini kontrol et
                inhouse_gorev = YuklemeGorev.query.filter(
                    YuklemeGorev.otel_id == otel.id,
                    YuklemeGorev.gorev_tarihi == bugun,
                    YuklemeGorev.dosya_tipi == 'inhouse'
                ).first()
                
                arrivals_gorev = YuklemeGorev.query.filter(
                    YuklemeGorev.otel_id == otel.id,
                    YuklemeGorev.gorev_tarihi == bugun,
                    YuklemeGorev.dosya_tipi == 'arrivals'
                ).first()
                
                # Eksik yüklemeleri belirle
                eksik_yuklemeler = []
                if not inhouse_gorev or inhouse_gorev.durum == 'pending':
                    eksik_yuklemeler.append('In House')
                if not arrivals_gorev or arrivals_gorev.durum == 'pending':
                    eksik_yuklemeler.append('Arrivals')
                
                if not eksik_yuklemeler:
                    continue  # Bu otel için yükleme tamamlanmış
                
                # Bugün için zaten uyarı gönderilmiş mi kontrol et
                mevcut_uyari = DolulukUyariLog.query.filter(
                    DolulukUyariLog.otel_id == otel.id,
                    DolulukUyariLog.uyari_tarihi == bugun
                ).first()
                
                if mevcut_uyari and mevcut_uyari.email_gonderildi:
                    continue  # Zaten uyarı gönderilmiş
                
                # Bu otele atanmış depo sorumlularını bul
                depo_sorumlu_atamalari = KullaniciOtel.query.join(Kullanici).filter(
                    KullaniciOtel.otel_id == otel.id,
                    Kullanici.rol == 'depo_sorumlusu',
                    Kullanici.aktif == True
                ).all()
                
                for atama in depo_sorumlu_atamalari:
                    depo_sorumlusu = atama.kullanici
                    
                    if not depo_sorumlusu.email:
                        logger.warning(f"Depo sorumlusu email adresi yok: {depo_sorumlusu.kullanici_adi}")
                        continue
                    
                    # Uyarı tipi belirle
                    if len(eksik_yuklemeler) == 2:
                        uyari_tipi = 'her_ikisi_eksik'
                    elif 'In House' in eksik_yuklemeler:
                        uyari_tipi = 'inhouse_eksik'
                    else:
                        uyari_tipi = 'arrivals_eksik'
                    
                    # Email içeriği oluştur
                    subject = f"⚠️ Günlük Doluluk Yüklemesi Eksik - {otel.ad}"
                    body = f"""Sayın {depo_sorumlusu.ad} {depo_sorumlusu.soyad},

{otel.ad} oteli için bugünkü ({bugun.strftime('%d.%m.%Y')}) günlük doluluk bilgileri henüz sisteme yüklenmemiştir.

Eksik Yüklemeler:
{chr(10).join(['- ' + y for y in eksik_yuklemeler])}

Lütfen en kısa sürede doluluk bilgilerini sisteme yükleyiniz.
Bu bilgiler kat sorumlularının günlük görevlerinin oluşturulması için gereklidir.

Saygılarımızla,
Minibar Takip Sistemi
"""
                    
                    html_body = f"""
<html>
<body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
    <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
        <div style="background: linear-gradient(135deg, #f59e0b, #d97706); padding: 20px; border-radius: 10px 10px 0 0;">
            <h2 style="color: white; margin: 0;">⚠️ Günlük Doluluk Yüklemesi Eksik</h2>
        </div>
        <div style="background: #fff; padding: 20px; border: 1px solid #e5e7eb; border-top: none; border-radius: 0 0 10px 10px;">
            <p>Sayın <strong>{depo_sorumlusu.ad} {depo_sorumlusu.soyad}</strong>,</p>
            <p><strong>{otel.ad}</strong> oteli için bugünkü (<strong>{bugun.strftime('%d.%m.%Y')}</strong>) günlük doluluk bilgileri henüz sisteme yüklenmemiştir.</p>
            
            <div style="background: #fef3c7; border-left: 4px solid #f59e0b; padding: 15px; margin: 20px 0;">
                <strong>Eksik Yüklemeler:</strong>
                <ul style="margin: 10px 0 0 0; padding-left: 20px;">
                    {''.join([f'<li>{y}</li>' for y in eksik_yuklemeler])}
                </ul>
            </div>
            
            <p>Lütfen en kısa sürede doluluk bilgilerini sisteme yükleyiniz.</p>
            <p style="color: #6b7280; font-size: 14px;">Bu bilgiler kat sorumlularının günlük görevlerinin oluşturulması için gereklidir.</p>
            
            <hr style="border: none; border-top: 1px solid #e5e7eb; margin: 20px 0;">
            <p style="color: #9ca3af; font-size: 12px;">Minibar Takip Sistemi</p>
        </div>
    </div>
</body>
</html>
"""
                    
                    # Email gönder
                    result = EmailService.send_email(
                        to_email=depo_sorumlusu.email,
                        subject=subject,
                        body=body,
                        email_tipi='uyari',
                        kullanici_id=depo_sorumlusu.id,
                        ilgili_tablo='yukleme_gorevleri',
                        html_body=html_body,
                        ek_bilgiler={
                            'otel_id': otel.id,
                            'otel_ad': otel.ad,
                            'eksik_yuklemeler': eksik_yuklemeler
                        }
                    )
                    
                    # Uyarı log kaydı oluştur
                    uyari_log = DolulukUyariLog(
                        otel_id=otel.id,
                        depo_sorumlusu_id=depo_sorumlusu.id,
                        uyari_tarihi=bugun,
                        uyari_tipi=uyari_tipi,
                        email_gonderildi=result['success'],
                        email_log_id=result.get('email_log_id')
                    )
                    db.session.add(uyari_log)
                    
                    if result['success']:
                        warnings_sent += 1
                    
                    details.append({
                        'otel': otel.ad,
                        'depo_sorumlusu': f"{depo_sorumlusu.ad} {depo_sorumlusu.soyad}",
                        'email': depo_sorumlusu.email,
                        'eksik_yuklemeler': eksik_yuklemeler,
                        'email_gonderildi': result['success']
                    })
                
                # Sistem yöneticilerine bilgi maili gönder
                DolulukUyariService._send_admin_notification(otel, eksik_yuklemeler, bugun)
            
            db.session.commit()
            
            logger.info(f"Doluluk uyarı kontrolü tamamlandı - {warnings_sent} uyarı gönderildi")
            
            return {
                'warnings_sent': warnings_sent,
                'details': details
            }
            
        except Exception as e:
            logger.error(f"Doluluk uyarı kontrolü hatası: {str(e)}")
            return {
                'warnings_sent': 0,
                'details': [],
                'error': str(e)
            }
    
    @staticmethod
    def _send_admin_notification(otel, eksik_yuklemeler, tarih):
        """Sistem yöneticilerine bilgi maili gönder"""
        try:
            from models import Kullanici
            
            # Sistem yöneticilerini bul
            sistem_yoneticileri = Kullanici.query.filter(
                Kullanici.rol.in_(['sistem_yoneticisi', 'admin']),
                Kullanici.aktif == True,
                Kullanici.email.isnot(None)
            ).all()
            
            if not sistem_yoneticileri:
                return
            
            subject = f"📊 Doluluk Yüklemesi Bilgilendirme - {otel.ad}"
            body = f"""Sistem Yöneticisi Bilgilendirmesi

{otel.ad} oteli için {tarih.strftime('%d.%m.%Y')} tarihli doluluk bilgileri saat 10:00'a kadar yüklenmemiştir.

Eksik Yüklemeler:
{chr(10).join(['- ' + y for y in eksik_yuklemeler])}

İlgili depo sorumlusuna uyarı maili gönderilmiştir.

Minibar Takip Sistemi
"""
            
            for yonetici in sistem_yoneticileri:
                if yonetici.email:
                    EmailService.send_email(
                        to_email=yonetici.email,
                        subject=subject,
                        body=body,
                        email_tipi='bilgi',
                        kullanici_id=yonetici.id,
                        ek_bilgiler={
                            'otel_id': otel.id,
                            'bildirim_tipi': 'admin_notification'
                        }
                    )
                    
        except Exception as e:
            logger.error(f"Admin bildirim hatası: {str(e)}")
