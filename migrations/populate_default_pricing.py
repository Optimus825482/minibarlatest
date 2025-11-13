"""
Mevcut Verilere Fiyat Atama Script
Tarih: 2025-11-13
Açıklama: Tüm ürünlere varsayılan alış fiyatı atar, varsayılan tedarikçi oluşturur ve UrunStok kayıtları oluşturur
Gereksinimler: 20.1, 20.2, 21.1
"""

import sys
import os
from pathlib import Path

# Proje kök dizinini Python path'e ekle
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from flask import Flask
from models import db, Tedarikci, UrunTedarikciFiyat, Urun, UrunStok, Otel, Kullanici
from sqlalchemy import text
from dotenv import load_dotenv
from datetime import datetime, timezone
from decimal import Decimal

# .env dosyasını yükle
load_dotenv()

# Flask uygulaması oluştur
app = Flask(__name__)
app.config.from_object('config.Config')
db.init_app(app)

# Ürün fiyat eşleştirme tablosu (ff.md'den)
URUN_FIYATLARI = {
    # Bar ve Atıştırmalıklar
    "Bar Nestle Nesfit Kakaolu 23.5 Gr": 34.328,
    "Bar Nestle Nesfit Karamelli 23.5 Gr": 34.33,
    "Bar Nestle Nesfit Kırmızı Meyveli 23.5 Gr": 34.33,
    "Bar Nestle Nesfit Sütlü Çikolatalı Ve Muzlu 23.5 G": 34.326,
    
    # İçecekler
    "Bira Efes Şişe 33 Cl": 40.972,
    "Pepsi Kutu 250 Ml": 9.546,
    "Pepsi Kutu Max 250 Ml": 9.55,
    "Seven Up Kutu 250 Ml": 9.546,
    "Yedigün Kutu 250 Ml": 9.546,
    
    # Bisküvi ve Çikolatalar
    "Bisküvi Eti Crax Peynirli 50 Gr": 12.75,
    "Cips Pringels 40 Gr": 68.9,
    "Çikolata Snickers 50 Gr": 34.605,
    "Çikolata Twix Double Chocolate Bar 50 Gr": 31.455,
    "Eti Browni İntense 45 Gr": 25.705,
    "Ülker Çokonat 33 Gr": 19.04,
    
    # Çaylar
    "Çay Poşet Earl Grey Sade": 2.01,
    "Çay Poşet Englısh Breakfast Tea": 6.0,
    "Çay Poşet Ihlamur": 2.0,
    "Çay Poşet Papatya": 2.0,
    "Çay Poşet Yeşil Çay": 2.5,
    
    # Çerezler
    "Çerez Fıstık Tuzlu": 3.4,
    "Çerez Kesesi - Boş": 2.5,
    "Maretti Bruschette Cheese": 28.56,
    "Maretti Bruschette Tomato": 28.56,
    
    # Sakızlar
    "First Sensations Yeşil Nane Aromalı Sakız 27 G": 34.886,
    "Sakız First Sensations Çilek Aromalı 27 Gr (Miniba": 34.886,
    
    # Kahveler
    "Ice Coffe 240 Ml Mr Brown Black": 45.447,
    "Kahve Kreması Nescafe Stick": 3.072,
    "Kahve Mehmet Efendi": 22.815,
    "Kahve Nescafe Stick Gold": 7.064,
    "Kahve Segafredo Kapsül": 21.861,
    
    # Şaraplar
    "Jp Chenet Ice Edition 20 Cl": 99.0,
    "Maison Castel Chardonnay 187 ml": 52.08,
    "Maison Castel Merlot 187 Ml": 52.08,
    "Mateus Rose Orgınal 25 Cl": 50.25,
    
    # Sular ve Sodalar
    "Soda Şişe Sade 200 Ml (Beypazarı)": 8.0,
    "Soguk Çay 330 Ml Seftali (Lipton)": 26.452,
    "Su Cam Logolu (Sırma) 330 Ml": 17.5,
    "Su Cam Logolu (Sırma) 750 Ml": 36.5,
    "Su Mineralli Pellegrino 250 Ml": 83.0,
    "Su Mineralli Perrier 330 Ml": 102.0,
    
    # Diğer
    "Kavanoz 210 Cc Metal Kapakli": 13.0,
    "Sakarin Stick": 0.65,
    "Şeker Stick Beyaz": 0.45,
    "Şeker Stick Esmer": 0.5,
}

# Varsayılan fiyat (eşleşmeyen ürünler için)
VARSAYILAN_ALIS_FIYATI = 10.00
VARSAYILAN_SATIS_FIYATI = 20.00  # %100 kar marjı


def normalize_urun_adi(urun_adi):
    """Ürün adını normalize et (karşılaştırma için)"""
    if not urun_adi:
        return ""
    
    # Küçük harfe çevir ve fazla boşlukları temizle
    normalized = urun_adi.lower().strip()
    
    # Özel karakterleri temizle
    replacements = {
        'ı': 'i',
        'ğ': 'g',
        'ü': 'u',
        'ş': 's',
        'ö': 'o',
        'ç': 'c',
        'İ': 'i',
        'Ğ': 'g',
        'Ü': 'u',
        'Ş': 's',
        'Ö': 'o',
        'Ç': 'c',
    }
    
    for old, new in replacements.items():
        normalized = normalized.replace(old, new)
    
    # Noktalama işaretlerini kaldır
    normalized = normalized.replace('.', '').replace(',', '')
    
    return normalized


def extract_keywords(urun_adi):
    """Ürün adından anahtar kelimeleri çıkar"""
    normalized = normalize_urun_adi(urun_adi)
    
    # Gereksiz kelimeleri çıkar
    stop_words = ['kutu', 'sise', 'cam', 'poset', 'stick', 'gr', 'ml', 'cl', 'logolu', 'aromalı', 'aromali']
    
    words = normalized.split()
    keywords = [w for w in words if w not in stop_words and len(w) > 2]
    
    return set(keywords)


def find_matching_price(urun_adi):
    """Ürün adına göre fiyat bul (gelişmiş fuzzy matching)"""
    normalized_urun = normalize_urun_adi(urun_adi)
    urun_keywords = extract_keywords(urun_adi)
    
    # Tam eşleşme ara
    for fiyat_urun, fiyat in URUN_FIYATLARI.items():
        if normalize_urun_adi(fiyat_urun) == normalized_urun:
            return Decimal(str(fiyat)), fiyat_urun
    
    # Anahtar kelime eşleşmesi ara (en az 2 kelime eşleşmeli)
    best_match = None
    best_score = 0
    
    for fiyat_urun, fiyat in URUN_FIYATLARI.items():
        fiyat_keywords = extract_keywords(fiyat_urun)
        
        # Ortak kelimeleri say
        common_keywords = urun_keywords.intersection(fiyat_keywords)
        score = len(common_keywords)
        
        # En az 2 kelime eşleşmeli ve önceki en iyi skordan yüksek olmalı
        if score >= 2 and score > best_score:
            best_score = score
            best_match = (Decimal(str(fiyat)), fiyat_urun)
    
    if best_match:
        return best_match
    
    # Kısmi eşleşme ara (tek kelime bile eşleşse)
    for fiyat_urun, fiyat in URUN_FIYATLARI.items():
        normalized_fiyat_urun = normalize_urun_adi(fiyat_urun)
        
        # Önemli kelimeleri kontrol et
        if any(keyword in normalized_fiyat_urun for keyword in ['efes', 'pepsi', 'seven', 'yedigun', 'redbull', 'sirma', 'perrier', 'pellegrino']):
            if any(keyword in normalized_urun for keyword in ['efes', 'pepsi', 'seven', 'yedigun', 'redbull', 'sirma', 'perrier', 'pellegrino']):
                # Marka eşleşmesi var, boyut kontrolü yap
                if any(size in normalized_urun and size in normalized_fiyat_urun for size in ['250', '330', '750', '33', '200', '240']):
                    return Decimal(str(fiyat)), fiyat_urun
    
    # Eşleşme bulunamadı, varsayılan fiyat
    return Decimal(str(VARSAYILAN_ALIS_FIYATI)), None


def create_default_supplier():
    """Varsayılan tedarikçi oluştur"""
    try:
        # Varsayılan tedarikçi var mı kontrol et
        tedarikci = Tedarikci.query.filter_by(tedarikci_adi='Varsayılan Tedarikçi').first()
        
        if not tedarikci:
            print("   📦 Varsayılan tedarikçi oluşturuluyor...")
            tedarikci = Tedarikci(
                tedarikci_adi='Varsayılan Tedarikçi',
                iletisim_bilgileri={
                    'telefon': '',
                    'email': '',
                    'adres': 'Sistem tarafından otomatik oluşturuldu'
                },
                aktif=True,
                olusturma_tarihi=datetime.now(timezone.utc)
            )
            db.session.add(tedarikci)
            db.session.commit()
            print(f"   ✅ Varsayılan tedarikçi oluşturuldu (ID: {tedarikci.id})")
        else:
            print(f"   ℹ️  Varsayılan tedarikçi zaten mevcut (ID: {tedarikci.id})")
        
        return tedarikci
        
    except Exception as e:
        db.session.rollback()
        raise Exception(f"Tedarikçi oluşturma hatası: {e}")


def assign_prices_to_products(tedarikci):
    """Tüm ürünlere alış fiyatı ata"""
    try:
        # Sistem kullanıcısını bul (ID=1 genellikle ilk admin)
        sistem_kullanici = Kullanici.query.filter_by(rol='sistem_yoneticisi').first()
        if not sistem_kullanici:
            sistem_kullanici = Kullanici.query.first()
        
        if not sistem_kullanici:
            raise Exception("Sistem kullanıcısı bulunamadı!")
        
        # Tüm ürünleri getir
        urunler = Urun.query.filter_by(aktif=True).all()
        
        print(f"\n   📋 {len(urunler)} ürüne fiyat atanıyor...")
        
        basarili = 0
        eslesen = 0
        varsayilan = 0
        
        for urun in urunler:
            try:
                # Bu ürün için zaten fiyat var mı kontrol et
                mevcut_fiyat = UrunTedarikciFiyat.query.filter_by(
                    urun_id=urun.id,
                    tedarikci_id=tedarikci.id,
                    aktif=True
                ).first()
                
                if mevcut_fiyat:
                    continue  # Zaten fiyat var, atla
                
                # Fiyat bul
                alis_fiyati, eslesen_urun = find_matching_price(urun.urun_adi)
                
                if eslesen_urun:
                    eslesen += 1
                    print(f"   ✓ {urun.urun_adi} → {eslesen_urun} ({alis_fiyati} TL)")
                else:
                    varsayilan += 1
                
                # Fiyat kaydı oluştur
                urun_fiyat = UrunTedarikciFiyat(
                    urun_id=urun.id,
                    tedarikci_id=tedarikci.id,
                    alis_fiyati=alis_fiyati,
                    minimum_miktar=1,
                    baslangic_tarihi=datetime.now(timezone.utc),
                    bitis_tarihi=None,
                    aktif=True,
                    olusturma_tarihi=datetime.now(timezone.utc),
                    olusturan_id=sistem_kullanici.id
                )
                
                db.session.add(urun_fiyat)
                basarili += 1
                
                # Her 50 üründe bir commit
                if basarili % 50 == 0:
                    db.session.commit()
                    print(f"   ⏳ {basarili} ürün işlendi...")
                
            except Exception as e:
                print(f"   ⚠️  {urun.urun_adi} için fiyat atanamadı: {e}")
                continue
        
        # Son commit
        db.session.commit()
        
        print(f"\n   ✅ Fiyat atama tamamlandı:")
        print(f"      • Başarılı: {basarili} ürün")
        print(f"      • Eşleşen fiyat: {eslesen} ürün")
        print(f"      • Varsayılan fiyat: {varsayilan} ürün")
        
        return basarili
        
    except Exception as e:
        db.session.rollback()
        raise Exception(f"Fiyat atama hatası: {e}")


def create_urun_stok_records():
    """Tüm ürünler için UrunStok kayıtları oluştur"""
    try:
        # Tüm otelleri getir
        oteller = Otel.query.filter_by(aktif=True).all()
        
        if not oteller:
            print("   ⚠️  Aktif otel bulunamadı, stok kayıtları oluşturulamadı")
            return 0
        
        # Tüm ürünleri getir
        urunler = Urun.query.filter_by(aktif=True).all()
        
        print(f"\n   📦 {len(urunler)} ürün × {len(oteller)} otel = {len(urunler) * len(oteller)} stok kaydı oluşturuluyor...")
        
        basarili = 0
        
        for otel in oteller:
            for urun in urunler:
                try:
                    # Bu ürün-otel kombinasyonu için zaten stok kaydı var mı?
                    mevcut_stok = UrunStok.query.filter_by(
                        urun_id=urun.id,
                        otel_id=otel.id
                    ).first()
                    
                    if mevcut_stok:
                        continue  # Zaten var, atla
                    
                    # Ürünün alış fiyatını bul
                    urun_fiyat = UrunTedarikciFiyat.query.filter_by(
                        urun_id=urun.id,
                        aktif=True
                    ).first()
                    
                    birim_maliyet = urun_fiyat.alis_fiyati if urun_fiyat else Decimal('0')
                    
                    # Stok kaydı oluştur
                    stok = UrunStok(
                        urun_id=urun.id,
                        otel_id=otel.id,
                        mevcut_stok=0,  # Başlangıçta 0
                        minimum_stok=urun.kritik_stok_seviyesi or 10,
                        maksimum_stok=1000,
                        kritik_stok_seviyesi=urun.kritik_stok_seviyesi or 5,
                        birim_maliyet=birim_maliyet,
                        toplam_deger=Decimal('0'),  # 0 × birim_maliyet = 0
                        son_30gun_cikis=0,
                        stok_devir_hizi=Decimal('0'),
                        son_guncelleme_tarihi=datetime.now(timezone.utc)
                    )
                    
                    db.session.add(stok)
                    basarili += 1
                    
                    # Her 100 kayıtta bir commit
                    if basarili % 100 == 0:
                        db.session.commit()
                        print(f"   ⏳ {basarili} stok kaydı oluşturuldu...")
                    
                except Exception as e:
                    print(f"   ⚠️  {urun.urun_adi} - {otel.ad} için stok kaydı oluşturulamadı: {e}")
                    continue
        
        # Son commit
        db.session.commit()
        
        print(f"\n   ✅ Stok kayıtları oluşturuldu: {basarili} kayıt")
        
        return basarili
        
    except Exception as e:
        db.session.rollback()
        raise Exception(f"Stok kaydı oluşturma hatası: {e}")


def main():
    """Ana işlem"""
    with app.app_context():
        try:
            print("\n" + "="*70)
            print("🚀 MEVCUT VERİLERE FİYAT ATAMA BAŞLIYOR")
            print("="*70 + "\n")
            
            # 1. Varsayılan tedarikçi oluştur
            print("📋 1. Varsayılan tedarikçi oluşturuluyor...")
            tedarikci = create_default_supplier()
            print()
            
            # 2. Tüm ürünlere fiyat ata
            print("📋 2. Ürünlere alış fiyatları atanıyor...")
            fiyat_sayisi = assign_prices_to_products(tedarikci)
            print()
            
            # 3. UrunStok kayıtları oluştur
            print("📋 3. UrunStok kayıtları oluşturuluyor...")
            stok_sayisi = create_urun_stok_records()
            print()
            
            print("="*70)
            print("✅ İŞLEM BAŞARIYLA TAMAMLANDI!")
            print("="*70)
            print(f"\n📊 Özet:")
            print(f"   • Tedarikçi: 1 adet (Varsayılan Tedarikçi)")
            print(f"   • Fiyat Ataması: {fiyat_sayisi} ürün")
            print(f"   • Stok Kayıtları: {stok_sayisi} kayıt")
            print(f"\n💡 Not: Eşleşmeyen ürünlere varsayılan fiyat ({VARSAYILAN_ALIS_FIYATI} TL) atandı")
            print(f"   Bu fiyatları admin panelinden güncelleyebilirsiniz.\n")
            
        except Exception as e:
            print(f"\n❌ HATA: {str(e)}\n")
            raise


if __name__ == '__main__':
    main()
