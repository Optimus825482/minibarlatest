# Setup Yönetim Sistemi - Kullanım Kılavuzu

## Genel Bakış

Setup yönetim sistemi, otel odalarına atanacak minibar içeriklerini tanımlamak ve yönetmek için kullanılır.

## Erişim

- **URL:** `/setup-yonetimi`
- **Menü:** Admin Sidebar > Otel & Yapı > Setup'lar (Odalar'ın altında)
- **Yetki:** Sistem Yöneticisi, Admin

## Özellikler

### 1. Setup Listesi

- Tüm tanımlı setup'ları görüntüleme
- Her setup için:
  - Setup adı (MINI, MAXI vb.)
  - Açıklama
  - Ürün sayısı
  - Atanan oda tipleri

### 2. Yeni Setup Ekleme

- **Buton:** Sağ üstte "Yeni Setup Ekle"
- **Alanlar:**
  - Setup Adı (zorunlu)
  - Açıklama (opsiyonel)

### 3. Setup İçerik Düzenleme

- **Buton:** Her setup satırında "İçerik" butonu
- **İşlemler:**
  - Ürün listesinden ürün seçme
  - Adet belirleme
  - Ürün ekleme
  - Mevcut ürünleri silme

### 4. Setup Atama

- **Buton:** Her setup satırında "Atama" butonu
- **İşlem:** Setup'ı oda tiplerine atama
- Bir oda tipi sadece bir setup kullanabilir

### 5. Setup Silme

- **Buton:** Her setup satırında "Sil" butonu
- Soft delete (aktif = False)

## Veritabanı Yapısı

### setuplar Tablosu

- `id`: Primary key
- `ad`: Setup adı (unique)
- `aciklama`: Açıklama
- `aktif`: Aktif/Pasif durumu
- `olusturma_tarihi`: Oluşturma zamanı

### setup_icerik Tablosu

- `id`: Primary key
- `setup_id`: Setup referansı
- `urun_id`: Ürün referansı
- `adet`: Ürün adedi
- `olusturma_tarihi`: Oluşturma zamanı

## API Endpoint'leri

1. `GET /api/setuplar` - Setup listesi
2. `POST /api/setuplar` - Yeni setup ekle
3. `DELETE /api/setuplar/<id>` - Setup sil
4. `GET /api/setuplar/<id>/icerik` - Setup içeriği
5. `POST /api/setuplar/<id>/icerik` - İçeriğe ürün ekle
6. `DELETE /api/setup-icerik/<id>` - İçerikten ürün sil
7. `POST /api/setup-atama` - Setup'ı oda tiplerine ata
8. `GET /api/urunler-liste` - Ürün listesi

## Kullanım Senaryosu

### Örnek: MINI Setup Oluşturma

1. **Setup Oluştur:**

   - "Yeni Setup Ekle" butonuna tıkla
   - Ad: "MINI"
   - Açıklama: "Standart oda minibar içeriği"
   - Kaydet

2. **İçerik Ekle:**

   - MINI setup'ın "İçerik" butonuna tıkla
   - Ürün seç: "Coca Cola"
   - Adet: 2
   - Ekle
   - Diğer ürünleri de ekle

3. **Oda Tiplerine Ata:**
   - MINI setup'ın "Atama" butonuna tıkla
   - "STANDARD" ve "JUNIOR SUITE" oda tiplerini seç
   - Kaydet

## Varsayılan Setup'lar

- **MINI:** Mini setup - Standart oda içeriği
- **MAXI:** Maxi setup - Geniş oda içeriği

## Notlar

- Her oda tipi sadece bir setup kullanabilir
- Setup silindiğinde içeriği de silinir (cascade)
- Oda tipine atanan setup, oda tanımlarında görünür
