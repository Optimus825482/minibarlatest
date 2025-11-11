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

# Upload klasörünü oluştur
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def parse_sql_backup(filepath):
    """SQL backup dosyasını parse et ve tablo bilgilerini çıkar"""
    tables = {}
    
    with open(filepath, 'r', encoding='utf-8') as f:
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

def get_table_dependencies():
    """Tablo bağımlılıklarını döndür (foreign key ilişkileri)"""
    inspector = inspect(db.engine)
    dependencies = {}
    
    for table_name in inspector.get_table_names():
        foreign_keys = inspector.get_foreign_keys(table_name)
        deps = []
        
        for fk in foreign_keys:
            referred_table = fk['referred_table']
            deps.append(referred_table)
        
        if deps:
            dependencies[table_name] = deps
    
    return dependencies

def get_current_table_counts():
    """Mevcut database'deki tablo kayıt sayılarını döndür"""
    inspector = inspect(db.engine)
    counts = {}
    
    with db.engine.connect() as conn:
        for table_name in inspector.get_table_names():
            try:
                result = conn.execute(text(f"SELECT COUNT(*) FROM {table_name}"))
                count = result.scalar()
                counts[table_name] = count
            except:
                counts[table_name] = 0
    
    return counts

@restore_bp.route('/restore_backup')
def restore_backup_page():
    """Backup restore sayfası"""
    return render_template('restore_backup.html')

@restore_bp.route('/api/upload_backup', methods=['POST'])
def upload_backup():
    """Backup dosyasını yükle ve analiz et"""
    
    if 'backup_file' not in request.files:
        return jsonify({'error': 'Dosya seçilmedi'}), 400
    
    file = request.files['backup_file']
    
    if file.filename == '':
        return jsonify({'error': 'Dosya seçilmedi'}), 400
    
    if not allowed_file(file.filename):
        return jsonify({'error': 'Sadece .sql dosyaları yüklenebilir'}), 400
    
    try:
        # Dosyayı kaydet
        filename = secure_filename(file.filename)
        filepath = os.path.join(UPLOAD_FOLDER, filename)
        file.save(filepath)
        
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
        # SQL dosyasını oku
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # İlgili tabloyu bul
        # CREATE TABLE statement
        create_pattern = re.compile(
            rf'CREATE TABLE {table_name}.*?;',
            re.IGNORECASE | re.DOTALL
        )
        create_match = create_pattern.search(content)
        
        # INSERT statements
        insert_pattern = re.compile(
            rf'INSERT INTO {table_name}.*?;',
            re.IGNORECASE
        )
        insert_matches = insert_pattern.findall(content)
        
        with db.engine.connect() as conn:
            # Tabloyu temizle
            conn.execute(text(f"TRUNCATE TABLE {table_name} CASCADE"))
            conn.commit()
            
            # INSERT'leri çalıştır
            success_count = 0
            for insert_sql in insert_matches:
                try:
                    conn.execute(text(insert_sql))
                    success_count += 1
                except Exception as e:
                    print(f"Insert hatası: {e}")
                    continue
            
            conn.commit()
        
        return jsonify({
            'success': True,
            'table': table_name,
            'restored_count': success_count
        })
        
    except Exception as e:
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
            
            # Backup'ı restore et
            conn.execute(text(content))
            conn.commit()
        
        return jsonify({
            'success': True,
            'message': 'Tüm veriler başarıyla restore edildi'
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500
