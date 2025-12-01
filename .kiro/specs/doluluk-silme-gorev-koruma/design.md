# Design Document

## Overview

Bu tasarım, doluluk yönetimi belgelerinin silinmesi sırasında görev verilerinin nasıl yönetileceğini tanımlar. Temel prensip "tamamlanmış işleri koru, bekleyen işleri temizle" mantığına dayanır.

### Mevcut Durum

Şu anda `FileManagementService.delete_upload_by_islem_kodu()` fonksiyonu:

1. DosyaYukleme kaydını siler
2. İlişkili MisafirKayit kayıtlarını siler
3. Fiziksel dosyayı siler

### Hedef Durum

Silme işlemi şu şekilde genişletilecek:

1. Tamamlanmış görevleri koruma
2. Bekleyen görevleri silme
3. Foreign key ilişkilerini düzgün yönetme
4. Audit log kaydı

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    FileManagementService                         │
│                                                                  │
│  delete_upload_by_islem_kodu(islem_kodu, user_id)               │
│         │                                                        │
│         ▼                                                        │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │ 1. DosyaYukleme kaydını bul                              │   │
│  └──────────────────────────────────────────────────────────┘   │
│         │                                                        │
│         ▼                                                        │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │ 2. İlişkili MisafirKayit ID'lerini al                    │   │
│  └──────────────────────────────────────────────────────────┘   │
│         │                                                        │
│         ▼                                                        │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │ 3. GorevDetay kayıtlarını analiz et                      │   │
│  │    - Tamamlanmış: misafir_kayit_id = NULL yap            │   │
│  │    - Bekleyen: Sil                                       │   │
│  └──────────────────────────────────────────────────────────┘   │
│         │                                                        │
│         ▼                                                        │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │ 4. Boş kalan GunlukGorev kayıtlarını sil                 │   │
│  └──────────────────────────────────────────────────────────┘   │
│         │                                                        │
│         ▼                                                        │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │ 5. MisafirKayit kayıtlarını sil                          │   │
│  └──────────────────────────────────────────────────────────┘   │
│         │                                                        │
│         ▼                                                        │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │ 6. DosyaYukleme kaydını sil + Fiziksel dosyayı sil       │   │
│  └──────────────────────────────────────────────────────────┘   │
│         │                                                        │
│         ▼                                                        │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │ 7. Audit log kaydı oluştur                               │   │
│  └──────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
```

## Components and Interfaces

### FileManagementService (Güncelleme)

```python
class FileManagementService:
    @staticmethod
    def delete_upload_by_islem_kodu(islem_kodu: str, user_id: int = None) -> Tuple[bool, str, Dict]:
        """
        İşlem koduna göre yüklemeyi ve ilgili kayıtları siler.
        Tamamlanmış görevleri korur.

        Args:
            islem_kodu: İşlem kodu
            user_id: Silme işlemini yapan kullanıcı ID

        Returns:
            Tuple[bool, str, Dict]: (success, message, summary)
            summary: {
                'deleted_misafir_kayit': int,
                'deleted_pending_tasks': int,
                'preserved_completed_tasks': int,
                'deleted_empty_gorevler': int
            }
        """
```

### GorevService (Yeni Fonksiyon)

```python
class GorevService:
    @staticmethod
    def handle_misafir_kayit_deletion(misafir_kayit_ids: List[int]) -> Dict:
        """
        MisafirKayit silinmeden önce ilişkili görevleri yönetir.

        Args:
            misafir_kayit_ids: Silinecek MisafirKayit ID listesi

        Returns:
            Dict: {
                'nullified_completed': int,  # misafir_kayit_id NULL yapılan
                'deleted_pending': int,       # Silinen bekleyen görevler
                'deleted_empty_gorevler': int # Silinen boş ana görevler
            }
        """
```

## Data Models

### Mevcut İlişkiler (Değişiklik Yok)

```
DosyaYukleme (1) ──── (N) MisafirKayit
                           │
                           │ misafir_kayit_id (FK, SET NULL)
                           ▼
                      GorevDetay ──── (N) DNDKontrol
                           │         ──── (N) GorevDurumLog
                           │
                           │ gorev_id (FK, CASCADE)
                           ▼
                      GunlukGorev
```

### Foreign Key Davranışları

| İlişki                     | Mevcut   | Hedef                     |
| -------------------------- | -------- | ------------------------- |
| MisafirKayit → GorevDetay  | SET NULL | SET NULL (değişiklik yok) |
| GunlukGorev → GorevDetay   | CASCADE  | CASCADE (değişiklik yok)  |
| GorevDetay → DNDKontrol    | CASCADE  | CASCADE (değişiklik yok)  |
| GorevDetay → GorevDurumLog | CASCADE  | CASCADE (değişiklik yok)  |

## Correctness Properties

_A property is a characteristic or behavior that should hold true across all valid executions of a system-essentially, a formal statement about what the system should do. Properties serve as the bridge between human-readable specifications and machine-verifiable correctness guarantees._

### Property 1: Completed tasks preservation

_For any_ deletion operation on a DosyaYukleme record, all GorevDetay records with `durum = 'completed'` that were linked to the deleted MisafirKayit records should still exist after deletion with `misafir_kayit_id = NULL`
**Validates: Requirements 1.3, 2.1**

### Property 2: Pending tasks deletion

_For any_ deletion operation on a DosyaYukleme record, all GorevDetay records with `durum IN ('pending', 'dnd_pending', 'in_progress')` that were linked to the deleted MisafirKayit records should be deleted
**Validates: Requirements 1.2**

### Property 3: Parent task preservation with completed children

_For any_ GunlukGorev record that has at least one completed GorevDetay, the GunlukGorev record should be preserved after deletion of related MisafirKayit records
**Validates: Requirements 2.4**

### Property 4: Empty parent task cleanup

_For any_ GunlukGorev record that has no remaining GorevDetay records after deletion, the GunlukGorev record should also be deleted
**Validates: Requirements 1.2**

### Property 5: Atomic rollback on failure

_For any_ deletion operation that fails at any step, all database changes should be rolled back and the original state should be maintained
**Validates: Requirements 4.1**

### Property 6: Deletion summary accuracy

_For any_ successful deletion operation, the returned summary should accurately reflect the counts of deleted MisafirKayit records, deleted pending tasks, and preserved completed tasks
**Validates: Requirements 4.2**

### Property 7: Report inclusion of orphaned completed tasks

_For any_ completed GorevDetay with `misafir_kayit_id = NULL`, the task should still appear in task reports and summaries
**Validates: Requirements 3.3**

## Error Handling

### Hata Senaryoları

1. **İşlem kodu bulunamadı**: `(False, "İşlem kodu bulunamadı", {})`
2. **Veritabanı hatası**: Rollback + `(False, "Silme hatası: {error}", {})`
3. **Dosya silme hatası**: Log + devam et (kritik değil)

### Rollback Stratejisi

```python
try:
    # Tüm işlemler
    db.session.commit()
except Exception as e:
    db.session.rollback()
    raise
```

## Testing Strategy

### Dual Testing Approach

Bu özellik için hem unit testler hem de property-based testler kullanılacaktır:

- **Unit Tests**: Spesifik senaryoları ve edge case'leri test eder
- **Property-Based Tests**: Genel doğruluk özelliklerini rastgele verilerle doğrular

### Property-Based Testing Framework

- **Framework**: `hypothesis` (Python)
- **Minimum iterations**: 100
- **Test dosyası**: `tests/test_doluluk_silme_properties.py`

### Test Senaryoları

1. **Sadece bekleyen görevler**: Tümü silinmeli
2. **Sadece tamamlanmış görevler**: Tümü korunmalı
3. **Karışık görevler**: Bekleyenler silinmeli, tamamlanmışlar korunmalı
4. **Boş ana görev**: Silinmeli
5. **Kısmen dolu ana görev**: Korunmalı
6. **Hata durumu**: Rollback çalışmalı
