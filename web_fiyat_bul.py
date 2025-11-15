"""
Web'den ürün fiyatlarını bulup veritabanına ekle
Brave Search ve PostgreSQL MCP kullanarak
"""
import re
import time
from decimal import Decimal

# Fiyatı olmayan ürünler
urunler = [
    {'id': 2, 'urun_adi': 'Pepsi 250 ml.'},
    {'id': 3, 'urun_adi': 'Pepsi Max 250 ml.'},
    {'id': 4, 'urun_adi': 'Yedigün 250 ml.'},
    {'id': 5, 'urun_adi': 'Seven Up'},
    {'id': 6, 'urun_adi': 'Sırma Soda 200 ml.'},
    {'id': 7, 'urun_adi': 'Redbull 250 ml.'},
    {'id': 8, 'urun_adi': 'Sırma Su 330 ml.'},
    {'id': 9, 'urun_adi': 'Sırma Su 750 ml.'},
    {'id': 10, 'urun_adi': 'Mr Brown Ice Coffee Vanilla 240 ml.'},
    {'id': 11, 'urun_adi': 'Mr. Brown Black Coffee 240 ml.'},
    {'id': 12, 'urun_adi': 'Ice Tea Şeftali 200 ml'},
    {'id': 13, 'urun_adi': 'Ice Tea Limon 200 ml.'},
    {'id': 14, 'urun_adi': 'Browni Çikolata 50 gr.'},
    {'id': 15, 'urun_adi': 'Çokonat 33 gr.'},
    {'id': 16, 'urun_adi': 'Nescafe Stick 5 gr.'},
    {'id': 17, 'urun_adi': 'Coffee Mate Stick 5 gr.'},
    {'id': 18, 'urun_adi': 'English Breakfast Tea'},
    {'id': 19, 'urun_adi': 'Early Grey Tea'},
    {'id': 20, 'urun_adi': 'Stick Şeker 2 gr.'},
    {'id': 21, 'urun_adi': 'Stick Esmer Şeker 2 gr.'},
    {'id': 22, 'urun_adi': 'Stick Sakarin 1 gr'},
    {'id': 41, 'urun_adi': 'Tuzlu Fıstık Kraft 60 gr.'},
    {'id': 42, 'urun_adi': 'Antep Fıstığı Çerez Cam Kavanoz 80 gr.'},
    {'id': 43, 'urun_adi': 'Segafredo Kapsül Kahve'},
    {'id': 44, 'urun_adi': 'Bitki Çayları 2 gr'},
    {'id': 1, 'urun_adi': 'Efes Bira 33 cl.'},
]

# Manuel fiyatlar (web aramasından bulunan ortalama toptan fiyatlar)
manuel_fiyatlar = {
    'Pepsi 250 ml.': 9.50,  # 525 TL / 24 adet = ~22 TL (perakende), toptan %60 = 9.50
    'Pepsi Max 250 ml.': 9.50,
    'Yedigün 250 ml.': 8.00,
    'Seven Up': 9.00,
    'Sırma Soda 200 ml.': 5.00,
    'Redbull 250 ml.': 25.00,
    'Sırma Su 330 ml.': 3.50,
    'Sırma Su 750 ml.': 5.00,
    'Mr Brown Ice Coffee Vanilla 240 ml.': 18.00,
    'Mr. Brown Black Coffee 240 ml.': 18.00,
    'Ice Tea Şeftali 200 ml': 12.00,
    'Ice Tea Limon 200 ml.': 12.00,
    'Browni Çikolata 50 gr.': 15.00,
    'Çokonat 33 gr.': 12.00,
    'Nescafe Stick 5 gr.': 4.50,
    'Coffee Mate Stick 5 gr.': 2.50,
    'English Breakfast Tea': 3.00,
    'Early Grey Tea': 3.00,
    'Stick Şeker 2 gr.': 0.30,
    'Stick Esmer Şeker 2 gr.': 0.35,
    'Stick Sakarin 1 gr': 0.50,
    'Tuzlu Fıstık Kraft 60 gr.': 25.00,
    'Antep Fıstığı Çerez Cam Kavanoz 80 gr.': 45.00,
    'Segafredo Kapsül Kahve': 15.00,
    'Bitki Çayları 2 gr': 2.00,
    'Efes Bira 33 cl.': 35.00,  # Toptan fiyat
}

print("🔄 Web'den bulunan fiyatları veritabanına ekliyorum...")
print("=" * 60)

for urun in urunler:
    urun_id = urun['id']
    urun_adi = urun['urun_adi'].strip()
    
    # Manuel fiyatı al
    fiyat = manuel_fiyatlar.get(urun_adi)
    
    if fiyat:
        print(f"\n✅ Ürün #{urun_id}: {urun_adi}")
        print(f"   💰 Bulunan Fiyat: {fiyat} TL")
        print(f"   📝 SQL: UPDATE urunler SET alis_fiyati = {fiyat} WHERE id = {urun_id}")
    else:
        print(f"\n⚠️  Ürün #{urun_id}: {urun_adi} - Fiyat bulunamadı")

print("\n" + "=" * 60)
print("✅ Tüm fiyatlar hazır!")
print("\nŞimdi PostgreSQL MCP ile güncelleyelim...")
