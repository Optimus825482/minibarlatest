"""
Email Bildirim Servisi
Satın alma ve tedarikçi modülü için email bildirimleri
"""

from flask import render_template_string
from flask_mail import Message
from app import mail, app
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class EmailServisi:
    """Email bildirim servisi"""

    @staticmethod
    def siparis_bildirimi_gonder(siparis, tedarikci_email=None):
        """
        Tedarikçiye sipariş bildirimi gönder
        
        Args:
            siparis: SatinAlmaSiparisi nesnesi
            tedarikci_email: Tedarikçi email adresi (opsiyonel)
        
        Returns:
            bool: Başarılı ise True
        """
        try:
            # Email adresi kontrolü
            email_adresi = tedarikci_email or siparis.tedarikci.email
            if not email_adresi:
                logger.warning(f"Tedarikçi {siparis.tedarikci.tedarikci_adi} için email adresi bulunamadı")
                return False

            # Email içeriği
            subject = f"Yeni Satın Alma Siparişi - {siparis.siparis_no}"
            
            html_body = EmailServisi._siparis_bildirimi_template(siparis)
            
            # Email gönder
            msg = Message(
                subject=subject,
                recipients=[email_adresi],
                html=html_body,
                sender=app.config.get('MAIL_DEFAULT_SENDER', 'noreply@minibartakip.com')
            )
            
            mail.send(msg)
            logger.info(f"Sipariş bildirimi gönderildi: {siparis.siparis_no} -> {email_adresi}")
            return True
            
        except Exception as e:
            logger.error(f"Sipariş bildirimi gönderilirken hata: {str(e)}")
            return False

    @staticmethod
    def gecikme_uyarisi_gonder(siparis, kullanici_email):
        """
        Depo sorumlusuna gecikme uyarısı gönder
        
        Args:
            siparis: SatinAlmaSiparisi nesnesi
            kullanici_email: Kullanıcı email adresi
        
        Returns:
            bool: Başarılı ise True
        """
        try:
            if not kullanici_email:
                logger.warning(f"Sipariş {siparis.siparis_no} için kullanıcı email adresi bulunamadı")
                return False

            # Gecikme süresi hesapla
            gecikme_gun = (datetime.now().date() - siparis.tahmini_teslimat_tarihi).days
            
            # Email içeriği
            subject = f"⚠️ Sipariş Gecikme Uyarısı - {siparis.siparis_no}"
            
            html_body = EmailServisi._gecikme_uyarisi_template(siparis, gecikme_gun)
            
            # Email gönder
            msg = Message(
                subject=subject,
                recipients=[kullanici_email],
                html=html_body,
                sender=app.config.get('MAIL_DEFAULT_SENDER', 'noreply@minibartakip.com')
            )
            
            mail.send(msg)
            logger.info(f"Gecikme uyarısı gönderildi: {siparis.siparis_no} -> {kullanici_email}")
            return True
            
        except Exception as e:
            logger.error(f"Gecikme uyarısı gönderilirken hata: {str(e)}")
            return False

    @staticmethod
    def siparis_onay_bildirimi_gonder(siparis, tedarikci_email=None):
        """
        Tedarikçiye sipariş onay bildirimi gönder
        
        Args:
            siparis: SatinAlmaSiparisi nesnesi
            tedarikci_email: Tedarikçi email adresi (opsiyonel)
        
        Returns:
            bool: Başarılı ise True
        """
        try:
            email_adresi = tedarikci_email or siparis.tedarikci.email
            if not email_adresi:
                return False

            subject = f"Sipariş Onaylandı - {siparis.siparis_no}"
            
            html_body = EmailServisi._siparis_onay_template(siparis)
            
            msg = Message(
                subject=subject,
                recipients=[email_adresi],
                html=html_body,
                sender=app.config.get('MAIL_DEFAULT_SENDER', 'noreply@minibartakip.com')
            )
            
            mail.send(msg)
            logger.info(f"Sipariş onay bildirimi gönderildi: {siparis.siparis_no}")
            return True
            
        except Exception as e:
            logger.error(f"Sipariş onay bildirimi gönderilirken hata: {str(e)}")
            return False

    @staticmethod
    def _siparis_bildirimi_template(siparis):
        """Sipariş bildirimi HTML template"""
        template = """
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <style>
                body { font-family: Arial, sans-serif; line-height: 1.6; color: #333; }
                .container { max-width: 600px; margin: 0 auto; padding: 20px; }
                .header { background-color: #3b82f6; color: white; padding: 20px; text-align: center; }
                .content { background-color: #f9fafb; padding: 20px; }
                .info-box { background-color: white; padding: 15px; margin: 10px 0; border-radius: 5px; }
                .info-row { display: flex; justify-content: space-between; padding: 8px 0; border-bottom: 1px solid #e5e7eb; }
                .info-label { font-weight: bold; color: #6b7280; }
                .info-value { color: #111827; }
                table { width: 100%; border-collapse: collapse; margin: 15px 0; }
                th, td { padding: 10px; text-align: left; border-bottom: 1px solid #e5e7eb; }
                th { background-color: #f3f4f6; font-weight: bold; }
                .total { font-size: 18px; font-weight: bold; color: #3b82f6; }
                .footer { text-align: center; padding: 20px; color: #6b7280; font-size: 12px; }
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>Yeni Satın Alma Siparişi</h1>
                </div>
                
                <div class="content">
                    <p>Sayın {{ siparis.tedarikci.tedarikci_adi }},</p>
                    <p>Aşağıdaki detaylarda yeni bir satın alma siparişi oluşturulmuştur:</p>
                    
                    <div class="info-box">
                        <div class="info-row">
                            <span class="info-label">Sipariş No:</span>
                            <span class="info-value">{{ siparis.siparis_no }}</span>
                        </div>
                        <div class="info-row">
                            <span class="info-label">Sipariş Tarihi:</span>
                            <span class="info-value">{{ siparis.siparis_tarihi.strftime('%d.%m.%Y %H:%M') }}</span>
                        </div>
                        <div class="info-row">
                            <span class="info-label">Tahmini Teslimat:</span>
                            <span class="info-value">{{ siparis.tahmini_teslimat_tarihi.strftime('%d.%m.%Y') }}</span>
                        </div>
                        <div class="info-row">
                            <span class="info-label">Otel:</span>
                            <span class="info-value">{{ siparis.otel.otel_adi }}</span>
                        </div>
                    </div>
                    
                    <h3>Sipariş Detayları</h3>
                    <table>
                        <thead>
                            <tr>
                                <th>Ürün</th>
                                <th>Miktar</th>
                                <th>Birim Fiyat</th>
                                <th>Toplam</th>
                            </tr>
                        </thead>
                        <tbody>
                            {% for detay in siparis.detaylar %}
                            <tr>
                                <td>{{ detay.urun.urun_adi }}</td>
                                <td>{{ detay.miktar }} {{ detay.urun.birim }}</td>
                                <td>{{ "%.2f"|format(detay.birim_fiyat) }} ₺</td>
                                <td>{{ "%.2f"|format(detay.toplam_fiyat) }} ₺</td>
                            </tr>
                            {% endfor %}
                        </tbody>
                        <tfoot>
                            <tr>
                                <td colspan="3" style="text-align: right;"><strong>Genel Toplam:</strong></td>
                                <td class="total">{{ "%.2f"|format(siparis.toplam_tutar) }} ₺</td>
                            </tr>
                        </tfoot>
                    </table>
                    
                    {% if siparis.aciklama %}
                    <div class="info-box">
                        <strong>Açıklama:</strong>
                        <p>{{ siparis.aciklama }}</p>
                    </div>
                    {% endif %}
                    
                    <p>Lütfen siparişi onaylayıp tahmini teslimat tarihinde teslim etmenizi rica ederiz.</p>
                </div>
                
                <div class="footer">
                    <p>Bu otomatik bir bildirimdir. Lütfen yanıtlamayın.</p>
                    <p>&copy; {{ datetime.now().year }} Minibar Takip Sistemi</p>
                </div>
            </div>
        </body>
        </html>
        """
        return render_template_string(template, siparis=siparis, datetime=datetime)

    @staticmethod
    def _gecikme_uyarisi_template(siparis, gecikme_gun):
        """Gecikme uyarısı HTML template"""
        template = """
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <style>
                body { font-family: Arial, sans-serif; line-height: 1.6; color: #333; }
                .container { max-width: 600px; margin: 0 auto; padding: 20px; }
                .header { background-color: #ef4444; color: white; padding: 20px; text-align: center; }
                .warning-icon { font-size: 48px; margin-bottom: 10px; }
                .content { background-color: #fef2f2; padding: 20px; border: 2px solid #fecaca; }
                .info-box { background-color: white; padding: 15px; margin: 10px 0; border-radius: 5px; }
                .info-row { display: flex; justify-content: space-between; padding: 8px 0; border-bottom: 1px solid #e5e7eb; }
                .info-label { font-weight: bold; color: #6b7280; }
                .info-value { color: #111827; }
                .delay-badge { background-color: #ef4444; color: white; padding: 5px 15px; border-radius: 20px; font-weight: bold; }
                .action-button { display: inline-block; background-color: #3b82f6; color: white; padding: 12px 24px; text-decoration: none; border-radius: 5px; margin: 15px 0; }
                .footer { text-align: center; padding: 20px; color: #6b7280; font-size: 12px; }
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <div class="warning-icon">⚠️</div>
                    <h1>Sipariş Gecikme Uyarısı</h1>
                </div>
                
                <div class="content">
                    <p><strong>Dikkat!</strong> Aşağıdaki sipariş tahmini teslimat tarihini geçmiştir:</p>
                    
                    <div class="info-box">
                        <div class="info-row">
                            <span class="info-label">Sipariş No:</span>
                            <span class="info-value">{{ siparis.siparis_no }}</span>
                        </div>
                        <div class="info-row">
                            <span class="info-label">Tedarikçi:</span>
                            <span class="info-value">{{ siparis.tedarikci.tedarikci_adi }}</span>
                        </div>
                        <div class="info-row">
                            <span class="info-label">Sipariş Tarihi:</span>
                            <span class="info-value">{{ siparis.siparis_tarihi.strftime('%d.%m.%Y') }}</span>
                        </div>
                        <div class="info-row">
                            <span class="info-label">Tahmini Teslimat:</span>
                            <span class="info-value">{{ siparis.tahmini_teslimat_tarihi.strftime('%d.%m.%Y') }}</span>
                        </div>
                        <div class="info-row">
                            <span class="info-label">Gecikme Süresi:</span>
                            <span class="info-value"><span class="delay-badge">{{ gecikme_gun }} Gün</span></span>
                        </div>
                        <div class="info-row">
                            <span class="info-label">Toplam Tutar:</span>
                            <span class="info-value">{{ "%.2f"|format(siparis.toplam_tutar) }} ₺</span>
                        </div>
                    </div>
                    
                    <p><strong>Önerilen İşlemler:</strong></p>
                    <ul>
                        <li>Tedarikçi ile iletişime geçin</li>
                        <li>Yeni teslimat tarihi talep edin</li>
                        <li>Gerekirse alternatif tedarikçi değerlendirin</li>
                        <li>Stok durumunu kontrol edin</li>
                    </ul>
                    
                    <p style="text-align: center;">
                        <a href="#" class="action-button">Sipariş Detayını Görüntüle</a>
                    </p>
                </div>
                
                <div class="footer">
                    <p>Bu otomatik bir uyarıdır.</p>
                    <p>&copy; {{ datetime.now().year }} Minibar Takip Sistemi</p>
                </div>
            </div>
        </body>
        </html>
        """
        return render_template_string(template, siparis=siparis, gecikme_gun=gecikme_gun, datetime=datetime)

    @staticmethod
    def _siparis_onay_template(siparis):
        """Sipariş onay bildirimi HTML template"""
        template = """
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <style>
                body { font-family: Arial, sans-serif; line-height: 1.6; color: #333; }
                .container { max-width: 600px; margin: 0 auto; padding: 20px; }
                .header { background-color: #10b981; color: white; padding: 20px; text-align: center; }
                .success-icon { font-size: 48px; margin-bottom: 10px; }
                .content { background-color: #f0fdf4; padding: 20px; }
                .info-box { background-color: white; padding: 15px; margin: 10px 0; border-radius: 5px; }
                .info-row { display: flex; justify-content: space-between; padding: 8px 0; border-bottom: 1px solid #e5e7eb; }
                .info-label { font-weight: bold; color: #6b7280; }
                .info-value { color: #111827; }
                .footer { text-align: center; padding: 20px; color: #6b7280; font-size: 12px; }
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <div class="success-icon">✅</div>
                    <h1>Sipariş Onaylandı</h1>
                </div>
                
                <div class="content">
                    <p>Sayın {{ siparis.tedarikci.tedarikci_adi }},</p>
                    <p>Siparişiniz onaylanmıştır. Lütfen belirtilen tarihte teslimat yapınız.</p>
                    
                    <div class="info-box">
                        <div class="info-row">
                            <span class="info-label">Sipariş No:</span>
                            <span class="info-value">{{ siparis.siparis_no }}</span>
                        </div>
                        <div class="info-row">
                            <span class="info-label">Onay Tarihi:</span>
                            <span class="info-value">{{ datetime.now().strftime('%d.%m.%Y %H:%M') }}</span>
                        </div>
                        <div class="info-row">
                            <span class="info-label">Teslimat Tarihi:</span>
                            <span class="info-value">{{ siparis.tahmini_teslimat_tarihi.strftime('%d.%m.%Y') }}</span>
                        </div>
                        <div class="info-row">
                            <span class="info-label">Teslimat Adresi:</span>
                            <span class="info-value">{{ siparis.otel.otel_adi }}<br>{{ siparis.otel.adres if siparis.otel.adres else '' }}</span>
                        </div>
                    </div>
                    
                    <p>Teslimat sırasında sipariş numarasını belirtmeyi unutmayınız.</p>
                </div>
                
                <div class="footer">
                    <p>Bu otomatik bir bildirimdir.</p>
                    <p>&copy; {{ datetime.now().year }} Minibar Takip Sistemi</p>
                </div>
            </div>
        </body>
        </html>
        """
        return render_template_string(template, siparis=siparis, datetime=datetime)
