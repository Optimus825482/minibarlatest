from functools import wraps
from flask import session, redirect, url_for, flash
from sqlalchemy.exc import OperationalError, TimeoutError, ProgrammingError
import time
import logging

logger = logging.getLogger(__name__)

# Setup kontrolü için in-memory cache (her worker için)
_setup_cache = {'value': None, 'timestamp': 0, 'table_missing': False}
SETUP_CACHE_TTL = 30  # 30 saniye cache

def db_query_with_retry(query_func, max_retries=3, retry_delay=1):
    """
    Database query'lerini retry mekanizması ile çalıştır
    Railway timeout sorunlarını çözer
    ProgrammingError (tablo yok vb.) retry YAPMAZ - anlamsız
    """
    for attempt in range(max_retries):
        try:
            return query_func()
        except ProgrammingError as e:
            # Tablo yok, kolon yok gibi hatalar retry ile düzelmez
            logger.error(f"❌ DB Schema hatası (retry yapılmıyor): {str(e)[:200]}")
            raise
        except (OperationalError, TimeoutError) as e:
            logger.warning(f"⚠️ DB Query timeout (Deneme {attempt + 1}/{max_retries}): {str(e)[:200]}")
            if attempt < max_retries - 1:
                time.sleep(retry_delay)
                retry_delay *= 1.5  # Exponential backoff
            else:
                logger.error(f"❌ DB Query {max_retries} denemeden sonra başarısız!")
                raise
        except Exception as e:
            logger.error(f"❌ DB Query beklenmeyen hata: {str(e)[:200]}")
            raise
    return None

def login_required(f):
    """Giriş yapmış kullanıcı kontrolü"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        from flask import request, jsonify
        
        if 'kullanici_id' not in session:
            # API isteği mi kontrol et
            if request.path.startswith('/api/') or request.is_json:
                return jsonify({'success': False, 'error': 'Giriş yapmalısınız'}), 401
            flash('Bu sayfaya erişmek için giriş yapmalısınız.', 'warning')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function


def role_required(*allowed_roles):
    """Belirli rollere sahip kullanıcı kontrolü
    
    Kullanım:
        @role_required('admin')  # Tek rol
        @role_required('admin', 'sistem_yoneticisi')  # Çoklu rol
        @role_required(['admin', 'sistem_yoneticisi'])  # Liste olarak da olabilir
    """
    # Eğer tek parametre ve liste/tuple ise, onu düzleştir
    if len(allowed_roles) == 1 and isinstance(allowed_roles[0], (list, tuple)):
        allowed_roles = allowed_roles[0]
    
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            from flask import request, jsonify
            
            if 'kullanici_id' not in session:
                # API isteği mi kontrol et
                if request.path.startswith('/api/') or request.is_json:
                    return jsonify({'success': False, 'error': 'Giriş yapmalısınız'}), 401
                flash('Bu sayfaya erişmek için giriş yapmalısınız.', 'warning')
                return redirect(url_for('login'))
            
            # Rol kontrolü - superadmin her yere erişebilir
            user_rol = session.get('rol', '')
            if user_rol == 'superadmin':
                return f(*args, **kwargs)
            
            if 'rol' not in session or user_rol not in allowed_roles:
                # API isteği mi kontrol et
                if request.path.startswith('/api/') or request.is_json:
                    # Debug için ekstra bilgi
                    error_msg = f"Bu işlem için yetkiniz yok (Gerekli: {', '.join(allowed_roles)}, Mevcut: {session.get('rol', 'Yok')})"
                    return jsonify({'success': False, 'error': error_msg}), 403
                flash('Bu sayfaya erişim yetkiniz yok.', 'danger')
                return redirect(url_for('dashboard'))
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator


def setup_required(f):
    """Setup tamamlanmamışsa setup sayfasına yönlendir.
    In-memory cache ile DB yükünü minimize eder."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        import time as _time
        global _setup_cache
        
        now = _time.time()
        
        # Tablo yoksa ve daha önce tespit edildiyse, DB'ye hiç gitme
        if _setup_cache['table_missing'] and (now - _setup_cache['timestamp']) < SETUP_CACHE_TTL:
            # Tablo yok = setup yapılmamış demek, ama login'e erişimi engelleme
            return f(*args, **kwargs)
        
        # Cache geçerliyse DB'ye gitme
        if _setup_cache['value'] is not None and (now - _setup_cache['timestamp']) < SETUP_CACHE_TTL:
            if _setup_cache['value'] != '1':
                return redirect(url_for('setup'))
            return f(*args, **kwargs)
        
        from models import SistemAyar
        
        try:
            setup_tamamlandi = db_query_with_retry(
                lambda: SistemAyar.query.filter_by(anahtar='setup_tamamlandi').first()
            )
            
            # Cache'i güncelle
            _setup_cache['value'] = setup_tamamlandi.deger if setup_tamamlandi else None
            _setup_cache['timestamp'] = now
            _setup_cache['table_missing'] = False
            
            if not setup_tamamlandi or setup_tamamlandi.deger != '1':
                return redirect(url_for('setup'))
        except ProgrammingError:
            # Tablo yok - cache'le ve bir daha sorma (TTL süresince)
            _setup_cache['table_missing'] = True
            _setup_cache['timestamp'] = now
            logger.warning("⚠️ sistem_ayarlari tablosu bulunamadı - setup_required atlanıyor")
        except Exception as e:
            logger.error(f"❌ Setup kontrolü başarısız: {str(e)[:200]}")
            pass
        
        return f(*args, **kwargs)
    return decorated_function


def setup_not_completed(f):
    """Setup tamamlandıysa ana sayfaya yönlendir"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        import time as _time
        global _setup_cache
        
        now = _time.time()
        
        # Tablo yoksa setup sayfasına devam et
        if _setup_cache['table_missing'] and (now - _setup_cache['timestamp']) < SETUP_CACHE_TTL:
            return f(*args, **kwargs)
        
        # Cache geçerliyse DB'ye gitme
        if _setup_cache['value'] is not None and (now - _setup_cache['timestamp']) < SETUP_CACHE_TTL:
            if _setup_cache['value'] == '1':
                flash('Setup zaten tamamlanmış.', 'info')
                return redirect(url_for('login'))
            return f(*args, **kwargs)
        
        from models import SistemAyar
        
        try:
            setup_tamamlandi = db_query_with_retry(
                lambda: SistemAyar.query.filter_by(anahtar='setup_tamamlandi').first()
            )
            
            # Cache'i güncelle
            _setup_cache['value'] = setup_tamamlandi.deger if setup_tamamlandi else None
            _setup_cache['timestamp'] = now
            _setup_cache['table_missing'] = False
            
            if setup_tamamlandi and setup_tamamlandi.deger == '1':
                flash('Setup zaten tamamlanmış.', 'info')
                return redirect(url_for('login'))
        except ProgrammingError:
            _setup_cache['table_missing'] = True
            _setup_cache['timestamp'] = now
            logger.warning("⚠️ sistem_ayarlari tablosu bulunamadı - setup_not_completed atlanıyor")
        except Exception as e:
            logger.error(f"❌ Setup kontrolü başarısız: {str(e)[:200]}")
            pass
        
        return f(*args, **kwargs)
    return decorated_function



def otel_erisim_gerekli(f):
    """
    Otel erişim kontrolü decorator'u
    Kullanıcının belirli bir otele erişimi olup olmadığını kontrol eder
    
    Kullanım:
        @otel_erisim_gerekli
        def my_route(otel_id):
            # otel_id parametresi veya request.args'dan alınır
            pass
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        from flask import request, jsonify, abort
        from utils.authorization import otel_erisim_kontrol
        
        # Kullanıcı bilgilerini al
        kullanici_id = session.get('kullanici_id')
        rol = session.get('kullanici_rol')
        
        if not kullanici_id or not rol:
            if request.path.startswith('/api/') or request.is_json:
                return jsonify({'success': False, 'error': 'Giriş yapmalısınız'}), 401
            flash('Bu sayfaya erişmek için giriş yapmalısınız.', 'warning')
            return redirect(url_for('login'))
        
        # Admin ve sistem yöneticisi tüm otellere erişebilir
        if rol in ['superadmin', 'admin', 'sistem_yoneticisi']:
            return f(*args, **kwargs)
        
        # Otel ID'yi al (kwargs, args veya request.args'dan)
        otel_id = kwargs.get('otel_id') or request.args.get('otel_id') or request.form.get('otel_id')
        
        # Otel ID yoksa devam et (bazı route'lar için gerekli olmayabilir)
        if not otel_id:
            return f(*args, **kwargs)
        
        # Integer'a çevir
        try:
            otel_id = int(otel_id)
        except (ValueError, TypeError):
            if request.path.startswith('/api/') or request.is_json:
                return jsonify({'success': False, 'error': 'Geçersiz otel ID'}), 400
            flash('Geçersiz otel ID.', 'danger')
            return redirect(url_for('dashboard'))
        
        # Erişim kontrolü
        if not otel_erisim_kontrol(kullanici_id, otel_id, rol):
            if request.path.startswith('/api/') or request.is_json:
                return jsonify({'success': False, 'error': 'Bu otele erişim yetkiniz yok'}), 403
            flash('Bu otele erişim yetkiniz yok.', 'danger')
            return redirect(url_for('dashboard'))
        
        return f(*args, **kwargs)
    return decorated_function



# İkinci otel_erisim_gerekli tanımı kaldırıldı - duplicate temizliği (29.12.2025)
