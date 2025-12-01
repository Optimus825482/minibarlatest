# Implementation Plan

- [x] 1. GorevService'e görev silme yönetim fonksiyonu ekle

  - [x] 1.1 `handle_misafir_kayit_deletion()` fonksiyonunu implement et

    - MisafirKayit ID listesi alır
    - Tamamlanmış görevlerde `misafir_kayit_id = NULL` yapar
    - Bekleyen görevleri siler
    - Boş kalan GunlukGorev kayıtlarını siler
    - Özet dict döndürür
    - _Requirements: 1.2, 1.3, 2.1, 2.4_

  - [ ]\* 1.2 Write property test for completed tasks preservation
    - **Property 1: Completed tasks preservation**
    - **Validates: Requirements 1.3, 2.1**
  - [ ]\* 1.3 Write property test for pending tasks deletion
    - **Property 2: Pending tasks deletion**
    - **Validates: Requirements 1.2**
  - [ ]\* 1.4 Write property test for parent task preservation
    - **Property 3: Parent task preservation with completed children**
    - **Validates: Requirements 2.4**

- [x] 2. FileManagementService silme fonksiyonunu güncelle

  - [x] 2.1 `delete_upload_by_islem_kodu()` fonksiyonunu genişlet

    - GorevService.handle_misafir_kayit_deletion() çağrısı ekle
    - Silme öncesi MisafirKayit ID'lerini topla
    - Özet bilgilerini döndür
    - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5_

  - [ ]\* 2.2 Write property test for atomic rollback
    - **Property 5: Atomic rollback on failure**
    - **Validates: Requirements 4.1**
  - [ ]\* 2.3 Write property test for deletion summary accuracy
    - **Property 6: Deletion summary accuracy**
    - **Validates: Requirements 4.2**

- [x] 3. Checkpoint - Make sure all tests are passing

  - Ensure all tests pass, ask the user if questions arise.

-

- [x] 4. Audit log entegrasyonu

  - [x] 4.1 Silme işlemi için audit log kaydı ekle

    - İşlem detaylarını kaydet (silinen/korunan kayıt sayıları)
    - Kullanıcı bilgilerini kaydet
    - _Requirements: 4.3_

- [x] 5. UI güncellemeleri

  - [x] 5.1 Tamamlanmış görevlerde "Kaynak silindi" göstergesi ekle

    - `misafir_kayit_id = NULL` olan görevlerde badge göster
    - Görev listesi ve detay sayfalarında görünsün
    - _Requirements: 3.1, 3.2_

  - [ ]\* 5.2 Write property test for report inclusion
    - **Property 7: Report inclusion of orphaned completed tasks**
    - **Validates: Requirements 3.3**

- [x] 6. Final Checkpoint - Make sure all tests are passing

  - Ensure all tests pass, ask the user if questions arise.
