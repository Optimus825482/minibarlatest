"""
Görevlendirme Sistemi - Routes
Kat sorumlusu, depo sorumlusu ve sistem yöneticisi için görev route'ları
"""

from flask import Blueprint, render_template, request, jsonify, session, redirect, url_for, flash
from datetime import datetime, date, timezone, timedelta
from functools import wraps

from models import db, Kullanici, GunlukGorev, GorevDetay, YuklemeGorev
from utils.gorev_service import GorevService
from utils.yukleme_gorev_service import YuklemeGorevService
from utils.bildirim_service import BildirimService

gorev_bp = Blueprint('gorev', __name__, url_prefix='/gorevler')


# ============================================
# YARDIMCI FONKSİYONLAR
# ============================================

def login_required(f):
    """Giriş kontrolü decorator'ı"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'kullanici_id' not in session:
            flash('Bu sayfaya erişmek için giriş yapmalısınız.', 'warning')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function


def rol_gerekli(*roller):
    """Rol kontrolü decorator'ı"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if 'kullanici_id' not in session:
                flash('Bu sayfaya erişmek için giriş yapmalısınız.', 'warning')
                return redirect(url_for('login'))
            
            kullanici = Kullanici.query.get(session['kullanici_id'])
            if not kullanici or kullanici.rol not in roller:
                flash('Bu sayfaya erişim yetkiniz yok.', 'danger')
                return redirect(url_for('dashboard'))
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator


def get_current_user():
    """Mevcut kullanıcıyı getirir"""
    if 'kullanici_id' in session:
        return Kullanici.query.get(session['kullanici_id'])
    return None


# ============================================
# KAT SORUMLUSU ROUTE'LARI
# ============================================

@gorev_bp.route('/')
@login_required
@rol_gerekli('kat_sorumlusu', 'depo_sorumlusu', 'sistem_yoneticisi', 'admin')
def gorev_listesi():
    """
    Günlük görev listesi sayfası
    GET /gorevler
    """
    try:
        kullanici = get_current_user()
        tarih_str = request.args.get('tarih', date.today().isoformat())
        tarih = datetime.strptime(tarih_str, '%Y-%m-%d').date()
        
        # Görev özetini al
        ozet = GorevService.get_task_summary(kullanici.id, tarih)
        
        # Bekleyen görevleri al
        bekleyen = GorevService.get_pending_tasks(kullanici.id, tarih)
        
        # Öncelik sıralaması: Önce kata göre, sonra Arrivals/Departures zamana göre karışık, sonra In House
        def oncelik_sirala(g):
            kat = g.get('kat_no') or 999
            tip = g.get('gorev_tipi', '')
            # Arrivals ve Departures için zaman bazlı sıralama (önce)
            if tip == 'arrival_kontrol' and g.get('varis_saati'):
                return (kat, 0, g.get('varis_saati', '99:99:99'))
            elif tip == 'departure_kontrol' and g.get('cikis_saati'):
                return (kat, 0, g.get('cikis_saati', '99:99:99'))
            # In House en sona (öncelik sırasına göre)
            return (kat, 1, str(g.get('oncelik_sirasi') or 999).zfill(5))
        
        bekleyen.sort(key=oncelik_sirala)
        
        # Tamamlanan görevleri al
        tamamlanan = GorevService.get_completed_tasks(kullanici.id, tarih)
        
        # DND görevleri al
        dnd_gorevler = GorevService.get_dnd_tasks(kullanici.id, tarih)
        
        return render_template(
            'kat_sorumlusu/gorev_listesi.html',
            ozet=ozet,
            bekleyen=bekleyen,
            tamamlanan=tamamlanan,
            dnd_gorevler=dnd_gorevler,
            tarih=tarih,
            kullanici=kullanici
        )
        
    except Exception as e:
        flash(f'Görev listesi yüklenirken hata oluştu: {str(e)}', 'danger')
        return redirect(url_for('dashboard'))


@gorev_bp.route('/yonetim')
@login_required
@rol_gerekli('kat_sorumlusu', 'depo_sorumlusu', 'sistem_yoneticisi', 'admin')
def gorev_yonetimi():
    """
    Gelişmiş görev yönetim sayfası - Filtreleme, yazdırma ve detaylı görünüm
    GET /gorevler/yonetim
    """
    try:
        kullanici = get_current_user()
        tarih_str = request.args.get('tarih', date.today().isoformat())
        tarih = datetime.strptime(tarih_str, '%Y-%m-%d').date()
        filtre_durum = request.args.get('durum', '')
        filtre_tip = request.args.get('tip', '')
        
        # Gün adını hesapla
        gun_adlari = ['Pazartesi', 'Salı', 'Çarşamba', 'Perşembe', 'Cuma', 'Cumartesi', 'Pazar']
        gun_adi = gun_adlari[tarih.weekday()]
        
        # Görev özetini al
        ozet = GorevService.get_task_summary(kullanici.id, tarih)
        
        # Tüm görevleri al ve birleştir
        bekleyen = GorevService.get_pending_tasks(kullanici.id, tarih)
        tamamlanan = GorevService.get_completed_tasks(kullanici.id, tarih)
        
        # Tüm görevleri birleştir
        tum_gorevler = bekleyen + tamamlanan
        
        # Filtreleme uygula
        if filtre_durum:
            tum_gorevler = [g for g in tum_gorevler if g['durum'] == filtre_durum]
        if filtre_tip:
            tum_gorevler = [g for g in tum_gorevler if g['gorev_tipi'] == filtre_tip]
        
        # Sıralama: Önce bekleyenler (öncelik sırasına göre), sonra DND, en son tamamlananlar
        # Arrivals için varış saatine göre, diğerleri için öncelik sırasına göre
        def siralama_key(g):
            durum_sirasi = {'pending': 0, 'dnd_pending': 1, 'completed': 2}
            durum = durum_sirasi.get(g['durum'], 3)
            
            # Arrivals için varış saatine göre sırala
            if g.get('gorev_tipi') == 'arrival_kontrol' and g.get('varis_saati'):
                return (durum, 0, g.get('varis_saati', '99:99'))
            # Diğerleri için öncelik sırasına göre
            return (durum, 1, g.get('oncelik_sirasi') or 999, g.get('oda_no', ''))
        
        tum_gorevler.sort(key=siralama_key)
        
        return render_template(
            'kat_sorumlusu/gorev_yonetimi.html',
            ozet=ozet,
            gorevler=tum_gorevler,
            tarih=tarih,
            gun_adi=gun_adi,
            filtre_durum=filtre_durum,
            filtre_tip=filtre_tip,
            kullanici=kullanici
        )
        
    except Exception as e:
        flash(f'Görev yönetimi yüklenirken hata oluştu: {str(e)}', 'danger')
        return redirect(url_for('dashboard'))


@gorev_bp.route('/inhouse')
@login_required
@rol_gerekli('kat_sorumlusu', 'depo_sorumlusu', 'sistem_yoneticisi', 'admin')
def inhouse_gorevler():
    """
    In House görevleri sayfası
    GET /gorevler/inhouse
    """
    try:
        kullanici = get_current_user()
        tarih_str = request.args.get('tarih', date.today().isoformat())
        tarih = datetime.strptime(tarih_str, '%Y-%m-%d').date()
        
        # Sadece In House görevleri filtrele
        bekleyen = GorevService.get_pending_tasks(kullanici.id, tarih)
        inhouse_bekleyen = [g for g in bekleyen if g['gorev_tipi'] == 'inhouse_kontrol']
        
        tamamlanan = GorevService.get_completed_tasks(kullanici.id, tarih)
        inhouse_tamamlanan = [g for g in tamamlanan if g['gorev_tipi'] == 'inhouse_kontrol']
        
        return render_template(
            'kat_sorumlusu/inhouse_gorevler.html',
            bekleyen=inhouse_bekleyen,
            tamamlanan=inhouse_tamamlanan,
            tarih=tarih,
            kullanici=kullanici
        )
        
    except Exception as e:
        flash(f'In House görevleri yüklenirken hata oluştu: {str(e)}', 'danger')
        return redirect(url_for('gorev.gorev_listesi'))


@gorev_bp.route('/arrivals')
@login_required
@rol_gerekli('kat_sorumlusu', 'depo_sorumlusu', 'sistem_yoneticisi', 'admin')
def arrivals_gorevler():
    """
    Arrivals görevleri sayfası
    GET /gorevler/arrivals
    """
    try:
        kullanici = get_current_user()
        tarih_str = request.args.get('tarih', date.today().isoformat())
        tarih = datetime.strptime(tarih_str, '%Y-%m-%d').date()
        
        # Sadece Arrivals görevleri filtrele
        bekleyen = GorevService.get_pending_tasks(kullanici.id, tarih)
        arrivals_bekleyen = [g for g in bekleyen if g['gorev_tipi'] == 'arrival_kontrol']
        
        tamamlanan = GorevService.get_completed_tasks(kullanici.id, tarih)
        arrivals_tamamlanan = [g for g in tamamlanan if g['gorev_tipi'] == 'arrival_kontrol']
        
        return render_template(
            'kat_sorumlusu/arrivals_gorevler.html',
            bekleyen=arrivals_bekleyen,
            tamamlanan=arrivals_tamamlanan,
            tarih=tarih,
            kullanici=kullanici
        )
        
    except Exception as e:
        flash(f'Arrivals görevleri yüklenirken hata oluştu: {str(e)}', 'danger')
        return redirect(url_for('gorev.gorev_listesi'))


@gorev_bp.route('/dnd')
@login_required
@rol_gerekli('kat_sorumlusu', 'depo_sorumlusu', 'sistem_yoneticisi', 'admin')
def dnd_listesi():
    """
    DND odaları listesi sayfası
    GET /gorevler/dnd
    """
    try:
        kullanici = get_current_user()
        tarih_str = request.args.get('tarih', date.today().isoformat())
        tarih = datetime.strptime(tarih_str, '%Y-%m-%d').date()
        
        dnd_gorevler = GorevService.get_dnd_tasks(kullanici.id, tarih)
        
        return render_template(
            'kat_sorumlusu/dnd_listesi.html',
            dnd_gorevler=dnd_gorevler,
            tarih=tarih,
            kullanici=kullanici
        )
        
    except Exception as e:
        flash(f'DND listesi yüklenirken hata oluştu: {str(e)}', 'danger')
        return redirect(url_for('gorev.gorev_listesi'))


@gorev_bp.route('/<int:gorev_detay_id>/tamamla', methods=['POST'])
@login_required
@rol_gerekli('kat_sorumlusu', 'depo_sorumlusu', 'sistem_yoneticisi', 'admin')
def gorev_tamamla(gorev_detay_id):
    """
    Görevi tamamla
    POST /gorevler/<id>/tamamla
    """
    try:
        kullanici = get_current_user()
        notlar = request.form.get('notlar', '')
        
        GorevService.complete_task(gorev_detay_id, kullanici.id, notlar)
        
        flash('Görev başarıyla tamamlandı.', 'success')
        
        # AJAX isteği ise JSON döndür
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'success': True, 'message': 'Görev tamamlandı'})
        
        return redirect(url_for('gorev.gorev_listesi'))
        
    except Exception as e:
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'success': False, 'error': str(e)}), 400
        
        flash(f'Görev tamamlanırken hata oluştu: {str(e)}', 'danger')
        return redirect(url_for('gorev.gorev_listesi'))


@gorev_bp.route('/<int:gorev_detay_id>/dnd', methods=['POST'])
@login_required
@rol_gerekli('kat_sorumlusu', 'depo_sorumlusu', 'sistem_yoneticisi', 'admin')
def gorev_dnd(gorev_detay_id):
    """
    Odayı DND olarak işaretle
    POST /gorevler/<id>/dnd
    """
    try:
        kullanici = get_current_user()
        notlar = request.form.get('notlar', '')
        
        result = GorevService.mark_dnd(gorev_detay_id, kullanici.id, notlar)
        
        if result.get('min_kontrol_tamamlandi'):
            flash(f'Oda DND - {result["dnd_sayisi"]}. kontrol kaydedildi. (Min. kontrol tamamlandı)', 'info')
        else:
            flash(f'Oda DND olarak işaretlendi. ({result["dnd_sayisi"]}/3 kontrol)', 'warning')
        
        # AJAX isteği ise JSON döndür
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'success': True, **result})
        
        return redirect(url_for('gorev.gorev_listesi'))
        
    except Exception as e:
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'success': False, 'error': str(e)}), 400
        
        flash(f'DND işaretlenirken hata oluştu: {str(e)}', 'danger')
        return redirect(url_for('gorev.gorev_listesi'))


# ============================================
# DEPO SORUMLUSU ROUTE'LARI
# ============================================

@gorev_bp.route('/depo/gorevler')
@login_required
@rol_gerekli('depo_sorumlusu', 'sistem_yoneticisi', 'admin')
def depo_gorevler():
    """
    Depo sorumlusu yükleme görevleri
    GET /gorevler/depo/gorevler
    """
    try:
        kullanici = get_current_user()
        tarih_str = request.args.get('tarih', date.today().isoformat())
        tarih = datetime.strptime(tarih_str, '%Y-%m-%d').date()
        
        # Bekleyen yükleme görevleri
        bekleyen = YuklemeGorevService.get_pending_uploads(kullanici.id, tarih)
        
        return render_template(
            'depo_sorumlusu/yukleme_gorevleri.html',
            bekleyen=bekleyen,
            tarih=tarih,
            kullanici=kullanici
        )
        
    except Exception as e:
        flash(f'Yükleme görevleri yüklenirken hata oluştu: {str(e)}', 'danger')
        return redirect(url_for('dashboard'))


@gorev_bp.route('/depo/personel-gorevler')
@login_required
@rol_gerekli('depo_sorumlusu', 'sistem_yoneticisi', 'admin')
def depo_personel_gorevler():
    """
    Personel görev durumları
    GET /gorevler/depo/personel-gorevler
    """
    try:
        kullanici = get_current_user()
        tarih_str = request.args.get('tarih', date.today().isoformat())
        tarih = datetime.strptime(tarih_str, '%Y-%m-%d').date()
        
        # Bağlı kat sorumlularını bul
        kat_sorumluları = Kullanici.query.filter(
            Kullanici.depo_sorumlusu_id == kullanici.id,
            Kullanici.rol == 'kat_sorumlusu',
            Kullanici.aktif == True
        ).all()
        
        personel_ozetleri = []
        for ks in kat_sorumluları:
            ozet = GorevService.get_task_summary(ks.id, tarih)
            personel_ozetleri.append({
                'personel_id': ks.id,
                'personel_adi': f"{ks.ad} {ks.soyad}",
                **ozet
            })
        
        return render_template(
            'depo_sorumlusu/personel_gorevler.html',
            personel_ozetleri=personel_ozetleri,
            tarih=tarih,
            kullanici=kullanici
        )
        
    except Exception as e:
        flash(f'Personel görevleri yüklenirken hata oluştu: {str(e)}', 'danger')
        return redirect(url_for('dashboard'))


@gorev_bp.route('/depo/gorev-raporlari')
@login_required
@rol_gerekli('depo_sorumlusu', 'sistem_yoneticisi', 'admin')
def depo_gorev_raporlari():
    """
    Görev raporları
    GET /gorevler/depo/gorev-raporlari
    """
    try:
        kullanici = get_current_user()
        baslangic_str = request.args.get('baslangic', (date.today() - timedelta(days=7)).isoformat())
        bitis_str = request.args.get('bitis', date.today().isoformat())
        
        baslangic = datetime.strptime(baslangic_str, '%Y-%m-%d').date()
        bitis = datetime.strptime(bitis_str, '%Y-%m-%d').date()
        
        # Tarih aralığındaki raporları hazırla
        raporlar = []
        current = baslangic
        while current <= bitis:
            # Bağlı kat sorumlularının özetlerini al
            kat_sorumluları = Kullanici.query.filter(
                Kullanici.depo_sorumlusu_id == kullanici.id,
                Kullanici.rol == 'kat_sorumlusu'
            ).all()
            
            gun_toplam = {'toplam': 0, 'tamamlanan': 0, 'bekleyen': 0, 'dnd': 0}
            for ks in kat_sorumluları:
                ozet = GorevService.get_task_summary(ks.id, current)
                gun_toplam['toplam'] += ozet['toplam']
                gun_toplam['tamamlanan'] += ozet['tamamlanan']
                gun_toplam['bekleyen'] += ozet['bekleyen']
                gun_toplam['dnd'] += ozet['dnd']
            
            gun_toplam['tarih'] = current.isoformat()
            gun_toplam['tamamlanma_orani'] = round((gun_toplam['tamamlanan'] / gun_toplam['toplam'] * 100), 1) if gun_toplam['toplam'] > 0 else 0
            raporlar.append(gun_toplam)
            
            current += timedelta(days=1)
        
        return render_template(
            'depo_sorumlusu/gorev_raporlari.html',
            raporlar=raporlar,
            baslangic=baslangic,
            bitis=bitis,
            kullanici=kullanici,
            today=date.today(),
            timedelta=timedelta
        )
        
    except Exception as e:
        flash(f'Görev raporları yüklenirken hata oluştu: {str(e)}', 'danger')
        return redirect(url_for('dashboard'))


# ============================================
# SİSTEM YÖNETİCİSİ ROUTE'LARI
# ============================================

@gorev_bp.route('/sistem/gorev-ozeti')
@login_required
@rol_gerekli('sistem_yoneticisi', 'admin')
def sistem_gorev_ozeti():
    """
    Otel geneli görev özeti
    GET /gorevler/sistem/gorev-ozeti
    """
    try:
        kullanici = get_current_user()
        tarih_str = request.args.get('tarih', date.today().isoformat())
        tarih = datetime.strptime(tarih_str, '%Y-%m-%d').date()
        
        # Tüm kat sorumlularının özetlerini al
        kat_sorumluları = Kullanici.query.filter(
            Kullanici.rol == 'kat_sorumlusu',
            Kullanici.aktif == True
        ).all()
        
        genel_ozet = {'toplam': 0, 'tamamlanan': 0, 'bekleyen': 0, 'dnd': 0}
        personel_ozetleri = []
        
        for ks in kat_sorumluları:
            ozet = GorevService.get_task_summary(ks.id, tarih)
            genel_ozet['toplam'] += ozet['toplam']
            genel_ozet['tamamlanan'] += ozet['tamamlanan']
            genel_ozet['bekleyen'] += ozet['bekleyen']
            genel_ozet['dnd'] += ozet['dnd']
            
            personel_ozetleri.append({
                'personel_id': ks.id,
                'personel_adi': f"{ks.ad} {ks.soyad}",
                'otel_adi': ks.otel.ad if ks.otel else 'Atanmamış',
                **ozet
            })
        
        genel_ozet['tamamlanma_orani'] = round((genel_ozet['tamamlanan'] / genel_ozet['toplam'] * 100), 1) if genel_ozet['toplam'] > 0 else 0
        
        return render_template(
            'sistem_yoneticisi/gorev_ozeti.html',
            genel_ozet=genel_ozet,
            personel_ozetleri=personel_ozetleri,
            tarih=tarih,
            kullanici=kullanici
        )
        
    except Exception as e:
        flash(f'Görev özeti yüklenirken hata oluştu: {str(e)}', 'danger')
        return redirect(url_for('dashboard'))


@gorev_bp.route('/sistem/yukleme-takip')
@login_required
@rol_gerekli('sistem_yoneticisi', 'admin')
def sistem_yukleme_takip():
    """
    Yükleme takip raporu
    GET /gorevler/sistem/yukleme-takip
    """
    try:
        kullanici = get_current_user()
        baslangic_str = request.args.get('baslangic', (date.today() - timedelta(days=7)).isoformat())
        bitis_str = request.args.get('bitis', date.today().isoformat())
        
        baslangic = datetime.strptime(baslangic_str, '%Y-%m-%d').date()
        bitis = datetime.strptime(bitis_str, '%Y-%m-%d').date()
        
        # Eksik yüklemeleri tespit et
        eksik_yuklemeler = YuklemeGorevService.get_missing_uploads(baslangic, bitis)
        
        return render_template(
            'sistem_yoneticisi/yukleme_takip.html',
            eksik_yuklemeler=eksik_yuklemeler,
            baslangic=baslangic,
            bitis=bitis,
            kullanici=kullanici
        )
        
    except Exception as e:
        flash(f'Yükleme takip raporu yüklenirken hata oluştu: {str(e)}', 'danger')
        return redirect(url_for('dashboard'))


@gorev_bp.route('/sistem/dnd-bildirimleri')
@login_required
@rol_gerekli('sistem_yoneticisi', 'admin')
def sistem_dnd_bildirimleri():
    """
    DND bildirimleri
    GET /gorevler/sistem/dnd-bildirimleri
    """
    try:
        kullanici = get_current_user()
        tarih_str = request.args.get('tarih', date.today().isoformat())
        tarih = datetime.strptime(tarih_str, '%Y-%m-%d').date()
        
        # Tamamlanmayan DND görevlerini bul
        tamamlanmayan_dnd = GorevDetay.query.join(GunlukGorev).filter(
            GunlukGorev.gorev_tarihi == tarih,
            GorevDetay.dnd_sayisi > 0,
            GorevDetay.dnd_sayisi < 3,
            GorevDetay.durum != 'completed'
        ).all()
        
        dnd_listesi = []
        for detay in tamamlanmayan_dnd:
            dnd_listesi.append({
                'detay_id': detay.id,
                'oda_no': detay.oda.oda_no if detay.oda else 'Bilinmiyor',
                'dnd_sayisi': detay.dnd_sayisi,
                'son_dnd_zamani': detay.son_dnd_zamani.isoformat() if detay.son_dnd_zamani else None,
                'personel_adi': f"{detay.gorev.personel.ad} {detay.gorev.personel.soyad}" if detay.gorev and detay.gorev.personel else 'Bilinmiyor'
            })
        
        return render_template(
            'sistem_yoneticisi/dnd_bildirimleri.html',
            dnd_listesi=dnd_listesi,
            tarih=tarih,
            kullanici=kullanici
        )
        
    except Exception as e:
        flash(f'DND bildirimleri yüklenirken hata oluştu: {str(e)}', 'danger')
        return redirect(url_for('dashboard'))


# ============================================
# API ROUTE'LARI
# ============================================

@gorev_bp.route('/api/bekleyen')
@login_required
def api_bekleyen_gorevler():
    """
    Bekleyen görev sayısı API
    GET /gorevler/api/bekleyen
    """
    try:
        kullanici = get_current_user()
        tarih = date.today()
        
        ozet = GorevService.get_task_summary(kullanici.id, tarih)
        
        return jsonify({
            'success': True,
            'bekleyen': ozet['bekleyen'],
            'dnd': ozet['dnd'],
            'toplam': ozet['toplam']
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@gorev_bp.route('/api/countdown/<int:gorev_detay_id>')
@login_required
def api_countdown(gorev_detay_id):
    """
    Geri sayım bilgisi API
    GET /gorevler/api/countdown/<id>
    """
    try:
        detay = GorevDetay.query.get(gorev_detay_id)
        if not detay:
            return jsonify({'success': False, 'error': 'Görev bulunamadı'}), 404
        
        if not detay.varis_saati:
            return jsonify({'success': False, 'error': 'Varış saati yok'}), 400
        
        countdown = GorevService.calculate_countdown(detay.varis_saati)
        
        return jsonify({
            'success': True,
            **countdown
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@gorev_bp.route('/api/bildirim-oku', methods=['POST'])
@login_required
def api_bildirim_oku():
    """
    Bildirimi okundu işaretle API
    POST /gorevler/api/bildirim-oku
    """
    try:
        bildirim_id = request.json.get('bildirim_id')
        if not bildirim_id:
            return jsonify({'success': False, 'error': 'Bildirim ID gerekli'}), 400
        
        BildirimService.mark_notification_read(bildirim_id)
        
        return jsonify({'success': True})
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@gorev_bp.route('/yazdir')
@login_required
@rol_gerekli('kat_sorumlusu', 'depo_sorumlusu', 'sistem_yoneticisi', 'admin')
def gorev_yazdir():
    """
    Görev listesi yazdırma sayfası
    GET /gorevler/yazdir
    """
    try:
        kullanici = get_current_user()
        tarih_str = request.args.get('tarih', date.today().isoformat())
        tarih = datetime.strptime(tarih_str, '%Y-%m-%d').date()
        
        # Gün adını hesapla
        gun_adlari = ['Pazartesi', 'Salı', 'Çarşamba', 'Perşembe', 'Cuma', 'Cumartesi', 'Pazar']
        gun_adi = gun_adlari[tarih.weekday()]
        
        # Görev özetini al
        ozet = GorevService.get_task_summary(kullanici.id, tarih)
        
        # Tüm görevleri al
        bekleyen = GorevService.get_pending_tasks(kullanici.id, tarih)
        tamamlanan = GorevService.get_completed_tasks(kullanici.id, tarih)
        tum_gorevler = bekleyen + tamamlanan
        
        # Sıralama: Önce bekleyenler (öncelik sırasına göre), sonra DND, en son tamamlananlar
        def siralama_key(g):
            durum_sirasi = {'pending': 0, 'dnd_pending': 1, 'completed': 2}
            durum = durum_sirasi.get(g['durum'], 3)
            
            # Arrivals için varış saatine göre sırala
            if g.get('gorev_tipi') == 'arrival_kontrol' and g.get('varis_saati'):
                return (durum, 0, g.get('varis_saati', '99:99'))
            # Diğerleri için öncelik sırasına göre
            return (durum, 1, g.get('oncelik_sirasi') or 999, g.get('oda_no', ''))
        
        tum_gorevler.sort(key=siralama_key)
        
        return render_template(
            'kat_sorumlusu/gorev_yazdir.html',
            ozet=ozet,
            gorevler=tum_gorevler,
            tarih=tarih,
            gun_adi=gun_adi,
            kullanici=kullanici
        )
        
    except Exception as e:
        flash(f'Yazdırma sayfası yüklenirken hata oluştu: {str(e)}', 'danger')
        return redirect(url_for('gorev.gorev_yonetimi'))


@gorev_bp.route('/api/bildirimler')
@login_required
def api_bildirimler():
    """
    Bildirimler API
    GET /gorevler/api/bildirimler
    """
    try:
        kullanici = get_current_user()
        sadece_okunmamis = request.args.get('sadece_okunmamis', 'false').lower() == 'true'
        
        bildirimler = BildirimService.get_notifications(kullanici.id, sadece_okunmamis)
        okunmamis_sayisi = BildirimService.get_unread_count(kullanici.id)
        
        return jsonify({
            'success': True,
            'bildirimler': bildirimler,
            'okunmamis_sayisi': okunmamis_sayisi
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@gorev_bp.route('/api/dnd-kontroller/<int:gorev_detay_id>')
@login_required
def api_dnd_kontroller(gorev_detay_id):
    """
    DND kontrol kayıtları API
    GET /gorevler/api/dnd-kontroller/<id>
    """
    try:
        from models import DNDKontrol
        
        detay = GorevDetay.query.get(gorev_detay_id)
        if not detay:
            return jsonify({'success': False, 'error': 'Görev bulunamadı'}), 404
        
        # DND kontrol kayıtlarını getir
        kontroller = DNDKontrol.query.filter_by(gorev_detay_id=gorev_detay_id).order_by(DNDKontrol.kontrol_zamani.desc()).all()
        
        kontrol_listesi = []
        for k in kontroller:
            kontrol_listesi.append({
                'id': k.id,
                'kontrol_zamani': k.kontrol_zamani.strftime('%H:%M') if k.kontrol_zamani else '-',
                'kontrol_tarihi': k.kontrol_zamani.strftime('%d.%m.%Y') if k.kontrol_zamani else '-',
                'kontrol_eden': f"{k.kontrol_eden.ad} {k.kontrol_eden.soyad}" if k.kontrol_eden else 'Bilinmiyor',
                'notlar': k.notlar or ''
            })
        
        return jsonify({
            'success': True,
            'oda_no': detay.oda.oda_no if detay.oda else 'Bilinmiyor',
            'dnd_sayisi': detay.dnd_sayisi,
            'kontroller': kontrol_listesi
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@gorev_bp.route('/api/gorev-detay/<int:gorev_detay_id>')
@login_required
def api_gorev_detay(gorev_detay_id):
    """
    Tamamlanan görev detayları API
    GET /gorevler/api/gorev-detay/<id>
    """
    try:
        from models import GorevDurumLog, OdaKontrolKaydi
        
        detay = GorevDetay.query.get(gorev_detay_id)
        if not detay:
            return jsonify({'success': False, 'error': 'Görev bulunamadı'}), 404
        
        # Kontrol kaydını oda_id ve tarih ile bul - en son kaydı al
        kontrol_tarihi = detay.gorev.gorev_tarihi if detay.gorev else date.today()
        kontrol_kaydi = OdaKontrolKaydi.query.filter_by(
            oda_id=detay.oda_id,
            kontrol_tarihi=kontrol_tarihi
        ).order_by(OdaKontrolKaydi.bitis_zamani.desc()).first()
        
        baslangic = None
        bitis = None
        sure = None
        
        if kontrol_kaydi:
            if kontrol_kaydi.baslangic_zamani:
                baslangic = kontrol_kaydi.baslangic_zamani.strftime('%H:%M')
            if kontrol_kaydi.bitis_zamani:
                bitis = kontrol_kaydi.bitis_zamani.strftime('%H:%M')
            if kontrol_kaydi.baslangic_zamani and kontrol_kaydi.bitis_zamani:
                delta = kontrol_kaydi.bitis_zamani - kontrol_kaydi.baslangic_zamani
                dakika = int(delta.total_seconds() // 60)
                saniye = int(delta.total_seconds() % 60)
                sure = f"{dakika} dk {saniye} sn"
        elif detay.kontrol_zamani:
            bitis = detay.kontrol_zamani.strftime('%H:%M')
        
        # Tamamlama tipini belirle
        tamamlama_tipi = 'Manuel'
        if detay.notlar:
            if 'Sarfiyat yok' in detay.notlar:
                tamamlama_tipi = 'Sarfiyat Yok'
            elif 'Ürün eklendi' in detay.notlar:
                tamamlama_tipi = 'Ürün Eklendi'
            elif 'DND' in detay.notlar:
                tamamlama_tipi = 'DND Kontrolü'
        
        # Durum geçmişini al
        loglar = GorevDurumLog.query.filter_by(gorev_detay_id=gorev_detay_id).order_by(GorevDurumLog.degisiklik_zamani.desc()).all()
        
        gecmis = []
        for log in loglar:
            gecmis.append({
                'onceki_durum': log.onceki_durum or 'Yeni',
                'yeni_durum': log.yeni_durum,
                'zaman': log.degisiklik_zamani.strftime('%H:%M') if log.degisiklik_zamani else '-',
                'aciklama': log.aciklama or ''
            })
        
        return jsonify({
            'success': True,
            'oda_no': detay.oda.oda_no if detay.oda else 'Bilinmiyor',
            'baslangic': baslangic,
            'bitis': bitis,
            'sure': sure,
            'tamamlama_tipi': tamamlama_tipi,
            'notlar': detay.notlar,
            'gecmis': gecmis,
            'kaynak_silindi': detay.misafir_kayit_id is None  # Kaynak silindi göstergesi
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500
