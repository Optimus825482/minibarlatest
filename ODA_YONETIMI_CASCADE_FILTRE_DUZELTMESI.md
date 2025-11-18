# Oda Yönetimi - Cascade Filtre Düzeltmesi

## Problem

Oda Yönetimi sayfasında filtreler düzgün çalışmıyordu:

- Otel seçildiğinde kat filtresi güncellenmiyordu
- Oda tipi filtresi sadece 1 tane gösteriyordu
- Otel → Kat → Oda Tipi cascade çalışmıyordu

## Kök Neden

Benzersiz oda tipi listesi oluşturulurken sadece oda tipi adı bazında benzersiz yapılıyordu.
Aynı oda tipi farklı otellerde olabilir ama otel/kat bilgisi kaybediliyordu.

## Çözüm

### 1. Benzersiz Oda Tipi Mantığı Değiştirildi

**Önceki Kod**:

```javascript
const benzersizOdaTipleri = [];
const gorulenTipler = new Set();
tumOdaTipleri.forEach((tip) => {
  if (!gorulenTipler.has(tip.value)) {
    gorulenTipler.add(tip.value);
    benzersizOdaTipleri.push(tip);
  }
});
```

**Yeni Kod**:

```javascript
// Otel ve kat bilgisi ile benzersiz yap
const benzersizOdaTipleri = [];
const gorulenTipler = new Map();

tumOdaTipleri.forEach((tip) => {
  const key = `${tip.value}|${tip.otelAdi}|${tip.katAdi}`;
  if (!gorulenTipler.has(key)) {
    gorulenTipler.set(key, true);
    benzersizOdaTipleri.push(tip);
  }
});

// Dropdown için sadece oda tipi adlarını benzersiz yap
const benzersizOdaTipiAdlari = [];
const gorulenAdlar = new Set();
tumOdaTipleri.forEach((tip) => {
  if (!gorulenAdlar.has(tip.value)) {
    gorulenAdlar.add(tip.value);
    benzersizOdaTipiAdlari.push({
      value: tip.value,
      label: tip.label,
    });
  }
});
```

### 2. Kat Filtresi Değişikliği Güncellendi

Kat seçildiğinde oda tipi filtresi hem kat hem otel bazında filtreleniyor:

```javascript
if (secilenKat) {
  let filtreliOdaTipleri = benzersizOdaTipleri.filter(
    (tip) => tip.katAdi === secilenKat
  );

  // Eğer otel de seçiliyse, hem otel hem kat filtresi uygula
  if (secilenOtel) {
    filtreliOdaTipleri = filtreliOdaTipleri.filter(
      (tip) => tip.otelAdi === secilenOtel
    );
  }
}
```

### 3. Data Attribute Eklendi

Tablo satırlarına filtre için data attribute eklendi:

```html
<tr
  class="oda-row"
  data-otel-id="{{ oda.kat.otel.id }}"
  data-kat-id="{{ oda.kat.id }}"
  data-oda-tipi="{{ oda.oda_tipi_adi }}"
></tr>
```

## Cascade Filtre Akışı

### 1. Otel Seçildiğinde

- Kat filtresi güncellenir → Sadece o otele ait katlar
- Oda tipi filtresi güncellenir → Sadece o otele ait oda tipleri
- Tablo filtrelenir

### 2. Kat Seçildiğinde

- Oda tipi filtresi güncellenir → Hem otel hem kata ait oda tipleri
- Tablo filtrelenir

### 3. Oda Tipi Seçildiğinde

- Tablo filtrelenir

## Test Senaryoları

### ✅ Senaryo 1: Sadece Otel Seçimi

1. Otel filtresi → "Otel A" seç
2. Kat filtresi → Sadece Otel A'nın katları görünmeli
3. Oda tipi filtresi → Sadece Otel A'daki oda tipleri görünmeli
4. Tablo → Sadece Otel A'nın odaları görünmeli

### ✅ Senaryo 2: Otel + Kat Seçimi

1. Otel filtresi → "Otel A" seç
2. Kat filtresi → "1. Kat" seç
3. Oda tipi filtresi → Sadece Otel A'nın 1. Katındaki oda tipleri görünmeli
4. Tablo → Sadece Otel A'nın 1. Katındaki odalar görünmeli

### ✅ Senaryo 3: Otel + Kat + Oda Tipi Seçimi

1. Otel filtresi → "Otel A" seç
2. Kat filtresi → "1. Kat" seç
3. Oda tipi filtresi → "STANDARD" seç
4. Tablo → Sadece Otel A'nın 1. Katındaki STANDARD odalar görünmeli

## Sonuç

✅ Cascade filtreler çalışıyor
✅ Otel → Kat → Oda Tipi zincirleme filtreleme
✅ Her filtre bir öncekine bağlı
✅ Tablo dinamik güncelleniyor
