# Merit Royal Otel Grubu — Minibar Takip Sistemi

## Kapsamlı Teknik Doküman

**Versiyon:** 2.0  
**Tarih:** 21 Şubat 2026  
**Hazırlayan:** Erkan & Dijital İkiz Sistemi  
**Durum:** Canlı Üretim Ortamı (Production)

---

## 1. Sistem Genel Bakış

### 1.1 Sistemin Amacı

Merit Royal Otel Grubu'nun 3 otelinde (Merit Royal Diamond, Merit Royal Premium, Merit Royal Hotel) toplam **558 odanın** minibar operasyonlarını uçtan uca dijitalleştiren, yapay zeka destekli akıllı yönetim platformudur.

### 1.2 Çözdüğü Temel Sorunlar

| #   | Önceki Durum (Manuel)                                  | Şimdiki Durum (Dijital)                      |
| --- | ------------------------------------------------------ | -------------------------------------------- |
| 1   | Kağıt üzerinde minibar takibi, kayıp/hata riski yüksek | Gerçek zamanlı dijital kayıt, sıfır kayıp    |
| 2   | Stok sayımı günler alıyor                              | Anlık stok durumu, FIFO bazlı izleme         |
| 3   | Tüketim verileri bilinmiyor                            | Oda/ürün/dönem bazlı detaylı tüketim analizi |
| 4   | Personel performansı ölçülemiyor                       | Görev tamamlama oranları, süre takibi        |
| 5   | Anomaliler fark edilmiyor                              | ML tabanlı otomatik anomali tespiti          |
| 6   | Doluluk-tüketim ilişkisi bilinmiyor                    | Excel import ile doluluk entegrasyonu        |
| 7   | Zimmet takibi yok                                      | Personel bazlı zimmet ve stok yönetimi       |
| 8   | Raporlama manuel                                       | 15+ otomatik rapor tipi (Excel/PDF)          |

### 1.3 Canlı Sistem İstatistikleri (21 Şubat 2026)

```
┌─────────────────────────────────────────────────┐
│  3 Otel  │  558 Oda  │  18 Kat  │  69 Ürün     │
│  16 Kullanıcı  │  7 Ürün Grubu               │
├─────────────────────────────────────────────────┤
│  47.914 Minibar İşlemi                          │
│  49.306 Oda Kontrol Kaydı                       │
│  40.060 Görev Detayı                            │
│  14.333 Misafir Kaydı                           │
│  68.528 Audit Log                               │
│  176.274 ML Metrik                              │
│  18.021 ML Alert                                │
└─────────────────────────────────────────────────┘
```

---

## 2. Mimari Yapı

### 2.1 Teknoloji Yığını

```
┌──────────────────────────────────────────────────────────┐
│                    FRONTEND KATMANI                       │
│  Bootstrap 5 + jQuery + Jinja2 Templates + PWA           │
│  Responsive Tasarım + Service Worker + Cache Busting     │
├──────────────────────────────────────────────────────────┤
│                    BACKEND KATMANI                        │
│  Python 3.13 + Flask Framework                           │
│  Gunicorn (4 worker × 4 thread)                          │
│  31 Route Modülü + 40+ Utility Servisi                   │
├──────────────────────────────────────────────────────────┤
│                    VERİ KATMANI                           │
│  PostgreSQL (Ana Veritabanı - 80+ Tablo)                 │
│  Redis (Celery Broker + Master Data Cache)               │
│  SQLAlchemy ORM + Alembic Migrations                     │
├──────────────────────────────────────────────────────────┤
│                    ARKA PLAN İŞLEMLERİ                   │
│  Celery (25+ Zamanlanmış Görev)                          │
│  ML Pipeline (Veri Toplama → Anomali → Eğitim)           │
│  Otomatik Yedekleme + Log Temizleme                      │
├──────────────────────────────────────────────────────────┤
│                    ALTYAPI                                │
│  Docker + Coolify (Self-hosted PaaS)                     │
│  Sentry (Hata İzleme) + Audit Logging                   │
│  KKTC Timezone (Europe/Nicosia)                          │
└──────────────────────────────────────────────────────────┘
```

### 2.2 Veritabanı Şeması (Ana Tablolar)

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│    oteller (3)   │────▶│   katlar (18)   │────▶│  odalar (558)   │
│  - ad            │     │  - kat_no       │     │  - oda_no       │
│  - adres         │     │  - otel_id      │     │  - kat_id       │
│  - aktif         │     │                 │     │  - oda_tipi_id  │
└─────────────────┘     └─────────────────┘     │  - qr_kod_token │
                                                 └────────┬────────┘
                                                          │
┌─────────────────┐     ┌─────────────────┐              │
│  oda_tipleri     │────▶│  setup_icerik   │◀─────────────┘
│  - tip_adi       │     │  - urun_id      │
│  - aciklama      │     │  - miktar       │  (Oda tipine göre
└─────────────────┘     │  - setup_id     │   minibar setup)
                         └─────────────────┘

┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│  urun_gruplari   │────▶│  urunler (69)   │────▶│  urun_stok      │
│  - grup_adi      │     │  - urun_adi     │     │  - miktar       │
│  (7 grup)        │     │  - alis_fiyati  │     │  - min_stok     │
└─────────────────┘     │  - satis_fiyati │     │  - max_stok     │
                         └────────┬────────┘     └─────────────────┘
                                  │
         ┌────────────────────────┼────────────────────────┐
         ▼                        ▼                        ▼
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│ minibar_islem   │     │ stok_hareketleri│     │ stok_fifo_kayit │
│ _detay          │     │  - hareket_tipi │     │  - miktar       │
│  - tuketim      │     │  - miktar       │     │  - kalan_miktar │
│  - eklenen      │     │  - tarih        │     │  - birim_fiyat  │
│  - satis_fiyati │     └─────────────────┘     └─────────────────┘
│  - kar_tutari   │
└─────────────────┘

┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│ kullanicilar(16)│     │ personel_zimmet │     │ otel_zimmet_stok│
│  - rol          │────▶│  - personel_id  │     │  - otel_id      │
│  - otel_id      │     │  - durum        │     │  - urun_id      │
│  (3 rol tipi)   │     │  - detaylar     │     │  - miktar       │
└─────────────────┘     └─────────────────┘     └─────────────────┘

┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│ gunluk_gorevler │────▶│ gorev_detaylari │     │ oda_kontrol     │
│  - gorev_tarihi │     │  - oda_id       │     │ _kayitlari      │
│  - gorev_tipi   │     │  - durum        │     │  - kontrol_tipi │
│  - otel_id      │     │  - personel_id  │     │  - kontrol_tarihi│
└─────────────────┘     └─────────────────┘     └─────────────────┘

┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│ ml_metrics      │     │ ml_alerts       │     │ ml_models       │
│  (176.274)      │     │  (18.021)       │     │  - model_tipi   │
│  - metric_type  │     │  - alert_type   │     │  - accuracy     │
│  - value        │     │  - severity     │     │  - model_path   │
└─────────────────┘     └─────────────────┘     └─────────────────┘
```

---

## 3. Kullanıcı Rolleri ve Yetkileri

### 3.1 Rol Hiyerarşisi

```
                    ┌──────────────────────┐
                    │  Sistem Yöneticisi   │  (3 kişi)
                    │  ─────────────────── │
                    │  • Tüm otellere erişim│
                    │  • Kullanıcı yönetimi │
                    │  • Setup tanımlama    │
                    │  • ML Dashboard       │
                    │  • Raporlar           │
                    │  • Sistem ayarları    │
                    │  • Audit trail        │
                    │  • Yedekleme          │
                    └──────────┬───────────┘
                               │
              ┌────────────────┼────────────────┐
              ▼                                  ▼
┌──────────────────────┐          ┌──────────────────────┐
│   Depo Sorumlusu     │          │   Kat Sorumlusu      │  (11 kişi)
│   (2 kişi)           │          │   ─────────────────── │
│   ─────────────────── │          │  • Kendi katı odaları │
│  • Ana depo stok      │          │  • Minibar kontrol    │
│  • Tedarik yönetimi   │◀────────│  • Tüketim kaydı      │
│  • Zimmet dağıtımı    │ Sipariş │  • DND takibi         │
│  • Stok hareketleri   │ Talebi  │  • Görev yönetimi     │
│  • FIFO takibi        │          │  • Zimmet stoğu       │
│  • Sipariş onaylama   │          │  • QR kod okutma      │
└──────────────────────┘          │  • Dolum talebi       │
                                   └──────────────────────┘
```

### 3.2 Rol Bazlı Erişim Matrisi

| Modül              | Sistem Yöneticisi |  Depo Sorumlusu   |     Kat Sorumlusu     |
| ------------------ | :---------------: | :---------------: | :-------------------: |
| Dashboard          |  ✅ Tüm oteller   | ✅ Kendi otelleri |     ✅ Kendi katı     |
| Minibar Kontrol    |        ✅         |        ❌         |          ✅           |
| Stok Yönetimi      |        ✅         |        ✅         | 🔸 Sadece görüntüleme |
| Zimmet Yönetimi    |        ✅         |        ✅         |   ✅ Kendi zimmeti    |
| Görev Yönetimi     |        ✅         |        ✅         |          ✅           |
| Doluluk Yönetimi   |        ✅         |        ❌         |          ❌           |
| Raporlar           |      ✅ Tümü      | ✅ Stok raporları |  ✅ Kendi raporları   |
| Setup Tanımlama    |        ✅         |        ❌         |          ❌           |
| Kullanıcı Yönetimi |        ✅         |        ❌         |          ❌           |
| ML Dashboard       |        ✅         |        ❌         |          ❌           |
| Sistem Ayarları    |        ✅         |        ❌         |          ❌           |
| Audit Trail        |        ✅         |        ❌         |          ❌           |
| Yedekleme          |        ✅         |        ❌         |          ❌           |

---

## 4. Temel İş Akışları

### 4.1 Minibar Kontrol Akışı (Ana İş Süreci)

```
┌─────────────┐    ┌──────────────┐    ┌──────────────┐    ┌──────────────┐
│ Excel Import │───▶│ Misafir Kayıt│───▶│ Görev Oluştur│───▶│ Kat Sorumlusu│
│ (Doluluk)    │    │ (IN/ARR/DEP) │    │ (Otomatik)   │    │ Odaya Gider  │
└─────────────┘    └──────────────┘    └──────────────┘    └──────┬───────┘
                                                                   │
                    ┌──────────────┐    ┌──────────────┐          │
                    │ Tüketim      │◀───│ Setup ile    │◀─────────┘
                    │ Hesaplanır   │    │ Karşılaştır  │
                    │ (Otomatik)   │    │ (Mevcut stok)│
                    └──────┬───────┘    └──────────────┘
                           │
              ┌────────────┼────────────┐
              ▼                          ▼
┌──────────────────┐          ┌──────────────────┐
│ Tüketim Var      │          │ Tüketim Yok      │
│ ─────────────── │          │ ─────────────── │
│ • Stok düşülür   │          │ • Sadece kontrol │
│ • Zimmet güncellenir│       │   kaydı oluşur   │
│ • ML metrik kaydı │          │ • Görev tamamlanır│
│ • Dolum talebi    │          └──────────────────┘
│   oluşabilir      │
└──────────────────┘
```

### 4.2 Stok Yönetim Akışı (FIFO)

```
┌─────────────┐    ┌──────────────┐    ┌──────────────┐
│ Tedarikçiden │───▶│ Ana Depo     │───▶│ FIFO Kayıt   │
│ Mal Gelişi   │    │ Stok Girişi  │    │ (Tarih+Fiyat)│
└─────────────┘    └──────────────┘    └──────┬───────┘
                                               │
                    ┌──────────────┐           │
                    │ Kat Sorumlusu│◀──────────┘
                    │ Zimmet Talebi│    Zimmet Dağıtımı
                    └──────┬───────┘
                           │
                    ┌──────▼───────┐    ┌──────────────┐
                    │ Personel     │───▶│ Oda Minibar   │
                    │ Zimmet Stok  │    │ Dolum         │
                    └──────────────┘    └──────────────┘
```

### 4.3 ML Pipeline (Yapay Zeka Akışı)

```
┌─────────────────────────────────────────────────────────────┐
│                    ML PIPELINE                               │
│                                                              │
│  ┌──────────┐   ┌──────────┐   ┌──────────┐   ┌─────────┐ │
│  │ Veri     │──▶│ Feature  │──▶│ Model    │──▶│ Anomali │ │
│  │ Toplama  │   │ Engineer │   │ Eğitimi  │   │ Tespiti │ │
│  │ (Günlük) │   │ (30 gün) │   │ (Haftalık)│  │ (Günlük)│ │
│  └──────────┘   └──────────┘   └──────────┘   └────┬────┘ │
│                                                      │      │
│  Metrikler:                    Modeller:             ▼      │
│  • Stok seviye               • Isolation Forest  ┌──────┐  │
│  • Tüketim oranı             • Z-Score           │Alert │  │
│  • Dolum süresi              • Feature Selection  │Mgr  │  │
│  • Anomali skoru                                  └──────┘  │
│                                                              │
│  Alert Tipleri:              Severity:                       │
│  • bosta_tuketim_var (15.191)  • kritik                     │
│  • stok_anomali (2.714)        • yüksek                     │
│  • zimmet_fire_yuksek (116)    • orta                       │
│                                 • düşük                      │
└─────────────────────────────────────────────────────────────┘
```

---

## 5. API Endpoint Haritası

### 5.1 Route Modülleri (31 Modül)

| Modül           | Dosya                       | Temel İşlev                     |
| --------------- | --------------------------- | ------------------------------- |
| Auth            | `auth_routes.py`            | Giriş/çıkış, oturum yönetimi    |
| Dashboard       | `dashboard_routes.py`       | Ana panel, istatistikler        |
| Admin Minibar   | `admin_minibar_routes.py`   | Minibar yönetimi (admin)        |
| Admin Stok      | `admin_stok_routes.py`      | Stok yönetimi (admin)           |
| Admin Zimmet    | `admin_zimmet_routes.py`    | Zimmet yönetimi (admin)         |
| Admin QR        | `admin_qr_routes.py`        | QR kod yönetimi                 |
| Admin User      | `admin_user_routes.py`      | Kullanıcı yönetimi              |
| Kat Sorumlusu   | `kat_sorumlusu_routes.py`   | Kat operasyonları               |
| Depo            | `depo_routes.py`            | Depo operasyonları              |
| Doluluk         | `doluluk_routes.py`         | Doluluk yönetimi (Excel import) |
| Dolum Talebi    | `dolum_talebi_routes.py`    | Minibar dolum talepleri         |
| Görev           | `gorev_routes.py`           | Günlük görev yönetimi           |
| Stok            | `stok_routes.py`            | Stok API'leri                   |
| Rapor           | `rapor_routes.py`           | 15+ rapor tipi                  |
| ML              | `ml_routes.py`              | Makine öğrenmesi dashboard      |
| Bildirim        | `bildirim_routes.py`        | Bildirim sistemi                |
| API             | `api_routes.py`             | Genel API endpoint'leri         |
| Health          | `health_routes.py`          | Sistem sağlık kontrolü          |
| Celery          | `celery_routes.py`          | Arka plan görev yönetimi        |
| Sistem Ayarları | `sistem_ayarlari_routes.py` | Konfigürasyon                   |
| Developer       | `developer_routes.py`       | Geliştirici araçları            |

### 5.2 Celery Zamanlanmış Görevler (25+)

| Görev                                   | Periyot     | İşlev                    |
| --------------------------------------- | ----------- | ------------------------ |
| `ml_veri_toplama_task`                  | Her 4 saat  | ML metrik toplama        |
| `ml_anomali_tespiti_task`               | Her 6 saat  | Anomali tespiti          |
| `ml_model_egitimi_task`                 | Haftalık    | Model eğitimi            |
| `ml_stok_bitis_kontrolu_task`           | Her 12 saat | Stok tükenme tahmini     |
| `haftalik_trend_analizi_task`           | Haftalık    | Tüketim trend analizi    |
| `aylik_stok_devir_analizi_task`         | Aylık       | Stok devir hızı          |
| `gunluk_yukleme_gorevleri_olustur_task` | Günlük      | Otomatik görev oluşturma |
| `doluluk_yukleme_uyar_kontrolu_task`    | Günlük      | Doluluk uyarıları        |
| `dnd_tamamlanmayan_kontrol_task`        | Günlük      | DND takibi               |
| `gunluk_gorev_raporu_task`              | Günlük      | Görev özet raporu        |
| `gunluk_minibar_sarfiyat_raporu_task`   | Günlük      | Sarfiyat raporu          |
| `otomatik_yedekleme_task`               | Günlük      | Veritabanı yedekleme     |
| `eski_yedekleri_temizle_task`           | Haftalık    | Eski yedek temizleme     |
| `query_logs_temizle_task`               | Günlük      | Log temizleme            |
| `ml_eski_verileri_temizle_task`         | Haftalık    | ML veri temizleme        |
| `ml_gunluk_alert_ozeti_task`            | Günlük      | Alert özet e-posta       |

---

## 6. Canlı Veri Analizi (Son 3 Ay)

### 6.1 Otel Bazlı Dağılım

| Otel                | Oda Sayısı | Kat Sayısı |
| ------------------- | :--------: | :--------: |
| Merit Royal Diamond |    302     |     7      |
| Merit Royal Premium |    131     |     6      |
| Merit Royal Hotel   |    125     |     5      |
| **Toplam**          |  **558**   |   **18**   |

### 6.2 Aylık Minibar İşlem Trendi

| Ay          | İşlem Sayısı | Kontrol Edilen Oda | Toplam Tüketim (adet) |
| ----------- | :----------: | :----------------: | :-------------------: |
| Aralık 2025 |    1.665     |        264         |         2.784         |
| Ocak 2026   |    26.285    |        539         |        19.232         |
| Şubat 2026  |    19.964    |        549         |        10.654         |

### 6.3 Görev Tamamlanma Oranları

| Ay          | Toplam Görev | Tamamlanan | Bekleyen | Tamamlanma % |
| ----------- | :----------: | :--------: | :------: | :----------: |
| Aralık 2025 |    13.425    |    261     |  13.111  |     %1.9     |
| Ocak 2026   |    15.865    |   5.461    |  9.447   |    %34.4     |
| Şubat 2026  |    10.770    |   4.765    |  4.698   |  **%44.2**   |

> **Trend:** Görev tamamlanma oranı Aralık'tan Şubat'a **%1.9 → %44.2** olarak dramatik şekilde artmıştır. Sistem adaptasyonu başarılı.

### 6.4 En Çok Tüketilen Ürünler (Top 10)

| #   | Ürün                      | Grup               | Toplam Tüketim |
| --- | ------------------------- | ------------------ | :------------: |
| 1   | Küçük Su Cam Logolu 330ml | Alkolsüz İçecekler |     8.026      |
| 2   | Su Cam Logolu 750ml       | Alkolsüz İçecekler |     2.888      |
| 3   | Soda Şişe Sade 200ml      | Alkolsüz İçecekler |     1.577      |
| 4   | Redbull 250ml             | Alkolsüz İçecekler |     1.473      |
| 5   | Ice Tea Şeftali 330ml     | Alkolsüz İçecekler |     1.360      |
| 6   | Bitki Çayları 2gr         | Sıcak İçecek       |     1.320      |
| 7   | Bira Efes Şişe 33cl       | Alkollü İçecekler  |     1.166      |
| 8   | Pepsi Max 250ml           | Alkolsüz İçecekler |     1.079      |
| 9   | Pepsi Kutu 250ml          | Alkolsüz İçecekler |     1.074      |
| 10  | Yedigün Kutu 250ml        | Alkolsüz İçecekler |     1.032      |

### 6.5 ML Alert Dağılımı

| Alert Tipi         | Severity |  Sayı  |
| ------------------ | -------- | :----: |
| Boşta Tüketim Var  | Kritik   | 15.191 |
| Stok Anomali       | Düşük    | 2.095  |
| Stok Anomali       | Kritik   |  443   |
| Zimmet Fire Yüksek | Orta     |  116   |
| Stok Anomali       | Orta     |   92   |
| Stok Anomali       | Yüksek   |   84   |

---

## 7. Güvenlik Mimarisi

### 7.1 Güvenlik Katmanları

```
┌─────────────────────────────────────────────────┐
│ 1. CSRF Koruması (WTF-CSRF, 1 saat timeout)    │
│ 2. Session Güvenliği (HttpOnly, SameSite=Lax)   │
│ 3. Rate Limiting (Login: 5/dk, API: 100/dk)     │
│ 4. Security Headers (CSP, HSTS, X-Frame-Options)│
│ 5. Rol Bazlı Erişim Kontrolü (RBAC)            │
│ 6. Audit Logging (68.528+ kayıt)               │
│ 7. Şifre Hashing (Werkzeug)                    │
│ 8. SQL Injection Koruması (SQLAlchemy ORM)      │
│ 9. XSS Koruması (Jinja2 auto-escape)           │
│ 10. Dosya Yükleme Kısıtlaması (16MB, whitelist) │
└─────────────────────────────────────────────────┘
```

### 7.2 Audit Trail Sistemi

Her kritik işlem `audit_logs` tablosuna kaydedilir:

- İşlem tipi (CRUD + özel işlemler)
- Kullanıcı bilgisi
- IP adresi ve User-Agent
- Eski/yeni değer karşılaştırması
- Zaman damgası (KKTC timezone)

---

## 8. Raporlama Sistemi

### 8.1 Rapor Tipleri (15+)

| Kategori          | Rapor                         | Format            |
| ----------------- | ----------------------------- | ----------------- |
| **Doluluk**       | Günlük doluluk raporu         | Web + Excel       |
| **Doluluk**       | Haftalık doluluk özeti        | Web + Excel       |
| **Stok**          | Mevcut stok raporu            | Web + Excel       |
| **Stok**          | Stok hareketleri raporu       | Web + Excel       |
| **Stok**          | Stok devir raporu             | Web + Excel       |
| **Stok**          | Stok değer raporu             | Web               |
| **Minibar**       | Detaylı minibar raporu        | Web + Excel       |
| **Minibar**       | Özet minibar raporu           | Web + Excel       |
| **Zimmet**        | Zimmet raporu                 | Web + Excel       |
| **Performans**    | Personel performans raporu    | Web + Excel       |
| **Otel Zimmet**   | Otel zimmet stok raporu       | Web + Excel + PDF |
| **Kat Sorumlusu** | Kullanım raporu               | Web + Excel + PDF |
| **Oda Bazlı**     | Tüketim raporu                | Web               |
| **Görev**         | Günlük görev detay raporu     | Web               |
| **Karşılaştırma** | Otel karşılaştırma raporu     | Web               |
| **Gün Sonu**      | Kat sorumlusu gün sonu raporu | Web + Excel + PDF |

---

## 9. Gelecek Geliştirme Önerileri

### 9.1 Kısa Vadeli (1-3 Ay)

| #   | Geliştirme                            | Beklenen Kazanım                        |
| --- | ------------------------------------- | --------------------------------------- |
| 1   | PMS (Opera/Protel) Entegrasyonu       | Manuel Excel import'u ortadan kaldırma  |
| 2   | Mobil Uygulama (PWA iyileştirme)      | Kat sorumlusu sahada daha hızlı çalışır |
| 3   | Gelir Raporlama Modülü                | Minibar gelir/kar analizi               |
| 4   | Tedarikçi Portal                      | Otomatik sipariş ve fiyat güncelleme    |
| 5   | Görev tamamlanma oranını %70+ çıkarma | Operasyonel verimlilik                  |

### 9.2 Orta Vadeli (3-6 Ay)

| #   | Geliştirme                | Beklenen Kazanım                       |
| --- | ------------------------- | -------------------------------------- |
| 1   | Tahminleme Modeli (ML v2) | Stok tükenme tahmini, otomatik sipariş |
| 2   | Misafir Profil Analizi    | Kişiselleştirilmiş minibar setup       |
| 3   | Sezonsal Analiz           | Dönemsel stok optimizasyonu            |
| 4   | Multi-property Dashboard  | Tüm otelleri tek ekranda karşılaştırma |
| 5   | Otomatik Fiyatlandırma    | Dinamik fiyat optimizasyonu            |

### 9.3 Uzun Vadeli (6-12 Ay)

| #   | Geliştirme                     | Beklenen Kazanım                |
| --- | ------------------------------ | ------------------------------- |
| 1   | IoT Sensör Entegrasyonu        | Gerçek zamanlı minibar izleme   |
| 2   | Chatbot / Misafir Self-Service | Misafir minibar siparişi        |
| 3   | Blockchain Tedarik Zinciri     | Şeffaf tedarik takibi           |
| 4   | Gelişmiş BI Dashboard          | Power BI / Grafana entegrasyonu |
| 5   | Çoklu Otel Zinciri Desteği     | Franchise model                 |

---

## 10. Sistem Performans Metrikleri

```
Veritabanı Bağlantı Havuzu: 8 bağlantı/worker + 8 overflow
Statement Timeout: 60 saniye
Connection Recycle: 15 dakika
Cache: Master data only (ürün, setup, otel/kat/oda)
Session Lifetime: 8 saat
Gunicorn Workers: 4 × 4 thread = 16 eşzamanlı istek
```

---

_Bu doküman, Merit Royal Otel Grubu Minibar Takip Sistemi'nin 21 Şubat 2026 tarihli canlı üretim ortamı verilerine dayanmaktadır._
