"""
ML System Benchmark - Performans Analizi ve Test
Tüm ML özelliklerinin performansını ölçer
"""

import time
import psutil
import numpy as np
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class MLSystemBenchmark:
    """ML sistem performans testi"""
    
    def __init__(self, db):
        self.db = db
        self.results = {}
    
    def measure_time_memory(self, func, *args, **kwargs):
        """Fonksiyon çalışma süresi ve bellek kullanımını ölç"""
        import tracemalloc
        
        # Başlangıç
        tracemalloc.start()
        start_time = time.time()
        start_memory = psutil.Process().memory_info().rss / 1024 / 1024  # MB
        
        # Fonksiyonu çalıştır
        try:
            result = func(*args, **kwargs)
            success = True
            error = None
        except Exception as e:
            result = None
            success = False
            error = str(e)
        
        # Bitiş
        end_time = time.time()
        end_memory = psutil.Process().memory_info().rss / 1024 / 1024  # MB
        current, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()
        
        metrics = {
            'duration_seconds': end_time - start_time,
            'memory_used_mb': end_memory - start_memory,
            'peak_memory_mb': peak / 1024 / 1024,
            'success': success,
            'error': error
        }
        
        return result, metrics
    
    def benchmark_data_collection(self):
        """Veri toplama performansı"""
        logger.info("📊 Veri toplama benchmark başladı...")
        
        # Eski sistem
        from utils.ml.data_collector import DataCollector
        old_collector = DataCollector(self.db)
        
        result, metrics = self.measure_time_memory(
            old_collector.collect_stok_metrics
        )
        
        self.results['data_collection_old'] = {
            'name': 'Veri Toplama (Eski)',
            'collected_count': result if result else 0,
            **metrics
        }
        
        # Yeni sistem
        from utils.ml.data_collector_v2 import DataCollectorV2
        new_collector = DataCollectorV2(self.db)
        
        result, metrics = self.measure_time_memory(
            new_collector.collect_stok_metrics_incremental
        )
        
        self.results['data_collection_new'] = {
            'name': 'Veri Toplama (Yeni - Incremental)',
            'collected_count': result if result else 0,
            **metrics
        }
        
        logger.info("✅ Veri toplama benchmark tamamlandı")
    
    def benchmark_feature_engineering(self):
        """Feature engineering performansı"""
        logger.info("📊 Feature engineering benchmark başladı...")
        
        from utils.ml.feature_engineer import FeatureEngineer
        
        engineer = FeatureEngineer(self.db)
        
        # Tek ürün için
        result, metrics = self.measure_time_memory(
            engineer.extract_stok_features,
            urun_id=1,
            lookback_days=30
        )
        
        self.results['feature_engineering_single'] = {
            'name': 'Feature Engineering (Tek Entity)',
            'feature_count': len(result) if result else 0,
            **metrics
        }
        
        # Tüm ürünler için
        result, metrics = self.measure_time_memory(
            engineer.create_feature_matrix,
            'stok_seviye',
            lookback_days=30
        )
        
        self.results['feature_engineering_matrix'] = {
            'name': 'Feature Engineering (Matrix)',
            'entity_count': len(result) if result is not None else 0,
            'feature_count': len(result.columns) if result is not None else 0,
            **metrics
        }
        
        logger.info("✅ Feature engineering benchmark tamamlandı")
    
    def benchmark_feature_selection(self):
        """Feature selection performansı"""
        logger.info("📊 Feature selection benchmark başladı...")
        
        from utils.ml.feature_engineer import FeatureEngineer
        from utils.ml.feature_selector import FeatureSelector
        
        # Feature matrix oluştur
        engineer = FeatureEngineer(self.db)
        df = engineer.create_feature_matrix('stok_seviye', lookback_days=30)
        
        if df is None or len(df) < 10:
            logger.warning("Yetersiz veri, feature selection atlanıyor")
            return
        
        selector = FeatureSelector()
        
        # Auto selection
        result, metrics = self.measure_time_memory(
            selector.auto_select,
            df.copy(),
            method='all'
        )
        
        self.results['feature_selection'] = {
            'name': 'Feature Selection (Auto)',
            'original_features': len(df.columns),
            'selected_features': len(result) if result else 0,
            'reduction_percent': ((len(df.columns) - len(result)) / len(df.columns) * 100) if result else 0,
            **metrics
        }
        
        logger.info("✅ Feature selection benchmark tamamlandı")
    
    def benchmark_feature_interaction(self):
        """Feature interaction performansı"""
        logger.info("📊 Feature interaction benchmark başladı...")
        
        from utils.ml.feature_engineer import FeatureEngineer
        from utils.ml.feature_interaction import enhance_features_with_interactions
        
        # Feature matrix oluştur
        engineer = FeatureEngineer(self.db)
        df = engineer.create_feature_matrix('stok_seviye', lookback_days=30)
        
        if df is None or len(df) < 10:
            logger.warning("Yetersiz veri, feature interaction atlanıyor")
            return
        
        original_count = len(df.columns)
        
        # Interaction ekleme
        result, metrics = self.measure_time_memory(
            enhance_features_with_interactions,
            df.copy()
        )
        
        self.results['feature_interaction'] = {
            'name': 'Feature Interaction',
            'original_features': original_count,
            'final_features': len(result.columns) if result is not None else 0,
            'added_features': (len(result.columns) - original_count) if result is not None else 0,
            **metrics
        }
        
        logger.info("✅ Feature interaction benchmark tamamlandı")
    
    def benchmark_model_training(self):
        """Model eğitimi performansı"""
        logger.info("📊 Model eğitimi benchmark başladı...")
        
        from utils.ml.model_trainer import ModelTrainer
        from models import MLMetric
        from datetime import timedelta, timezone
        
        trainer = ModelTrainer(self.db)
        
        # Veri hazırla
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=30)
        metrics = MLMetric.query.filter(
            MLMetric.metric_type == 'stok_seviye',
            MLMetric.timestamp >= cutoff_date
        ).all()
        
        if len(metrics) < 10:
            logger.warning("Yetersiz veri, model training atlanıyor")
            return
        
        data = np.array([m.metric_value for m in metrics])
        
        # Ham veri ile eğitim
        result, metrics_dict = self.measure_time_memory(
            trainer.train_isolation_forest,
            'stok_seviye',
            data,
            use_feature_engineering=False
        )
        
        self.results['model_training_basic'] = {
            'name': 'Model Eğitimi (Ham Veri)',
            'data_points': len(data),
            'accuracy': result[3] if result and result[0] else 0,
            **metrics_dict
        }
        
        # Feature engineering ile eğitim
        result, metrics_dict = self.measure_time_memory(
            trainer.train_isolation_forest,
            'stok_seviye',
            data,
            use_feature_engineering=True
        )
        
        self.results['model_training_advanced'] = {
            'name': 'Model Eğitimi (Feature Engineering)',
            'data_points': len(data),
            'feature_count': len(result[2]) if result and result[2] else 0,
            'accuracy': result[3] if result and result[0] else 0,
            **metrics_dict
        }
        
        logger.info("✅ Model eğitimi benchmark tamamlandı")
    
    def run_full_benchmark(self):
        """Tüm benchmark'ları çalıştır"""
        logger.info("🚀 Tam sistem benchmark başladı...")
        
        start_time = time.time()
        
        try:
            self.benchmark_data_collection()
        except Exception as e:
            logger.error(f"Data collection benchmark hatası: {str(e)}")
        
        try:
            self.benchmark_feature_engineering()
        except Exception as e:
            logger.error(f"Feature engineering benchmark hatası: {str(e)}")
        
        try:
            self.benchmark_feature_selection()
        except Exception as e:
            logger.error(f"Feature selection benchmark hatası: {str(e)}")
        
        try:
            self.benchmark_feature_interaction()
        except Exception as e:
            logger.error(f"Feature interaction benchmark hatası: {str(e)}")
        
        try:
            self.benchmark_model_training()
        except Exception as e:
            logger.error(f"Model training benchmark hatası: {str(e)}")
        
        total_time = time.time() - start_time
        
        logger.info(f"✅ Tam benchmark tamamlandı ({total_time:.2f} saniye)")
        
        return self.results
    
    def generate_report(self):
        """Benchmark raporu oluştur"""
        if not self.results:
            return "Benchmark henüz çalıştırılmadı!"
        
        report = []
        report.append("="*80)
        report.append("ML SİSTEM PERFORMANS RAPORU")
        report.append("="*80)
        report.append(f"Tarih: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report.append("")
        
        for key, result in self.results.items():
            report.append(f"\n{result['name']}")
            report.append("-"*60)
            report.append(f"  Süre: {result['duration_seconds']:.3f} saniye")
            report.append(f"  Bellek: {result['memory_used_mb']:.2f} MB")
            report.append(f"  Peak Bellek: {result['peak_memory_mb']:.2f} MB")
            report.append(f"  Başarılı: {'✅' if result['success'] else '❌'}")
            
            if not result['success']:
                report.append(f"  Hata: {result['error']}")
            
            # Özel metrikler
            for k, v in result.items():
                if k not in ['name', 'duration_seconds', 'memory_used_mb', 'peak_memory_mb', 'success', 'error']:
                    report.append(f"  {k}: {v}")
        
        report.append("\n" + "="*80)
        
        return "\n".join(report)
    
    def save_report(self, filepath='benchmark_report.txt'):
        """Raporu dosyaya kaydet"""
        report = self.generate_report()
        
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(report)
        
        logger.info(f"✅ Rapor kaydedildi: {filepath}")
        
        return filepath


# Kullanım
def run_system_benchmark():
    """Sistem benchmark'ını çalıştır"""
    try:
        from models import db
        from app import app
        
        with app.app_context():
            benchmark = MLSystemBenchmark(db)
            results = benchmark.run_full_benchmark()
            
            # Rapor oluştur
            report = benchmark.generate_report()
            print(report)
            
            # Dosyaya kaydet
            benchmark.save_report('docs/benchmark_report.txt')
            
            return results
            
    except Exception as e:
        logger.error(f"Benchmark hatası: {str(e)}")
        import traceback
        traceback.print_exc()
        return None


if __name__ == '__main__':
    run_system_benchmark()
