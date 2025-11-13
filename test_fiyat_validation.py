"""
FiyatValidation Sınıfı Test Scripti
Erkan için hızlı test ve doğrulama
"""
from utils.validation import FiyatValidation

def test_validate_fiyat():
    """Fiyat validasyon testleri"""
    print("=" * 60)
    print("FIYAT VALIDASYON TESTLERİ")
    print("=" * 60)
    
    test_cases = [
        (100.50, "Geçerli fiyat"),
        (-50, "Negatif fiyat (HATA BEKLENİYOR)"),
        (0, "Sıfır fiyat"),
        (999999.99, "Maksimum fiyat"),
        (1000000, "Maksimum üstü fiyat (HATA BEKLENİYOR)"),
        ("abc", "Geçersiz tip (HATA BEKLENİYOR)"),
        (None, "None değer (HATA BEKLENİYOR)"),
        (50.999, "3 ondalık basamak (HATA BEKLENİYOR)"),
    ]
    
    for fiyat, aciklama in test_cases:
        gecerli, hata = FiyatValidation.validate_fiyat(fiyat)
        status = "✓ BAŞARILI" if gecerli else "✗ HATA"
        print(f"\n{status}: {aciklama}")
        print(f"  Değer: {fiyat}")
        if not gecerli:
            print(f"  Hata: {hata}")

def test_validate_kampanya():
    """Kampanya validasyon testleri"""
    print("\n" + "=" * 60)
    print("KAMPANYA VALIDASYON TESTLERİ")
    print("=" * 60)
    
    test_cases = [
        ("yuzde", 20, 1, 100, "Geçerli yüzde kampanyası"),
        ("tutar", 50, 2, 50, "Geçerli tutar kampanyası"),
        ("yuzde", 150, 1, 100, "Yüzde 100'den fazla (HATA BEKLENİYOR)"),
        ("yuzde", -10, 1, 100, "Negatif indirim (HATA BEKLENİYOR)"),
        ("tutar", 15000, 1, 100, "Çok yüksek tutar (HATA BEKLENİYOR)"),
        ("gecersiz", 20, 1, 100, "Geçersiz tip (HATA BEKLENİYOR)"),
    ]
    
    for indirim_tipi, indirim_degeri, min_siparis, max_kullanim, aciklama in test_cases:
        gecerli, hata = FiyatValidation.validate_kampanya(
            indirim_tipi, indirim_degeri, min_siparis, max_kullanim
        )
        status = "✓ BAŞARILI" if gecerli else "✗ HATA"
        print(f"\n{status}: {aciklama}")
        print(f"  Tip: {indirim_tipi}, Değer: {indirim_degeri}")
        if not gecerli:
            print(f"  Hata: {hata}")

def test_validate_bedelsiz_limit():
    """Bedelsiz limit validasyon testleri"""
    print("\n" + "=" * 60)
    print("BEDELSIZ LİMİT VALIDASYON TESTLERİ")
    print("=" * 60)
    
    test_cases = [
        (10, 5, "misafir", "Geçerli limit"),
        (50, 0, "kampanya", "Kullanılmamış limit"),
        (100, 100, "personel", "Tam kullanılmış limit"),
        (0, 0, "misafir", "Sıfır limit (HATA BEKLENİYOR)"),
        (10, 15, "misafir", "Aşılmış limit (HATA BEKLENİYOR)"),
        (10, -5, "misafir", "Negatif kullanım (HATA BEKLENİYOR)"),
        (2000, 0, "misafir", "Çok yüksek limit (HATA BEKLENİYOR)"),
        (10, 5, "gecersiz", "Geçersiz tip (HATA BEKLENİYOR)"),
    ]
    
    for max_miktar, kullanilan, limit_tipi, aciklama in test_cases:
        gecerli, hata = FiyatValidation.validate_bedelsiz_limit(
            max_miktar, kullanilan, limit_tipi
        )
        status = "✓ BAŞARILI" if gecerli else "✗ HATA"
        print(f"\n{status}: {aciklama}")
        print(f"  Max: {max_miktar}, Kullanılan: {kullanilan}, Tip: {limit_tipi}")
        if not gecerli:
            print(f"  Hata: {hata}")

def test_validate_tarih_araligi():
    """Tarih aralığı validasyon testleri"""
    print("\n" + "=" * 60)
    print("TARİH ARALIĞI VALIDASYON TESTLERİ")
    print("=" * 60)
    
    from datetime import datetime, timedelta
    
    simdi = datetime.now()
    yarin = simdi + timedelta(days=1)
    bir_yil_sonra = simdi + timedelta(days=365)
    on_yil_sonra = simdi + timedelta(days=365 * 10)
    
    test_cases = [
        (simdi, yarin, "Geçerli aralık"),
        (simdi, bir_yil_sonra, "1 yıllık aralık"),
        (yarin, simdi, "Ters tarih (HATA BEKLENİYOR)"),
        (simdi, on_yil_sonra, "Çok uzun aralık (HATA BEKLENİYOR)"),
        (None, yarin, "None başlangıç (HATA BEKLENİYOR)"),
    ]
    
    for baslangic, bitis, aciklama in test_cases:
        gecerli, hata = FiyatValidation.validate_tarih_araligi(baslangic, bitis)
        status = "✓ BAŞARILI" if gecerli else "✗ HATA"
        print(f"\n{status}: {aciklama}")
        if not gecerli:
            print(f"  Hata: {hata}")

if __name__ == "__main__":
    try:
        test_validate_fiyat()
        test_validate_kampanya()
        test_validate_bedelsiz_limit()
        test_validate_tarih_araligi()
        
        print("\n" + "=" * 60)
        print("TÜM TESTLER TAMAMLANDI!")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n❌ TEST HATASI: {str(e)}")
        import traceback
        traceback.print_exc()
