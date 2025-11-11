"""
Backup Restore Routes V2
Gelişmiş yedek yükleme ve geri yükleme sistemi
"""

from flask import Blueprint, render_template, request, jsonify, session, flash, redirect, url_for
from werkzeug.utils import secure_filename
from sqlalchemy import create_engine, text, inspect
from models import db
from utils.decorators import login_required, role_required
import os
import re

restore_v2_bp = Blueprint('restore_v2', __name__)

ALLOWED_EXTENSIONS = {'sql'}
UPLOAD_FOLDER = 'uploads/backups'
MAX_FILE_SIZE = 100 * 1024 * 1024  # 100MB

os.makedirs(UPLOAD_FOLDER, exist_ok=True)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@restore_v2_bp.route('/restore_backup')
@login_required
@role_required(['sistem_yoneticisi'])
def restore_backup_page():
    """Backup restore sayfası - Sadece sistem yöneticisi"""
    return render_template('restore_backup_v2.html')

@restore_v2_bp.route('/api/upload_backup', methods=['POST'])
@login_required
@role_required(['sistem_yoneticisi'])
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
        
        # Dosyayı kaydet
        filename = secure_filename(file.filename)
        filepath = os.path.join(UPLOAD_FOLDER, filename)
        
        with open(filepath, 'wb') as f:
            while True:
                chunk = file.stream.read(8192)
                if not chunk:
                    break
                f.write(chunk)
        
        # Session'a kaydet
        session['backup_filepath'] = filepath
        
        # Dosyayı analiz et
        file_size = os.path.getsize(filepath)
        
        # Tabloları parse et
        backup_tables = {}
        create_statements = {}
        
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
            
            # CREATE TABLE'ları bul - Daha gelişmiş pattern
            # IF NOT EXISTS, public schema, ve çeşitli formatları destekler
            create_pattern = re.compile(
                r'CREATE\s+TABLE\s+(?:IF\s+NOT\s+EXISTS\s+)?(?:public\.)?(\w+)\s*\((.*?)\);',
                re.IGNORECASE | re.DOTALL
            )
            
            for match in create_pattern.finditer(content):
                table_name = match.group(1)
                create_sql = match.group(0)
                
                # CREATE TABLE'ı normalize et (IF NOT EXISTS ekle)
                if 'IF NOT EXISTS' not in create_sql.upper():
                    create_sql = create_sql.replace(
                        f'CREATE TABLE {table_name}',
                        f'CREATE TABLE IF NOT EXISTS {table_name}',
                        1
                    )
                
                create_statements[table_name] = create_sql
                
                # INSERT sayısını say
                insert_count = len(re.findall(
                    rf'INSERT\s+INTO\s+(?:public\.)?{table_name}',
                    content,
                    re.IGNORECASE
                ))
                
                backup_tables[table_name] = insert_count
        
        # Mevcut tabloları kontrol et
        inspector = inspect(db.engine)
        current_tables = inspector.get_table_names()
        
        # Mevcut tablo kayıt sayıları
        current_counts = {}
        for table in current_tables:
            try:
                with db.engine.connect() as conn:
                    result = conn.execute(text(f"SELECT COUNT(*) FROM {table}"))
                    current_counts[table] = result.scalar() or 0
            except:
                current_counts[table] = 0
        
        # Bağımlılıkları bul
        dependencies = {}
        for table in current_tables:
            try:
                fks = inspector.get_foreign_keys(table)
                deps = [fk['referred_table'] for fk in fks if 'referred_table' in fk]
                if deps:
                    dependencies[table] = deps
            except:
                pass
        
        # Karşılaştırma verisi
        comparison = []
        all_tables = sorted(set(list(backup_tables.keys()) + current_tables))
        
        for table in all_tables:
            comparison.append({
                'table': table,
                'backup_count': backup_tables.get(table, 0),
                'current_count': current_counts.get(table, 0),
                'exists': table in current_tables,
                'dependencies': dependencies.get(table, []),
                'has_dependencies': table in dependencies
            })
        
        # Session'a CREATE statement'ları da kaydet
        session['create_statements'] = create_statements
        
        return jsonify({
            'success': True,
            'filename': filename,
            'file_size': file_size,
            'total_tables': len(backup_tables),
            'comparison': comparison
        })
    
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

@restore_v2_bp.route('/api/restore_tables', methods=['POST'])
@login_required
@role_required(['sistem_yoneticisi'])
def restore_tables():
    """Seçili tabloları restore et"""
    
    data = request.get_json()
    table_names = data.get('tables', [])
    
    if not table_names:
        return jsonify({'error': 'Tablo seçilmedi'}), 400
    
    filepath = session.get('backup_filepath')
    create_statements = session.get('create_statements', {})
    
    if not filepath or not os.path.exists(filepath):
        return jsonify({'error': 'Backup dosyası bulunamadı'}), 400
    
    results = []
    
    for table_name in table_names:
        try:
            # Tablo var mı kontrol et
            inspector = inspect(db.engine)
            table_exists = table_name in inspector.get_table_names()
            
            if not table_exists:
                # Tablo yoksa oluştur
                create_sql = create_statements.get(table_name)
                if create_sql:
                    try:
                        with db.engine.connect() as conn:
                            conn.execute(text(create_sql))
                            conn.commit()
                    except Exception as create_error:
                        # CREATE TABLE hatası - devam et
                        pass
            else:
                # Tablo varsa temizle
                try:
                    with db.engine.connect() as conn:
                        # Foreign key constraint'leri geçici olarak devre dışı bırak
                        conn.execute(text("SET session_replication_role = 'replica'"))
                        conn.execute(text(f"TRUNCATE TABLE {table_name} CASCADE"))
                        conn.execute(text("SET session_replication_role = 'origin'"))
                        conn.commit()
                except Exception as truncate_error:
                    # TRUNCATE hatası - DELETE dene
                    try:
                        with db.engine.connect() as conn:
                            conn.execute(text(f"DELETE FROM {table_name}"))
                            conn.commit()
                    except:
                        pass
            
            # INSERT'leri çalıştır
            success_count = 0
            error_count = 0
            
            with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                in_insert = False
                current_statement = []
                
                for line in f:
                    line_upper = line.upper().strip()
                    
                    # INSERT INTO table_name veya INSERT INTO public.table_name
                    if (f'INSERT INTO {table_name.upper()}' in line_upper or 
                        f'INSERT INTO PUBLIC.{table_name.upper()}' in line_upper):
                        in_insert = True
                        current_statement = [line]
                    elif in_insert:
                        current_statement.append(line)
                        
                        if line.strip().endswith(');'):
                            statement = ''.join(current_statement)
                            try:
                                with db.engine.connect() as conn:
                                    # public. prefix'ini kaldır
                                    statement = statement.replace('INSERT INTO public.', 'INSERT INTO ')
                                    conn.execute(text(statement))
                                    conn.commit()
                                    success_count += 1
                            except Exception as e:
                                error_count += 1
                                # Hata logla ama devam et
                                import traceback
                                print(f"INSERT hatası: {str(e)[:100]}")
                            
                            in_insert = False
                            current_statement = []
            
            results.append({
                'table': table_name,
                'success': True,
                'restored_count': success_count,
                'error_count': error_count,
                'created': not table_exists
            })
            
        except Exception as e:
            import traceback
            traceback.print_exc()
            results.append({
                'table': table_name,
                'success': False,
                'error': str(e)
            })
    
    return jsonify({
        'success': True,
        'results': results
    })

@restore_v2_bp.route('/api/restore_full', methods=['POST'])
@login_required
@role_required(['sistem_yoneticisi'])
def restore_full():
    """Tüm database'i restore et - Gelişmiş versiyon"""
    
    filepath = session.get('backup_filepath')
    
    if not filepath or not os.path.exists(filepath):
        return jsonify({'error': 'Backup dosyası bulunamadı'}), 400
    
    try:
        # Schema'yı temizle
        with db.engine.connect() as conn:
            conn.execute(text("DROP SCHEMA public CASCADE"))
            conn.execute(text("CREATE SCHEMA public"))
            conn.execute(text("GRANT ALL ON SCHEMA public TO PUBLIC"))
            conn.commit()
        
        # SQL'i satır satır çalıştır
        success_count = 0
        error_count = 0
        
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            current_statement = []
            in_copy = False
            
            for line in f:
                # Yorum satırlarını atla
                if line.strip().startswith('--'):
                    continue
                
                # COPY komutlarını atla (PostgreSQL specific)
                if line.strip().upper().startswith('COPY '):
                    in_copy = True
                    continue
                
                if in_copy:
                    if line.strip() == '\\.':
                        in_copy = False
                    continue
                
                current_statement.append(line)
                
                # Statement bitişi
                if line.strip().endswith(';'):
                    statement = ''.join(current_statement).strip()
                    
                    if statement and not statement.startswith('--'):
                        try:
                            with db.engine.connect() as conn:
                                # public. prefix'ini kaldır
                                statement = statement.replace('public.', '')
                                conn.execute(text(statement))
                                conn.commit()
                                success_count += 1
                        except Exception as e:
                            error_count += 1
                            # Kritik olmayan hataları logla ve devam et
                            error_msg = str(e)
                            if 'already exists' not in error_msg.lower():
                                print(f"SQL Hatası: {error_msg[:200]}")
                    
                    current_statement = []
        
        return jsonify({
            'success': True,
            'message': f'Full restore tamamlandı!',
            'success_count': success_count,
            'error_count': error_count
        })
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500
