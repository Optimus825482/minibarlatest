# ML Sistem Performans Analizi

## 📊 Genel Bakış

Bu doküman, ML sisteminin performans analizi ve optimizasyon sonuçlarını içerir.

## 🎯 Analiz Edilen Bileşenler

### 1. Veri Toplama (Data Collection)

- **Eski Sistem**: `DataCollector`
- **Yeni Sistem**: `DataCollectorV2` (Incremental)

### 2. Feature Engineering

- Tek entity feature extraction
- Toplu feature matrix oluşturma
- 20+ feature çıkarımı

### 3. Feature Selection

- Correlation-based selection
- Variance-based selection
- Mutual information selection

### 4. Feature Interaction

- Polynomial interactions
- Feature combinations

### 5. Model Training

- Ham veri ile eğitim
- Feature engineering ile eğitim

## 🚀 Benchmark Çalıştırma

```python
from utils.ml.system_benchmark import run_system_benchmark

# Tam benchmark
results = run_system_benchmark()
```

## 🔍 Entegrasyon Kontrolü

```python
from utils.ml.integration_checker import check_system_integration

# Entegrasyon kontrolü
results = check_system_integration()
```

## 📈 Beklenen İyileştirmeler

### Veri Toplama

- ✅ Duplicate prevention
- ✅ Incremental collection
- ✅ %50-70 hız artışı

### Feature Engineering

- ✅ 20+ feature otomatik çıkarımı
- ✅ Statistical, trend, domain features
- ✅ Model accuracy artışı

### Feature Selection

- ✅ Gereksiz feature'ları eleme
- ✅ %30-50 feature reduction
- ✅ Overfitting önleme

### Model Performance

- ✅ Daha yüksek accuracy
- ✅ Daha az false positive
- ✅ Daha hızlı prediction

## 📊 Metrikler

### Performans Metrikleri

- **Süre (Duration)**: Saniye cinsinden
- **Bellek (Memory)**: MB cinsinden
- **Peak Memory**: Maksimum bellek kullanımı
- **Başarı Oranı**: Success/Failure

### Kalite Metrikleri

- **Accuracy**: Model doğruluğu
- **Feature Count**: Kullanılan feature sayısı
- **Data Points**: İşlenen veri noktası sayısı
- **Reduction**: Feature azaltma oranı

## 🔧 Optimizasyon Önerileri

### 1. Veri Toplama

```python
# Incremental collection kullan
collector = DataCollectorV2(db)
collector.collect_stok_metrics_incremental()
```

### 2. Feature Engineering

```python
# Feature matrix oluştur
engineer = FeatureEngineer(db)
df = engineer.create_feature_matrix('stok_seviye', lookback_days=30)
```

### 3. Feature Selection

```python
# Auto selection
selector = FeatureSelector()
selected = selector.auto_select(df, method='all')
```

### 4. Model Training

```python
# Feature engineering ile eğit
trainer = ModelTrainer(db)
model = trainer.train_isolation_forest(
    'stok_seviye',
    data,
    use_feature_engineering=True
)
```

## 📝 Rapor Dosyaları

- `docs/benchmark_report.txt`: Performans benchmark raporu
- `docs/integration_report.txt`: Entegrasyon kontrol raporu

## ⚠️ Dikkat Edilmesi Gerekenler

1. **Veri Miktarı**: En az 10 veri noktası gerekli
2. **Bellek Kullanımı**: Büyük dataset'lerde dikkat
3. **Süre**: Feature engineering zaman alabilir
4. **Scheduler**: DataCollectorV2 kullanımına geç

## 🎯 Sonraki Adımlar

1. ✅ Benchmark çalıştır
2. ✅ Entegrasyon kontrol et
3. ⏳ Scheduler'ı güncelle
4. ⏳ Production'a deploy et
5. ⏳ Monitoring ekle

## 📞 Destek

Sorular için: Developer Dashboard > System Health
