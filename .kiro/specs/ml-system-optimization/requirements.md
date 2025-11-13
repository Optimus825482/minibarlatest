# Requirements Document - ML Sistem Optimizasyonu

## Introduction

Bu spec, Minibar Takip Sistemi'nin ML (Machine Learning) alt sisteminin performans ve kaynak kullanımı optimizasyonlarını kapsar. Mevcut sistemde ML modelleri veritabanında (BLOB olarak) saklanıyor ve RAM'de tutulabiliyor. Bu optimizasyon ile modeller dosya sisteminde saklanacak ve ihtiyaç anında yüklenecek.

## Glossary

- **ML Model**: Makine öğrenmesi modeli (Isolation Forest, Z-Score)
- **Model Persistence**: Model kalıcılığı - modelin saklanması
- **File System Storage**: Dosya sistemi depolama
- **Database Storage**: Veritabanı depolama (BLOB)
- **RAM**: Random Access Memory - geçici bellek
- **Pickle**: Python object serialization format
- **Model Manager**: Model yönetim servisi
- **Anomaly Detector**: Anomali tespit motoru
- **Model Trainer**: Model eğitim servisi
- **Coolify**: Deployment platformu
- **PostgreSQL**: Veritabanı sistemi

## Requirements

### Requirement 1: Model Dosya Sistemi Depolama

**User Story:** As a sistem yöneticisi, I want ML modellerinin dosya sisteminde saklanmasını, so that RAM kullanımı azalsın ve sistem performansı artsın.

#### Acceptance Criteria

1. WHEN bir ML modeli eğitildiğinde, THE System SHALL modeli `/app/ml_models/` dizinine pickle formatında kaydetmek
2. WHEN model kaydedildiğinde, THE System SHALL dosya adını `{model_type}_{metric_type}_{timestamp}.pkl` formatında oluşturmak
3. WHEN model dosyası oluşturulduğunda, THE System SHALL dosya izinlerini 644 (rw-r--r--) olarak ayarlamak
4. WHEN model kaydedildiğinde, THE System SHALL veritabanında sadece model metadata'sını (path, accuracy, training_date) saklamak
5. WHERE model_data kolonu varsa, THE System SHALL bu kolonu nullable yapmak ve yeni modeller için NULL bırakmak

### Requirement 2: Model Yükleme ve Önbellekleme

**User Story:** As a sistem, I want modelleri ihtiyaç anında dosyadan yüklemek, so that başlangıç süresi hızlansın ve RAM kullanımı optimize edilsin.

#### Acceptance Criteria

1. WHEN anomali tespiti başladığında, THE System SHALL gerekli modeli dosyadan yüklemek
2. WHEN model yüklendiğinde, THE System SHALL model'in geçerliliğini kontrol etmek (corrupted file check)
3. IF model dosyası bulunamazsa, THEN THE System SHALL hata loglamak ve fallback Z-Score metodunu kullanmak
4. WHEN model yükleme başarısız olursa, THE System SHALL 3 kez retry denemek (exponential backoff ile)
5. WHEN anomali tespiti tamamlandığında, THE System SHALL yüklenen modeli bellekten temizlemek

### Requirement 3: Model Versiyonlama ve Temizlik

**User Story:** As a sistem yöneticisi, I want eski model dosyalarının otomatik temizlenmesini, so that disk alanı verimli kullanılsın.

#### Acceptance Criteria

1. WHEN yeni bir model eğitildiğinde, THE System SHALL aynı tip için en fazla 3 versiyon saklamak
2. WHEN 3'ten fazla versiyon olduğunda, THE System SHALL en eski versiyonu silmek
3. WHEN model dosyası silindiğinde, THE System SHALL veritabanındaki ilgili kaydı is_active=false yapmak
4. WHEN model temizliği çalıştığında, THE System SHALL 30 günden eski inactive modelleri silmek
5. WHERE disk kullanımı %90'ı geçerse, THE System SHALL acil temizlik başlatmak ve admin'e bildirim göndermek

### Requirement 4: Model Manager Servisi

**User Story:** As a developer, I want merkezi bir model yönetim servisi, so that model işlemleri tutarlı ve güvenli olsun.

#### Acceptance Criteria

1. THE System SHALL ModelManager sınıfı oluşturmak
2. WHEN ModelManager başlatıldığında, THE System SHALL `/app/ml_models/` dizinini kontrol etmek ve yoksa oluşturmak
3. THE System SHALL save_model_to_file(model, model_type, metric_type) metodunu sağlamak
4. THE System SHALL load_model_from_file(model_type, metric_type) metodunu sağlamak
5. THE System SHALL list_available_models() metodunu sağlamak
6. THE System SHALL cleanup_old_models(keep_versions=3) metodunu sağlamak
7. THE System SHALL get_model_info(model_type, metric_type) metodunu sağlamak
8. WHEN herhangi bir file operation hatası olursa, THEN THE System SHALL detaylı hata loglamak

### Requirement 5: Backward Compatibility

**User Story:** As a sistem yöneticisi, I want mevcut veritabanındaki modellerin çalışmaya devam etmesini, so that geçiş sorunsuz olsun.

#### Acceptance Criteria

1. WHEN model yüklenirken dosya bulunamazsa, THE System SHALL veritabanındaki model_data kolonunu kontrol etmek
2. IF model_data kolonu dolu ise, THEN THE System SHALL bu modeli kullanmak
3. WHEN veritabanından model yüklendiğinde, THE System SHALL bu modeli dosyaya da kaydetmek (migration)
4. THE System SHALL hem dosya hem veritabanı modellerini desteklemek
5. WHEN migration tamamlandığında, THE System SHALL veritabanındaki model_data'yı NULL yapmak

### Requirement 6: Monitoring ve Logging

**User Story:** As a sistem yöneticisi, I want model işlemlerinin loglanmasını, so that sorunları tespit edip çözebiliyim.

#### Acceptance Criteria

1. WHEN model kaydedildiğinde, THE System SHALL "Model saved: {path}, size: {size}KB" loglamak
2. WHEN model yüklendiğinde, THE System SHALL "Model loaded: {path}, load_time: {ms}ms" loglamak
3. WHEN model dosyası bulunamazsa, THE System SHALL ERROR seviyesinde loglamak
4. WHEN disk alanı azaldığında, THE System SHALL WARNING seviyesinde loglamak
5. WHEN model temizliği çalıştığında, THE System SHALL "Cleaned {count} old models, freed {size}MB" loglamak

### Requirement 7: Coolify Deployment Uyumluluğu

**User Story:** As a DevOps engineer, I want model dosyalarının Coolify deployment'ında korunmasını, so that her deploy'da modeller kaybolmasın.

#### Acceptance Criteria

1. THE System SHALL `/app/ml_models/` dizinini persistent volume olarak tanımlamak
2. WHEN Coolify deploy edildiğinde, THE System SHALL mevcut model dosyalarını korumak
3. THE System SHALL Dockerfile'da model dizinini oluşturmak
4. WHEN container başlatıldığında, THE System SHALL model dizini izinlerini kontrol etmek
5. THE System SHALL .dockerignore'da model dosyalarını exclude etmemek

### Requirement 8: Performance Metrikleri

**User Story:** As a sistem yöneticisi, I want model yükleme performansını izlemek, so that optimizasyon fırsatlarını görebiliyim.

#### Acceptance Criteria

1. WHEN model yüklendiğinde, THE System SHALL yükleme süresini ölçmek ve loglamak
2. WHEN anomali tespiti çalıştığında, THE System SHALL toplam süreyi ve model yükleme süresini karşılaştırmak
3. THE System SHALL model dosya boyutlarını izlemek
4. THE System SHALL disk kullanımını izlemek
5. WHEN performans metriği toplanırsa, THE System SHALL bu metrikleri ml_metrics tablosuna kaydetmek

### Requirement 9: Error Handling ve Fallback

**User Story:** As a sistem, I want model yükleme hatalarında fallback mekanizması, so that sistem çalışmaya devam etsin.

#### Acceptance Criteria

1. IF model dosyası corrupt ise, THEN THE System SHALL Z-Score metodunu fallback olarak kullanmak
2. IF model yükleme 3 kez başarısız olursa, THEN THE System SHALL anomali tespitini Z-Score ile devam ettirmek
3. WHEN fallback kullanıldığında, THE System SHALL admin'e bildirim göndermek
4. THE System SHALL fallback kullanım sayısını izlemek
5. IF fallback kullanımı %50'yi geçerse, THEN THE System SHALL kritik alert oluşturmak

### Requirement 10: Migration Script

**User Story:** As a sistem yöneticisi, I want mevcut veritabanı modellerini dosyaya migrate edecek script, so that geçiş otomatik olsun.

#### Acceptance Criteria

1. THE System SHALL migrate_models_to_filesystem.py scripti sağlamak
2. WHEN script çalıştırıldığında, THE System SHALL tüm aktif modelleri veritabanından okumak
3. WHEN model okunduğunda, THE System SHALL modeli dosyaya kaydetmek
4. WHEN dosyaya kaydedildiğinde, THE System SHALL veritabanında model_path güncellemek
5. WHEN migration tamamlandığında, THE System SHALL özet rapor göstermek (migrated: X, failed: Y)
6. THE System SHALL dry-run modu sağlamak (--dry-run flag)
7. WHEN migration başarısız olursa, THE System SHALL rollback yapmak

## Testing Strategy

### Unit Tests

- ModelManager sınıfı metodları
- Model save/load işlemleri
- File system operations
- Error handling scenarios

### Integration Tests

- Model eğitimi → dosyaya kaydetme → yükleme flow'u
- Anomali tespiti ile entegrasyon
- Veritabanı migration
- Cleanup işlemleri

### Performance Tests

- Model yükleme süresi (< 100ms olmalı)
- Disk kullanımı (model başına < 5MB)
- RAM kullanımı (yükleme sırasında < 50MB artış)
- Concurrent model yükleme

### Deployment Tests

- Coolify deployment sonrası model dosyalarının korunması
- Container restart sonrası model erişimi
- Persistent volume mount kontrolü

## Success Criteria

1. ✅ RAM kullanımı %50 azalmalı
2. ✅ Model yükleme süresi < 100ms olmalı
3. ✅ Disk kullanımı < 100MB olmalı (tüm modeller için)
4. ✅ Backward compatibility %100 olmalı
5. ✅ Zero downtime migration
6. ✅ Tüm testler geçmeli
7. ✅ Coolify deployment'da sorunsuz çalışmalı

## Non-Functional Requirements

### Performance

- Model yükleme: < 100ms
- Model kaydetme: < 500ms
- Cleanup işlemi: < 5 saniye

### Reliability

- Model yükleme başarı oranı: > %99.9
- Fallback mekanizması: %100 çalışmalı
- Data loss: 0

### Scalability

- 100+ model dosyası desteklemeli
- Concurrent access: 10+ thread
- Disk space: 1GB'a kadar

### Security

- File permissions: 644 (owner: rw, group: r, others: r)
- Directory permissions: 755
- No sensitive data in model files
- Secure file paths (no path traversal)

### Maintainability

- Clean code
- Comprehensive logging
- Clear error messages
- Documentation

## Dependencies

- Python 3.9+
- scikit-learn
- pickle
- PostgreSQL 14+
- Coolify deployment platform
- Existing ML system (anomaly_detector, model_trainer, data_collector)

## Risks and Mitigations

### Risk 1: Disk Space Yetersizliği

**Mitigation**: Otomatik cleanup, disk monitoring, alert sistemi

### Risk 2: File Corruption

**Mitigation**: Checksum validation, backup mechanism, fallback to Z-Score

### Risk 3: Concurrent Access

**Mitigation**: File locking, atomic operations, retry mechanism

### Risk 4: Migration Failure

**Mitigation**: Dry-run mode, rollback mechanism, backup before migration

### Risk 5: Coolify Persistent Volume

**Mitigation**: Volume mount testing, documentation, deployment checklist

## Timeline Estimate

- **Phase 1**: ModelManager servisi (2-3 saat)
- **Phase 2**: Model save/load implementasyonu (2-3 saat)
- **Phase 3**: Migration script (1-2 saat)
- **Phase 4**: Cleanup ve monitoring (1-2 saat)
- **Phase 5**: Testing ve deployment (2-3 saat)

**Total**: 8-13 saat

## Notes

- Bu optimizasyon backward compatible olmalı
- Mevcut sistem çalışmaya devam etmeli
- Zero downtime migration hedefleniyor
- Coolify deployment'a özel dikkat edilmeli
- Model dosyaları persistent volume'de saklanmalı
