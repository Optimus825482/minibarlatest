# Implementation Plan - ML Sistem Optimizasyonu

## Task List

- [x] 1. Database Migration ve Schema Güncellemesi

  - Alembic migration dosyası oluştur
  - `ml_models` tablosuna `model_path` kolonu ekle
  - `model_data` kolonunu nullable yap
  - Index'leri ekle
  - Migration test et (up/down)
  - _Requirements: 1.5, 5.1, 5.2_

- [x] 2. ModelManager Servisi - Temel Yapı

  - `utils/ml/model_manager.py` dosyası oluştur
  - ModelManager class tanımla
  - `__init__` metodunu implement et
  - `_ensure_directory_exists` metodunu implement et
  - `_generate_filename` metodunu implement et
  - `_validate_path` metodunu implement et (security)
  - `_get_file_size_kb` metodunu implement et
  - `_check_disk_space` metodunu implement et
  - _Requirements: 4.1, 4.2, 4.8_

- [x] 3. ModelManager - Model Kaydetme

  - `save_model_to_file` metodunu implement et
  - Model'i pickle ile serialize et
  - Dosya adı oluştur (timestamp ile)
  - Dosyayı `/app/ml_models/` dizinine kaydet
  - File permissions ayarla (644)
  - PostgreSQL'e metadata kaydet (path, accuracy, date)
  - Error handling ekle (IOError, DatabaseError)
  - Logging ekle
  - _Requirements: 1.1, 1.2, 1.3, 1.4, 6.1_

- [x] 4. ModelManager - Model Yükleme

  - `load_model_from_file` metodunu implement et
  - Dosya varlığını kontrol et
  - Pickle ile deserialize et
  - Model validation yap (corrupt check)
  - Retry mekanizması ekle (3 deneme, exponential backoff)
  - Error handling ekle (PickleError, IOError)
  - Logging ekle
  - _Requirements: 2.1, 2.2, 2.4, 6.2_

- [x] 5. ModelManager - Backward Compatibility

  - `load_model_from_file` içinde fallback ekle
  - Dosya bulunamazsa veritabanını kontrol et
  - Veritabanından model yükle (eski yöntem)
  - Yüklenen modeli dosyaya kaydet (migration)
  - Veritabanındaki model_data'yı NULL yap
  - _Requirements: 5.1, 5.2, 5.3, 5.4, 5.5_

- [x] 6. ModelManager - Model Listeleme ve Bilgi

  - `list_available_models` metodunu implement et
  - Dosya sistemindeki modelleri tara
  - PostgreSQL'den metadata al
  - Model bilgilerini birleştir
  - `get_model_info` metodunu implement et
  - _Requirements: 4.5, 4.7_

- [x] 7. ModelManager - Cleanup ve Versiyonlama

  - `cleanup_old_models` metodunu implement et
  - Her model tipi için dosyaları listele
  - Timestamp'e göre sırala
  - En son 3 versiyonu sakla, diğerlerini sil
  - PostgreSQL'de is_active=false yap
  - 30 günden eski inactive modelleri sil
  - Disk kullanımı %90+ ise acil temizlik
  - Freed space hesapla ve logla
  - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5, 6.5_

- [x] 8. Model Trainer Entegrasyonu

  - `utils/ml/model_trainer.py` dosyasını güncelle
  - ModelManager instance oluştur
  - `save_model` metodunu güncelle
  - ModelManager.save_model_to_file kullan
  - Eski veritabanı kaydetme metodunu fallback yap
  - Error handling ekle
  - Logging güncelle
  - _Requirements: 1.1, 1.4, 5.1_

- [x] 9. Anomaly Detector Entegrasyonu

  - `utils/ml/anomaly_detector.py` dosyasını güncelle
  - ModelManager instance oluştur
  - Model yükleme kodunu güncelle
  - ModelManager.load_model_from_file kullan
  - Fallback mekanizması ekle (Z-Score)
  - Model bulunamazsa Z-Score kullan
  - Memory cleanup ekle (del model)
  - Error handling ekle
  - Logging güncelle
  - _Requirements: 2.1, 2.3, 2.5, 9.1, 9.2, 9.3_

- [x] 10. Migration Script

  - `migrate_models_to_filesystem.py` scripti oluştur
  - Veritabanındaki tüm aktif modelleri oku
  - Her model için dosyaya kaydet
  - PostgreSQL'de model_path güncelle
  - model_data'yı NULL yap
  - Dry-run modu ekle (--dry-run flag)
  - Progress bar ekle
  - Özet rapor göster (migrated, failed, skipped)
  - Rollback mekanizması ekle
  - _Requirements: 10.1, 10.2, 10.3, 10.4, 10.5, 10.6, 10.7_

- [x] 11. Scheduler Entegrasyonu

  - `app.py` dosyasını güncelle
  - Cleanup job ekle (günlük 03:00)
  - ModelManager.cleanup_old_models çağır
  - Disk space monitoring ekle
  - Alert sistemi entegre et
  - _Requirements: 3.1, 3.5_

- [x] 12. Coolify Deployment Konfigürasyonu

  - `Dockerfile` güncelle
  - `/app/ml_models/` dizini oluştur
  - Directory permissions ayarla (755)
  - VOLUME tanımla
  - `docker-compose.yml` oluştur/güncelle
  - Persistent volume tanımla
  - Environment variables ekle (ML_MODELS_DIR)
  - `.dockerignore` kontrol et
  - _Requirements: 7.1, 7.2, 7.3, 7.4, 7.5_

- [x] 13. Monitoring ve Logging

  - Log mesajlarını standardize et
  - Model save/load için detaylı log
  - Disk usage warning ekle
  - Cleanup sonuçlarını logla
  - Performance metrikleri topla (load_time)
  - ml_metrics tablosuna kaydet
  - _Requirements: 6.1, 6.2, 6.3, 6.4, 6.5, 8.1, 8.2, 8.3, 8.4, 8.5_

- [x] 14. Error Handling ve Fallback

  - Tüm error scenario'ları implement et
  - File not found → Z-Score fallback
  - Corrupt file → Retry → Z-Score fallback
  - Disk full → Alert → Cleanup
  - Permission denied → Log → Use DB model
  - DB connection lost → Retry → Use file
  - Fallback kullanım sayısını izle
  - %50+ fallback ise kritik alert
  - _Requirements: 9.1, 9.2, 9.3, 9.4, 9.5_

- [x] 15. Unit Tests

  - `tests/test_model_manager.py` oluştur
  - test_save_model_to_file
  - test_load_model_from_file
  - test_file_not_found_returns_none
  - test_cleanup_keeps_latest_versions
  - test_disk_space_warning
  - test_corrupt_file_handling
  - test_backward_compatibility
  - test_migration_from_database
  - _Requirements: Testing Strategy_

- [x] 16. Integration Tests

  - `tests/test_ml_system_integration.py` oluştur
  - test_train_save_load_flow
  - test_anomaly_detection_with_file_model
  - test_fallback_to_zscore
  - test_migration_from_database
  - test_cleanup_integration
  - _Requirements: Testing Strategy_

- [x] 17. Performance Tests

  - `tests/test_performance.py` oluştur
  - test_model_load_time (< 100ms)
  - test_memory_usage (< 50MB artış)
  - test_concurrent_access (10 thread)
  - test_disk_usage
  - _Requirements: Testing Strategy, 8.1, 8.2_

- [x] 18. Documentation

  - README.md güncelle
  - Model dosya sistemi dokümante et
  - Migration adımlarını dokümante et
  - Troubleshooting guide ekle
  - API documentation (ModelManager)
  - _Requirements: General_

- [ ] 19. Deployment ve Verification

  - Database migration çalıştır (flask db upgrade)
  - Model migration çalıştır (dry-run → gerçek)
  - GitHub'a push et
  - Coolify auto-deploy
  - Persistent volume mount kontrol et
  - Model dosyalarını kontrol et (ls -lh /app/ml_models/)
  - Anomali tespiti test et
  - Logs kontrol et
  - Performance metrikleri kontrol et
  - _Requirements: 7.1, 7.2, 7.3, 7.4_

- [ ] 20. Post-Deployment Monitoring
  - İlk 24 saat logs izle
  - Model yükleme başarı oranı kontrol et
  - Fallback kullanım oranı kontrol et
  - Disk kullanımı izle
  - RAM kullanımı karşılaştır (önce/sonra)
  - Performance metrikleri karşılaştır
  - Anomali tespit kalitesi kontrol et
  - _Requirements: Success Criteria_

## Implementation Notes

### Önemli Noktalar

1. **Backward Compatibility**: Mevcut sistem çalışmaya devam etmeli. Dosya bulunamazsa veritabanını kullan.

2. **Zero Downtime**: Migration sırasında sistem çalışmaya devam etmeli. Önce dosya sistemini hazırla, sonra geçiş yap.

3. **Rollback Plan**: Her adımda rollback mümkün olmalı. Alembic downgrade, git revert hazır olsun.

4. **Testing**: Her component için test yaz. Integration testleri önemli.

5. **Monitoring**: Detaylı logging ekle. Performance metrikleri topla.

6. **Security**: Path validation, file permissions, no sensitive data.

7. **Coolify**: Persistent volume zorunlu. Volume mount test et.

### Sıralama Önemi

- Task 1-2: Temel altyapı (önce yapılmalı)
- Task 3-7: ModelManager (core functionality)
- Task 8-9: Entegrasyon (ModelManager hazır olmalı)
- Task 10: Migration (tüm kod hazır olmalı)
- Task 11-14: Ek özellikler
- Task 15-17: Testing (comprehensive)
- Task 18-20: Deployment ve monitoring

### Tahmini Süreler

- Task 1: 30 dakika
- Task 2: 1 saat
- Task 3: 1 saat
- Task 4: 1 saat
- Task 5: 1 saat
- Task 6: 30 dakika
- Task 7: 1 saat
- Task 8: 30 dakika
- Task 9: 1 saat
- Task 10: 1 saat
- Task 11: 30 dakika
- Task 12: 1 saat
- Task 13: 30 dakika
- Task 14: 1 saat
- Task 15-17: 2 saat (optional)
- Task 18: 30 dakika
- Task 19: 1 saat
- Task 20: Ongoing

**Total**: ~15 saat (comprehensive testing dahil)

### Risk Mitigation

- **Risk**: Disk dolu → **Mitigation**: Otomatik cleanup, monitoring
- **Risk**: File corruption → **Mitigation**: Validation, retry, fallback
- **Risk**: Migration failure → **Mitigation**: Dry-run, rollback, backup
- **Risk**: Coolify volume → **Mitigation**: Testing, documentation

### Success Criteria

- ✅ RAM kullanımı %50 azalmalı
- ✅ Model yükleme < 100ms
- ✅ Disk kullanımı < 100MB
- ✅ Backward compatibility %100
- ✅ Zero downtime migration
- ✅ Tüm testler geçmeli
- ✅ Coolify'da sorunsuz çalışmalı
