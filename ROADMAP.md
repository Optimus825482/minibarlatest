# Minibar Takip - Proje Iyilestirme Roadmap

> Son guncelleme: 23 Mart 2026
> Durum: Faz 1-4 tamamlandi, Faz 5 devam ediyor (Excel/PDF refactoring tamamlandi), Faz 6 bekliyor
> Toplam bulgu: 5 kritik guvenlik, 15 indexsiz tablo, 4 N+1 sorunu, 1008 lint hatasi

---

## Faz 1 - ACIL GUVENLIK (Bugun)

Bunlar production'da aktif risk olusturan, hemen duzeltilmesi gereken sorunlar.

### 1.1 SQL Injection Aciklari

- [x] **[KRITIK] data_validator.py L37-65** - Tablo adi string interpolasyonu
  - `f"SELECT COUNT(*) FROM {table_name}"` → whitelist + parameterized query
  - Dosya: `utils/data_validator.py`

- [x] **[KRITIK] restore_routes.py L126** - Ayni pattern
  - `f"SELECT COUNT(*) FROM {table_name}"` → whitelist kontrolu
  - Dosya: `routes/restore_routes.py`

### 1.2 Hardcoded Credentials

- [x] **[KRITIK] app.py L2083** - Sistem reset sifresi kaynak kodda
  - `RESET_PASSWORD = "518518Erkan!"` → env var + bcrypt hash env var a gerek yok tamamen kaldır sistem reset şifresini ve fonksiyonunu
  - Dosya: `app.py`

### 1.3 Eksik Yetkilendirme

- [x] **[KRITIK] app.py L2083** - `/resetsystem` route'unda auth yok
  - `@login_required` ve `@role_required('sistem_yoneticisi')` ekle
  - CSRF exempt'i kaldir
  - Dosya: `app.py`

### 1.4 Session Fixation

- [x] **[KRITIK] auth_routes.py L111** - Login sonrasi session ID yenilenmiyor
  - `session.clear()` sonrasi yeni session ID regenerate et
  - Dosya: `routes/auth_routes.py`

---

## Faz 2 - GUVENLIK IYILESTIRME (Bu Hafta)

### 2.1 CSRF Korumasi

- [x] **[YUKSEK]** API POST endpoint'lerine CSRF token dogrulamasi ekle
  - Dosya: `routes/api_routes.py`

### 2.2 Hata Mesaji Sizintisi

- [x] **[YUKSEK]** `str(e)` kullaniciya gonderilmesini engelle, generic mesaj goster
  - Etkilenen: `routes/api_routes.py`, `routes/admin_routes.py`, diger route'lar
  - Pattern: `flash(f'Hata: {str(e)}')` → `flash('Bir hata olustu')` + `logger.error()`

### 2.3 Rate Limiting

- [x] **[YUKSEK]** Login rate limit'i 10/dk → 5/dk
  - Progressive delay ekle (3 basarisiz giris → 30sn bekleme)
  - Dosya: `utils/rate_limiter.py`

### 2.4 Session Cookie Guvenlik

- [x] **[ORTA]** `SESSION_COOKIE_SECURE` production default'u `True` yap
- [x] **[ORTA]** `SESSION_COOKIE_SAMESITE` → `Strict`
  - Dosya: `config.py` L109-113

### 2.5 Input Validation

- [x] **[ORTA]** Route parametrelerinde tip ve aralik kontrolu ekle
  - miktar parametreleri 1-10000 aralik kontrolu, ValueError yakalama
  - Dosyalar: `routes/depo_routes.py` (3 endpoint), `routes/kat_sorumlusu_routes.py` (2 blok), `app.py` (zimmet-iade)

### 2.6 Diger Guvenlik

- [x] **[ORTA]** `bildirim_service.py` L185 - `.replace()` ile SQL building'i kaldir
- [ ] **[ORTA]** Setup route'una ek auth kontrolu ekle (`routes/auth_routes.py` L60)
- [ ] **[ORTA]** File upload icin content validation ekle (sadece extension yetmez)
- [ ] **[DUSUK]** Template'lerde `innerHTML` kullanimi → `textContent` veya DOMPurify
- [ ] **[DUSUK]** Log'lardan hassas veri (password hash) cikart

---

## Faz 3 - VERITABANI INDEXLERI (Bu Sprint)

### 3.1 Kritik Tablolar (Login + Yuksek Trafik)

- [x] **[KRITIK]** `kullanicilar` tablosu indexleri

  ```sql
  CREATE UNIQUE INDEX idx_kullanici_adi ON kullanicilar(kullanici_adi);
  CREATE INDEX idx_kullanici_email ON kullanicilar(email);
  CREATE INDEX idx_kullanici_aktif_rol ON kullanicilar(aktif, rol);
  ```

- [x] **[KRITIK]** `stok_hareketleri` tablosu

  ```sql
  CREATE INDEX idx_stok_hareket_urun_tarih ON stok_hareketleri(urun_id, islem_tarihi DESC);
  CREATE INDEX idx_stok_hareket_tipi ON stok_hareketleri(hareket_tipi);
  ```

- [x] **[KRITIK]** `personel_zimmet` tablosu

  ```sql
  CREATE INDEX idx_zimmet_personel_durum ON personel_zimmet(personel_id, durum, zimmet_tarihi DESC);
  CREATE INDEX idx_zimmet_otel ON personel_zimmet(otel_id);
  ```

- [x] **[KRITIK]** `minibar_islem_detay` tablosu

  ```sql
  CREATE INDEX idx_minibar_detay_islem ON minibar_islem_detay(islem_id, urun_id);
  CREATE INDEX idx_minibar_detay_kar ON minibar_islem_detay(kar_tutari);
  ```

### 3.2 Yuksek Oncelikli Tablolar

- [x] **[YUKSEK]** `urunler` tablosu

  ```sql
  CREATE INDEX idx_urun_grup_aktif ON urunler(grup_id, aktif);
  CREATE INDEX idx_urun_kodu ON urunler(urun_kodu);
  CREATE INDEX idx_urun_barkod ON urunler(barkod);
  ```

- [x] **[YUKSEK]** `katlar` tablosu

  ```sql
  CREATE INDEX idx_kat_otel ON katlar(otel_id, kat_no);
  ```

- [x] **[YUKSEK]** `setup_icerik` tablosu

  ```sql
  CREATE INDEX idx_setup_icerik_setup ON setup_icerik(setup_id, urun_id);
  ```

- [x] **[YUKSEK]** `personel_zimmet_detay` tablosu

  ```sql
  CREATE INDEX idx_zimmet_detay_zimmet ON personel_zimmet_detay(zimmet_id);
  CREATE INDEX idx_zimmet_detay_urun ON personel_zimmet_detay(urun_id);
  ```

### 3.3 Orta Oncelikli Tablolar

- [x] **[ORTA]** `sistem_ayarlari` - `anahtar` UNIQUE index
- [x] **[ORTA]** `sistem_loglari` - `kullanici_id`, `islem_tipi`, `islem_tarihi` indexleri
- [x] **[ORTA]** `hata_loglari` - `olusturma_tarihi`, `cozuldu` indexleri
- [x] **[ORTA]** `urun_gruplari` - `aktif` index
- [x] **[ORTA]** `oda_tipleri` - temel index
- [x] **[ORTA]** `email_ayarlari` - `aktif` index

### 3.4 JSONB Indexleri

- [x] **[ORTA]** `audit_logs` tablosu GIN indexleri

  ```sql
  CREATE INDEX idx_audit_eski_deger ON audit_logs USING GIN(eski_deger);
  CREATE INDEX idx_audit_yeni_deger ON audit_logs USING GIN(yeni_deger);
  ```

---

## Faz 4 - PERFORMANS (Bu Sprint)

### 4.1 N+1 Query Duzeltmeleri

- [x] **[KRITIK]** Zimmet sistemi N+1 - `selectinload` kullan
  - `PersonelZimmet.query` → `get_zimmetler_optimized()` kullan
  - Etkilenen: `routes/depo_routes.py`, zimmet route'lari

- [x] **[KRITIK]** Minibar islemleri N+1 - eager loading ekle
  - `MinibarIslem.query` → `get_minibar_islemler_optimized()` kullan
  - Etkilenen: `app.py`, minibar route'lari

- [x] **[YUKSEK]** Stok hareketleri N+1
  - `StokHareket.query` → `get_stok_hareketleri_optimized()` kullan
  - Etkilenen: rapor route'lari

- [x] **[YUKSEK]** Rapor servisleri N+1
  - `Otel.query.get()` loop icinde → JOIN ile tek sorguda coz
  - Dosya: `utils/rapor_servisleri.py`

### 4.2 Excel/PDF Export Blocking I/O

- [x] **[KRITIK]** Excel export'lari Celery task'a tasi
  - `utils/rapor_export_service.py` service layer olusturuldu (~400 satir)
  - `celery_app.py`'ye `excel_export_task` eklendi
  - `app.py` 250+ satirlik god function → 30 satirlik slim handler

- [x] **[YUKSEK]** PDF export'lari Celery task'a tasi
  - `celery_app.py`'ye `pdf_export_task` eklendi
  - `routes/export_routes.py` async API endpoint'leri eklendi

### 4.3 Connection Pool ve Timeout

- [x] **[YUKSEK]** Pool size artir: `pool_size: 8 → 5`, `max_overflow: 8 → 10`
  - Dosya: `config.py` L56

- [ ] **[YUKSEK]** Gunicorn timeout dusur: `300s → 60s`
  - Dosya: `gunicorn.conf.py`

### 4.4 Unbounded Query'ler

- [x] **[YUKSEK]** `.all()` kullanimlarina LIMIT ekle
  - 18 unbounded sorgu limitlendi: HTML raporlar 5000, Excel export 10000, liste sayfalar 500-2000
  - Dosyalar: `app.py`, `routes/rapor_routes.py`, `routes/depo_routes.py`, `routes/kat_sorumlusu_routes.py`, `routes/api_routes.py`

### 4.5 Cache ve Config

- [x] **[ORTA]** `TEMPLATES_AUTO_RELOAD = False` production'da
- [x] **[ORTA]** `SEND_FILE_MAX_AGE_DEFAULT` gecerli bir deger ver (3600 vs)
- [ ] **[ORTA]** Query logging'i production'da kapat veya sampling yap
- [ ] **[ORTA]** Dashboard aggregation sonuclarini kisa TTL ile cache'le

---

## Faz 5 - KOD KALITESI (Gelecek Sprint)

### 5.1 Compile/Lint Hatalari (1008 adet)

- [x] **[YUKSEK]** openpyxl `wb.active` type assertion ekle
  - 15 dosyada `assert ws is not None` eklendi
  - Bu tek duzeltme ~1000 hatanin cogunlugunu cozdu

### 5.2 Duplicate Model Tanimlari

- [ ] **[YUKSEK]** `models.py` ve `models/` dizini arasinda karar ver
  - Tercih: `models/` dizinini kullan, `models.py`'yi import wrapper'a cevir
  - 24 duplicate model temizle
  - Import'lari guncelle

### 5.3 God Function'lar

- [x] **[ORTA]** `app.py` excel_export (250+ satir) → service layer'a bol
  - `utils/rapor_export_service.py`'ye tasindi, dispatch dict pattern ile modüler
  - 5 Excel + 6 PDF generator, her rapor tipi ayri fonksiyon

- [ ] **[ORTA]** Dashboard route'lari (200+ satir) → service delegate
  - Dosya: `routes/dashboard_routes.py`

### 5.4 Duplicate Endpoint'ler

- [x] **[ORTA]** Excel/PDF export hem `app.py` hem route'larda var → tek yere tasi
  - `utils/rapor_export_service.py` tek kaynak, `app.py` slim handler cagiriyor

### 5.5 Tutarsiz Loglama

- [x] **[ORTA]** `print()` → `logger.error/warning/info` degistir
  - ~170+ print() cagirisi logger'a donusturuldu (28+ dosya)
  - Kalan ~35 print: infrastructure/diagnostic (legitimate)

### 5.6 Silent Failure Pattern

- [x] **[ORTA]** `except Exception: pass/print(...)` → proper error handling
  - 23 bare `except:` → `except Exception:` donusturuldu
  - 32 `except Exception: pass` → `logger.debug("Sessiz hata yakalandi", exc_info=True)` donusturuldu
  - 5 dosyaya yeni logger altyapisi eklendi

### 5.7 Response Format Standardizasyonu

- [ ] **[DUSUK]** API response'lari icin standart format belirle
  - `APIResponse.success(data)` / `APIResponse.error(message)` pattern

### 5.8 Race Condition

- [x] **[ORTA]** Zimmet durum degisikliklerinde pessimistic lock ekle
  - `with_for_update()` eklendi: FIFO stok cikis, FIFO stok giris, UrunStok guncelleme
  - Dosya: `utils/fifo_servisler.py` (3 sorguya lock eklendi)

### 5.9 Global Mutable State

- [x] **[DUSUK]** `utils/performance.py` thread-safe olmayan global counter -> threading.Lock
  - query_stats listesi, get_stats, reset_stats fonksiyonlari Lock ile korundu
- [ ] **[DUSUK]** `db_optimization.py` hardcoded tablo listesini guncelle

---

## Faz 6 - MIMARI IYILESTIRME (Sonraki Sprint)

### 6.1 Blueprint Migration

- [ ] **[DUSUK]** Route'lari Flask Blueprint'lere tasi (35 route dosyasi)
  - URL prefix'leri ile namespace collision onle
  - Asama asama: once admin, sonra api, sonra diger

### 6.2 Service Layer Standardizasyonu

- [ ] **[DUSUK]** Tum is mantigi route'lardan service modullere tasi
  - Route'lar sadece request parse + response format olsun
  - Service'ler test edilebilir olsun

### 6.3 Dependency Audit

- [ ] **[DUSUK]** `pip-audit` calistir, vulnerable package'lari guncelle
  - `requirements.txt` guncelle

---

## Ilerleme Takibi

| Faz | Toplam | Tamamlanan | Kalan | Durum |
| ----- | -------- | ------------ | ------- | ------- |
| 1 - Acil Guvenlik | 5 | 5 | 0 | Tamamlandi |
| 2 - Guvenlik Iyilestirme | 11 | 7 | 4 | Kismen Tamamlandi |
| 3 - DB Indexleri | 16 | 16 | 0 | Tamamlandi |
| 4 - Performans | 12 | 10 | 2 | Kismen Tamamlandi |
| 5 - Kod Kalitesi | 12 | 8 | 4 | Devam Ediyor |
| 6 - Mimari | 3 | 0 | 3 | Bekliyor |
| **TOPLAM** | **59** | **44** | **14** | |

---

## Notlar

- Faz 1 (Acil Guvenlik) production'da aktif risk olusturuyor, oncelikle bunlara odaklan
- Faz 3 (Indexler) icin migration script yazilmali: `migrations_manual/` altina
- Faz 4 (Performans) icin mevcut `query_helpers.py`'deki optimized fonksiyonlar hazir, sadece route'larda kullanima al
- Her faz tamamlandiginda bu dosyayi guncelle
