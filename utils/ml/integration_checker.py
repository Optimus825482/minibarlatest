"""
Integration Checker - Sistem Entegrasyon Kontrolü
Tüm ML bileşenlerinin doğru entegre edildiğini kontrol eder
"""

import logging
from datetime import datetime

logger = logging.getLogger(__name__)


class IntegrationChecker:
    """Sistem entegrasyon kontrolcüsü"""
    
    def __init__(self, db):
        self.db = db
        self.checks = {}
    
    def check_data_collector_v2_integration(self):
        """DataCollectorV2 entegrasyonu"""
        try:
            from utils.ml.data_collector_v2 import DataCollectorV2
            
            collector = DataCollectorV2(self.db)
            
            # Test: Duplicate kontrolü çalışıyor mu?
            test1 = collector._check_duplicate('test_metric', 1, datetime.now())
            
            # Test: Son toplama zamanı alınıyor mu?
            test2 = collector._get_last_collection_time('stok_seviye')
            
            self.checks['data_collector_v2'] = {
                'status': 'OK',
                'duplicate_check': 'Çalışıyor',
                'last_collection_time': 'Çalışıyor',
                'integrated': True
            }
            
            return True
            
        except Exception as e:
            self.checks['data_collector_v2'] = {
                'status': 'ERROR',
                'error': str(e),
                'integrated': False
            }
            return False
    
    def check_feature_engineer_integration(self):
        """FeatureEngineer entegrasyonu"""
        try:
            from utils.ml.feature_engineer import FeatureEngineer
            
            engineer = FeatureEngineer(self.db)
            
            # Test: Feature extraction çalışıyor mu?
            features = engineer.extract_stok_features(1, lookback_days=7)
            
            # Test: Feature matrix oluşturuluyor mu?
            df = engineer.create_feature_matrix('stok_seviye', lookback_days=7)
            
            self.checks['feature_engineer'] = {
                'status': 'OK',
                'single_extraction': 'Çalışıyor' if features else 'Yetersiz veri',
                'matrix_creation': 'Çalışıyor' if df is not None else 'Yetersiz veri',
                'integrated': True
            }
            
            return True
            
        except Exception as e:
            self.checks['feature_engineer'] = {
                'status': 'ERROR',
                'error': str(e),
                'integrated': False
            }
            return False
    
    def check_model_trainer_integration(self):
        """ModelTrainer feature engineering entegrasyonu"""
        try:
            from utils.ml.model_trainer import ModelTrainer
            import inspect
            
            trainer = ModelTrainer(self.db)
            
            # Fonksiyon signature kontrol et
            sig = inspect.signature(trainer.train_isolation_forest)
            params = list(sig.parameters.keys())
            
            has_feature_param = 'use_feature_engineering' in params
            
            self.checks['model_trainer'] = {
                'status': 'OK' if has_feature_param else 'WARNING',
                'feature_engineering_param': 'Var' if has_feature_param else 'Yok',
                'integrated': has_feature_param
            }
            
            return has_feature_param
            
        except Exception as e:
            self.checks['model_trainer'] = {
                'status': 'ERROR',
                'error': str(e),
                'integrated': False
            }
            return False
    
    def check_scheduler_integration(self):
        """Scheduler entegrasyonu"""
        try:
            # scheduler.py'de DataCollectorV2 kullanılıyor mu?
            with open('scheduler.py', 'r', encoding='utf-8') as f:
                content = f.read()
            
            uses_v2 = 'DataCollectorV2' in content or 'data_collector_v2' in content
            uses_old = 'DataCollector(' in content and 'DataCollectorV2' not in content
            
            self.checks['scheduler'] = {
                'status': 'OK' if uses_v2 else 'WARNING',
                'uses_v2': uses_v2,
                'uses_old': uses_old,
                'integrated': uses_v2,
                'action_needed': 'Scheduler güncellenmeli' if uses_old else 'OK'
            }
            
            return uses_v2
            
        except Exception as e:
            self.checks['scheduler'] = {
                'status': 'ERROR',
                'error': str(e),
                'integrated': False
            }
            return False
    
    def check_all_integrations(self):
        """Tüm entegrasyonları kontrol et"""
        logger.info("🔍 Entegrasyon kontrolü başladı...")
        
        results = {
            'data_collector_v2': self.check_data_collector_v2_integration(),
            'feature_engineer': self.check_feature_engineer_integration(),
            'model_trainer': self.check_model_trainer_integration(),
            'scheduler': self.check_scheduler_integration(),
        }
        
        all_ok = all(results.values())
        
        logger.info(f"{'✅' if all_ok else '⚠️ '} Entegrasyon kontrolü tamamlandı")
        
        return self.checks
    
    def generate_report(self):
        """Entegrasyon raporu oluştur"""
        if not self.checks:
            return "Kontrol henüz yapılmadı!"
        
        report = []
        report.append("="*80)
        report.append("ML SİSTEM ENTEGRASYON RAPORU")
        report.append("="*80)
        report.append(f"Tarih: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report.append("")
        
        for component, check in self.checks.items():
            status_icon = '✅' if check['status'] == 'OK' else '⚠️ ' if check['status'] == 'WARNING' else '❌'
            
            report.append(f"\n{status_icon} {component.upper()}")
            report.append("-"*60)
            
            for key, value in check.items():
                if key != 'status':
                    report.append(f"  {key}: {value}")
        
        report.append("\n" + "="*80)
        
        # Özet
        ok_count = sum(1 for c in self.checks.values() if c['status'] == 'OK')
        warning_count = sum(1 for c in self.checks.values() if c['status'] == 'WARNING')
        error_count = sum(1 for c in self.checks.values() if c['status'] == 'ERROR')
        
        report.append(f"\nÖZET:")
        report.append(f"  ✅ OK: {ok_count}")
        report.append(f"  ⚠️  WARNING: {warning_count}")
        report.append(f"  ❌ ERROR: {error_count}")
        report.append(f"  Toplam: {len(self.checks)}")
        
        return "\n".join(report)


# Kullanım
def check_system_integration():
    """Sistem entegrasyonunu kontrol et"""
    try:
        from models import db
        from app import app
        from datetime import datetime
        
        with app.app_context():
            checker = IntegrationChecker(db)
            results = checker.check_all_integrations()
            
            # Rapor oluştur
            report = checker.generate_report()
            print(report)
            
            # Dosyaya kaydet
            with open('docs/integration_report.txt', 'w', encoding='utf-8') as f:
                f.write(report)
            
            logger.info("✅ Rapor kaydedildi: docs/integration_report.txt")
            
            return results
            
    except Exception as e:
        logger.error(f"Entegrasyon kontrolü hatası: {str(e)}")
        import traceback
        traceback.print_exc()
        return None


if __name__ == '__main__':
    check_system_integration()
