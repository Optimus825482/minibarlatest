"""
PostgreSQL bağlantı havuzunu ve SQLAlchemy cache'ini temizle
"""
from app import app
from models import db

with app.app_context():
    # Tüm bağlantıları kapat
    db.session.remove()
    db.engine.dispose()
    print("✅ Veritabanı bağlantı havuzu temizlendi")
    
    # Yeni bağlantı oluştur
    db.engine.connect()
    print("✅ Yeni veritabanı bağlantısı oluşturuldu")
    
print("\n✅ Şimdi Flask'ı başlatabilirsin: python app.py")
