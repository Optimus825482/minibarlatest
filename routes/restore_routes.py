"""
Backup Restore Routes
Yedek yükleme ve geri yükleme sayfası
"""

from flask import Blueprint, render_template, request, jsonify, session
from werkzeug.utils import secure_filename
from sqlalchemy import create_engine, text, inspect, MetaData
from models import db
import os
import re
import tempfile

restore_bp = Blueprint('restore', __name__)

ALLOWED_EXTENSIONS = {'sql'}
UPLOAD_FOLDER = 'uploads/backups'
MAX_FILE_SIZE = 100 * 1024 * 1024  # 100MB

# Upload klasörünü oluştur
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def parse_sql_backup(filepath):
    """SQL backup dosyasını parse et ve tablo bilgilerini çıkar"""
    tables = {}
    
    try:
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
        
        # CREATE TABLE statement'larını bul
        create_pattern = re.compile(r'CREATE TABLE (\w+)', re.IGNORECASE)
        table_names = create_pattern.findall(content)
        
        # Her tablo için INSERT sayısını say
        for table in table_names:
            insert_pattern = re.compile(rf'INSERT INTO {table}', re.IGNORECASE)
            insert_count = len(insert_pattern.findall(content))
            tables[table] = insert_count
        
        return tables
    except Exception as e:
        print(f"Parse error: {e}")
        return {}

def get_table_dependencies():
    """Tablo bağımlılıklarını döndür (foreign key ilişkileri)"""
    try:
        inspector = inspect(db.engine)
        dependencies = {}
        
        for table_name in inspector.get_table_names():
            try:
                foreign_keys = inspector.get_foreign_keys(table_name)
                deps = []
                
                for fk in foreign_keys:
                    referred_table = fk.get('referred_table')
                    if referred_table:
                        deps.append(referred_table)
                
                if deps:
                    dependencies[table_name] = deps
            except:
                continue
        
        return dependencies
    except Exception as e:
        print(f"Dependency error: {e}")
        return {}

def get_current_table_counts():
    """Mevcut database'deki tablo kayıt sayılarını döndür"""
    try:
        inspector = inspect(db.engine)
        counts = {}
        
        with db.engine.connect() as conn:
            for table_name in inspector.get_table_names():
                try:
                    result = conn.execute(text(f"SELECT COUNT(*) FROM {table_name}"))
                    count = result.scalar()
                    counts[table_name] = count if count else 0
                except:
                    counts[table_name] = 0
        
        return counts
    except Exception as e:
        print(f"Count error: {e}")
        return {}

@restore_bp.route('/restore_backup')
def restore_backup_page():
    """Backup restore sayfası"""
    return render_template('restore_backup.html')

@restore_bp.route('/api/upload_backup', methods=['POST'])
def upload_backup():
    """Backup dosyasını yükle ve analiz et"""
    
    try:
        if 'backup_file' not in request.files:
            return jsonify({'error': 'Dosya seçilmedi'}), 400
    
        file = request.files['backup_file']
        
        if file.filename == '':
            return jsonify({'error': 'Dosya seçilmedi'}), 400
        
        if not allowed_file(file.filename):
            return jsonify({'error': 'Sadece .sql dosyaları yüklenebilir'}), 400
        # Dosyayı kaydet (chunk olarak)
        filename = secure_filename(file.filename)
        filepath = os.path.join(UPLOAD_FOLDER, filename)
        
        # Chunk olarak kaydet (büyük dosyalar için)
        with open(filepath, 'wb') as f:
            while True:
                chunk = file.stream.read(8192)  # 8KB chunks
                if not chunk:
                    break
                f.write(chunk)
        
        # Session'a kaydet
        session['backup_filepath'] = filepath
        
        # Backup'ı analiz et
        backup_tables = parse_sql_backup(filepath)
        current_tables = get_current_table_counts()
        dependencies = get_table_dependencies()
        
        # Karşılaştırma verisi hazırla
        comparison = []
        
        for table_name in sorted(set(list(backup_tables.keys()) + list(current_tables.keys()))):
            backup_count = backup_tables.get(table_name, 0)
            current_count = current_tables.get(table_name, 0)
            deps = dependencies.get(table_name, [])
            
            comparison.append({
                'table': table_name,
                'backup_count': backup_count,
                'current_count': current_count,
                'dependencies': deps,
                'has_dependencies': len(deps) > 0
            })
        
        return jsonify({
            'success': True,
            'filename': filename,
            'comparison': comparison
        })
    
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

@restore_bp.route('/api/restore_table', methods=['POST'])
def restore_table():
    """Belirli bir tabloyu restore et"""
    
    data = request.get_json()
    table_name = data.get('table')
    
    if not table_name:
        return jsonify({'error': 'Tablo adı gerekli'}), 400
    
    filepath = session.get('backup_filepath')
    
    if not filepath or not os.path.exists(filepath):
        return jsonify({'error': 'Backup dosyası bulunamadı'}), 400
    
    try:
        # Önce tabloyu temizle
        with db.engine.connect() as conn:
            conn.execute(text(f"TRUNCATE TABLE {table_name} CASCADE"))
            conn.commit()
        
        # SQL dosyasını satır satır oku ve sadece ilgili tabloyu işle
        success_count = 0
        error_count = 0
        in_insert = False
        current_statement = []
        
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            for line in f:
                line_upper = line.upper().strip()
                
                # INSERT INTO table_name ile başlayan satır
                if f'INSERT INTO {table_name.upper()}' in line_upper:
                    in_insert = True
                    current_statement = [line]
                elif in_insert:
                    current_statement.append(line)
                    
                    # Statement bitişi (satır sonu ; ile)
                    if line.strip().endswith(');'):
                        statement = ''.join(current_statement)
                        try:
                            with db.engine.connect() as conn:
                                conn.execute(text(statement))
                                conn.commit()
                                success_count += 1
                        except Exception as e:
                            error_count += 1
                            # Hata olursa devam et
                            pass
                        
                        in_insert = False
                        current_statement = []
        
        return jsonify({
            'success': True,
            'table': table_name,
            'restored_count': success_count,
            'error_count': error_count
        })
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

@restore_bp.route('/api/restore_all', methods=['POST'])
def restore_all():
    """Tüm tabloları restore et"""
    
    filepath = session.get('backup_filepath')
    
    if not filepath or not os.path.exists(filepath):
        return jsonify({'error': 'Backup dosyası bulunamadı'}), 400
    
    try:
        # SQL dosyasını oku
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Tüm database'i temizle
        with db.engine.connect() as conn:
            conn.execute(text("DROP SCHEMA public CASCADE"))
            conn.execute(text("CREATE SCHEMA public"))
            conn.commit()
        
        # SQL'i satırlara böl ve tek tek çalıştır
        statements = content.split(';')
        success_count = 0
        error_count = 0
        
        for statement in statements:
            statement = statement.strip()
            if not statement or statement.startswith('--'):
                continue
            
            try:
                with db.engine.connect() as conn:
                    conn.execute(text(statement + ';'))
                    conn.commit()
                    success_count += 1
            except Exception as e:
                error_count += 1
                print(f"Statement error: {e}")
                continue
        
        return jsonify({
            'success': True,
            'message': f'Restore tamamlandı! Başarılı: {success_count}, Hatalı: {error_count}'
        })
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500
