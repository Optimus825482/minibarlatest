"""
Developer Dashboard Routes
Sistem geliştiricisi için özel dashboard ve araçlar
"""
from flask import Blueprint, render_template, request, jsonify, session, redirect, url_for
from functools import wraps
import psutil
import os
from datetime import datetime, timedelta
from sqlalchemy import func, text
from models import db, Kullanici, Otel, Oda, MisafirKayit, MinibarIslem
import logging
import pytz

# KKTC Timezone
KKTC_TZ = pytz.timezone('Europe/Nicosia')

def get_kktc_now():
    """Kıbrıs saat diliminde şu anki zamanı döndürür."""
    return datetime.now(KKTC_TZ)

# CSRF protection
try:
    from app import csrf
except ImportError:
    csrf = None

developer_bp = Blueprint('developer', __name__, url_prefix='/developer')

# Developer şifresi: 518518Erkan!!

def developer_required(f):
    """Developer authentication decorator"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('developer_authenticated'):
            return redirect(url_for('developer.login'))
        return f(*args, **kwargs)
    return decorated_function

@developer_bp.route('/login', methods=['GET', 'POST'])
def login():
    """Developer login sayfası"""
    if request.method == 'POST':
        password = request.form.get('password')
        
        # Şifre kontrolü
        if password == '518518Erkan!!':
            session['developer_authenticated'] = True
            session.permanent = True
            logging.info("Developer dashboard'a giriş yapıldı")
            return redirect(url_for('developer.dashboard'))
        else:
            logging.warning("Developer dashboard'a başarısız giriş denemesi")
            return render_template('developer/login.html', error='Geçersiz şifre!')
    
    return render_template('developer/login.html')

@developer_bp.route('/logout')
def logout():
    """Developer logout"""
    session.pop('developer_authenticated', None)
    return redirect(url_for('developer.login'))

@developer_bp.route('/')
@developer_required
def dashboard():
    """Ana developer dashboard"""
    try:
        # Sistem metrikleri
        system_metrics = get_system_metrics()
        
        # Database istatistikleri
        db_stats = get_database_stats()
        
        # Son hatalar
        recent_errors = get_recent_errors()
        
        # Aktif kullanıcılar
        active_users = get_active_users_stats()
        
        # Ürün istatistikleri
        product_stats = get_product_stats()
        
        # Yeni enhanced dashboard kullan
        return render_template('developer/dashboard_enhanced.html')
    except Exception as e:
        logging.error(f"Developer dashboard hatası: {str(e)}")
        return render_template('developer/dashboard.html', error=str(e))

@developer_bp.route('/api/system-health')
@developer_required
def system_health():
    """Sistem sağlık durumu API"""
    try:
        # Uptime hesapla (boot time'dan beri)
        boot_time = psutil.boot_time()
        uptime_seconds = get_kktc_now().timestamp() - boot_time
        
        health = {
            'database': check_database_health(),
            'disk': check_disk_health(),
            'memory': check_memory_health(),
            'cpu': check_cpu_health(),
            'uptime': int(uptime_seconds),
            'timestamp': get_kktc_now().isoformat()
        }
        return jsonify(health)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@developer_bp.route('/api/metrics/summary')
@developer_required
def metrics_summary():
    """Sistem metrikleri özeti"""
    try:
        # Aktif kullanıcı sayısı (son 15 dakikada işlem yapan)
        fifteen_min_ago = get_kktc_now() - timedelta(minutes=15)
        active_users = db.session.query(func.count(func.distinct(MinibarIslem.personel_id)))\
            .filter(MinibarIslem.islem_tarihi >= fifteen_min_ago).scalar() or 0
        
        # Son 1 saatteki işlem sayısı
        one_hour_ago = get_kktc_now() - timedelta(hours=1)
        total_requests = db.session.query(func.count(MinibarIslem.id))\
            .filter(MinibarIslem.islem_tarihi >= one_hour_ago).scalar() or 0
        
        # Request per second hesapla
        requests_per_sec = round(total_requests / 3600, 2)
        
        # Top endpoints - QueryLog'dan gerçek veriler
        try:
            from models import QueryLog
            
            # Son 1 saatteki endpoint istatistikleri
            endpoint_stats = db.session.query(
                QueryLog.endpoint,
                func.count(QueryLog.id).label('count'),
                func.avg(QueryLog.execution_time).label('avg_time')
            ).filter(
                QueryLog.timestamp >= one_hour_ago,
                QueryLog.endpoint.isnot(None)
            ).group_by(
                QueryLog.endpoint
            ).order_by(
                func.count(QueryLog.id).desc()
            ).limit(10).all()
            
            top_endpoints = [
                {
                    'endpoint': stat.endpoint,
                    'count': stat.count,
                    'avg_time': round(stat.avg_time * 1000, 1),  # ms'ye çevir
                    'error_rate': 0.0  # TODO: Error tracking eklenecek
                }
                for stat in endpoint_stats
            ]
            
            # Eğer hiç veri yoksa boş liste
            if not top_endpoints:
                top_endpoints = []
                
        except Exception as e:
            logging.warning(f"Top endpoints alınamadı: {str(e)}")
            top_endpoints = []
        
        # Performance history (son 10 dakika)
        performance_history = []
        for i in range(10, 0, -1):
            time_point = get_kktc_now() - timedelta(minutes=i)
            cpu = psutil.cpu_percent(interval=0.1)
            memory = psutil.virtual_memory().percent
            performance_history.append({
                'time': time_point.strftime('%H:%M'),
                'cpu': round(cpu, 1),
                'memory': round(memory, 1)
            })
        
        # Ortalama response time (QueryLog'dan)
        try:
            avg_exec_time = db.session.query(
                func.avg(QueryLog.execution_time)
            ).filter(
                QueryLog.timestamp >= one_hour_ago
            ).scalar() or 0
            avg_response_time = round(avg_exec_time * 1000, 1)  # ms'ye çevir
        except:
            avg_response_time = 0
        
        summary = {
            'active_users': active_users,
            'requests_per_sec': requests_per_sec,
            'error_rate': 0.0,  # TODO: Error tracking eklenecek
            'avg_response_time': avg_response_time,
            'top_endpoints': top_endpoints,
            'performance_history': performance_history
        }
        
        return jsonify({'success': True, 'data': summary})
    except Exception as e:
        logging.error(f"Metrics summary error: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

@developer_bp.route('/api/logs')
@developer_required
def get_logs():
    """Son logları getir"""
    try:
        lines = int(request.args.get('lines', 100))
        log_file = 'app.log'
        
        if os.path.exists(log_file):
            with open(log_file, 'r', encoding='utf-8') as f:
                logs = f.readlines()[-lines:]
            return jsonify({'logs': logs})
        else:
            return jsonify({'logs': []})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@developer_bp.route('/api/check-negative-stock')
@developer_required
def check_negative_stock():
    """Negatif stok kontrolü yap"""
    try:
        from utils.ml.negative_stock_detector import NegativeStockDetector
        
        detector = NegativeStockDetector()
        result = detector.check_all_products()
        
        return jsonify({
            'success': True,
            'result': result
        })
    except Exception as e:
        logging.error(f"Negatif stok kontrolü hatası: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

@developer_bp.route('/api/fix-negative-stock', methods=['POST'])
@developer_required
def fix_negative_stock():
    """Negatif stokları düzelt"""
    try:
        from utils.fix_negative_stock import fix_negative_stocks
        
        fixed_items = fix_negative_stocks(dry_run=False)
        
        return jsonify({
            'success': True,
            'fixed_count': len(fixed_items),
            'items': fixed_items
        })
    except Exception as e:
        logging.error(f"Negatif stok düzeltme hatası: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

# Helper Functions
def get_system_metrics():
    """Sistem kaynak kullanımı"""
    try:
        cpu_percent = psutil.cpu_percent(interval=1)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        
        return {
            'cpu': {
                'percent': cpu_percent,
                'count': psutil.cpu_count()
            },
            'memory': {
                'total': memory.total / (1024**3),  # GB
                'used': memory.used / (1024**3),
                'percent': memory.percent
            },
            'disk': {
                'total': disk.total / (1024**3),
                'used': disk.used / (1024**3),
                'percent': disk.percent
            }
        }
    except Exception as e:
        logging.error(f"Sistem metrikleri alınamadı: {str(e)}")
        return {}

def get_database_stats():
    """Database tablo istatistikleri"""
    try:
        stats = {
            'users': Kullanici.query.count(),
            'otels': Otel.query.count(),
            'odas': Oda.query.count(),
            'rezervasyons': MisafirKayit.query.count(),
            'misafirs': MisafirKayit.query.filter(MisafirKayit.kayit_tipi == 'in_house').count(),
        }
        
        # Son 24 saat aktivite
        yesterday = get_kktc_now() - timedelta(days=1)
        try:
            stats['new_rezervasyons_24h'] = MinibarIslem.query.filter(
                MinibarIslem.islem_tarihi >= yesterday
            ).count()
        except:
            stats['new_rezervasyons_24h'] = 0
        
        return stats
    except Exception as e:
        logging.error(f"Database stats alınamadı: {str(e)}")
        return {}

def get_recent_errors():
    """Son hataları logdan oku"""
    try:
        errors = []
        log_file = 'app.log'
        
        if os.path.exists(log_file):
            with open(log_file, 'r', encoding='utf-8') as f:
                lines = f.readlines()[-500:]  # Son 500 satır
                
            for line in lines:
                if 'ERROR' in line or 'CRITICAL' in line:
                    errors.append(line.strip())
        
        return errors[-50:]  # Son 50 hata
    except Exception as e:
        logging.error(f"Hatalar okunamadı: {str(e)}")
        return []

def get_active_users_stats():
    """Aktif kullanıcı istatistikleri"""
    try:
        total_users = Kullanici.query.count()
        active_users = Kullanici.query.filter_by(aktif=True).count()
        admin_users = Kullanici.query.filter_by(rol='admin').count()
        
        return {
            'total': total_users,
            'active': active_users,
            'admin': admin_users,
            'inactive': total_users - active_users
        }
    except Exception as e:
        logging.error(f"Kullanıcı stats alınamadı: {str(e)}")
        return {}

def get_product_stats():
    """Detaylı ürün istatistikleri"""
    try:
        from models import Urun, UrunGrup, StokHareket
        from sqlalchemy import func
        from datetime import datetime, timedelta
        
        total_products = Urun.query.filter_by(aktif=True).count()
        total_groups = UrunGrup.query.filter_by(aktif=True).count()
        
        # Tüm ürünlerin stok durumunu hesapla
        urunler = Urun.query.filter_by(aktif=True).all()
        
        kritik_count = 0
        dusuk_stok_count = 0
        normal_stok_count = 0
        stoksuz_count = 0
        toplam_stok_degeri = 0
        
        kritik_urunler_list = []
        
        for urun in urunler:
            # Stok hesapla
            giris = db.session.query(func.sum(StokHareket.miktar)).filter(
                StokHareket.urun_id == urun.id,
                StokHareket.hareket_tipi == 'giris'
            ).scalar() or 0
            
            cikis = db.session.query(func.sum(StokHareket.miktar)).filter(
                StokHareket.urun_id == urun.id,
                StokHareket.hareket_tipi == 'cikis'
            ).scalar() or 0
            
            mevcut_stok = giris - cikis
            
            # Stok durumu kategorize et
            if mevcut_stok <= 0:
                stoksuz_count += 1
            elif mevcut_stok <= urun.kritik_stok_seviyesi:
                kritik_count += 1
                kritik_urunler_list.append({
                    'ad': urun.urun_adi,
                    'stok': int(mevcut_stok),
                    'kritik_seviye': urun.kritik_stok_seviyesi
                })
            elif mevcut_stok <= (urun.kritik_stok_seviyesi * 2):
                dusuk_stok_count += 1
            else:
                normal_stok_count += 1
            
            # Toplam stok değeri (varsayılan birim fiyat yoksa 0)
            toplam_stok_degeri += mevcut_stok
        
        # Grup bazlı istatistikler
        grup_stats = []
        gruplar = UrunGrup.query.filter_by(aktif=True).all()
        
        for grup in gruplar:
            grup_urunleri = Urun.query.filter_by(grup_id=grup.id, aktif=True).all()
            grup_urun_sayisi = len(grup_urunleri)
            
            grup_toplam_stok = 0
            grup_kritik = 0
            
            for urun in grup_urunleri:
                giris = db.session.query(func.sum(StokHareket.miktar)).filter(
                    StokHareket.urun_id == urun.id,
                    StokHareket.hareket_tipi == 'giris'
                ).scalar() or 0
                
                cikis = db.session.query(func.sum(StokHareket.miktar)).filter(
                    StokHareket.urun_id == urun.id,
                    StokHareket.hareket_tipi == 'cikis'
                ).scalar() or 0
                
                mevcut_stok = giris - cikis
                grup_toplam_stok += mevcut_stok
                
                if mevcut_stok <= urun.kritik_stok_seviyesi:
                    grup_kritik += 1
            
            grup_stats.append({
                'ad': grup.grup_adi,
                'urun_sayisi': grup_urun_sayisi,
                'toplam_stok': int(grup_toplam_stok),
                'kritik_urun': grup_kritik
            })
        
        # Grup stats'ı stok miktarına göre sırala
        grup_stats.sort(key=lambda x: x['toplam_stok'], reverse=True)
        
        # Son 24 saat stok hareketleri
        yesterday = get_kktc_now() - timedelta(days=1)
        recent_movements = StokHareket.query.filter(
            StokHareket.islem_tarihi >= yesterday
        ).count()
        
        giris_movements = StokHareket.query.filter(
            StokHareket.islem_tarihi >= yesterday,
            StokHareket.hareket_tipi == 'giris'
        ).count()
        
        cikis_movements = StokHareket.query.filter(
            StokHareket.islem_tarihi >= yesterday,
            StokHareket.hareket_tipi == 'cikis'
        ).count()
        
        # En çok hareket gören ürün
        top_product = db.session.query(
            Urun.urun_adi,
            func.count(StokHareket.id).label('hareket_sayisi')
        ).join(
            StokHareket, Urun.id == StokHareket.urun_id
        ).filter(
            StokHareket.islem_tarihi >= yesterday
        ).group_by(
            Urun.id, Urun.urun_adi
        ).order_by(
            func.count(StokHareket.id).desc()
        ).first()
        
        return {
            'total': total_products,
            'groups': total_groups,
            'kritik': kritik_count,
            'dusuk_stok': dusuk_stok_count,
            'normal_stok': normal_stok_count,
            'stoksuz': stoksuz_count,
            'toplam_stok_miktar': int(toplam_stok_degeri),
            'movements_24h': recent_movements,
            'giris_24h': giris_movements,
            'cikis_24h': cikis_movements,
            'top_product': top_product[0] if top_product else 'N/A',
            'top_product_count': top_product[1] if top_product else 0,
            'grup_stats': grup_stats[:5],  # İlk 5 grup
            'kritik_urunler': kritik_urunler_list[:5]  # İlk 5 kritik ürün
        }
    except Exception as e:
        logging.error(f"Ürün stats alınamadı: {str(e)}")
        return {
            'total': 0,
            'groups': 0,
            'kritik': 0,
            'dusuk_stok': 0,
            'normal_stok': 0,
            'stoksuz': 0,
            'toplam_stok_miktar': 0,
            'movements_24h': 0,
            'giris_24h': 0,
            'cikis_24h': 0,
            'top_product': 'N/A',
            'top_product_count': 0,
            'grup_stats': [],
            'kritik_urunler': []
        }

def check_database_health():
    """Database bağlantı kontrolü"""
    try:
        db.session.execute(text('SELECT 1'))
        return {'status': 'healthy', 'message': 'Database bağlantısı OK'}
    except Exception as e:
        return {'status': 'unhealthy', 'message': str(e)}

def check_disk_health():
    """Disk durumu kontrolü"""
    try:
        disk = psutil.disk_usage('/')
        status = 'healthy' if disk.percent < 90 else 'warning'
        return {'status': status, 'percent': disk.percent}
    except Exception as e:
        return {'status': 'error', 'message': str(e)}

def check_memory_health():
    """Bellek durumu kontrolü"""
    try:
        memory = psutil.virtual_memory()
        status = 'healthy' if memory.percent < 90 else 'warning'
        return {'status': status, 'percent': memory.percent}
    except Exception as e:
        return {'status': 'error', 'message': str(e)}

def check_cpu_health():
    """CPU durumu kontrolü"""
    try:
        cpu_percent = psutil.cpu_percent(interval=1)
        status = 'healthy' if cpu_percent < 80 else 'warning'
        return {'status': status, 'percent': cpu_percent}
    except Exception as e:
        return {'status': 'error', 'message': str(e)}


# ============================================
# CACHE MANAGEMENT API ENDPOINTS
# ============================================

@developer_bp.route('/api/cache/stats')
@developer_required
def cache_stats():
    """Cache istatistikleri"""
    try:
        from utils.monitoring.cache_service import CacheService
        
        cache_service = CacheService()
        stats = cache_service.get_cache_stats()
        
        return jsonify({
            'success': True,
            'data': stats
        })
    except Exception as e:
        logging.error(f"Cache stats hatası: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@developer_bp.route('/api/cache/keys')
@developer_required
def cache_keys():
    """Cache anahtarları listesi"""
    try:
        from utils.monitoring.cache_service import CacheService
        
        pattern = request.args.get('pattern', '*')
        limit = int(request.args.get('limit', 1000))
        
        cache_service = CacheService()
        keys = cache_service.get_all_keys(pattern=pattern, limit=limit)
        
        return jsonify({
            'success': True,
            'data': keys,
            'count': len(keys)
        })
    except Exception as e:
        logging.error(f"Cache keys hatası: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@developer_bp.route('/api/cache/key/<path:key>')
@developer_required
def cache_key_details(key):
    """Belirli bir key'in detayları"""
    try:
        from utils.monitoring.cache_service import CacheService
        
        cache_service = CacheService()
        details = cache_service.get_key_details(key)
        
        if details is None:
            return jsonify({
                'success': False,
                'error': 'Key bulunamadı'
            }), 404
        
        return jsonify({
            'success': True,
            'data': details
        })
    except Exception as e:
        logging.error(f"Cache key details hatası: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@developer_bp.route('/api/cache/clear', methods=['POST'])
@developer_required
def cache_clear():
    """Cache temizleme"""
    try:
        from utils.monitoring.cache_service import CacheService
        
        data = request.get_json() or {}
        pattern = data.get('pattern', '*')
        
        cache_service = CacheService()
        result = cache_service.clear_cache(pattern=pattern)
        
        return jsonify(result)
    except Exception as e:
        logging.error(f"Cache clear hatası: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@developer_bp.route('/api/cache/metrics')
@developer_required
def cache_metrics():
    """Cache hit/miss metrikleri"""
    try:
        from utils.monitoring.cache_service import CacheService
        
        cache_service = CacheService()
        metrics = cache_service.get_hit_miss_ratio()
        
        return jsonify({
            'success': True,
            'data': metrics
        })
    except Exception as e:
        logging.error(f"Cache metrics hatası: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@developer_bp.route('/api/cache/key/<path:key>', methods=['DELETE'])
@developer_required
def cache_delete_key(key):
    """Belirli bir key'i sil"""
    try:
        from utils.monitoring.cache_service import CacheService
        
        cache_service = CacheService()
        success = cache_service.delete_key(key)
        
        return jsonify({
            'success': success,
            'message': 'Key silindi' if success else 'Key silinemedi'
        })
    except Exception as e:
        logging.error(f"Cache delete key hatası: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@developer_bp.route('/api/cache/key/<path:key>/ttl', methods=['PUT'])
@developer_required
def cache_set_ttl(key):
    """Key TTL ayarla"""
    try:
        from utils.monitoring.cache_service import CacheService
        
        data = request.get_json() or {}
        ttl = int(data.get('ttl', 3600))
        
        cache_service = CacheService()
        success = cache_service.set_ttl(key, ttl)
        
        return jsonify({
            'success': success,
            'message': f'TTL ayarlandı: {ttl}s' if success else 'TTL ayarlanamadı'
        })
    except Exception as e:
        logging.error(f"Cache set TTL hatası: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


# ============================================
# QUERY ANALYZER API ENDPOINTS
# ============================================

@developer_bp.route('/api/queries/recent')
@developer_required
def queries_recent():
    """Son query'ler"""
    try:
        from utils.monitoring.query_analyzer import QueryAnalyzer
        
        limit = int(request.args.get('limit', 100))
        min_time = request.args.get('min_time', type=float)
        
        analyzer = QueryAnalyzer()
        queries = analyzer.get_recent_queries(
            limit=limit,
            min_execution_time=min_time
        )
        
        return jsonify({
            'success': True,
            'data': queries,
            'count': len(queries)
        })
    except Exception as e:
        logging.error(f"Recent queries hatası: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@developer_bp.route('/api/queries/slow')
@developer_required
def queries_slow():
    """Yavaş query'ler"""
    try:
        from utils.monitoring.query_analyzer import QueryAnalyzer
        
        threshold = float(request.args.get('threshold', 1.0))
        limit = int(request.args.get('limit', 50))
        hours = int(request.args.get('hours', 24))
        
        analyzer = QueryAnalyzer()
        queries = analyzer.get_slow_queries(
            threshold=threshold,
            limit=limit,
            hours=hours
        )
        
        return jsonify({
            'success': True,
            'data': queries,
            'count': len(queries)
        })
    except Exception as e:
        logging.error(f"Slow queries hatası: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@developer_bp.route('/api/queries/stats')
@developer_required
def queries_stats():
    """Query istatistikleri"""
    try:
        from utils.monitoring.query_analyzer import QueryAnalyzer
        
        hours = int(request.args.get('hours', 24))
        
        analyzer = QueryAnalyzer()
        stats = analyzer.get_query_stats(hours=hours)
        
        return jsonify({
            'success': True,
            'data': stats
        })
    except Exception as e:
        logging.error(f"Query stats hatası: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@developer_bp.route('/api/queries/explain', methods=['POST'])
@developer_required
def queries_explain():
    """Query EXPLAIN"""
    try:
        from utils.monitoring.query_analyzer import QueryAnalyzer
        
        data = request.get_json() or {}
        query_text = data.get('query')
        
        if not query_text:
            return jsonify({
                'success': False,
                'error': 'Query text gerekli'
            }), 400
        
        analyzer = QueryAnalyzer()
        result = analyzer.explain_query(query_text)
        
        return jsonify(result)
    except Exception as e:
        logging.error(f"Query explain hatası: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@developer_bp.route('/api/queries/optimize/<int:query_id>')
@developer_required
def queries_optimize(query_id):
    """Query optimizasyon önerileri"""
    try:
        from utils.monitoring.query_analyzer import QueryAnalyzer
        
        analyzer = QueryAnalyzer()
        suggestions = analyzer.get_optimization_suggestions(query_id)
        
        return jsonify(suggestions)
    except Exception as e:
        logging.error(f"Query optimize hatası: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@developer_bp.route('/api/queries/<int:query_id>')
@developer_required
def queries_detail(query_id):
    """Query detayı"""
    try:
        from utils.monitoring.query_analyzer import QueryAnalyzer
        
        analyzer = QueryAnalyzer()
        query = analyzer.get_query_by_id(query_id)
        
        if query is None:
            return jsonify({
                'success': False,
                'error': 'Query bulunamadı'
            }), 404
        
        return jsonify({
            'success': True,
            'data': query
        })
    except Exception as e:
        logging.error(f"Query detail hatası: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


# ============================================
# API METRICS ENDPOINTS
# ============================================

@developer_bp.route('/api/metrics/endpoints')
@developer_required
def metrics_endpoints():
    """Tüm endpoint metrikleri"""
    try:
        from utils.monitoring.api_metrics import APIMetrics
        
        sort_by = request.args.get('sort_by', 'avg_time')
        
        stats = APIMetrics.get_endpoint_stats(sort_by=sort_by)
        
        return jsonify({
            'success': True,
            'data': stats,
            'count': len(stats)
        })
    except Exception as e:
        logging.error(f"Metrics endpoints hatası: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@developer_bp.route('/api/metrics/endpoint/<path:endpoint_name>')
@developer_required
def metrics_endpoint_detail(endpoint_name):
    """Belirli bir endpoint'in detaylı metrikleri"""
    try:
        from utils.monitoring.api_metrics import APIMetrics
        
        details = APIMetrics.get_endpoint_details(endpoint_name)
        
        if details is None:
            return jsonify({
                'success': False,
                'error': 'Endpoint bulunamadı'
            }), 404
        
        return jsonify({
            'success': True,
            'data': details
        })
    except Exception as e:
        logging.error(f"Metrics endpoint detail hatası: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@developer_bp.route('/api/metrics/errors')
@developer_required
def metrics_errors():
    """Hata oranları"""
    try:
        from utils.monitoring.api_metrics import APIMetrics
        
        endpoint = request.args.get('endpoint')
        
        error_stats = APIMetrics.get_error_rate(endpoint=endpoint)
        
        return jsonify({
            'success': True,
            'data': error_stats
        })
    except Exception as e:
        logging.error(f"Metrics errors hatası: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@developer_bp.route('/api/metrics/performance')
@developer_required
def metrics_performance():
    """Genel performans özeti"""
    try:
        from utils.monitoring.api_metrics import APIMetrics
        
        summary = APIMetrics.get_performance_summary()
        
        return jsonify({
            'success': True,
            'data': summary
        })
    except Exception as e:
        logging.error(f"Metrics performance hatası: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@developer_bp.route('/api/metrics/reset', methods=['POST'])
@developer_required
def metrics_reset():
    """Metrikleri sıfırla"""
    try:
        from utils.monitoring.api_metrics import APIMetrics
        
        data = request.get_json() or {}
        endpoint = data.get('endpoint')
        
        success = APIMetrics.reset_metrics(endpoint=endpoint)
        
        return jsonify({
            'success': success,
            'message': f'Metrics sıfırlandı: {endpoint or "tümü"}'
        })
    except Exception as e:
        logging.error(f"Metrics reset hatası: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


# ============================================
# BACKGROUND JOB MONITORING ENDPOINTS
# ============================================

@developer_bp.route('/api/jobs/active')
@developer_required
def jobs_active():
    """Aktif job'lar"""
    try:
        from utils.monitoring.job_monitor import JobMonitor
        
        monitor = JobMonitor()
        jobs = monitor.get_active_jobs()
        
        return jsonify({
            'success': True,
            'data': jobs,
            'count': len(jobs)
        })
    except Exception as e:
        logging.error(f"Active jobs hatası: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@developer_bp.route('/api/jobs/pending')
@developer_required
def jobs_pending():
    """Bekleyen job'lar"""
    try:
        from utils.monitoring.job_monitor import JobMonitor
        
        monitor = JobMonitor()
        jobs = monitor.get_pending_jobs()
        
        return jsonify({
            'success': True,
            'data': jobs,
            'count': len(jobs)
        })
    except Exception as e:
        logging.error(f"Pending jobs hatası: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@developer_bp.route('/api/jobs/completed')
@developer_required
def jobs_completed():
    """Tamamlanan job'lar"""
    try:
        from utils.monitoring.job_monitor import JobMonitor
        
        limit = int(request.args.get('limit', 50))
        
        monitor = JobMonitor()
        jobs = monitor.get_completed_jobs(limit=limit)
        
        return jsonify({
            'success': True,
            'data': jobs,
            'count': len(jobs)
        })
    except Exception as e:
        logging.error(f"Completed jobs hatası: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@developer_bp.route('/api/jobs/failed')
@developer_required
def jobs_failed():
    """Başarısız job'lar"""
    try:
        from utils.monitoring.job_monitor import JobMonitor
        
        limit = int(request.args.get('limit', 50))
        
        monitor = JobMonitor()
        jobs = monitor.get_failed_jobs(limit=limit)
        
        return jsonify({
            'success': True,
            'data': jobs,
            'count': len(jobs)
        })
    except Exception as e:
        logging.error(f"Failed jobs hatası: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@developer_bp.route('/api/jobs/<job_id>')
@developer_required
def jobs_detail(job_id):
    """Job detayı"""
    try:
        from utils.monitoring.job_monitor import JobMonitor
        
        monitor = JobMonitor()
        job = monitor.get_job_details(job_id)
        
        if job is None:
            return jsonify({
                'success': False,
                'error': 'Job bulunamadı'
            }), 404
        
        return jsonify({
            'success': True,
            'data': job
        })
    except Exception as e:
        logging.error(f"Job detail hatası: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@developer_bp.route('/api/jobs/<job_id>/retry', methods=['POST'])
@developer_required
def jobs_retry(job_id):
    """Job'ı yeniden çalıştır"""
    try:
        from utils.monitoring.job_monitor import JobMonitor
        
        monitor = JobMonitor()
        new_job_id = monitor.retry_job(job_id)
        
        if new_job_id is None:
            return jsonify({
                'success': False,
                'error': 'Job retry edilemedi'
            }), 400
        
        return jsonify({
            'success': True,
            'new_job_id': new_job_id,
            'message': 'Job yeniden başlatıldı'
        })
    except Exception as e:
        logging.error(f"Job retry hatası: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@developer_bp.route('/api/jobs/<job_id>/cancel', methods=['DELETE'])
@developer_required
def jobs_cancel(job_id):
    """Job'ı iptal et"""
    try:
        from utils.monitoring.job_monitor import JobMonitor
        
        monitor = JobMonitor()
        success = monitor.cancel_job(job_id)
        
        if not success:
            return jsonify({
                'success': False,
                'error': 'Job iptal edilemedi'
            }), 400
        
        return jsonify({
            'success': True,
            'message': 'Job iptal edildi'
        })
    except Exception as e:
        logging.error(f"Job cancel hatası: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@developer_bp.route('/api/jobs/stats')
@developer_required
def jobs_stats():
    """Job istatistikleri"""
    try:
        from utils.monitoring.job_monitor import JobMonitor
        
        hours = int(request.args.get('hours', 24))
        
        monitor = JobMonitor()
        stats = monitor.get_job_stats(hours=hours)
        
        return jsonify({
            'success': True,
            'data': stats
        })
    except Exception as e:
        logging.error(f"Job stats hatası: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


# ============================================
# REDIS MONITORING ENDPOINTS
# ============================================

@developer_bp.route('/api/redis/status')
@developer_required
def redis_status():
    """Redis durumu"""
    try:
        from utils.monitoring.redis_monitor import RedisMonitor
        
        monitor = RedisMonitor()
        info = monitor.get_redis_info()
        
        return jsonify({
            'success': True,
            'data': info
        })
    except Exception as e:
        logging.error(f"Redis status hatası: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@developer_bp.route('/api/redis/memory')
@developer_required
def redis_memory():
    """Redis memory kullanımı"""
    try:
        from utils.monitoring.redis_monitor import RedisMonitor
        
        monitor = RedisMonitor()
        stats = monitor.get_memory_stats()
        
        return jsonify({
            'success': True,
            'data': stats
        })
    except Exception as e:
        logging.error(f"Redis memory hatası: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@developer_bp.route('/api/redis/keys')
@developer_required
def redis_keys():
    """Redis key istatistikleri"""
    try:
        from utils.monitoring.redis_monitor import RedisMonitor
        
        monitor = RedisMonitor()
        stats = monitor.get_key_stats()
        
        return jsonify({
            'success': True,
            'data': stats
        })
    except Exception as e:
        logging.error(f"Redis keys hatası: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@developer_bp.route('/api/redis/clients')
@developer_required
def redis_clients():
    """Bağlı Redis client'ları"""
    try:
        from utils.monitoring.redis_monitor import RedisMonitor
        
        monitor = RedisMonitor()
        clients = monitor.get_client_list()
        
        return jsonify({
            'success': True,
            'data': clients,
            'count': len(clients)
        })
    except Exception as e:
        logging.error(f"Redis clients hatası: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@developer_bp.route('/api/redis/slowlog')
@developer_required
def redis_slowlog():
    """Redis yavaş komutlar"""
    try:
        from utils.monitoring.redis_monitor import RedisMonitor
        
        count = int(request.args.get('count', 10))
        
        monitor = RedisMonitor()
        slowlog = monitor.get_slowlog(count=count)
        
        return jsonify({
            'success': True,
            'data': slowlog,
            'count': len(slowlog)
        })
    except Exception as e:
        logging.error(f"Redis slowlog hatası: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@developer_bp.route('/api/redis/summary')
@developer_required
def redis_summary():
    """Redis özet istatistikler"""
    try:
        from utils.monitoring.redis_monitor import RedisMonitor
        
        monitor = RedisMonitor()
        summary = monitor.get_stats_summary()
        
        return jsonify({
            'success': True,
            'data': summary
        })
    except Exception as e:
        logging.error(f"Redis summary hatası: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


# ============================================
# ML MODEL METRICS ENDPOINTS
# ============================================

@developer_bp.route('/api/ml/models')
@developer_required
def ml_models():
    """ML model listesi"""
    try:
        from utils.monitoring.ml_metrics import MLMetrics
        
        ml_metrics = MLMetrics()
        models = ml_metrics.get_model_list()
        
        return jsonify({
            'success': True,
            'data': models,
            'count': len(models)
        })
    except Exception as e:
        logging.error(f"ML models hatası: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@developer_bp.route('/api/ml/model/<model_name>/metrics')
@developer_required
def ml_model_metrics(model_name):
    """Model metrikleri"""
    try:
        from utils.monitoring.ml_metrics import MLMetrics
        
        ml_metrics = MLMetrics()
        metrics = ml_metrics.get_model_metrics(model_name)
        
        if metrics is None:
            return jsonify({
                'success': False,
                'error': 'Model bulunamadı'
            }), 404
        
        return jsonify({
            'success': True,
            'data': metrics
        })
    except Exception as e:
        logging.error(f"ML model metrics hatası: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@developer_bp.route('/api/ml/model/<model_name>/predictions')
@developer_required
def ml_model_predictions(model_name):
    """Model tahmin istatistikleri"""
    try:
        from utils.monitoring.ml_metrics import MLMetrics
        
        hours = int(request.args.get('hours', 24))
        
        ml_metrics = MLMetrics()
        stats = ml_metrics.get_prediction_stats(model_name, hours=hours)
        
        return jsonify({
            'success': True,
            'data': stats
        })
    except Exception as e:
        logging.error(f"ML predictions hatası: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@developer_bp.route('/api/ml/model/<model_name>/history')
@developer_required
def ml_model_history(model_name):
    """Model performans geçmişi"""
    try:
        from utils.monitoring.ml_metrics import MLMetrics
        
        days = int(request.args.get('days', 30))
        
        ml_metrics = MLMetrics()
        history = ml_metrics.get_model_performance_history(model_name, days=days)
        
        return jsonify({
            'success': True,
            'data': history,
            'count': len(history)
        })
    except Exception as e:
        logging.error(f"ML history hatası: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@developer_bp.route('/api/ml/model/<model_name>/features')
@developer_required
def ml_model_features(model_name):
    """Model feature importance"""
    try:
        from utils.monitoring.ml_metrics import MLMetrics
        
        ml_metrics = MLMetrics()
        features = ml_metrics.get_feature_importance(model_name)
        
        return jsonify({
            'success': True,
            'data': features
        })
    except Exception as e:
        logging.error(f"ML features hatası: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@developer_bp.route('/api/ml/alerts')
@developer_required
def ml_alerts():
    """ML alert'leri"""
    try:
        from utils.monitoring.ml_metrics import MLMetrics
        
        limit = int(request.args.get('limit', 50))
        unread_only = request.args.get('unread_only', 'false').lower() == 'true'
        
        ml_metrics = MLMetrics()
        alerts = ml_metrics.get_ml_alerts(limit=limit, unread_only=unread_only)
        
        return jsonify({
            'success': True,
            'data': alerts,
            'count': len(alerts)
        })
    except Exception as e:
        logging.error(f"ML alerts hatası: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@developer_bp.route('/api/ml/summary')
@developer_required
def ml_summary():
    """ML sistem özeti"""
    try:
        from utils.monitoring.ml_metrics import MLMetrics
        
        ml_metrics = MLMetrics()
        summary = ml_metrics.get_ml_summary()
        
        return jsonify({
            'success': True,
            'data': summary
        })
    except Exception as e:
        logging.error(f"ML summary hatası: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@developer_bp.route('/api/ml/alert/<int:alert_id>/read', methods=['PUT'])
@developer_required
def ml_alert_read(alert_id):
    """Alert'i okundu işaretle"""
    try:
        from utils.monitoring.ml_metrics import MLMetrics
        
        ml_metrics = MLMetrics()
        success = ml_metrics.mark_alert_read(alert_id)
        
        if not success:
            return jsonify({
                'success': False,
                'error': 'Alert bulunamadı'
            }), 404
        
        return jsonify({
            'success': True,
            'message': 'Alert okundu olarak işaretlendi'
        })
    except Exception as e:
        logging.error(f"ML alert read hatası: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


# ============================================
# LOG VIEWER ENDPOINTS
# ============================================

@developer_bp.route('/api/logs/tail')
@developer_required
def logs_tail():
    """Son log satırları"""
    try:
        from utils.monitoring.log_viewer import LogViewer
        
        lines = int(request.args.get('lines', 100))
        
        viewer = LogViewer()
        logs = viewer.tail_logs(lines=lines)
        
        return jsonify({
            'success': True,
            'data': logs,
            'count': len(logs)
        })
    except Exception as e:
        logging.error(f"Logs tail hatası: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@developer_bp.route('/api/logs/filter')
@developer_required
def logs_filter():
    """Filtrelenmiş loglar"""
    try:
        from utils.monitoring.log_viewer import LogViewer
        
        level = request.args.get('level')
        search = request.args.get('search')
        lines = int(request.args.get('lines', 100))
        
        viewer = LogViewer()
        logs = viewer.filter_logs(level=level, search=search, lines=lines)
        
        return jsonify({
            'success': True,
            'data': logs,
            'count': len(logs)
        })
    except Exception as e:
        logging.error(f"Logs filter hatası: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@developer_bp.route('/api/logs/stats')
@developer_required
def logs_stats():
    """Log istatistikleri"""
    try:
        from utils.monitoring.log_viewer import LogViewer
        
        lines = int(request.args.get('lines', 1000))
        
        viewer = LogViewer()
        stats = viewer.get_log_stats(lines=lines)
        
        return jsonify({
            'success': True,
            'data': stats
        })
    except Exception as e:
        logging.error(f"Logs stats hatası: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@developer_bp.route('/api/logs/errors')
@developer_required
def logs_errors():
    """Son hatalar"""
    try:
        from utils.monitoring.log_viewer import LogViewer
        
        count = int(request.args.get('count', 50))
        
        viewer = LogViewer()
        errors = viewer.get_recent_errors(count=count)
        
        return jsonify({
            'success': True,
            'data': errors,
            'count': len(errors)
        })
    except Exception as e:
        logging.error(f"Logs errors hatası: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@developer_bp.route('/api/logs/search')
@developer_required
def logs_search():
    """Log'larda arama"""
    try:
        from utils.monitoring.log_viewer import LogViewer
        
        pattern = request.args.get('pattern', '')
        lines = int(request.args.get('lines', 1000))
        case_sensitive = request.args.get('case_sensitive', 'false').lower() == 'true'
        
        if not pattern:
            return jsonify({
                'success': False,
                'error': 'Pattern gerekli'
            }), 400
        
        viewer = LogViewer()
        matches = viewer.search_logs(
            pattern=pattern,
            lines=lines,
            case_sensitive=case_sensitive
        )
        
        return jsonify({
            'success': True,
            'data': matches,
            'count': len(matches)
        })
    except Exception as e:
        logging.error(f"Logs search hatası: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


# ============================================
# BACKUP/RESTORE ENDPOINTS
# ============================================

@developer_bp.route('/api/backup/create', methods=['POST'])
@developer_required
def backup_create():
    """Yeni backup oluştur"""
    try:
        from utils.monitoring.backup_manager import BackupManager
        
        data = request.get_json() or {}
        description = data.get('description')
        
        manager = BackupManager()
        result = manager.create_backup(description=description)
        
        return jsonify(result)
    except Exception as e:
        logging.error(f"Backup create hatası: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@developer_bp.route('/api/backup/list')
@developer_required
def backup_list():
    """Backup listesi"""
    try:
        from utils.monitoring.backup_manager import BackupManager
        
        manager = BackupManager()
        backups = manager.list_backups()
        
        return jsonify({
            'success': True,
            'data': backups,
            'count': len(backups)
        })
    except Exception as e:
        logging.error(f"Backup list hatası: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@developer_bp.route('/api/backup/<backup_id>')
@developer_required
def backup_details(backup_id):
    """Backup detayları"""
    try:
        from utils.monitoring.backup_manager import BackupManager
        
        manager = BackupManager()
        details = manager.get_backup_details(backup_id)
        
        if details is None:
            return jsonify({
                'success': False,
                'error': 'Backup bulunamadı'
            }), 404
        
        return jsonify({
            'success': True,
            'data': details
        })
    except Exception as e:
        logging.error(f"Backup details hatası: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@developer_bp.route('/api/backup/<backup_id>/restore', methods=['POST'])
@developer_required
def backup_restore(backup_id):
    """Backup restore et"""
    try:
        from utils.monitoring.backup_manager import BackupManager
        
        manager = BackupManager()
        result = manager.restore_backup(backup_id)
        
        return jsonify(result)
    except Exception as e:
        logging.error(f"Backup restore hatası: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@developer_bp.route('/api/backup/<backup_id>', methods=['DELETE'])
@developer_required
def backup_delete(backup_id):
    """Backup sil"""
    try:
        from utils.monitoring.backup_manager import BackupManager
        
        manager = BackupManager()
        success = manager.delete_backup(backup_id)
        
        if not success:
            return jsonify({
                'success': False,
                'error': 'Backup silinemedi'
            }), 400
        
        return jsonify({
            'success': True,
            'message': 'Backup silindi'
        })
    except Exception as e:
        logging.error(f"Backup delete hatası: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


# ============================================
# CONFIG EDITOR ENDPOINTS
# ============================================

@developer_bp.route('/api/config/files')
@developer_required
def config_files():
    """Config dosya listesi"""
    try:
        from utils.monitoring.config_editor import ConfigEditor
        
        editor = ConfigEditor()
        files = editor.list_config_files()
        
        return jsonify({
            'success': True,
            'data': files,
            'count': len(files)
        })
    except Exception as e:
        logging.error(f"Config files hatası: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@developer_bp.route('/api/config/file/<filename>')
@developer_required
def config_file_content(filename):
    """Config dosya içeriği"""
    try:
        from utils.monitoring.config_editor import ConfigEditor
        
        editor = ConfigEditor()
        content = editor.get_config_content(filename)
        
        if content is None:
            return jsonify({
                'success': False,
                'error': 'Dosya bulunamadı veya izin verilmedi'
            }), 404
        
        return jsonify({
            'success': True,
            'data': {
                'filename': filename,
                'content': content
            }
        })
    except Exception as e:
        logging.error(f"Config file content hatası: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@developer_bp.route('/api/config/validate', methods=['POST'])
@developer_required
def config_validate():
    """Config validasyonu"""
    try:
        from utils.monitoring.config_editor import ConfigEditor
        
        data = request.get_json() or {}
        filename = data.get('filename')
        content = data.get('content')
        
        if not filename or content is None:
            return jsonify({
                'success': False,
                'error': 'Filename ve content gerekli'
            }), 400
        
        editor = ConfigEditor()
        validation = editor.validate_config(filename, content)
        
        return jsonify({
            'success': True,
            'data': validation
        })
    except Exception as e:
        logging.error(f"Config validate hatası: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@developer_bp.route('/api/config/file/<filename>', methods=['PUT'])
@developer_required
def config_file_save(filename):
    """Config dosyasını kaydet"""
    try:
        from utils.monitoring.config_editor import ConfigEditor
        
        data = request.get_json() or {}
        content = data.get('content')
        change_reason = data.get('change_reason')
        
        if content is None:
            return jsonify({
                'success': False,
                'error': 'Content gerekli'
            }), 400
        
        editor = ConfigEditor()
        result = editor.save_config(
            filename=filename,
            content=content,
            change_reason=change_reason
        )
        
        return jsonify(result)
    except Exception as e:
        logging.error(f"Config file save hatası: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@developer_bp.route('/api/config/file/<filename>/history')
@developer_required
def config_file_history(filename):
    """Config değişiklik geçmişi"""
    try:
        from utils.monitoring.config_editor import ConfigEditor
        
        limit = int(request.args.get('limit', 10))
        
        editor = ConfigEditor()
        history = editor.get_config_history(filename, limit=limit)
        
        return jsonify({
            'success': True,
            'data': history,
            'count': len(history)
        })
    except Exception as e:
        logging.error(f"Config history hatası: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@developer_bp.route('/api/config/file/<filename>/rollback', methods=['POST'])
@developer_required
def config_file_rollback(filename):
    """Config rollback"""
    try:
        from utils.monitoring.config_editor import ConfigEditor
        
        data = request.get_json() or {}
        version = data.get('version')
        
        if not version:
            return jsonify({
                'success': False,
                'error': 'Version gerekli'
            }), 400
        
        editor = ConfigEditor()
        result = editor.rollback_config(filename, version)
        
        return jsonify(result)
    except Exception as e:
        logging.error(f"Config rollback hatası: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


# ============================================
# PERFORMANCE PROFILER ENDPOINTS
# ============================================

@developer_bp.route('/api/profiler/start', methods=['POST'])
@developer_required
def profiler_start():
    """Profiling başlat"""
    try:
        from utils.monitoring.profiler import PerformanceProfiler
        
        data = request.get_json() or {}
        duration = int(data.get('duration', 60))
        
        profile_id = PerformanceProfiler.start_profiling(duration=duration)
        
        if not profile_id:
            return jsonify({
                'success': False,
                'error': 'Profiling başlatılamadı'
            }), 500
        
        return jsonify({
            'success': True,
            'profile_id': profile_id,
            'duration': duration
        })
    except Exception as e:
        logging.error(f"Profiler start hatası: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@developer_bp.route('/api/profiler/stop', methods=['POST'])
@developer_required
def profiler_stop():
    """Profiling durdur"""
    try:
        from utils.monitoring.profiler import PerformanceProfiler
        
        data = request.get_json() or {}
        profile_id = data.get('profile_id')
        
        if not profile_id:
            return jsonify({
                'success': False,
                'error': 'Profile ID gerekli'
            }), 400
        
        result = PerformanceProfiler.stop_profiling(profile_id)
        
        return jsonify(result)
    except Exception as e:
        logging.error(f"Profiler stop hatası: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@developer_bp.route('/api/profiler/<profile_id>/results')
@developer_required
def profiler_results(profile_id):
    """Profile sonuçları"""
    try:
        from utils.monitoring.profiler import PerformanceProfiler
        
        results = PerformanceProfiler.get_profile_results(profile_id)
        
        if results is None:
            return jsonify({
                'success': False,
                'error': 'Profile bulunamadı'
            }), 404
        
        return jsonify({
            'success': True,
            'data': results
        })
    except Exception as e:
        logging.error(f"Profiler results hatası: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@developer_bp.route('/api/profiler/<profile_id>/cpu')
@developer_required
def profiler_cpu_hotspots(profile_id):
    """CPU hotspot'ları"""
    try:
        from utils.monitoring.profiler import PerformanceProfiler
        
        hotspots = PerformanceProfiler.get_cpu_hotspots(profile_id)
        
        return jsonify({
            'success': True,
            'data': hotspots,
            'count': len(hotspots)
        })
    except Exception as e:
        logging.error(f"Profiler CPU hotspots hatası: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@developer_bp.route('/api/profiler/<profile_id>/memory')
@developer_required
def profiler_memory(profile_id):
    """Memory allocations"""
    try:
        from utils.monitoring.profiler import PerformanceProfiler
        
        memory = PerformanceProfiler.get_memory_allocations()
        
        return jsonify({
            'success': True,
            'data': memory
        })
    except Exception as e:
        logging.error(f"Profiler memory hatası: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@developer_bp.route('/api/profiler/<profile_id>/export')
@developer_required
def profiler_export(profile_id):
    """Profile export"""
    try:
        from utils.monitoring.profiler import PerformanceProfiler
        
        format = request.args.get('format', 'json')
        
        data = PerformanceProfiler.export_profile(profile_id, format=format)
        
        if data is None:
            return jsonify({
                'success': False,
                'error': 'Profile bulunamadı'
            }), 404
        
        return jsonify({
            'success': True,
            'data': data
        })
    except Exception as e:
        logging.error(f"Profiler export hatası: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@developer_bp.route('/api/profiler/list')
@developer_required
def profiler_list():
    """Aktif profile'lar"""
    try:
        from utils.monitoring.profiler import PerformanceProfiler
        
        profiles = PerformanceProfiler.list_active_profiles()
        
        return jsonify({
            'success': True,
            'data': profiles,
            'count': len(profiles)
        })
    except Exception as e:
        logging.error(f"Profiler list hatası: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
