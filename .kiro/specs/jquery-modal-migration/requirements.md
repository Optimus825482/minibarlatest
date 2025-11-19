# jQuery Modal Migration - Requirements

## Genel Bakış

Tüm template dosyalarındaki modal yapılarını jQuery Modal kütüphanesine çevireceğiz. Bu, tutarlı bir modal deneyimi ve daha az kod tekrarı sağlayacak.

## Hedefler

### 1. Tutarlılık

- Tüm modal'lar aynı görünüm ve davranışa sahip olacak
- Tek bir global CSS ile yönetilecek
- Aynı animasyon ve geçişler

### 2. Basitlik

- Daha az JavaScript kodu
- Kapatma fonksiyonlarına gerek yok
- `rel="modal:close"` ile otomatik kapatma

### 3. Özellikler

- ✨ Gradient başlıklar
- 🎨 Dark mode desteği
- 🔴 Kırmızı gradient kapatma butonu
- 💫 Smooth animasyonlar (fade)
- 📜 Custom scrollbar
- 🌫️ Backdrop blur efekti
- 📱 Responsive tasarım

## Kapsam

### Çevrilecek Dosyalar (19 modal)

1. **templates/sistem_yoneticisi/setup_yonetimi.html** (4 modal)

   - Yeni Setup Modal
   - Setup Düzenle Modal
   - Setup İçerik Modal
   - Oda Tipi Setup Atama Modal

2. **templates/admin/urunler.html** (2 modal)

   - Yeni Ürün Modal
   - Ürün Düzenle Modal

3. **templates/admin/urun_gruplari.html** (2 modal)

   - Yeni Grup Modal
   - Grup Düzenle Modal

4. **templates/kat_sorumlusu/dolum_talepleri.html** (2 modal)

   - Tamamla Modal
   - İptal Modal

5. **templates/admin/personel_tanimla.html** (1 modal)

   - Yeni Kullanıcı Modal

6. **templates/sistem_yoneticisi/kat_tanimla.html** (7 modal)

   - Yeni Kat Modal
   - Kat Düzenle Modal
   - Oda Tipleri Modal
   - Oda Tipleri Yönetim Modal
   - Yeni Oda Tipi Modal
   - Oda Tipi Düzenle Modal
   - Kat Oda Tipleri Modal

7. **templates/admin/otel_listesi.html** (1 modal) ✅ TAMAMLANDI
   - Otel Oda Tipleri Modal

## Kabul Kriterleri

### Fonksiyonel Gereksinimler

1. **Modal Açma**

   - Modal'lar JavaScript ile açılabilmeli
   - Fade animasyonu ile açılmalı (250ms)
   - Z-index sorunu olmamalı

2. **Modal Kapatma**

   - X butonu ile kapatılabilmeli
   - ESC tuşu ile kapatılabilmeli
   - Overlay'e tıklayınca kapatılabilmeli
   - `rel="modal:close"` butonları ile kapatılabilmeli

3. **Form İşlemleri**

   - Form submit işlemleri çalışmalı
   - AJAX çağrıları çalışmalı
   - Validasyon çalışmalı
   - Modal kapandıktan sonra sayfa yenilenmeli (gerekirse)

4. **Responsive**

   - Mobil cihazlarda düzgün görünmeli
   - Tablet'te düzgün görünmeli
   - Desktop'ta düzgün görünmeli
   - Scroll çalışmalı

5. **Dark Mode**
   - Dark mode'da düzgün görünmeli
   - Renkler uyumlu olmalı

### Teknik Gereksinimler

1. **HTML Yapısı**

```html
<div id="modalId" class="modal bg-white dark:bg-slate-800 shadow-2xl">
  <!-- Header -->
  <div class="px-4 sm:px-6 md:px-8 py-4 sm:py-5 md:py-6 border-b ...">
    <h5>Başlık</h5>
  </div>

  <!-- Body -->
  <div
    class="p-4 sm:p-6 md:p-8 overflow-y-auto"
    style="max-height: calc(90vh - 180px);"
  >
    İçerik
  </div>

  <!-- Footer -->
  <div class="px-4 sm:px-6 md:px-8 py-4 sm:py-5 ...">
    <a href="#" rel="modal:close">Kapat</a>
  </div>
</div>
```

2. **JavaScript Yapısı**

```javascript
function modalAc() {
  $("#modalId").modal({
    fadeDuration: 250,
    fadeDelay: 0.5,
    escapeClose: true,
    clickClose: true,
    showClose: true,
  });

  setTimeout(function () {
    $(".jquery-modal.blocker").css("z-index", "999999");
  }, 10);
}
```

3. **CSS**
   - Global CSS base.html'de tanımlı
   - Dosya bazlı özel CSS kaldırılmalı
   - Sadece modal'a özel stiller kalabilir

## Kapsam Dışı

- Yeni modal ekleme
- Modal içerik değişiklikleri
- Backend değişiklikleri
- API değişiklikleri

## Riskler ve Azaltma

### Risk 1: Form Submit Çalışmayabilir

**Azaltma:** Her modal'ı test et, form submit'leri kontrol et

### Risk 2: Z-index Sorunları

**Azaltma:** Her modal'da z-index fix ekle

### Risk 3: AJAX Çağrıları Bozulabilir

**Azaltma:** AJAX callback'lerde modal kapatma işlemlerini güncelle

### Risk 4: Responsive Sorunlar

**Azaltma:** Her ekran boyutunda test et

## Test Planı

### Her Modal İçin Test Senaryoları

1. **Açma Testi**

   - [ ] Modal açılıyor mu?
   - [ ] Animasyon çalışıyor mu?
   - [ ] Z-index doğru mu?

2. **Kapatma Testi**

   - [ ] X butonu çalışıyor mu?
   - [ ] ESC tuşu çalışıyor mu?
   - [ ] Overlay tıklama çalışıyor mu?
   - [ ] Kapat butonu çalışıyor mu?

3. **Form Testi**

   - [ ] Form submit çalışıyor mu?
   - [ ] Validasyon çalışıyor mu?
   - [ ] AJAX çağrıları çalışıyor mu?
   - [ ] Modal kapanıyor mu?

4. **Responsive Testi**

   - [ ] Mobil'de düzgün görünüyor mu?
   - [ ] Tablet'te düzgün görünüyor mu?
   - [ ] Desktop'ta düzgün görünüyor mu?

5. **Dark Mode Testi**
   - [ ] Dark mode'da düzgün görünüyor mu?

## Başarı Metrikleri

- ✅ 19 modal başarıyla çevrildi
- ✅ Tüm testler geçti
- ✅ Hiçbir fonksiyonellik bozulmadı
- ✅ Responsive tasarım çalışıyor
- ✅ Dark mode çalışıyor
- ✅ Z-index sorunları yok

## Zaman Tahmini

- Her modal: ~15 dakika
- Test: ~5 dakika
- Toplam: ~6 saat (19 modal × 20 dakika)

## Notlar

- Global CSS zaten base.html'de hazır
- otel_listesi.html örnek olarak tamamlandı
- Her dosya için aynı pattern kullanılacak
