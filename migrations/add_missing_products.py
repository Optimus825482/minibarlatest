"""
Eksik Ürünleri Ekle
Erkan için - ff.md'deki eksik ürünleri uygun gruplara ekle
"""
from app import app, db
from models import Urun, UrunGrup, UrunStok, Otel
from datetime import datetime
from decimal import Decimal

# Eksik ürünler ve bilgileri
EKSIK_URUNLER = [
    # (Ürün Adı, Grup Adı, Fiyat, Tarih)
    ("Çay Poşet Ihlamur", "Maxi Bar Ürünleri", "2", "2025-10-23"),
    ("Çay Poşet Papatya", "Maxi Bar Ürünleri", "2", "2025-11-04"),
    ("Çay Poşet Yeşil Çay", "Maxi Bar Ürünleri", "2.5", "2025-11-04"),
    ("Çerez Kesesi - Boş", "Atıştırmalık Ürünler", "2.5", "2025-01-01"),
    ("Eti Browni İntense 45 Gr", "Atıştırmalık Ürünler", "25.705", "2025-10-08"),
    ("Kahve Mehmet Efendi", "Maxi Bar Ürünleri", "22.815", "2025-11-09"),
    ("Kavanoz 210 Cc Metal Kapakli", "Maxi Bar Ürünleri", "13", "2025-07-10"),
    ("Sakarin Stick", "Maxi Bar Ürünleri", "0.65", "2025-08-08"),
    ("Soda Şişe Sade 200 Ml (Beypazarı)", "Alkolsüz İçecekler", "8", "2025-10-29"),
]


def add_missing_products():
    """Eksik ürünleri ekle"""
    with app.app_context():
        print("🔄 Eksik ürünler ekleniyor...\n")
        
        # Grupları getir
        gruplar = {g.grup_adi: g for g in UrunGrup.query.filter_by(aktif=True).all()}
        
        # Otelleri getir
        oteller = Otel.query.filter_by(aktif=True).all()
        
        eklenen = 0
        hatalar = []
        
        for urun_adi, grup_adi, fiyat_str, tarih_str in EKSIK_URUNLER:
            try:
                # Grup bul
                grup = gruplar.get(grup_adi)
                if not grup:
                    hatalar.append((urun_adi, f"Grup bulunamadı: {grup_adi}"))
                    print(f"❌ {urun_adi}: Grup bulunamadı ({grup_adi})")
                    continue
                
                # Ürün zaten var mı kontrol et
                mevcut = Urun.query.filter_by(urun_adi=urun_adi).first()
                if mevcut:
                    print(f"⚠️  {urun_adi}: Zaten mevcut, atlanıyor")
                    continue
                
                # Yeni ürün oluştur
                urun = Urun(
                    grup_id=grup.id,
                    urun_adi=urun_adi,
                    barkod=None,
                    birim='Adet',
                    kritik_stok_seviyesi=10,
                    aktif=True,
                    olusturma_tarihi=datetime.now()
                )
                db.session.add(urun)
                db.session.flush()  # ID'yi al
                
                # Fiyatı decimal'e çevir
                fiyat = Decimal(fiyat_str.replace(",", "."))
                
                # Her otel için stok kaydı oluştur
                for otel in oteller:
                    stok = UrunStok(
                        urun_id=urun.id,
                        otel_id=otel.id,
                        mevcut_stok=0,
                        minimum_stok=10,
                        maksimum_stok=1000,
                        kritik_stok_seviyesi=5,
                        birim_maliyet=fiyat,
                        toplam_deger=0,
                        son_30gun_cikis=0,
                        stok_devir_hizi=0,
                        son_guncelleme_tarihi=datetime.now(),
                        sayim_farki=0
                    )
                    db.session.add(stok)
                
                print(f"✅ {urun_adi} eklendi (Grup: {grup_adi}, Fiyat: {fiyat} TL)")
                eklenen += 1
                
            except Exception as e:
                hatalar.append((urun_adi, str(e)))
                print(f"❌ Hata ({urun_adi}): {str(e)}")
        
        # Kaydet
        try:
            db.session.commit()
            print(f"\n{'='*60}")
            print("✅ Ürünler eklendi!")
            print(f"   Eklenen: {eklenen}")
            print(f"   Hata: {len(hatalar)}")
            print(f"   Toplam otel: {len(oteller)}")
            print(f"   Her ürün için {len(oteller)} stok kaydı oluşturuldu")
            print(f"{'='*60}")
            
            if hatalar:
                print(f"\n❌ Hatalar ({len(hatalar)}):")
                for urun, hata in hatalar:
                    print(f"   - {urun}: {hata}")
                    
        except Exception as e:
            db.session.rollback()
            print(f"\n❌ Veritabanı hatası: {str(e)}")


if __name__ == '__main__':
    add_missing_products()
