"""
DND API Endpoint Test
/api/kat-sorumlusu/dnd-durum/<oda_id> endpoint'ini test eder
"""

from models import Oda
from utils.dnd_service import DNDService

def test_api_dnd_durum():
    """API endpoint'inin döndüreceği sonucu test et"""
    
    # Oda 1305'i bul
    oda = Oda.query.filter_by(oda_no='1305').first()
    
    if not oda:
        print("❌ Oda 1305 bulunamadı!")
        return
    
    print(f"✅ Oda bulundu: ID={oda.id}, Oda No={oda.oda_no}")
    
    # DNDService.oda_durumu() çağır (API endpoint'i bunu kullanıyor)
    durum = DNDService.oda_durumu(oda.id)
    
    print(f"\n📡 API Response:")
    print(f"   dnd_durumu: {durum}")
    
    if durum is None:
        print(f"\n✅ BAŞARILI! Oda artık DND olarak görünmüyor!")
        print(f"   Frontend'de DND butonu normal görünecek")
        print(f"   Oda listesinde DND badge'i olmayacak")
    else:
        print(f"\n❌ SORUN! Oda hala DND olarak görünüyor!")
        print(f"   Durum: {durum.get('durum')}")
        print(f"   DND Sayısı: {durum.get('dnd_sayisi')}")

if __name__ == '__main__':
    from app import app
    with app.app_context():
        test_api_dnd_durum()
