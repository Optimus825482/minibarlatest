"""
Rollback Manager
Migration başarısız olduğunda geri alma işlemleri
"""

import json
import os
from datetime import datetime, timezone
import pytz

# KKTC Timezone
KKTC_TZ = pytz.timezone('Europe/Nicosia')
def get_kktc_now():
    return datetime.now(KKTC_TZ)
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
import subprocess


class RollbackManager:
    """Migration rollback yöneticisi"""
    
    def __init__(self, postgres_url: str, backup_dir: str = '/backups'):
        self.postgres_url = postgres_url
        self.backup_dir = backup_dir
        self.postgres_engine = create_engine(postgres_url)
        
        PostgresSession = sessionmaker(bind=self.postgres_engine)
        self.postgres_session = PostgresSession()
    
    def rollback_to_checkpoint(self, checkpoint_file: str, checkpoint_index: int):
        """
        Belirli bir checkpoint'e geri dön
        
        Args:
            checkpoint_file: Checkpoint JSON dosyası
            checkpoint_index: Geri dönülecek checkpoint index'i
        """
        print(f"\n🔄 Rolling back to checkpoint {checkpoint_index}")
        
        try:
            # Checkpoint'leri yükle
            with open(checkpoint_file, 'r') as f:
                checkpoints = json.load(f)
            
            if checkpoint_index >= len(checkpoints):
                print(f"❌ Invalid checkpoint index: {checkpoint_index}")
                return False
            
            target_checkpoint = checkpoints[checkpoint_index]
            print(f"   Target: {target_checkpoint['table']} - {target_checkpoint['timestamp']}")
            
            # Bu checkpoint'ten sonraki tabloları temizle
            tables_to_clear = [
                cp['table'] for cp in checkpoints[checkpoint_index + 1:]
            ]
            
            for table in reversed(tables_to_clear):  # Reverse order for FK constraints
                print(f"   Clearing table: {table}")
                try:
                    self.postgres_session.execute(text(f"TRUNCATE TABLE {table} CASCADE"))
                    self.postgres_session.commit()
                except Exception as e:
                    print(f"   ⚠️  Error clearing {table}: {str(e)}")
                    self.postgres_session.rollback()
            
            print("✅ Rollback completed")
            return True
            
        except Exception as e:
            print(f"❌ Rollback failed: {str(e)}")
            return False
    
    def restore_from_backup(self, backup_file: str):
        """
        Backup'tan tam geri yükleme
        
        Args:
            backup_file: Backup dosyası yolu
        """
        print(f"\n🔄 Restoring from backup: {backup_file}")
        
        if not os.path.exists(backup_file):
            print(f"❌ Backup file not found: {backup_file}")
            return False
        
        try:
            # Parse database URL
            db_config = self._parse_db_url(self.postgres_url)
            
            # Drop all tables first
            print("   Dropping existing tables...")
            self._drop_all_tables()
            
            # Restore from backup
            print("   Restoring from backup...")
            cmd = [
                'pg_restore',
                '-h', db_config['host'],
                '-U', db_config['user'],
                '-d', db_config['database'],
                '-c',  # Clean before restore
                '-F', 'c',  # Custom format
                backup_file
            ]
            
            env = os.environ.copy()
            env['PGPASSWORD'] = db_config['password']
            
            result = subprocess.run(
                cmd,
                env=env,
                capture_output=True,
                text=True
            )
            
            if result.returncode == 0:
                print("✅ Restore completed successfully")
                return True
            else:
                print(f"❌ Restore failed: {result.stderr}")
                return False
                
        except Exception as e:
            print(f"❌ Restore error: {str(e)}")
            return False
    
    def _drop_all_tables(self):
        """Tüm tabloları sil"""
        try:
            # Get all tables
            query = text("""
                SELECT tablename 
                FROM pg_tables 
                WHERE schemaname = 'public'
            """)
            tables = self.postgres_session.execute(query).fetchall()
            
            # Drop all tables
            for table in tables:
                table_name = table[0]
                self.postgres_session.execute(
                    text(f"DROP TABLE IF EXISTS {table_name} CASCADE")
                )
            
            self.postgres_session.commit()
            
        except Exception as e:
            self.postgres_session.rollback()
            raise
    
    def _parse_db_url(self, url: str) -> dict:
        """Database URL'ini parse et"""
        # postgresql://user:pass@host:port/dbname
        from urllib.parse import urlparse
        
        parsed = urlparse(url)
        
        return {
            'host': parsed.hostname,
            'port': parsed.port or 5432,
            'user': parsed.username,
            'password': parsed.password,
            'database': parsed.path.lstrip('/')
        }
    
    def create_rollback_script(self, output_file: str = 'rollback.sh'):
        """
        Rollback script'i oluştur
        
        Args:
            output_file: Çıktı dosyası adı
        """
        script_content = """#!/bin/bash
# PostgreSQL Migration Rollback Script
# Generated: {timestamp}

echo "🔄 Starting rollback process..."

# 1. Stop application
echo "Stopping application..."
# systemctl stop minibar-app  # Uncomment if using systemd

# 2. Backup current PostgreSQL state
echo "Creating backup of current state..."
pg_dump -h localhost -U postgres -d minibar_takip -F c -f /backups/pre_rollback_$(date +%Y%m%d_%H%M%S).backup

# 3. Restore from MySQL backup (if available)
echo "Restoring MySQL backup..."
# mysql -u root -p minibar_takip < /backups/mysql_backup.sql

# 4. Update config to MySQL
echo "Updating configuration..."
export DB_TYPE=mysql
export DATABASE_URL="mysql://user:pass@localhost:3306/minibar_takip"

# 5. Restart application
echo "Restarting application..."
# systemctl start minibar-app  # Uncomment if using systemd

echo "✅ Rollback completed"
echo "⚠️  Please verify application functionality"
""".format(timestamp=get_kktc_now().isoformat())
        
        with open(output_file, 'w') as f:
            f.write(script_content)
        
        # Make executable
        os.chmod(output_file, 0o755)
        
        print(f"✅ Rollback script created: {output_file}")
    
    def close(self):
        """Bağlantıları kapat"""
        self.postgres_session.close()
        self.postgres_engine.dispose()

