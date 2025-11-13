"""
Ürün Alış Fiyatlarını Güncelle
Erkan için - ff.md dosyasındaki fiyatları veritabanına aktar
"""
from app import app, db
from models import Urun, UrunTedarikciFiyat, Tedarikci
from datetime import datetime
from decimal import Decimal

# ff.md'den alınan fiyat verileri
FIYAT_VERILERI = [
    ("Bar Nestle Nesfit Kakaolu 23.5 Gr", "34.328", "2025-10-15"),
    ("Bar Nestle Nesfit Karamelli 23.5 Gr", "34.33", "2025-11-06"),
    ("Bar Nestle Nesfit Kırmızı Meyveli 23.5 Gr", "34.33", "2025-11-06"),
    ("Bar Nestle Nesfit Sütlü Çikolatalı Ve  Muzlu 23.5 G", "34.326", "2025-11-06"),
    ("Bira Efes Şişe 33 Cl", "40.972", "2025-10-28"),
    ("Bisküvi Eti Crax Peynirli 50 Gr", "12.75", "2025-10-08"),
    ("Cips Pringels 40 Gr", "68.9", "2025-08-15"),
    ("Çay Poşet Earl Grey Sade", "2.01", "2025-08-21"),
    ("Çay Poşet Englısh Breakfast Tea", "6", "2025-09-23"),
    ("Çay Poşet Ihlamur", "2", "2025-10-23"),
    ("Çay Poşet Papatya", "2", "2025-11-04"),
    ("Çay Poşet Yeşil Çay", "2.5", "2025-11-04"),
    ("Çerez Fıstık Tuzlu", "3.4", "2025-10-20"),
    ("Çerez Kesesi - Boş", "2.5", "2025-01-01"),
    ("Çikolata Snickers 50 Gr", "34.605", "2025-10-29"),
    ("Çikolata Twix Double Chocolate Bar 50 Gr", "31.455", "2025-09-17"),
    ("Eti Browni İntense 45 Gr", "25.705", "2025-10-08"),
    ("First Sensations Yeşil Nane Aromalı Sakız  27 G", "34.886", "2025-10-28"),
    ("Ice Coffe 240 Ml Mr Brown Black", "45.447", "2025-08-11"),
    ("Jp Chenet Ice Edition 20 Cl", "99", "2025-08-08"),
    ("Kahve Kreması Nescafe Stick", "3.072", "2025-09-26"),
    ("Kahve Mehmet Efendi", "22.815", "2025-11-09"),
    ("Kahve Nescafe Stick Gold", "7.064", "2025-09-26"),
    ("Kahve Segafredo Kapsül", "21.861", "2025-10-23"),
    ("Kavanoz 210 Cc Metal Kapakli", "13", "2025-07-10"),
    ("Maison Castel Chardonnay 187 ml", "52.08", "2025-05-13"),
    ("Maison Castel Merlot 187 Ml", "52.08", "2025-05-13"),
    ("Maretti Bruschette Cheese", "28.56", "2025-09-29"),
    ("Maretti Bruschette Tomato", "28.56", "2025-09-29"),
    ("Mateus Rose Orgınal 25 Cl", "50.25", "2025-05-13"),
    ("Pepsi Kutu 250 Ml", "9.546", "2025-09-23"),
    ("Pepsi Kutu Max 250 Ml", "9.55", "2025-09-09"),
    ("Sakarin Stick", "0.65", "2025-08-08"),
    ("Sakız First Sensations Çilek Aromalı 27  Gr (Miniba", "34.886", "2025-10-28"),
    ("Seven Up Kutu 250 Ml", "9.546", "2025-11-06"),
    ("Soda Şişe Sade 200 Ml (Beypazarı)", "8", "2025-10-29"),
    ("Soguk Çay 330 Ml Seftali (Lipton)", "26.452", "2025-09-01"),
    ("Su Cam Logolu (Sırma) 330 Ml", "17.5", "2025-11-03"),
    ("Su Cam Logolu (Sırma) 750 Ml", "36.5", "2025-11-03"),
    ("Su Mineralli Pellegrino 250 Ml", "83", "2025-10-07"),
    ("Su Mineralli Perrier 330 Ml", "102", "2025-11-03"),
    ("Şeker Stick Beyaz", "0.45", "2025-10-22"),
    ("Şeker Stick Esmer", "0.5", "2025-09-15"),
    ("Ülker Çokonat 33 Gr", "19.04", "2025-10-08"),
    ("Yedigün Kutu 250 Ml", "9.546", "2025-09-09"),
]


def normalize_name(name):
    """Ürün adını normalize et - karşılaştırma için"""
    return name.lower().strip().replace("  ", " ")


def update_prices():
    """Fiyatları güncelle"""
    with app.app_context():
        print("🔄 Ürün fiyatları güncelleniyor...\n")
        
        # Tüm ürünleri getir
        urunler = Urun.query.all()
        urun_dict = {normalize_name(u.urun_adi): u for u in urunler}
        
        # İstatistikler
        guncellenen = 0
        bulunamayan = []
        hatalar = []
        
        for urun_adi, fiyat_str, tarih_str in FIYAT_VERILERI:
            try:
                # Ürünü bul
                normalized_name = normalize_name(urun_adi)
                urun = urun_dict.get(normalized_name)
                
                if not urun:
                    bulunamayan.append(urun_adi)
                    print(f"⚠️  Ürün bulunamadı: {urun_adi}")
                    continue
                
                # Fiyatı decimal'e çevir (virgül yerine nokta)
                fiyat = Decimal(fiyat_str.replace(",", "."))
                
                # Tarihi parse et
                tarih = datetime.strptime(tarih_str, "%Y-%m-%d")
                
                # UrunStok tablosunda birim_maliyet güncelle
                from models import UrunStok
                stok = UrunStok.query.filter_by(urun_id=urun.id).first()
                if stok:
                    eski_fiyat = stok.birim_maliyet
                    stok.birim_maliyet = fiyat
                    stok.toplam_deger = stok.mevcut_stok * fiyat
                    stok.son_guncelleme_tarihi = datetime.now()
                    print(f"✅ {urun.urun_adi}: {eski_fiyat} TL → {fiyat} TL")
                else:
                    print(f"⚠️  {urun.urun_adi}: Stok kaydı yok, atlanıyor")
                
                guncellenen += 1
                
            except Exception as e:
                hatalar.append((urun_adi, str(e)))
                print(f"❌ Hata ({urun_adi}): {str(e)}")
        
        # Değişiklikleri kaydet
        try:
            db.session.commit()
            print(f"\n{'='*60}")
            print(f"✅ Güncelleme tamamlandı!")
            print(f"   Güncellenen: {guncellenen}")
            print(f"   Bulunamayan: {len(bulunamayan)}")
            print(f"   Hata: {len(hatalar)}")
            print(f"{'='*60}")
            
            if bulunamayan:
                print(f"\n⚠️  Bulunamayan ürünler ({len(bulunamayan)}):")
                for urun in bulunamayan[:10]:  # İlk 10'u göster
                    print(f"   - {urun}")
                if len(bulunamayan) > 10:
                    print(f"   ... ve {len(bulunamayan) - 10} tane daha")
            
            if hatalar:
                print(f"\n❌ Hatalar ({len(hatalar)}):")
                for urun, hata in hatalar[:5]:  # İlk 5'i göster
                    print(f"   - {urun}: {hata}")
                    
        except Exception as e:
            db.session.rollback()
            print(f"\n❌ Veritabanı hatası: {str(e)}")


if __name__ == '__main__':
    update_prices()
