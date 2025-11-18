# Setup Dolap İçi / Dolap Dışı Özelliği Eklendi

## Yapılan Değişiklikler

### 1. Veritabanı Migration

**Dosya**: `migrations_manual/add_setup_dolap_ici.sql`

```sql
ALTER TABLE setuplar
ADD COLUMN IF NOT EXISTS dolap_ici BOOLEAN DEFAULT TRUE;
```

- ✅ `dolap_ici` kolonu eklendi (Boolean)
- ✅ Varsayılan değer: `TRUE` (Dolap İçi)
- ✅ Migration başarıyla çalıştırıldı

### 2. Model Güncelleme

**Dosya**: `models.py`

```python
class Setup(db.Model):
    dolap_ici = db.Column(db.Boolean, default=True)  # True: Dolap İçi, False: Dolap Dışı
```

### 3. Frontend Güncellemeleri

**Dosya**: `templates/sistem_yoneticisi/setup_yonetimi.html`

#### Yeni Setup Modal

- ✅ "Yerleşim" select alanı eklendi
- ✅ Seçenekler: "Dolap İçi" / "Dolap Dışı"
- ✅ Varsayılan: "Dolap İçi"

#### Setup Düzenle Modal

- ✅ "Yerleşim" select alanı eklendi
- ✅ Mevcut değer otomatik seçili geliyor

#### Setup Listesi Tablosu

- ✅ "Yerleşim" sütunu eklendi
- ✅ Dolap İçi: Yeşil badge
- ✅ Dolap Dışı: Turuncu badge

#### JavaScript Fonksiyonları

```javascript
// setupKaydet - dolap_ici parametresi eklendi
const dolap_ici = document.getElementById("yeni_setup_dolap_ici").value === "true";

// setupDuzenleModal - dolapIci parametresi eklendi
function setupDuzenleModal(setupId, setupAd, setupAciklama, dolapIci)

// setupGuncelle - dolap_ici parametresi eklendi
const dolap_ici = document.getElementById("duzenle_setup_dolap_ici").value === "true";

// Tablo render - Yerleşim badge'i eklendi
const dolapYerlesim = setup.dolap_ici
  ? '<span class="badge green">Dolap İçi</span>'
  : '<span class="badge orange">Dolap Dışı</span>';
```

### 4. Backend API Güncellemeleri

**Dosya**: `routes/sistem_yoneticisi_routes.py`

#### GET /api/setuplar

```python
sonuc.append({
    'id': setup.id,
    'ad': setup.ad,
    'aciklama': setup.aciklama,
    'dolap_ici': setup.dolap_ici if hasattr(setup, 'dolap_ici') else True,
    'urun_sayisi': urun_sayisi,
    'oda_tipleri': oda_tipi_adlari,
    'toplam_maliyet': round(toplam_maliyet, 2)
})
```

#### POST /api/setuplar

```python
dolap_ici = data.get('dolap_ici', True)  # Varsayılan: Dolap İçi
yeni_setup = Setup(ad=ad, aciklama=aciklama, dolap_ici=dolap_ici)
```

#### PUT /api/setuplar/<id>

```python
dolap_ici = data.get('dolap_ici', True)
setup.dolap_ici = dolap_ici
```

## Kullanım Senaryoları

### Yeni Setup Ekleme

1. Setup Yönetimi > "Yeni Setup Ekle"
2. Setup Adı: "MINI"
3. Açıklama: "Mini bar setup"
4. **Yerleşim: "Dolap İçi" veya "Dolap Dışı" seç**
5. Kaydet

### Setup Düzenleme

1. Setup listesinde "Düzenle" butonuna tıkla
2. **Yerleşim değerini değiştir**
3. Güncelle

### Setup Listesi Görüntüleme

- Tabloda "Yerleşim" sütununda:
  - 🟢 **Dolap İçi**: Yeşil badge
  - 🟠 **Dolap Dışı**: Turuncu badge

## Teknik Detaylar

### Veri Tipi

- **Boolean**: `true` = Dolap İçi, `false` = Dolap Dışı
- **Varsayılan**: `true` (Dolap İçi)

### Frontend-Backend İletişimi

```javascript
// Frontend -> Backend
{
  "ad": "MINI",
  "aciklama": "Mini bar setup",
  "dolap_ici": true  // Boolean
}

// Backend -> Frontend
{
  "id": 1,
  "ad": "MINI",
  "aciklama": "Mini bar setup",
  "dolap_ici": true,  // Boolean
  "urun_sayisi": 5,
  "toplam_maliyet": 150.00
}
```

### Badge Renkleri

- **Dolap İçi**: `bg-green-100 text-green-800` (Yeşil)
- **Dolap Dışı**: `bg-orange-100 text-orange-800` (Turuncu)

## Test Edilmesi Gerekenler

### ✅ Yeni Setup Ekleme

- [ ] "Dolap İçi" seçerek setup ekle
- [ ] "Dolap Dışı" seçerek setup ekle
- [ ] Tabloda doğru badge görünsün

### ✅ Setup Düzenleme

- [ ] Mevcut setup'ı aç
- [ ] Yerleşim değeri doğru seçili gelsin
- [ ] Yerleşimi değiştir ve kaydet
- [ ] Tabloda güncel badge görünsün

### ✅ Setup Listesi

- [ ] Tüm setup'lar doğru yerleşim badge'i ile görünsün
- [ ] Dolap İçi: Yeşil badge
- [ ] Dolap Dışı: Turuncu badge

## Sonuç

✅ Setup'lara "Dolap İçi / Dolap Dışı" özelliği eklendi
✅ Yeni ekleme ve düzenleme modallarında seçim yapılabiliyor
✅ Tabloda renkli badge ile görüntüleniyor
✅ Backend API'leri güncellendi
✅ Migration başarıyla çalıştırıldı
