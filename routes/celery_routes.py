"""
Celery Asenkron Task Yönetimi API Route'ları
Task başlatma, durum sorgulama ve sonuç alma endpoint'leri
"""

from flask import Blueprint, request, jsonify
from utils.decorators import login_required, role_required
from celery.result import AsyncResult
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

# Blueprint tanımla
celery_bp = Blueprint('celery', __name__, url_prefix='/api/v1/celery')


@celery_bp.route('/task/donemsel-kar', methods=['POST'])
@login_required
@role_required(['sistem_yoneticisi', 'admin'])
def start_donemsel_kar_task():
    """
    Dönemsel kar hesaplama task'ını başlat
    
    Request Body:
        {
            "otel_id": int,
            "baslangic_tarihi": "YYYY-MM-DD",
            "bitis_tarihi": "YYYY-MM-DD",
            "donem_tipi": "gunluk" | "haftalik" | "aylik"
        }
    
    Returns:
        {
            "success": bool,
            "task_id": str,
            "message": str
        }
    """
    try:
        from celery_app import donemsel_kar_hesapla_async
        
        data = request.get_json()
        
        # Validasyon
        if not all(k in data for k in ['otel_id', 'baslangic_tarihi', 'bitis_tarihi']):
            return jsonify({
                'success': False,
                'message': 'Eksik parametreler'
            }), 400
        
        # Task'ı başlat
        task = donemsel_kar_hesapla_async.delay(
            otel_id=data['otel_id'],
            baslangic_tarihi=data['baslangic_tarihi'],
            bitis_tarihi=data['bitis_tarihi'],
            donem_tipi=data.get('donem_tipi', 'gunluk')
        )
        
        logger.info(f"Dönemsel kar hesaplama task başlatıldı - Task ID: {task.id}")
        
        return jsonify({
            'success': True,
            'task_id': task.id,
            'message': 'Dönemsel kar hesaplama başlatıldı'
        }), 202
        
    except Exception as e:
        logger.error(f"Dönemsel kar task başlatma hatası: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Hata: {str(e)}'
        }), 500


@celery_bp.route('/task/tuketim-trendi', methods=['POST'])
@login_required
@role_required(['sistem_yoneticisi', 'admin'])
def start_tuketim_trendi_task():
    """
    Tüketim trendi güncelleme task'ını başlat
    
    Request Body:
        {
            "otel_id": int (opsiyonel),
            "donem": "haftalik" | "aylik" | "yillik"
        }
    
    Returns:
        {
            "success": bool,
            "task_id": str,
            "message": str
        }
    """
    try:
        from celery_app import tuketim_trendi_guncelle_async
        
        data = request.get_json() or {}
        
        # Task'ı başlat
        task = tuketim_trendi_guncelle_async.delay(
            otel_id=data.get('otel_id'),
            donem=data.get('donem', 'aylik')
        )
        
        logger.info(f"Tüketim trendi güncelleme task başlatıldı - Task ID: {task.id}")
        
        return jsonify({
            'success': True,
            'task_id': task.id,
            'message': 'Tüketim trendi güncelleme başlatıldı'
        }), 202
        
    except Exception as e:
        logger.error(f"Tüketim trendi task başlatma hatası: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Hata: {str(e)}'
        }), 500


@celery_bp.route('/task/stok-devir', methods=['POST'])
@login_required
@role_required(['sistem_yoneticisi', 'admin', 'depo_sorumlusu'])
def start_stok_devir_task():
    """
    Stok devir hızı güncelleme task'ını başlat
    
    Request Body:
        {
            "otel_id": int (opsiyonel)
        }
    
    Returns:
        {
            "success": bool,
            "task_id": str,
            "message": str
        }
    """
    try:
        from celery_app import stok_devir_guncelle_async
        
        data = request.get_json() or {}
        
        # Task'ı başlat
        task = stok_devir_guncelle_async.delay(
            otel_id=data.get('otel_id')
        )
        
        logger.info(f"Stok devir güncelleme task başlatıldı - Task ID: {task.id}")
        
        return jsonify({
            'success': True,
            'task_id': task.id,
            'message': 'Stok devir güncelleme başlatıldı'
        }), 202
        
    except Exception as e:
        logger.error(f"Stok devir task başlatma hatası: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Hata: {str(e)}'
        }), 500


@celery_bp.route('/task/status/<task_id>', methods=['GET'])
@login_required
def get_task_status(task_id):
    """
    Task durumunu sorgula
    
    Args:
        task_id: Celery task ID
    
    Returns:
        {
            "success": bool,
            "task_id": str,
            "state": str,
            "result": dict,
            "info": dict
        }
    """
    try:
        from celery_app import celery
        
        # Task sonucunu al
        task_result = AsyncResult(task_id, app=celery)
        
        response = {
            'success': True,
            'task_id': task_id,
            'state': task_result.state,
            'result': None,
            'info': None
        }
        
        # Task durumuna göre bilgi ekle
        if task_result.state == 'PENDING':
            response['info'] = {
                'status': 'Task beklemede veya bulunamadı'
            }
        elif task_result.state == 'STARTED':
            response['info'] = {
                'status': 'Task çalışıyor'
            }
        elif task_result.state == 'SUCCESS':
            response['result'] = task_result.result
            response['info'] = {
                'status': 'Task başarıyla tamamlandı'
            }
        elif task_result.state == 'FAILURE':
            response['result'] = str(task_result.info)
            response['info'] = {
                'status': 'Task başarısız',
                'error': str(task_result.info)
            }
        else:
            response['info'] = {
                'status': f'Task durumu: {task_result.state}'
            }
        
        return jsonify(response), 200
        
    except Exception as e:
        logger.error(f"Task durum sorgulama hatası: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Hata: {str(e)}'
        }), 500


@celery_bp.route('/task/result/<task_id>', methods=['GET'])
@login_required
def get_task_result(task_id):
    """
    Task sonucunu al (sadece tamamlanmış task'lar için)
    
    Args:
        task_id: Celery task ID
    
    Returns:
        {
            "success": bool,
            "task_id": str,
            "state": str,
            "result": dict
        }
    """
    try:
        from celery_app import celery
        
        # Task sonucunu al
        task_result = AsyncResult(task_id, app=celery)
        
        if task_result.state != 'SUCCESS':
            return jsonify({
                'success': False,
                'task_id': task_id,
                'state': task_result.state,
                'message': 'Task henüz tamamlanmadı veya başarısız oldu'
            }), 400
        
        return jsonify({
            'success': True,
            'task_id': task_id,
            'state': task_result.state,
            'result': task_result.result
        }), 200
        
    except Exception as e:
        logger.error(f"Task sonuç alma hatası: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Hata: {str(e)}'
        }), 500


@celery_bp.route('/task/cancel/<task_id>', methods=['POST'])
@login_required
@role_required(['sistem_yoneticisi', 'admin'])
def cancel_task(task_id):
    """
    Çalışan task'ı iptal et
    
    Args:
        task_id: Celery task ID
    
    Returns:
        {
            "success": bool,
            "message": str
        }
    """
    try:
        from celery_app import celery
        
        # Task'ı iptal et
        celery.control.revoke(task_id, terminate=True)
        
        logger.info(f"Task iptal edildi - Task ID: {task_id}")
        
        return jsonify({
            'success': True,
            'message': 'Task iptal edildi'
        }), 200
        
    except Exception as e:
        logger.error(f"Task iptal hatası: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Hata: {str(e)}'
        }), 500


@celery_bp.route('/tasks/active', methods=['GET'])
@login_required
@role_required(['sistem_yoneticisi', 'admin'])
def get_active_tasks():
    """
    Aktif task'ları listele
    
    Returns:
        {
            "success": bool,
            "tasks": list
        }
    """
    try:
        from celery_app import celery
        
        # Aktif task'ları al
        inspect = celery.control.inspect()
        active_tasks = inspect.active()
        
        if not active_tasks:
            return jsonify({
                'success': True,
                'tasks': [],
                'message': 'Aktif task bulunamadı'
            }), 200
        
        # Task listesini düzenle
        tasks_list = []
        for worker, tasks in active_tasks.items():
            for task in tasks:
                tasks_list.append({
                    'task_id': task['id'],
                    'task_name': task['name'],
                    'worker': worker,
                    'args': task.get('args', []),
                    'kwargs': task.get('kwargs', {})
                })
        
        return jsonify({
            'success': True,
            'tasks': tasks_list,
            'total': len(tasks_list)
        }), 200
        
    except Exception as e:
        logger.error(f"Aktif task listeleme hatası: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Hata: {str(e)}'
        }), 500


@celery_bp.route('/task/doluluk-uyari', methods=['POST'])
@login_required
@role_required(['sistem_yoneticisi', 'admin'])
def start_doluluk_uyari_task():
    """
    Doluluk yükleme uyarı kontrolü task'ını manuel başlat
    Depo sorumlularına hatırlatıcı mail, sistem yöneticilerine bildirim maili gönderir
    
    Returns:
        {
            "success": bool,
            "task_id": str,
            "message": str
        }
    """
    try:
        from celery_app import doluluk_yukleme_uyari_kontrolu_task
        
        # Task'ı başlat
        task = doluluk_yukleme_uyari_kontrolu_task.delay()
        
        logger.info(f"Doluluk uyarı kontrolü task başlatıldı - Task ID: {task.id}")
        
        return jsonify({
            'success': True,
            'task_id': task.id,
            'message': 'Doluluk uyarı kontrolü başlatıldı. Eksik yüklemeler için mail gönderilecek.'
        }), 202
        
    except Exception as e:
        logger.error(f"Doluluk uyarı task başlatma hatası: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Hata: {str(e)}'
        }), 500


@celery_bp.route('/task/doluluk-uyari/check', methods=['GET'])
@login_required
@role_required(['sistem_yoneticisi', 'admin'])
def check_doluluk_uyari_status():
    """
    Bugünkü doluluk yükleme durumunu kontrol et (mail göndermeden)
    
    Returns:
        {
            "success": bool,
            "eksik_yuklemeler": list,
            "toplam_otel": int,
            "eksik_otel_sayisi": int
        }
    """
    try:
        from models import db, Otel, Kullanici, KullaniciOtel, YuklemeGorev
        from datetime import date
        
        bugun = date.today()
        eksik_yuklemeler = []
        
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
            otel_eksikler = []
            if not inhouse_gorev or inhouse_gorev.durum == 'pending':
                otel_eksikler.append('In House')
            if not arrivals_gorev or arrivals_gorev.durum == 'pending':
                otel_eksikler.append('Arrivals')
            
            if otel_eksikler:
                # Depo sorumlularını bul
                depo_sorumlu_atamalari = KullaniciOtel.query.join(Kullanici).filter(
                    KullaniciOtel.otel_id == otel.id,
                    Kullanici.rol == 'depo_sorumlusu',
                    Kullanici.aktif == True
                ).all()
                
                depo_sorumlulari = [
                    {
                        'ad': a.kullanici.ad,
                        'soyad': a.kullanici.soyad,
                        'email': a.kullanici.email
                    } for a in depo_sorumlu_atamalari
                ]
                
                eksik_yuklemeler.append({
                    'otel_id': otel.id,
                    'otel_ad': otel.ad,
                    'eksik_dosyalar': otel_eksikler,
                    'depo_sorumlulari': depo_sorumlulari
                })
        
        return jsonify({
            'success': True,
            'tarih': bugun.strftime('%d.%m.%Y'),
            'toplam_otel': len(oteller),
            'eksik_otel_sayisi': len(eksik_yuklemeler),
            'eksik_yuklemeler': eksik_yuklemeler
        }), 200
        
    except Exception as e:
        logger.error(f"Doluluk durum kontrolü hatası: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Hata: {str(e)}'
        }), 500


@celery_bp.route('/tasks/scheduled', methods=['GET'])
@login_required
@role_required(['sistem_yoneticisi', 'admin'])
def get_scheduled_tasks():
    """
    Zamanlanmış task'ları listele
    
    Returns:
        {
            "success": bool,
            "tasks": list
        }
    """
    try:
        from celery_app import celery
        
        # Zamanlanmış task'ları al
        inspect = celery.control.inspect()
        scheduled_tasks = inspect.scheduled()
        
        if not scheduled_tasks:
            return jsonify({
                'success': True,
                'tasks': [],
                'message': 'Zamanlanmış task bulunamadı'
            }), 200
        
        # Task listesini düzenle
        tasks_list = []
        for worker, tasks in scheduled_tasks.items():
            for task in tasks:
                tasks_list.append({
                    'task_id': task['request']['id'],
                    'task_name': task['request']['name'],
                    'worker': worker,
                    'eta': task.get('eta'),
                    'args': task['request'].get('args', []),
                    'kwargs': task['request'].get('kwargs', {})
                })
        
        return jsonify({
            'success': True,
            'tasks': tasks_list,
            'total': len(tasks_list)
        }), 200
        
    except Exception as e:
        logger.error(f"Zamanlanmış task listeleme hatası: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Hata: {str(e)}'
        }), 500
