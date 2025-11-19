"""
Kat Sorumlusu Sipariş Talepleri Tabloları Oluşturma
Tarih: 2025-11-18
"""

from app import app, db
from models import KatSorumlusuSiparisTalebi, KatSorumlusuSiparisTalepDetay

def upgrade():
    """Tabloları oluştur"""
    with app.app_context():
        try:
            # Tabloları oluştur
            db.create_all()
            print("✅ Kat sorumlusu sipariş talepleri tabloları oluşturuldu")
            
            # Tablo kontrolü
            from sqlalchemy import inspect
            inspector = inspect(db.engine)
            
            tables = inspector.get_table_names()
            if 'kat_sorumlusu_siparis_talepleri' in tables:
                print("✅ kat_sorumlusu_siparis_talepleri tablosu mevcut")
            else:
                print("❌ kat_sorumlusu_siparis_talepleri tablosu oluşturulamadı")
                
            if 'kat_sorumlusu_siparis_talep_detaylari' in tables:
                print("✅ kat_sorumlusu_siparis_talep_detaylari tablosu mevcut")
            else:
                print("❌ kat_sorumlusu_siparis_talep_detaylari tablosu oluşturulamadı")
                
            return True
            
        except Exception as e:
            print(f"❌ Hata: {e}")
            return False

def downgrade():
    """Tabloları sil"""
    with app.app_context():
        try:
            # Tabloları sil
            db.session.execute(db.text('DROP TABLE IF EXISTS kat_sorumlusu_siparis_talep_detaylari CASCADE'))
            db.session.execute(db.text('DROP TABLE IF EXISTS kat_sorumlusu_siparis_talepleri CASCADE'))
            db.session.commit()
            print("✅ Kat sorumlusu sipariş talepleri tabloları silindi")
            return True
            
        except Exception as e:
            print(f"❌ Hata: {e}")
            db.session.rollback()
            return False

if __name__ == '__main__':
    print("Kat Sorumlusu Sipariş Talepleri Migration")
    print("=" * 50)
    upgrade()
