# ML Sistemi - Tam Veri Akışı

## 🎯 Genel Bakış

Bu doküman, ML sisteminin baştan sona tüm veri akışını açıklar.

## 📊 Veri Akış Diyagramı

```
┌─────────────────────────────────────────────────────────────────┐
│                    1. HAM VERİ TOPLAMA                          │
│                                                                 │
│  DataCollectorV2 → ml_metrics tablosu                          │
│  - stok_seviye                                                  │
│  - tuketim_miktar                                              │
│  - dolum_sure                                                   │
│  - zimmet_kullanim                                             │
└─────────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────────┐
│                 2. FEATURE ENGINEERING                          │
│                                                                 │
│  FeatureEngineer → 20+ feature oluşturur                       │
│  - Statistical: mean, std, min, max, median, q25, q75         │
│  - Trend: slope, direction, volatility, momentum               │
│  - Time: hour, day_of_week, is_weekend, day_of_month         │
│  - Domain: days_since_change, change_frequency, etc.          │
│  - Lag: lag_1, lag_7, lag_30                                  │
│  - Rolling: rolling_mean_7, rolling_std_7, etc.              │
└─────────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────────┐
│                  3. FEATURE STORAGE ✅ YENİ                     │
│                                                                 │
│  FeatureStorage → ml_features tablosu                          │
│  - Feature'lar kaydedilir                                      │
│  - Hızlı erişim için index'lenir                              │
│  - Geçmiş takip edilir                                         │
└─────────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────────┐
│                   4. FEATURE SELECTION                          │
│                                                                 │
│  FeatureSelector → En iyi feature'ları seçer                   │
│  - Correlation-based                                           │
│  - Variance-based                                              │
│  - Mutual information                                          │
└─────────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────────┐
│                  5. FEATURE INTERACTION                         │
│                                                                 │
│  FeatureInteraction → Feature kombinasyonları                  │
│  - Polynomial interactions                                     │
│  - Feature combinations                                        │
└─────────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────────┐
│                    6. MODEL TRAINING                            │
│                                                                 │
│  ModelTrainer → ml_models tablosu                              │
│  - Isolation Forest                                            │
│  - Z-Score                                                     │
│  - Deep Learning (opsiyonel)                                   │
└─────────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────────┐
│                   7. ANOMALY DETECTION                          │
│                                                                 │
│  AnomalyDetector → ml_alerts tablosu                           │
│  - Stok anomalileri                                            │
│  - Tüketim anomalileri                                         │
│  - Dolum gecikmeleri                                           │
└─────────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────────┐
│                    8. ALERTS & ACTIONS                          │
│                                                                 │
│  - Dashboard'da gösterim                                       │
│  - Email/SMS bildirimleri                                      │
│  - Otomatik aksiyonlar                                         │
└─────────────────────────────────────────────────────────────────┘
```

## 🗄️ Veritabanı Tabloları

### 1. ml_metrics (Ham Veri)

```sql
- id
- metric_type (stok_seviye, tuketim_miktar, vb.)
- entity_id (urun_id, oda_id, vb.)
- metric_value (ham değer)
- timestamp
- extra_data (JSONB)
```

### 2. ml_features (İşlenmiş Feature'lar) ✅ YENİ

```sql
- id
- metric_type
- entity_id
- timestamp
- mean_value, std_value, min_value, max_value, ...
- trend_slope, trend_direction, volatility, ...
- hour_of_day, day_of_week, is_weekend, ...
- lag_1, lag_7, lag_30
- rolling_mean_7, rolling_std_7, ...
- extra_features (JSONB)
```

### 3. ml_models (Eğitilmiş Modeller)

```sql
- id
- model_type (isolation_forest, z_score)
- metric_type
- model_data (pickle) veya model_path (dosya)
- parameters (JSONB)
- accuracy, precision, recall
- is_active
```

### 4. ml_alerts (Uyarılar)

```sql
- id
- alert_type (stok_anomali, tuketim_anomali, vb.)
- severity (dusuk, orta, yuksek, kritik)
- entity_id
- metric_value, expected_value, deviation_percent
- message, suggested_action
- is_read, is_false_positive
```

### 5. ml_training_logs (Eğitim Logları)

```sql
- id
- model_id
- training_start, training_end
- data_points
- success, error_message
- metrics (JSONB)
```

## 🔄 Scheduler İşleri

### 1. Veri Toplama (Her 15 dakika)

```python
DataCollectorV2.collect_all_metrics()
↓
ml_metrics tablosuna kayıt
```

### 2. Feature Engineering (Her 30 dakika)

```python
FeatureEngineer.extract_stok_features(save_to_db=True)
↓
ml_features tablosuna kayıt ✅
```

### 3. Anomali Tespiti (Her 60 dakika)

```python
AnomalyDetector.detect_anomalies()
↓
ml_alerts tablosuna kayıt
```

### 4. Model Eğitimi (Günde 1 kez - 00:00)

```python
ModelTrainer.train_isolation_forest(use_stored_features=True)
↓
ml_models tablosuna kayıt
```

### 5. Cleanup (Her gece 04:00)

```python
- Eski ml_metrics (90 gün)
- Eski ml_features (90 gün) ✅
- Eski ml_alerts (30 gün)
- Eski ml_training_logs (180 gün)
```

## 📈 Performans Optimizasyonları

### 1. Incremental Data Collection

```python
# Sadece yeni verileri topla
DataCollectorV2.collect_stok_metrics_incremental()
# %80 hız artışı
```

### 2. Feature Storage ✅ YENİ

```python
# Feature'ları kaydet ve tekrar kullan
storage.get_feature_matrix('stok_seviye')
# %90 hız artışı
```

### 3. Feature Selection

```python
# Gereksiz feature'ları ele
selector.auto_select(df, method='all')
# %30-50 feature reduction
```

### 4. Model Caching

```python
# Modeli dosyaya kaydet
model_manager.save_model(model, 'isolation_forest', 'stok_seviye')
# Her seferinde eğitme
```

## 🎯 Kullanım Senaryoları

### Senaryo 1: Yeni Ürün Eklendi

```
1. Ürün oluşturuldu
2. İlk stok hareketi → ml_metrics
3. 15 dakika sonra → Feature engineering → ml_features ✅
4. 30 dakika sonra → Anomali tespiti
5. Gece → Model yeniden eğitilir
```

### Senaryo 2: Stok Anomalisi Tespit Edildi

```
1. Anomali tespit edildi → ml_alerts
2. Dashboard'da gösterildi
3. Email/SMS gönderildi
4. Depo sorumlusu kontrol etti
5. False positive → is_false_positive=True
6. Model yeniden eğitilir (false positive'i öğrenir)
```

### Senaryo 3: Model Performansı Düştü

```
1. Accuracy < 0.7 tespit edildi
2. Yeni veri toplandı
3. Feature engineering yapıldı → ml_features ✅
4. Feature selection yapıldı
5. Model yeniden eğitildi
6. Performans iyileşti
```

## 🔍 Monitoring ve Debugging

### 1. Feature Kalitesi

```python
# Feature'ların kalitesini kontrol et
storage = FeatureStorage(db)
df = storage.get_feature_matrix('stok_seviye')

# Null değerler
print(df.isnull().sum())

# Feature korelasyonları
print(df.corr())
```

### 2. Model Performansı

```python
# Model accuracy'yi kontrol et
model = MLModel.query.filter_by(
    metric_type='stok_seviye',
    is_active=True
).first()

print(f"Accuracy: {model.accuracy}")
print(f"Precision: {model.precision}")
print(f"Recall: {model.recall}")
```

### 3. Alert Analizi

```python
# False positive oranı
total_alerts = MLAlert.query.count()
false_positives = MLAlert.query.filter_by(is_false_positive=True).count()
fp_rate = false_positives / total_alerts

print(f"False Positive Rate: {fp_rate:.2%}")
```

## 📊 Metrikler ve KPI'lar

### Sistem Sağlığı

- ✅ Veri toplama başarı oranı: >95%
- ✅ Feature engineering başarı oranı: >90%
- ✅ Model accuracy: >70%
- ✅ Alert false positive rate: <20%

### Performans

- ✅ Veri toplama süresi: <1 saniye
- ✅ Feature engineering süresi: <5 saniye
- ✅ Model training süresi: <30 saniye
- ✅ Anomali tespiti süresi: <10 saniye

### Veri Kalitesi

- ✅ Null değer oranı: <5%
- ✅ Duplicate oranı: 0%
- ✅ Feature coverage: >80%
- ✅ Data freshness: <1 saat

## 🚀 Gelecek Geliştirmeler

1. **Real-time Feature Engineering**

   - Stream processing ile anlık feature hesaplama
   - Apache Kafka entegrasyonu

2. **Advanced Feature Selection**

   - SHAP values ile feature importance
   - Recursive feature elimination

3. **AutoML**

   - Otomatik model seçimi
   - Hyperparameter tuning

4. **Distributed Training**
   - Büyük veri setleri için
   - Spark/Dask entegrasyonu

## 📞 Destek

- Developer Dashboard: `/developer/dashboard`
- Dokümanlar: `/docs`
- Loglar: `logs/ml_system.log`
