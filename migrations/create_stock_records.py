"""
Tüm Ürünler İçin Stok Kayıtları Oluştur
Erkan için - UrunStok tablosunu doldur
"""
from app import app, db
from models import Urun, UrunStok, Otel
from datetime import datetime

def create_stock_records():
    """Her ürün için her otelde stok kaydı oluştur"""
    with app.app_context():
        print("🔄 Stok kayıtları oluşturuluyor...\n")
        
        # Tüm ürünleri ve otelleri getir
        urunler = Urun.query.filter_by(aktif=True).all()
        oteller = Otel.query.filter_by(aktif=True).all()
        
        if not oteller:
            print("⚠️  Aktif otel bulunamadı! Önce otel ekleyin.")
            return
        
        olusturulan = 0
        mevcut = 0
        
        for otel in oteller:
            for urun in urunler:
                # Stok kaydı var mı kontrol et
                stok = UrunStok.query.filter_by(
                    urun_id=urun.id,
                    otel_id=otel.id
                ).first()
                
                if not stok:
                    # Yeni stok kaydı oluştur
                    stok = UrunStok(
                        urun_id=urun.id,
                        otel_id=otel.id,
                        mevcut_stok=0,
                        minimum_stok=10,
                        maksimum_stok=1000,
                        kritik_stok_seviyesi=5,
                        birim_maliyet=0,
                        toplam_deger=0,
                        son_30gun_cikis=0,
                        stok_devir_hizi=0,
                        son_guncelleme_tarihi=datetime.now(),
                        sayim_farki=0
                    )
                    db.session.add(stok)
                    olusturulan += 1
                    
                    if olusturulan % 50 == 0:
                        print(f"   {olusturulan} kayıt oluşturuldu...")
                else:
                    mevcut += 1
        
        # Kaydet
        try:
            db.session.commit()
            print(f"\n{'='*60}")
            print(f"✅ Stok kayıtları oluşturuldu!")
            print(f"   Yeni oluşturulan: {olusturulan}")
            print(f"   Zaten mevcut: {mevcut}")
            print(f"   Toplam ürün: {len(urunler)}")
            print(f"   Toplam otel: {len(oteller)}")
            print(f"{'='*60}")
        except Exception as e:
            db.session.rollback()
            print(f"\n❌ Hata: {str(e)}")


if __name__ == '__main__':
    create_stock_records()
