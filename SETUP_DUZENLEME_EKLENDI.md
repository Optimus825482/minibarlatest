# ✅ Setup Yönetimi - Düzenleme Özelliği Eklendi

## 🎯 Değişiklik

Setup Yönetimi sayfasına **"Düzenle"** butonu ve modalı eklendi. Artık setup adı ve açıklaması düzenlenebilir.

## ✅ Yapılan Değişiklikler

### 1. **Düzenle Butonu Eklendi**

İşlemler kolonuna yeni buton eklendi:

```html
<button onclick="setupDuzenleModal(...)" class="btn btn-sm btn-primary">
  <i class="fas fa-edit"></i>
</button>
```

**Buton Sırası:**

```
[✏️ Düzenle] [İçerik] [Atama] [Sil]
```

### 2. **Setup Düzenleme Modal'ı Eklendi**

```html
<div class="modal fade" id="setupDuzenleModal">
  <form id="setupDuzenleForm" onsubmit="setupGuncelle(event)">
    <input type="hidden" id="duzenle_setup_id" />

    <!-- Setup Adı -->
    <input type="text" id="duzenle_setup_ad" required />

    <!-- Açıklama -->
    <textarea id="duzenle_setup_aciklama"></textarea>

    <button type="submit">Güncelle</button>
  </form>
</div>
```

### 3. **JavaScript Fonksiyonları Eklendi**

#### setupDuzenleModal()

```javascript
function setupDuzenleModal(setupId, setupAd, setupAciklama) {
  document.getElementById("duzenle_setup_id").value = setupId;
  document.getElementById("duzenle_setup_ad").value = setupAd;
  document.getElementById("duzenle_setup_aciklama").value = setupAciklama || "";
  $("#setupDuzenleModal").modal("show");
}
```

#### setupGuncelle()

```javascript
function setupGuncelle(event) {
  event.preventDefault();

  const setupId = document.getElementById("duzenle_setup_id").value;
  const ad = document.getElementById("duzenle_setup_ad").value.trim();
  const aciklama = document
    .getElementById("duzenle_setup_aciklama")
    .value.trim();

  // Validasyon
  if (!ad) {
    alert("Setup adı boş olamaz");
    return;
  }

  // API çağrısı
  fetch(`/api/setuplar/${setupId}`, {
    method: "PUT",
    headers: {
      "Content-Type": "application/json",
      "X-CSRFToken": csrfToken,
    },
    body: JSON.stringify({ ad, aciklama }),
  })
    .then((response) => response.json())
    .then((data) => {
      if (data.success) {
        $("#setupDuzenleModal").modal("hide");
        setupListesiYukle();
        alert("Setup başarıyla güncellendi");
      } else {
        alert("Hata: " + data.error);
      }
    });
}
```

## 🎨 Kullanıcı Deneyimi

### Düzenleme Akışı:

```
1. Kullanıcı "Düzenle" butonuna tıklar
2. Modal açılır, mevcut bilgiler dolu gelir
3. Kullanıcı adı ve/veya açıklamayı değiştirir
4. "Güncelle" butonuna tıklar
5. API çağrısı yapılır
6. Başarılı mesajı gösterilir
7. Liste yenilenir
```

### Modal Görünümü:

```
┌─────────────────────────────────────┐
│ Setup Düzenle                    [X]│
├─────────────────────────────────────┤
│                                     │
│ Setup Adı *                         │
│ [MINI                            ]  │
│                                     │
│ Açıklama                            │
│ [Küçük odalar için standart     ]  │
│ [setup                          ]  │
│                                     │
├─────────────────────────────────────┤
│              [İptal] [Güncelle]     │
└─────────────────────────────────────┘
```

## 📋 Özellikler

### ✅ Düzenlenebilir Alanlar

- Setup Adı (zorunlu)
- Açıklama (opsiyonel)

### ✅ Validasyon

- Setup adı boş olamaz
- Trim işlemi yapılır (boşluklar temizlenir)

### ✅ Güvenlik

- CSRF token kontrolü
- PUT metodu kullanılır
- Server-side validasyon gerekli

## 🔄 API Endpoint

### PUT /api/setuplar/{id}

**Request:**

```json
{
  "ad": "MINI",
  "aciklama": "Küçük odalar için standart setup"
}
```

**Response (Başarılı):**

```json
{
  "success": true,
  "message": "Setup başarıyla güncellendi"
}
```

**Response (Hata):**

```json
{
  "success": false,
  "error": "Setup adı zaten kullanılıyor"
}
```

## 🚀 Avantajlar

1. **Kolay Düzenleme**: Tek tıkla düzenleme
2. **Mevcut Bilgiler**: Form dolu gelir
3. **Validasyon**: Hatalı girişleri önler
4. **Kullanıcı Dostu**: Basit ve anlaşılır
5. **Güvenli**: CSRF korumalı

## ⚠️ Backend Gereksinimi

Backend'de şu endpoint eklenmeli:

```python
@app.route('/api/setuplar/<int:setup_id>', methods=['PUT'])
@login_required
def setup_guncelle(setup_id):
    try:
        data = request.get_json()
        ad = data.get('ad', '').strip()
        aciklama = data.get('aciklama', '').strip()

        # Validasyon
        if not ad:
            return jsonify({'success': False, 'error': 'Setup adı boş olamaz'}), 400

        # Setup bul
        setup = Setup.query.get_or_404(setup_id)

        # Aynı isimde başka setup var mı kontrol et
        existing = Setup.query.filter(
            Setup.ad == ad,
            Setup.id != setup_id
        ).first()

        if existing:
            return jsonify({'success': False, 'error': 'Bu isimde bir setup zaten var'}), 400

        # Güncelle
        setup.ad = ad
        setup.aciklama = aciklama
        db.session.commit()

        return jsonify({'success': True, 'message': 'Setup başarıyla güncellendi'})

    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500
```

## 📁 Değiştirilen Dosya

**templates/sistem_yoneticisi/setup_yonetimi.html**

- Düzenle butonu eklendi
- Setup Düzenleme Modal'ı eklendi
- `setupDuzenleModal()` fonksiyonu eklendi
- `setupGuncelle()` fonksiyonu eklendi

## 🎯 Sonuç

Artık kullanıcılar:

- Setup adını düzenleyebilir
- Setup açıklamasını düzenleyebilir
- Tek tıkla düzenleme yapabilir
- Mevcut bilgileri görebilir

---

**Tarih**: 17 Kasım 2025  
**Durum**: ✅ Tamamlandı (Backend endpoint gerekli)  
**Dosya**: templates/sistem_yoneticisi/setup_yonetimi.html
