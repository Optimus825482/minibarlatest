"""
Urun Fiyat Gecmisi tablosundaki alış fiyatlarını Urunler tablosuna aktar
"""
import sys
import os

# Proje kök dizinini path'e ekle
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models import db, Urun, UrunFiyatGecmisi  # type: ignore[attr-defined]

def migrate_fiyat_data():
    """Fiyat geçmişindeki en son alış fiyatlarını urunler tablosuna aktar"""
    
    # Flask app'i oluştur
    from flask import Flask
    app = Flask(__name__)
    app.config.from_object('config.Config')
    db.init_app(app)
    
    with app.app_context():
        try:
            print("🔄 Fiyat geçmişi verilerini aktarma başlıyor...")
            
            # Tüm ürünleri al
            urunler = Urun.query.all()
            guncellenen_sayisi = 0
            
            for urun in urunler:
                # Bu ürün için en son alış fiyatı kaydını bul
                en_son_alis_fiyat = UrunFiyatGecmisi.query.filter(
                    UrunFiyatGecmisi.urun_id == urun.id,
                    UrunFiyatGecmisi.degisiklik_tipi == 'alis_fiyati'
                ).order_by(
                    UrunFiyatGecmisi.degisiklik_tarihi.desc()
                ).first()
                
                if en_son_alis_fiyat:
                    # Ürünün alış fiyatını güncelle
                    eski_fiyat = urun.alis_fiyati
                    urun.alis_fiyati = en_son_alis_fiyat.yeni_fiyat
                    
                    print(f"✅ Ürün #{urun.id} ({urun.urun_adi}): {eski_fiyat} -> {en_son_alis_fiyat.yeni_fiyat}")
                    guncellenen_sayisi += 1
                else:
                    print(f"⚠️  Ürün #{urun.id} ({urun.urun_adi}): Fiyat geçmişi bulunamadı")
            
            # Değişiklikleri kaydet
            db.session.commit()
            
            print(f"\n✅ Toplam {guncellenen_sayisi} ürünün alış fiyatı güncellendi!")
            print(f"📊 Toplam {len(urunler)} ürün kontrol edildi")
            
        except Exception as e:
            db.session.rollback()
            print(f"❌ HATA: {str(e)}")
            raise

if __name__ == '__main__':
    migrate_fiyat_data()
