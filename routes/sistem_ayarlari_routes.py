"""
Sistem Ayarları Route'ları

Bu modül sistem yöneticisi için ayar sayfalarını içerir.

Endpoint'ler:
- /sistem-ayarlari - Ana ayarlar sayfası
- /sistem-ayarlari/email - Email ayarları
- /sistem-ayarlari/email/test - Email bağlantı testi
- /sistem-ayarlari/email-loglari - Email log listesi
- /api/email-tracking/<tracking_id> - Email okundu takibi

Roller:
- sistem_yoneticisi
"""

from flask import render_template, request, redirect, url_for, flash, session, jsonify, send_file
from models import db, EmailAyarlari, EmailLog, Kullanici, BackupHistory
from utils.decorators import login_required, role_required
from utils.helpers import log_islem
from utils.email_service import EmailService
from utils.backup_service import BackupService
from datetime import datetime, timezone
from pathlib import Path
import io


def register_sistem_ayarlari_routes(app):
    """Sistem ayarları route'larını kaydet"""
    
    @app.route('/sistem-ayarlari')
    @login_required
    @role_required('sistem_yoneticisi', 'admin')
    def sistem_ayarlari():
        """Sistem ayarları ana sayfası"""
        return render_template('sistem_yoneticisi/sistem_ayarlari.html', active_tab='genel')
    
    @app.route('/sistem-ayarlari/email', methods=['GET', 'POST'])
    @login_required
    @role_required('sistem_yoneticisi', 'admin')
    def sistem_ayarlari_email():
        """Email ayarları sayfası"""
        
        if request.method == 'POST':
            try:
                # Mevcut ayarları al veya yeni oluştur
                ayarlar = EmailAyarlari.query.filter_by(aktif=True).first()
                if not ayarlar:
                    ayarlar = EmailAyarlari()
                    db.session.add(ayarlar)
                
                # Form verilerini al
                ayarlar.smtp_server = request.form.get('smtp_server', '').strip()
                ayarlar.smtp_port = int(request.form.get('smtp_port', 587))
                ayarlar.smtp_username = request.form.get('smtp_username', '').strip()
                
                # Şifre sadece değiştirildiyse güncelle
                new_password = request.form.get('smtp_password', '').strip()
                if new_password:
                    ayarlar.smtp_password = new_password
                
                ayarlar.smtp_use_tls = request.form.get('smtp_use_tls') == 'on'
                ayarlar.smtp_use_ssl = request.form.get('smtp_use_ssl') == 'on'
                ayarlar.sender_email = request.form.get('sender_email', '').strip()
                ayarlar.sender_name = request.form.get('sender_name', 'Minibar Takip Sistemi').strip()
                ayarlar.aktif = True
                ayarlar.guncelleyen_id = session.get('kullanici_id')
                
                db.session.commit()
                
                log_islem('guncelleme', 'email_ayarlari', {
                    'smtp_server': ayarlar.smtp_server,
                    'smtp_port': ayarlar.smtp_port
                })
                
                flash('Email ayarları başarıyla kaydedildi.', 'success')
                
            except ValueError as e:
                flash(f'Geçersiz değer: {str(e)}', 'danger')
            except Exception as e:
                db.session.rollback()
                flash(f'Hata oluştu: {str(e)}', 'danger')
            
            return redirect(url_for('sistem_ayarlari_email'))
        
        # Mevcut ayarları getir
        ayarlar = EmailAyarlari.query.filter_by(aktif=True).first()
        
        return render_template('sistem_yoneticisi/sistem_ayarlari.html', 
                             active_tab='email',
                             email_ayarlari=ayarlar)
    
    @app.route('/sistem-ayarlari/email/test', methods=['POST'])
    @login_required
    @role_required('sistem_yoneticisi', 'admin')
    def sistem_ayarlari_email_test():
        """Email bağlantı testi"""
        try:
            result = EmailService.test_connection()
            
            if result['success']:
                # Test maili gönder
                kullanici = Kullanici.query.get(session.get('kullanici_id'))
                if kullanici and kullanici.email:
                    test_result = EmailService.send_email(
                        to_email=kullanici.email,
                        subject='🧪 Minibar Takip - Email Test',
                        body=f'Bu bir test emailidir.\n\nEmail sistemi başarıyla yapılandırılmıştır.\n\nTest Tarihi: {datetime.now().strftime("%d.%m.%Y %H:%M")}',
                        email_tipi='sistem',
                        kullanici_id=kullanici.id,
                        html_body=f'''
<html>
<body style="font-family: Arial, sans-serif;">
    <div style="max-width: 500px; margin: 0 auto; padding: 20px;">
        <div style="background: linear-gradient(135deg, #10b981, #059669); padding: 20px; border-radius: 10px;">
            <h2 style="color: white; margin: 0;">✅ Email Test Başarılı</h2>
        </div>
        <div style="padding: 20px; background: #f9fafb; border-radius: 0 0 10px 10px;">
            <p>Email sistemi başarıyla yapılandırılmıştır.</p>
            <p style="color: #6b7280; font-size: 14px;">Test Tarihi: {datetime.now().strftime("%d.%m.%Y %H:%M")}</p>
        </div>
    </div>
</body>
</html>
'''
                    )
                    
                    if test_result['success']:
                        return jsonify({
                            'success': True,
                            'message': f'Bağlantı başarılı! Test maili {kullanici.email} adresine gönderildi.'
                        })
                    else:
                        return jsonify({
                            'success': False,
                            'message': f'Bağlantı başarılı ancak test maili gönderilemedi: {test_result["message"]}'
                        })
                else:
                    return jsonify({
                        'success': True,
                        'message': 'Bağlantı başarılı! (Test maili için email adresinizi güncelleyin)'
                    })
            else:
                return jsonify(result)
                
        except Exception as e:
            return jsonify({
                'success': False,
                'message': f'Test hatası: {str(e)}'
            })
    
    @app.route('/sistem-ayarlari/email-loglari')
    @login_required
    @role_required('sistem_yoneticisi', 'admin')
    def email_loglari():
        """Email log listesi"""
        page = request.args.get('page', 1, type=int)
        per_page = 50
        
        # Filtreler
        email_tipi = request.args.get('tipi')
        durum = request.args.get('durum')
        tarih_baslangic = request.args.get('tarih_baslangic')
        tarih_bitis = request.args.get('tarih_bitis')
        
        query = EmailLog.query
        
        if email_tipi:
            query = query.filter(EmailLog.email_tipi == email_tipi)
        if durum:
            query = query.filter(EmailLog.durum == durum)
        if tarih_baslangic:
            query = query.filter(EmailLog.gonderim_tarihi >= tarih_baslangic)
        if tarih_bitis:
            query = query.filter(EmailLog.gonderim_tarihi <= tarih_bitis)
        
        logs = query.order_by(EmailLog.gonderim_tarihi.desc()).paginate(
            page=page, per_page=per_page, error_out=False
        )
        
        # İstatistikler
        istatistikler = {
            'toplam': EmailLog.query.count(),
            'gonderildi': EmailLog.query.filter_by(durum='gonderildi').count(),
            'hata': EmailLog.query.filter_by(durum='hata').count(),
            'okundu': EmailLog.query.filter_by(okundu=True).count()
        }
        
        return render_template('sistem_yoneticisi/email_loglari.html',
                             logs=logs,
                             istatistikler=istatistikler,
                             email_tipi=email_tipi,
                             durum=durum)
    
    @app.route('/api/email-tracking/<tracking_id>')
    def email_tracking(tracking_id):
        """Email okundu takibi - 1x1 pixel döndürür"""
        try:
            EmailService.mark_as_read(tracking_id)
        except:
            pass
        
        # 1x1 transparent GIF
        gif_data = b'GIF89a\x01\x00\x01\x00\x80\x00\x00\xff\xff\xff\x00\x00\x00!\xf9\x04\x01\x00\x00\x00\x00,\x00\x00\x00\x00\x01\x00\x01\x00\x00\x02\x02D\x01\x00;'
        return send_file(
            io.BytesIO(gif_data),
            mimetype='image/gif',
            max_age=0
        )
    
    # ============================================
    # YEDEKLEME AYARLARI
    # ============================================
    
    @app.route('/sistem-ayarlari/yedekleme', methods=['GET', 'POST'])
    @login_required
    @role_required('sistem_yoneticisi')
    def sistem_ayarlari_yedekleme():
        """Yedekleme ayarları sayfası"""
        
        if request.method == 'POST':
            try:
                otomatik_yedekleme = request.form.get('otomatik_yedekleme') == 'on'
                yedekleme_saati = request.form.get('yedekleme_saati', '23:59')
                saklama_suresi = int(request.form.get('saklama_suresi', 15))
                
                # Validasyon
                if saklama_suresi < 1 or saklama_suresi > 365:
                    flash('Saklama süresi 1-365 gün arasında olmalıdır.', 'danger')
                    return redirect(url_for('sistem_ayarlari_yedekleme'))
                
                result = BackupService.save_backup_settings(
                    otomatik_yedekleme=otomatik_yedekleme,
                    yedekleme_saati=yedekleme_saati,
                    saklama_suresi=saklama_suresi
                )
                
                if result['success']:
                    log_islem('guncelleme', 'yedekleme_ayarlari', {
                        'otomatik_yedekleme': otomatik_yedekleme,
                        'saklama_suresi': saklama_suresi
                    })
                    flash('Yedekleme ayarları kaydedildi.', 'success')
                else:
                    flash(f'Hata: {result["message"]}', 'danger')
                    
            except Exception as e:
                flash(f'Hata: {str(e)}', 'danger')
            
            return redirect(url_for('sistem_ayarlari_yedekleme'))
        
        # Ayarları ve yedek listesini getir
        ayarlar = BackupService.get_backup_settings()
        yedekler = BackupService.get_backup_list()
        istatistikler = BackupService.get_backup_stats()
        
        return render_template('sistem_yoneticisi/sistem_ayarlari.html',
                             active_tab='yedekleme',
                             backup_ayarlari=ayarlar,
                             yedekler=yedekler,
                             backup_istatistikler=istatistikler)
    
    @app.route('/sistem-ayarlari/yedekleme/olustur', methods=['POST'])
    @login_required
    @role_required('sistem_yoneticisi')
    def yedek_olustur():
        """Manuel yedek oluştur"""
        try:
            aciklama = request.form.get('aciklama', f'Manuel yedek - {datetime.now().strftime("%d.%m.%Y %H:%M")}')
            
            result = BackupService.create_backup(
                kullanici_id=session.get('kullanici_id'),
                aciklama=aciklama
            )
            
            if result['success']:
                log_islem('olusturma', 'yedekleme', {
                    'backup_id': result['backup_id'],
                    'filename': result['filename']
                })
                flash(f'Yedek başarıyla oluşturuldu: {result["filename"]}', 'success')
            else:
                flash(f'Yedekleme hatası: {result["message"]}', 'danger')
                
        except Exception as e:
            flash(f'Hata: {str(e)}', 'danger')
        
        return redirect(url_for('sistem_ayarlari_yedekleme'))
    
    @app.route('/sistem-ayarlari/yedekleme/indir/<backup_id>')
    @login_required
    @role_required('sistem_yoneticisi')
    def yedek_indir(backup_id):
        """Yedek dosyasını indir"""
        try:
            backup = BackupHistory.query.filter_by(backup_id=backup_id).first()
            if not backup:
                flash('Yedek bulunamadı.', 'danger')
                return redirect(url_for('sistem_ayarlari_yedekleme'))
            
            filepath = Path('backups') / backup.filename
            if not filepath.exists():
                flash('Yedek dosyası bulunamadı.', 'danger')
                return redirect(url_for('sistem_ayarlari_yedekleme'))
            
            log_islem('indirme', 'yedekleme', {'backup_id': backup_id})
            
            return send_file(
                filepath,
                as_attachment=True,
                download_name=backup.filename
            )
            
        except Exception as e:
            flash(f'İndirme hatası: {str(e)}', 'danger')
            return redirect(url_for('sistem_ayarlari_yedekleme'))
    
    @app.route('/sistem-ayarlari/yedekleme/sil/<backup_id>', methods=['POST'])
    @login_required
    @role_required('sistem_yoneticisi')
    def yedek_sil(backup_id):
        """Yedek sil"""
        try:
            backup = BackupHistory.query.filter_by(backup_id=backup_id).first()
            if not backup:
                return jsonify({'success': False, 'message': 'Yedek bulunamadı'})
            
            # Dosyayı sil
            filepath = Path('backups') / backup.filename
            if filepath.exists():
                filepath.unlink()
            
            # Veritabanı kaydını sil
            db.session.delete(backup)
            db.session.commit()
            
            log_islem('silme', 'yedekleme', {'backup_id': backup_id})
            
            return jsonify({'success': True, 'message': 'Yedek silindi'})
            
        except Exception as e:
            return jsonify({'success': False, 'message': str(e)})
    
    @app.route('/sistem-ayarlari/yedekleme/geri-yukle/<backup_id>', methods=['POST'])
    @login_required
    @role_required('sistem_yoneticisi')
    def yedek_geri_yukle(backup_id):
        """Yedeği geri yükle"""
        try:
            result = BackupService.restore_backup(
                backup_id=backup_id,
                kullanici_id=session.get('kullanici_id')
            )
            
            if result['success']:
                log_islem('geri_yukleme', 'yedekleme', {'backup_id': backup_id})
                return jsonify({'success': True, 'message': 'Yedek başarıyla geri yüklendi'})
            else:
                return jsonify({'success': False, 'message': result['message']})
                
        except Exception as e:
            return jsonify({'success': False, 'message': str(e)})
    
    @app.route('/sistem-ayarlari/yedekleme/temizle', methods=['POST'])
    @login_required
    @role_required('sistem_yoneticisi')
    def eski_yedekleri_temizle():
        """Eski yedekleri manuel temizle"""
        try:
            ayarlar = BackupService.get_backup_settings()
            saklama_suresi = ayarlar.get('saklama_suresi', 15)
            
            result = BackupService.cleanup_old_backups(days=saklama_suresi)
            
            if result['deleted_count'] > 0:
                log_islem('temizleme', 'yedekleme', {
                    'silinen': result['deleted_count'],
                    'bosaltilan_mb': round(result['freed_space'] / 1024 / 1024, 2)
                })
                return jsonify({
                    'success': True,
                    'message': f'{result["deleted_count"]} eski yedek silindi, {round(result["freed_space"] / 1024 / 1024, 2)} MB alan boşaltıldı'
                })
            else:
                return jsonify({'success': True, 'message': 'Silinecek eski yedek yok'})
                
        except Exception as e:
            return jsonify({'success': False, 'message': str(e)})
