# FiyatValidation Sınıfı Kullanım Kılavuzu

## Genel Bakış

`FiyatValidation` sınıfı, fiyatlandırma ve karlılık hesaplama sistemi için özel validasyon fonksiyonları sağlar. Bu sınıf, fiyat, kampanya ve bedelsiz limit verilerinin güvenli ve doğru şekilde işlenmesini garanti eder.

## Kurulum

```python
from utils.validation import FiyatValidation, get_fiyat_validator

# Direkt sınıf kullanımı
validator = FiyatValidation()

# Veya global instance
validator = get_fiyat_validator()
```

## Fonksiyonlar

### 1. validate_fiyat()

Fiyat değerlerini doğrular. Negatif fiyat, geçersiz format ve aralık dışı değerleri kontrol eder.

**Parametreler:**

- `fiyat` (Any): Kontrol edilecek fiyat değeri
- `min_fiyat` (float, opsiyonel): Minimum kabul edilebilir fiyat (varsayılan: 0.0)
- `max_fiyat` (float, opsiyonel): Maksimum kabul edilebilir fiyat (varsayılan: 999999.99)

**Dönüş:**

- `tuple[bool, Optional[str]]`: (geçerli_mi, hata_mesajı)

**Örnekler:**

```python
# Geçerli fiyat
gecerli, hata = FiyatValidation.validate_fiyat(100.50)
# Sonuç: (True, None)

# Negatif fiyat (HATA)
gecerli, hata = FiyatValidation.validate_fiyat(-50)
# Sonuç: (False, "Fiyat negatif olamaz")

# Çok yüksek fiyat (HATA)
gecerli, hata = FiyatValidation.validate_fiyat(2000000)
# Sonuç: (False, "Fiyat maksimum 999999.99 TL olabilir")

# Özel aralık kontrolü
gecerli, hata = FiyatValidation.validate_fiyat(5, min_fiyat=10, max_fiyat=1000)
# Sonuç: (False, "Fiyat minimum 10 TL olmalıdır")
```

**Kontrol Edilen Durumlar:**

- ✓ None kontrolü
- ✓ Tip dönüşümü
- ✓ Negatif değer kontrolü
- ✓ Minimum/maksimum aralık kontrolü
- ✓ Ondalık basamak kontrolü (max 2 basamak)

---

### 2. validate_kampanya()

Kampanya parametrelerini doğrular. İndirim tipi, değer ve kullanım limitlerini kontrol eder.

**Parametreler:**

- `indirim_tipi` (str): 'yuzde' veya 'tutar'
- `indirim_degeri` (Any): İndirim değeri
- `min_siparis_miktari` (int, opsiyonel): Minimum sipariş miktarı
- `max_kullanim_sayisi` (int, opsiyonel): Maksimum kullanım sayısı

**Dönüş:**

- `tuple[bool, Optional[str]]`: (geçerli_mi, hata_mesajı)

**Örnekler:**

```python
# Geçerli yüzde kampanyası
gecerli, hata = FiyatValidation.validate_kampanya(
    indirim_tipi='yuzde',
    indirim_degeri=20,
    min_siparis_miktari=1,
    max_kullanim_sayisi=100
)
# Sonuç: (True, None)

# Geçersiz indirim oranı (HATA)
gecerli, hata = FiyatValidation.validate_kampanya(
    indirim_tipi='yuzde',
    indirim_degeri=150
)
# Sonuç: (False, "İndirim oranı %100'den fazla olamaz")

# Geçerli tutar kampanyası
gecerli, hata = FiyatValidation.validate_kampanya(
    indirim_tipi='tutar',
    indirim_degeri=50.00
)
# Sonuç: (True, None)
```

**Kontrol Edilen Durumlar:**

- ✓ İndirim tipi kontrolü ('yuzde' veya 'tutar')
- ✓ İndirim değeri tip kontrolü
- ✓ Negatif ve sıfır değer kontrolü
- ✓ Yüzde için %1-%100 aralık kontrolü
- ✓ Tutar için maksimum 10,000 TL kontrolü
- ✓ Minimum sipariş miktarı kontrolü (1-1000)
- ✓ Maksimum kullanım sayısı kontrolü (1-100,000)

---

### 3. validate_bedelsiz_limit()

Bedelsiz tüketim limitlerini doğrular. Limit miktarı ve kullanım durumunu kontrol eder.

**Parametreler:**

- `max_miktar` (int): Maksimum bedelsiz miktar
- `kullanilan_miktar` (int, opsiyonel): Kullanılan miktar (varsayılan: 0)
- `limit_tipi` (str, opsiyonel): 'misafir', 'kampanya' veya 'personel'

**Dönüş:**

- `tuple[bool, Optional[str]]`: (geçerli_mi, hata_mesajı)

**Örnekler:**

```python
# Geçerli limit
gecerli, hata = FiyatValidation.validate_bedelsiz_limit(
    max_miktar=10,
    kullanilan_miktar=5,
    limit_tipi='misafir'
)
# Sonuç: (True, None)

# Aşılmış limit (HATA)
gecerli, hata = FiyatValidation.validate_bedelsiz_limit(
    max_miktar=10,
    kullanilan_miktar=15
)
# Sonuç: (False, "Kullanılan miktar (15) maksimum miktardan (10) fazla olamaz")

# Negatif kullanım (HATA)
gecerli, hata = FiyatValidation.validate_bedelsiz_limit(
    max_miktar=10,
    kullanilan_miktar=-5
)
# Sonuç: (False, "Kullanılan miktar negatif olamaz")
```

**Kontrol Edilen Durumlar:**

- ✓ Maksimum miktar tip kontrolü
- ✓ Maksimum miktar aralık kontrolü (1-1000)
- ✓ Kullanılan miktar tip kontrolü
- ✓ Negatif kullanım kontrolü
- ✓ Kullanılan > Maksimum kontrolü
- ✓ Limit tipi kontrolü (opsiyonel)

---

### 4. validate_tarih_araligi()

Tarih aralıklarını doğrular. Başlangıç ve bitiş tarihlerinin mantıklı olduğunu kontrol eder.

**Parametreler:**

- `baslangic_tarihi` (Any): Başlangıç tarihi (datetime veya ISO string)
- `bitis_tarihi` (Any): Bitiş tarihi (datetime veya ISO string)

**Dönüş:**

- `tuple[bool, Optional[str]]`: (geçerli_mi, hata_mesajı)

**Örnekler:**

```python
from datetime import datetime, timedelta

simdi = datetime.now()
yarin = simdi + timedelta(days=1)

# Geçerli aralık
gecerli, hata = FiyatValidation.validate_tarih_araligi(simdi, yarin)
# Sonuç: (True, None)

# Ters tarih (HATA)
gecerli, hata = FiyatValidation.validate_tarih_araligi(yarin, simdi)
# Sonuç: (False, "Bitiş tarihi başlangıç tarihinden önce olamaz")

# ISO string formatı
gecerli, hata = FiyatValidation.validate_tarih_araligi(
    "2024-01-01T00:00:00",
    "2024-12-31T23:59:59"
)
# Sonuç: (True, None)
```

**Kontrol Edilen Durumlar:**

- ✓ None kontrolü
- ✓ Datetime dönüşümü (ISO string desteği)
- ✓ Bitiş < Başlangıç kontrolü
- ✓ Maksimum aralık kontrolü (5 yıl)

---

### 5. validate_oda_tipi()

Oda tipi değerlerini doğrular. SQL injection ve geçersiz karakterleri kontrol eder.

**Parametreler:**

- `oda_tipi` (str): Oda tipi

**Dönüş:**

- `tuple[bool, Optional[str]]`: (geçerli_mi, hata_mesajı)

**Örnekler:**

```python
# Geçerli oda tipi
gecerli, hata = FiyatValidation.validate_oda_tipi("Standard")
# Sonuç: (True, None)

# Çok kısa (HATA)
gecerli, hata = FiyatValidation.validate_oda_tipi("A")
# Sonuç: (False, "Oda tipi en az 2 karakter olmalıdır")

# SQL injection denemesi (HATA)
gecerli, hata = FiyatValidation.validate_oda_tipi("Standard' OR '1'='1")
# Sonuç: (False, "Oda tipi geçersiz karakterler içeriyor")
```

**Kontrol Edilen Durumlar:**

- ✓ Boş değer kontrolü
- ✓ Minimum uzunluk kontrolü (2 karakter)
- ✓ Maksimum uzunluk kontrolü (100 karakter)
- ✓ SQL injection kontrolü

---

## API Endpoint'lerinde Kullanım

### Flask Route Örneği

```python
from flask import request, jsonify
from utils.validation import get_fiyat_validator

@app.route('/api/v1/fiyat/urun/<int:urun_id>/guncelle', methods=['POST'])
@login_required
def update_urun_fiyat(urun_id):
    """Ürün fiyatını güncelle"""
    try:
        data = request.get_json()
        validator = get_fiyat_validator()

        # Alış fiyatı validasyonu
        alis_fiyati = data.get('alis_fiyati')
        gecerli, hata = validator.validate_fiyat(alis_fiyati)
        if not gecerli:
            return jsonify({'success': False, 'message': hata}), 400

        # Satış fiyatı validasyonu
        satis_fiyati = data.get('satis_fiyati')
        gecerli, hata = validator.validate_fiyat(satis_fiyati)
        if not gecerli:
            return jsonify({'success': False, 'message': hata}), 400

        # Fiyat güncelleme işlemi...

        return jsonify({'success': True, 'message': 'Fiyat güncellendi'})

    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500
```

### Kampanya Oluşturma Örneği

```python
@app.route('/api/v1/fiyat/kampanya', methods=['POST'])
@login_required
def create_kampanya():
    """Yeni kampanya oluştur"""
    try:
        data = request.get_json()
        validator = get_fiyat_validator()

        # Kampanya validasyonu
        gecerli, hata = validator.validate_kampanya(
            indirim_tipi=data.get('indirim_tipi'),
            indirim_degeri=data.get('indirim_degeri'),
            min_siparis_miktari=data.get('min_siparis_miktari'),
            max_kullanim_sayisi=data.get('max_kullanim_sayisi')
        )

        if not gecerli:
            return jsonify({'success': False, 'message': hata}), 400

        # Tarih aralığı validasyonu
        gecerli, hata = validator.validate_tarih_araligi(
            data.get('baslangic_tarihi'),
            data.get('bitis_tarihi')
        )

        if not gecerli:
            return jsonify({'success': False, 'message': hata}), 400

        # Kampanya oluşturma işlemi...

        return jsonify({'success': True, 'message': 'Kampanya oluşturuldu'})

    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500
```

## Servis Katmanında Kullanım

```python
from utils.validation import get_fiyat_validator

class FiyatYonetimServisi:
    """Fiyat yönetimi servisi"""

    @staticmethod
    def dinamik_fiyat_hesapla(urun_id, oda_id=None, tarih=None, miktar=1):
        """Dinamik fiyat hesaplama"""
        try:
            validator = get_fiyat_validator()

            # Miktar validasyonu
            if miktar < 1 or miktar > 1000:
                raise ValueError("Miktar 1-1000 arasında olmalıdır")

            # Fiyat hesaplama...
            alis_fiyati = 50.00
            satis_fiyati = 100.00

            # Hesaplanan fiyatları validate et
            gecerli, hata = validator.validate_fiyat(alis_fiyati)
            if not gecerli:
                raise ValueError(f"Alış fiyatı geçersiz: {hata}")

            gecerli, hata = validator.validate_fiyat(satis_fiyati)
            if not gecerli:
                raise ValueError(f"Satış fiyatı geçersiz: {hata}")

            return {
                'alis_fiyati': alis_fiyati,
                'satis_fiyati': satis_fiyati,
                'kar_tutari': satis_fiyati - alis_fiyati
            }

        except Exception as e:
            logger.error(f"Fiyat hesaplama hatası: {str(e)}")
            raise
```

## Hata Yönetimi

Tüm validasyon fonksiyonları `(bool, Optional[str])` tuple döner:

- İlk değer: Validasyon başarılı mı? (True/False)
- İkinci değer: Hata mesajı (başarılıysa None)

```python
gecerli, hata = validator.validate_fiyat(fiyat)

if gecerli:
    # İşleme devam et
    print("Fiyat geçerli!")
else:
    # Hatayı kullanıcıya göster
    print(f"Hata: {hata}")
```

## Güvenlik Özellikleri

1. **SQL Injection Koruması**: Oda tipi ve string değerler SQL injection'a karşı kontrol edilir
2. **Tip Güvenliği**: Tüm değerler doğru tipe dönüştürülür veya hata verilir
3. **Aralık Kontrolü**: Mantıklı minimum/maksimum değerler zorlanır
4. **Logging**: Tüm şüpheli durumlar loglanır
5. **Exception Handling**: Tüm hatalar yakalanır ve güvenli mesajlar döner

## Performans

- Tüm validasyon fonksiyonları O(1) karmaşıklığındadır
- Regex kontrolleri optimize edilmiştir
- Veritabanı sorgusu yapılmaz (stateless)
- Thread-safe tasarım

## Requirements Mapping

- **validate_fiyat()**: Requirement 2.1
- **validate_kampanya()**: Requirement 5.1
- **validate_bedelsiz_limit()**: Requirement 6.1

## Test Etme

Test scripti ile tüm fonksiyonları test edebilirsiniz:

```bash
python test_fiyat_validation.py
```

## Notlar

- Tüm fiyat değerleri Decimal tipinde saklanmalıdır (float değil)
- Tarih değerleri timezone-aware olmalıdır
- Validasyon başarısız olduğunda işlem yapılmamalıdır
- Hata mesajları kullanıcı dostu Türkçe'dir

## Destek

Sorularınız için: Erkan ile iletişime geçin
