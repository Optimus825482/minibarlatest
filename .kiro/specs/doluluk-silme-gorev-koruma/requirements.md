# Requirements Document

## Introduction

Bu özellik, doluluk yönetimi belgelerinin (Excel yüklemeleri) silinmesi durumunda ilişkili görevlerin nasıl yönetileceğini tanımlar. Temel prensip: Tamamlanmış görevlerin detayları (oda kontrol işlemleri) korunmalı, ancak bekleyen görevler silinebilir.

## Glossary

- **DosyaYukleme**: Excel dosya yükleme kaydı tablosu
- **MisafirKayit**: Excel'den yüklenen oda doluluk verileri
- **GunlukGorev**: Günlük minibar kontrol görevleri ana tablosu
- **GorevDetay**: Her oda için ayrı görev detayı
- **OdaKontrolKaydi**: Oda kontrol başlangıç/bitiş zamanları ve işlem kayıtları
- **MinibarIslem**: Minibar kontrol ve tüketim işlemleri
- **Tamamlanmış Görev**: `durum = 'completed'` olan GorevDetay kaydı
- **Bekleyen Görev**: `durum IN ('pending', 'dnd_pending', 'in_progress')` olan GorevDetay kaydı

## Requirements

### Requirement 1

**User Story:** As a depo sorumlusu, I want to delete uploaded occupancy files, so that I can correct mistakes or remove outdated data.

#### Acceptance Criteria

1. WHEN a depo sorumlusu deletes an upload record THEN the System SHALL remove the DosyaYukleme record and associated MisafirKayit records
2. WHEN a depo sorumlusu deletes an upload record THEN the System SHALL remove all pending GorevDetay records linked to the deleted MisafirKayit records
3. WHEN a depo sorumlusu deletes an upload record THEN the System SHALL preserve all completed GorevDetay records and their associated data
4. WHEN a depo sorumlusu deletes an upload record THEN the System SHALL preserve all OdaKontrolKaydi records for completed tasks
5. WHEN a depo sorumlusu deletes an upload record THEN the System SHALL preserve all MinibarIslem records for completed tasks

### Requirement 2

**User Story:** As a sistem yöneticisi, I want completed task data to be preserved even when source data is deleted, so that audit trails and historical records remain intact.

#### Acceptance Criteria

1. WHEN a MisafirKayit record is deleted THEN the System SHALL set the misafir_kayit_id to NULL in related completed GorevDetay records instead of deleting them
2. WHEN a completed GorevDetay exists THEN the System SHALL retain all DNDKontrol records associated with it
3. WHEN a completed GorevDetay exists THEN the System SHALL retain all GorevDurumLog records associated with it
4. WHEN a GunlukGorev has at least one completed GorevDetay THEN the System SHALL preserve the GunlukGorev record

### Requirement 3

**User Story:** As a kat sorumlusu, I want my completed work to be preserved regardless of administrative changes, so that my performance records remain accurate.

#### Acceptance Criteria

1. WHEN viewing completed tasks THEN the System SHALL display task details even if the source MisafirKayit was deleted
2. WHEN a source MisafirKayit is deleted THEN the System SHALL display "Kaynak silindi" indicator for affected completed tasks
3. WHEN generating reports THEN the System SHALL include completed tasks regardless of MisafirKayit deletion status

### Requirement 4

**User Story:** As a sistem yöneticisi, I want the deletion process to be atomic and consistent, so that data integrity is maintained.

#### Acceptance Criteria

1. WHEN deletion fails at any step THEN the System SHALL rollback all changes and maintain original state
2. WHEN deletion succeeds THEN the System SHALL return a summary of deleted and preserved records
3. WHEN deletion is attempted THEN the System SHALL log the operation details for audit purposes
