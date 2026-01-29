"""
DND Otomatik Tamamlama Debug Script
Oda 1305 için DND durumunu kontrol eder
"""

from datetime import date
from models import db, OdaDNDKayit, Oda
from utils.dnd_service import DNDService

def test_oda_1305():
    """Oda 1305 için DND durumunu kontrol et"""
    
    # Oda 1305'i bul
    oda = Oda.query.filter_by(oda_no='1305').first()
    
    if not oda:
        print("❌ Oda 1305 bulunamadı!")
        return
    
    print(f"✅ Oda bulundu: ID={oda.id}, Oda No={oda.oda_no}")
    
    # Bugünkü DND kaydını kontrol et
    bugun = date.today()
    dnd_kayit = OdaDNDKayit.query.filter_by(
        oda_id=oda.id,
        kayit_tarihi=bugun
    ).first()
    
    if not dnd_kayit:
        print(f"❌ Bugün ({bugun}) için DND kaydı bulunamadı!")
        return
    
    print(f"\n📋 DND Kayıt Bilgileri:")
    print(f"   ID: {dnd_kayit.id}")
    print(f"   Durum: {dnd_kayit.durum}")
    print(f"   DND Sayısı: {dnd_kayit.dnd_sayisi}")
    print(f"   İlk DND: {dnd_kayit.ilk_dnd_zamani}")
    print(f"   Son DND: {dnd_kayit.son_dnd_zamani}")
    print(f"   Kayıt Tarihi: {dnd_kayit.kayit_tarihi}")
    
    # Kontrolleri listele
    print(f"\n📝 DND Kontrolleri:")
    for kontrol in dnd_kayit.kontroller.order_by('kontrol_no').all():
        print(f"   #{kontrol.kontrol_no}: {kontrol.kontrol_zamani} - {kontrol.notlar}")
    
    # DNDService.otomatik_tamamla() fonksiyonunu test et
    print(f"\n🧪 otomatik_tamamla() fonksiyonu test ediliyor...")
    
    try:
        sonuc = DNDService.otomatik_tamamla(
            oda_id=oda.id,
            personel_id=1,  # Test için dummy personel ID
            islem_tipi='test'
        )
        
        if sonuc:
            print(f"✅ Fonksiyon çalıştı!")
            print(f"   Sonuç: {sonuc}")
        else:
            print(f"⚠️ Fonksiyon None döndü (DND aktif değil veya bulunamadı)")
            
    except Exception as e:
        print(f"❌ Hata: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    from app import app
    with app.app_context():
        test_oda_1305()
