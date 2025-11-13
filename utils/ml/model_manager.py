"""
Model Manager - ML Model File System Management
Merkezi model yönetim servisi: Model dosyalarını kaydetme/yükleme
"""

import os
import pickle
import logging
from pathlib import Path
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, List, Any
import shutil

logger = logging.getLogger(__name__)


class SecurityError(Exception):
    """Security related errors"""
    pass


class ModelManager:
    """
    Merkezi model yönetim servisi
    
    Sorumluluklar:
    - Model dosyalarını kaydetme/yükleme
    - Model versiyonlama
    - Otomatik temizlik
    - Hata yönetimi
    - Monitoring
    """
    
    def __init__(self, db, models_dir=None):
        """
        Args:
            db: SQLAlchemy database instance
            models_dir: Model dosyalarının saklanacağı dizin (default: /app/ml_models)
        """
        self.db = db
        
        # Model dizini - environment variable veya default
        if models_dir is None:
            models_dir = os.getenv('ML_MODELS_DIR', './ml_models')
        
        self.models_dir = Path(models_dir)
        
        # Dizin yoksa oluştur
        self.models_dir.mkdir(parents=True, exist_ok=True)
        self.logger = logging.getLogger(__name__)
        
        # Dizini oluştur
        self._ensure_directory_exists()
    
    def _ensure_directory_exists(self):
        """Model dizinini oluştur (yoksa)"""
        try:
            if not self.models_dir.exists():
                self.models_dir.mkdir(parents=True, exist_ok=True)
                # Set permissions: 755 (rwxr-xr-x)
                os.chmod(self.models_dir, 0o755)
                self.logger.info(f"📁 Model dizini oluşturuldu: {self.models_dir}")
            
            # .gitkeep dosyası oluştur
            gitkeep = self.models_dir / '.gitkeep'
            if not gitkeep.exists():
                gitkeep.touch()
            
        except Exception as e:
            self.logger.error(f"❌ Model dizini oluşturma hatası: {str(e)}")
            raise
    
    def _generate_filename(self, model_type: str, metric_type: str) -> str:
        """
        Model dosya adı oluştur
        Format: {model_type}_{metric_type}_{timestamp}.pkl
        
        Args:
            model_type: 'isolation_forest' veya 'z_score'
            metric_type: 'stok_seviye', 'tuketim_miktar', vb.
            
        Returns:
            str: Dosya adı (örn: isolation_forest_stok_seviye_20251112_140530.pkl)
        """
        timestamp = datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')
        return f"{model_type}_{metric_type}_{timestamp}.pkl"
    
    def _validate_path(self, filepath: Path) -> bool:
        """
        Path traversal saldırılarını önle
        
        Args:
            filepath: Kontrol edilecek dosya yolu
            
        Returns:
            bool: Path güvenli mi?
            
        Raises:
            SecurityError: Path traversal tespit edilirse
        """
        try:
            # Resolve absolute path
            abs_path = filepath.resolve()
            
            # models_dir içinde mi kontrol et
            if not str(abs_path).startswith(str(self.models_dir.resolve())):
                raise SecurityError(f"Path traversal attempt detected: {filepath}")
            
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Path validation error: {str(e)}")
            raise
    
    def _get_file_size_kb(self, filepath: Path) -> float:
        """
        Dosya boyutunu KB cinsinden döndür
        
        Args:
            filepath: Dosya yolu
            
        Returns:
            float: Dosya boyutu (KB)
        """
        try:
            if filepath.exists():
                size_bytes = filepath.stat().st_size
                return size_bytes / 1024
            return 0.0
        except Exception as e:
            self.logger.error(f"❌ File size error: {str(e)}")
            return 0.0
    
    def _check_disk_space(self) -> dict:
        """
        Disk kullanımını kontrol et
        
        Returns:
            dict: {'total_gb': 100, 'used_gb': 50, 'free_gb': 50, 'percent': 50}
        """
        try:
            stat = shutil.disk_usage(self.models_dir)
            
            total_gb = stat.total / (1024**3)
            used_gb = stat.used / (1024**3)
            free_gb = stat.free / (1024**3)
            percent = (stat.used / stat.total) * 100
            
            return {
                'total_gb': round(total_gb, 2),
                'used_gb': round(used_gb, 2),
                'free_gb': round(free_gb, 2),
                'percent': round(percent, 2)
            }
            
        except Exception as e:
            self.logger.error(f"❌ Disk space check error: {str(e)}")
            return {
                'total_gb': 0,
                'used_gb': 0,
                'free_gb': 0,
                'percent': 0
            }
    
    def _validate_model_file(self, filepath: Path) -> bool:
        """
        Model dosyasının geçerli olup olmadığını kontrol et
        
        Args:
            filepath: Model dosya yolu
            
        Returns:
            bool: Dosya geçerli mi?
        """
        try:
            if not filepath.exists():
                return False
            
            # Dosya boyutu kontrolü (max 10MB)
            size_mb = filepath.stat().st_size / (1024**2)
            if size_mb > 10:
                self.logger.warning(f"⚠️  Model dosyası çok büyük: {size_mb:.2f}MB")
                return False
            
            # Pickle dosyası mı kontrol et
            try:
                with open(filepath, 'rb') as f:
                    pickle.load(f)
                return True
            except Exception:
                return False
                
        except Exception as e:
            self.logger.error(f"❌ Model validation error: {str(e)}")
            return False

    def list_available_models(self) -> List[Dict]:
        """
        Mevcut modelleri listele
        
        Returns:
            List of dicts: Model bilgileri
        """
        try:
            from models import MLModel
            
            models = []
            
            # Veritabanından tüm aktif modelleri al
            db_models = MLModel.query.filter_by(is_active=True).all()
            
            for model_record in db_models:
                model_info = {
                    'id': model_record.id,
                    'model_type': model_record.model_type,
                    'metric_type': model_record.metric_type,
                    'path': model_record.model_path,
                    'size_kb': 0,
                    'created_at': model_record.training_date,
                    'accuracy': model_record.accuracy
                }
                
                # Dosya boyutu
                if model_record.model_path:
                    filepath = Path(model_record.model_path)
                    if filepath.exists():
                        model_info['size_kb'] = self._get_file_size_kb(filepath)
                
                models.append(model_info)
            
            return models
            
        except Exception as e:
            self.logger.error(f"❌ Model listeleme hatası: {str(e)}")
            return []
    
    def get_model_info(
        self,
        model_type: str,
        metric_type: str
    ) -> Optional[Dict]:
        """
        Model bilgilerini getir
        
        Returns:
            Dict veya None: Model bilgileri
        """
        try:
            from models import MLModel
            
            model_record = MLModel.query.filter_by(
                model_type=model_type,
                metric_type=metric_type,
                is_active=True
            ).first()
            
            if not model_record:
                return None
            
            info = {
                'id': model_record.id,
                'model_type': model_record.model_type,
                'metric_type': model_record.metric_type,
                'path': model_record.model_path,
                'size_kb': 0,
                'accuracy': model_record.accuracy,
                'precision': model_record.precision,
                'recall': model_record.recall,
                'training_date': model_record.training_date,
                'is_active': model_record.is_active
            }
            
            # Dosya boyutu
            if model_record.model_path:
                filepath = Path(model_record.model_path)
                if filepath.exists():
                    info['size_kb'] = self._get_file_size_kb(filepath)
            
            return info
            
        except Exception as e:
            self.logger.error(f"❌ Model bilgisi alma hatası: {str(e)}")
            return None
    
    def cleanup_old_models(self, keep_versions: int = 3) -> Dict:
        """
        Eski model versiyonlarını temizle
        
        Args:
            keep_versions: Her model tipi için kaç versiyon saklanacak
            
        Returns:
            Dict: {
                'deleted_count': 5,
                'freed_space_mb': 25.5,
                'kept_models': ['model1.pkl', 'model2.pkl']
            }
        """
        try:
            from models import MLModel
            
            deleted_count = 0
            freed_space_mb = 0.0
            kept_models = []
            
            # Her model tipi için
            model_types = self.db.session.query(
                MLModel.model_type,
                MLModel.metric_type
            ).distinct().all()
            
            for model_type, metric_type in model_types:
                # Bu tip için tüm modelleri al (timestamp'e göre sırala)
                models = MLModel.query.filter_by(
                    model_type=model_type,
                    metric_type=metric_type
                ).order_by(MLModel.training_date.desc()).all()
                
                # En son keep_versions kadarını sakla
                models_to_delete = models[keep_versions:]
                
                for model in models_to_delete:
                    # Dosyayı sil
                    if model.model_path:
                        filepath = Path(model.model_path)
                        if filepath.exists():
                            size_kb = self._get_file_size_kb(filepath)
                            filepath.unlink()
                            freed_space_mb += size_kb / 1024
                            deleted_count += 1
                    
                    # Veritabanında is_active=false yap
                    model.is_active = False
                
                # Saklanan modelleri kaydet
                for model in models[:keep_versions]:
                    if model.model_path:
                        kept_models.append(Path(model.model_path).name)
            
            # 30 günden eski inactive modelleri sil
            cutoff_date = datetime.now(timezone.utc) - timedelta(days=30)
            old_models = MLModel.query.filter(
                MLModel.is_active == False,
                MLModel.training_date < cutoff_date
            ).all()
            
            for model in old_models:
                if model.model_path:
                    filepath = Path(model.model_path)
                    if filepath.exists():
                        size_kb = self._get_file_size_kb(filepath)
                        filepath.unlink()
                        freed_space_mb += size_kb / 1024
                        deleted_count += 1
                
                self.db.session.delete(model)
            
            self.db.session.commit()
            
            # Disk kullanımı kontrol et
            disk_info = self._check_disk_space()
            if disk_info['percent'] > 90:
                self.logger.warning(
                    f"⚠️  Disk kullanımı yüksek: {disk_info['percent']:.1f}%"
                )
            
            self.logger.info(
                f"🗑️  Cleaned {deleted_count} old models, "
                f"freed {freed_space_mb:.2f}MB"
            )
            
            return {
                'deleted_count': deleted_count,
                'freed_space_mb': round(freed_space_mb, 2),
                'kept_models': kept_models
            }
            
        except Exception as e:
            self.db.session.rollback()
            self.logger.error(f"❌ Cleanup hatası: {str(e)}")
            return {
                'deleted_count': 0,
                'freed_space_mb': 0.0,
                'kept_models': []
            }

    def save_model_to_file(
        self,
        model,
        model_type: str,
        metric_type: str,
        accuracy: float,
        precision: float,
        recall: float
    ) -> str:
        """
        Modeli dosyaya kaydet ve metadata'yı veritabanına yaz
        
        Args:
            model: Eğitilmiş sklearn model
            model_type: 'isolation_forest' veya 'z_score'
            metric_type: 'stok_seviye', 'tuketim_miktar', vb.
            accuracy, precision, recall: Model performans metrikleri
            
        Returns:
            str: Kaydedilen dosyanın path'i
            
        Raises:
            IOError: Dosya yazma hatası
            DatabaseError: Veritabanı kayıt hatası
        """
        import time
        start_time = time.time()
        
        try:
            # Dosya adı oluştur
            filename = self._generate_filename(model_type, metric_type)
            filepath = self.models_dir / filename
            
            # Path validation
            self._validate_path(filepath)
            
            # Disk space kontrolü
            disk_info = self._check_disk_space()
            if disk_info['percent'] > 90:
                self.logger.warning(
                    f"⚠️  [DISK_WARNING] Disk kullanımı yüksek: {disk_info['percent']:.1f}% "
                    f"({disk_info['used_gb']:.2f}GB / {disk_info['total_gb']:.2f}GB)"
                )
                # Acil temizlik yap
                self.cleanup_old_models(keep_versions=1)
            
            # Model'i pickle ile serialize et
            self.logger.info(f"💾 [MODEL_SAVE_START] Model kaydediliyor: {filename}")
            serialize_start = time.time()
            
            with open(filepath, 'wb') as f:
                pickle.dump(model, f)
            
            serialize_time_ms = (time.time() - serialize_start) * 1000
            
            # File permissions ayarla: 644 (rw-r--r--)
            os.chmod(filepath, 0o644)
            
            # Dosya boyutu
            size_kb = self._get_file_size_kb(filepath)
            size_mb = size_kb / 1024
            
            # PostgreSQL'e metadata kaydet
            from models import MLModel
            
            # Eski aktif modeli pasif yap
            MLModel.query.filter_by(
                model_type=model_type,
                metric_type=metric_type,
                is_active=True
            ).update({'is_active': False})
            
            # Numpy değerlerini Python native type'a çevir
            accuracy_val = float(accuracy) if accuracy is not None else None
            precision_val = float(precision) if precision is not None else None
            recall_val = float(recall) if recall is not None else None
            
            # Yeni model kaydı
            new_model = MLModel(
                model_type=model_type,
                metric_type=metric_type,
                model_path=str(filepath),
                model_data=None,  # NULL (dosya sisteminde)
                parameters={
                    'contamination': 0.1,
                    'n_estimators': 100,
                    'random_state': 42
                },
                training_date=datetime.now(timezone.utc),
                accuracy=accuracy_val,
                precision=precision_val,
                recall=recall_val,
                is_active=True
            )
            
            self.db.session.add(new_model)
            self.db.session.commit()
            
            # Total save time
            total_time_ms = (time.time() - start_time) * 1000
            
            # Detaylı log
            self.logger.info(
                f"✅ [MODEL_SAVE_SUCCESS] Model kaydedildi: {model_type}_{metric_type} | "
                f"Path: {filepath.name} | "
                f"Size: {size_mb:.2f}MB | "
                f"Accuracy: {accuracy:.2%} | "
                f"Serialize: {serialize_time_ms:.0f}ms | "
                f"Total: {total_time_ms:.0f}ms | "
                f"Disk: {disk_info['percent']:.1f}%"
            )
            
            # Performance metrik kaydet
            self._log_performance_metric(
                operation='model_save',
                model_type=model_type,
                metric_type=metric_type,
                duration_ms=total_time_ms,
                file_size_mb=size_mb,
                success=True
            )
            
            return str(filepath)
            
        except Exception as e:
            total_time_ms = (time.time() - start_time) * 1000
            
            self.db.session.rollback()
            self.logger.error(
                f"❌ [MODEL_SAVE_ERROR] Model kaydetme hatası: {model_type}_{metric_type} | "
                f"Error: {str(e)} | "
                f"Duration: {total_time_ms:.0f}ms"
            )
            
            # Performance metrik kaydet (hata)
            self._log_performance_metric(
                operation='model_save',
                model_type=model_type,
                metric_type=metric_type,
                duration_ms=total_time_ms,
                file_size_mb=0,
                success=False,
                error=str(e)
            )
            
            raise

    def load_model_from_file(
        self,
        model_type: str,
        metric_type: str,
        max_retries: int = 3
    ):
        """
        Modeli dosyadan yükle (retry mekanizması ile)
        
        Args:
            model_type: Model tipi
            metric_type: Metrik tipi
            max_retries: Maksimum retry sayısı
            
        Returns:
            Model object veya None (bulunamazsa)
            
        Raises:
            PickleError: Model deserialize hatası
            IOError: Dosya okuma hatası
        """
        import time
        
        for attempt in range(max_retries):
            try:
                # Veritabanından model path'i al
                from models import MLModel
                
                model_record = MLModel.query.filter_by(
                    model_type=model_type,
                    metric_type=metric_type,
                    is_active=True
                ).first()
                
                if not model_record:
                    self.logger.warning(f"⚠️  Model kaydı bulunamadı: {model_type}_{metric_type}")
                    return None
                
                # model_path varsa dosyadan yükle
                if model_record.model_path:
                    filepath = Path(model_record.model_path)
                    
                    if not filepath.exists():
                        self.logger.error(f"❌ Model dosyası bulunamadı: {filepath}")
                        return None
                    
                    # Path validation
                    self._validate_path(filepath)
                    
                    # Model validation
                    if not self._validate_model_file(filepath):
                        self.logger.error(f"❌ Model dosyası geçersiz: {filepath}")
                        if attempt < max_retries - 1:
                            delay = 2 ** attempt  # Exponential backoff: 1, 2, 4 seconds
                            self.logger.warning(f"🔄 Retry {attempt + 1}/{max_retries} after {delay}s")
                            time.sleep(delay)
                            continue
                        return None
                    
                    # Model yükle
                    load_start = time.time()
                    with open(filepath, 'rb') as f:
                        model = pickle.load(f)
                    load_time_ms = (time.time() - load_start) * 1000
                    
                    # Dosya boyutu
                    size_kb = self._get_file_size_kb(filepath)
                    size_mb = size_kb / 1024
                    
                    # Detaylı log
                    self.logger.info(
                        f"📂 [MODEL_LOAD_SUCCESS] Model yüklendi: {model_type}_{metric_type} | "
                        f"Path: {filepath.name} | "
                        f"Size: {size_mb:.2f}MB | "
                        f"Load time: {load_time_ms:.0f}ms | "
                        f"Attempt: {attempt + 1}/{max_retries}"
                    )
                    
                    # Performance metrik kaydet
                    self._log_performance_metric(
                        operation='model_load',
                        model_type=model_type,
                        metric_type=metric_type,
                        duration_ms=load_time_ms,
                        file_size_mb=size_mb,
                        success=True
                    )
                    
                    return model
                
                # model_path yoksa veritabanından yükle (backward compatibility)
                if model_record.model_data:
                    self.logger.warning(f"⚠️  Dosya yok, veritabanından yükleniyor: {model_type}_{metric_type}")
                    model = pickle.loads(model_record.model_data)
                    
                    # Modeli dosyaya kaydet (migration)
                    try:
                        filename = self._generate_filename(model_type, metric_type)
                        filepath = self.models_dir / filename
                        
                        with open(filepath, 'wb') as f:
                            pickle.dump(model, f)
                        
                        os.chmod(filepath, 0o644)
                        
                        # Veritabanını güncelle
                        model_record.model_path = str(filepath)
                        model_record.model_data = None  # NULL yap
                        self.db.session.commit()
                        
                        self.logger.info(f"🔄 Model migrate edildi: {filepath}")
                    except Exception as migrate_error:
                        self.logger.error(f"❌ Migration hatası: {str(migrate_error)}")
                        self.db.session.rollback()
                    
                    return model
                
                return None
                
            except Exception as e:
                self.logger.error(f"❌ Model yükleme hatası (attempt {attempt + 1}/{max_retries}): {str(e)}")
                if attempt < max_retries - 1:
                    delay = 2 ** attempt
                    time.sleep(delay)
                else:
                    return None
        
        return None

    def list_available_models(self) -> list:
        """
        Mevcut modelleri listele
        
        Returns:
            List of dicts: Model bilgileri
        """
        try:
            from models import MLModel
            
            models = MLModel.query.filter_by(is_active=True).all()
            
            result = []
            for model in models:
                info = {
                    'model_type': model.model_type,
                    'metric_type': model.metric_type,
                    'path': model.model_path,
                    'size_kb': 0,
                    'created_at': model.training_date,
                    'accuracy': model.accuracy
                }
                
                # Dosya boyutu
                if model.model_path:
                    filepath = Path(model.model_path)
                    if filepath.exists():
                        info['size_kb'] = self._get_file_size_kb(filepath)
                
                result.append(info)
            
            return result
            
        except Exception as e:
            self.logger.error(f"❌ Model listeleme hatası: {str(e)}")
            return []
    
    def get_model_info(self, model_type: str, metric_type: str) -> dict:
        """
        Model bilgilerini getir
        
        Returns:
            Dict veya None
        """
        try:
            from models import MLModel
            
            model = MLModel.query.filter_by(
                model_type=model_type,
                metric_type=metric_type,
                is_active=True
            ).first()
            
            if not model:
                return None
            
            info = {
                'path': model.model_path,
                'size_kb': 0,
                'accuracy': model.accuracy,
                'precision': model.precision,
                'recall': model.recall,
                'training_date': model.training_date,
                'is_active': model.is_active
            }
            
            # Dosya boyutu
            if model.model_path:
                filepath = Path(model.model_path)
                if filepath.exists():
                    info['size_kb'] = self._get_file_size_kb(filepath)
            
            return info
            
        except Exception as e:
            self.logger.error(f"❌ Model bilgi hatası: {str(e)}")
            return None

    def cleanup_old_models(self, keep_versions: int = 3) -> dict:
        """
        Eski model versiyonlarını temizle
        
        Args:
            keep_versions: Her model tipi için kaç versiyon saklanacak
            
        Returns:
            Dict: Temizlik sonuçları
        """
        try:
            from models import MLModel
            from datetime import timedelta
            
            deleted_count = 0
            freed_space_mb = 0
            kept_models = []
            
            # Her model tipi için
            model_types = self.db.session.query(
                MLModel.model_type,
                MLModel.metric_type
            ).distinct().all()
            
            for model_type, metric_type in model_types:
                # Bu tip için tüm modelleri al (tarih sıralı)
                models = MLModel.query.filter_by(
                    model_type=model_type,
                    metric_type=metric_type
                ).order_by(MLModel.training_date.desc()).all()
                
                # İlk keep_versions kadarını sakla, diğerlerini sil
                for i, model in enumerate(models):
                    if i < keep_versions:
                        # Sakla
                        kept_models.append(f"{model_type}_{metric_type}")
                    else:
                        # Sil
                        if model.model_path:
                            filepath = Path(model.model_path)
                            if filepath.exists():
                                size_mb = filepath.stat().st_size / (1024**2)
                                filepath.unlink()
                                freed_space_mb += size_mb
                                deleted_count += 1
                        
                        # Veritabanında is_active=false yap
                        model.is_active = False
            
            # 30 günden eski inactive modelleri sil
            otuz_gun_once = datetime.now(timezone.utc) - timedelta(days=30)
            old_models = MLModel.query.filter(
                MLModel.is_active == False,
                MLModel.training_date < otuz_gun_once
            ).all()
            
            for model in old_models:
                if model.model_path:
                    filepath = Path(model.model_path)
                    if filepath.exists():
                        size_mb = filepath.stat().st_size / (1024**2)
                        filepath.unlink()
                        freed_space_mb += size_mb
                        deleted_count += 1
                
                self.db.session.delete(model)
            
            self.db.session.commit()
            
            # Disk bilgisi
            disk_info = self._check_disk_space()
            
            result = {
                'deleted_count': deleted_count,
                'freed_space_mb': round(freed_space_mb, 2),
                'kept_models': list(set(kept_models)),
                'disk_usage_percent': disk_info['percent']
            }
            
            # Detaylı log
            if deleted_count > 0:
                self.logger.info(
                    f"🗑️  [CLEANUP_SUCCESS] Model cleanup tamamlandı | "
                    f"Deleted: {deleted_count} models | "
                    f"Freed: {freed_space_mb:.2f}MB | "
                    f"Kept: {len(set(kept_models))} types | "
                    f"Disk: {disk_info['percent']:.1f}% ({disk_info['free_gb']:.2f}GB free)"
                )
            else:
                self.logger.info(
                    f"✅ [CLEANUP_SKIP] Temizlenecek model yok | "
                    f"Disk: {disk_info['percent']:.1f}%"
                )
            
            return result
            
        except Exception as e:
            self.db.session.rollback()
            self.logger.error(f"❌ Cleanup hatası: {str(e)}")
            return {
                'deleted_count': 0,
                'freed_space_mb': 0,
                'kept_models': []
            }

    def _log_performance_metric(
        self,
        operation: str,
        model_type: str,
        metric_type: str,
        duration_ms: float,
        file_size_mb: float,
        success: bool,
        error: str = None
    ):
        """
        Performance metriklerini ml_metrics tablosuna kaydet
        
        Args:
            operation: 'model_save' veya 'model_load'
            model_type: Model tipi
            metric_type: Metrik tipi
            duration_ms: İşlem süresi (milisaniye)
            file_size_mb: Dosya boyutu (MB)
            success: İşlem başarılı mı?
            error: Hata mesajı (varsa)
        """
        try:
            from models import MLMetric
            
            # Metrik kaydı oluştur
            metric = MLMetric(
                metric_type='dolum_sure',  # En yakın tip (işlem süresi için)
                entity_id=0,  # Sistem seviyesi
                metric_value=duration_ms,
                timestamp=datetime.now(timezone.utc),
                extra_data={
                    'operation': operation,
                    'model_type': model_type,
                    'metric_type': metric_type,
                    'duration_ms': duration_ms,
                    'file_size_mb': round(file_size_mb, 2),
                    'success': success,
                    'error': error
                }
            )
            
            self.db.session.add(metric)
            self.db.session.commit()
            
        except Exception as e:
            # Metrik kaydetme hatası uygulamayı durdurmamalı
            self.logger.warning(f"⚠️  Performance metrik kaydedilemedi: {str(e)}")
            self.db.session.rollback()
    
    def get_performance_stats(self, hours: int = 24) -> Dict:
        """
        Son X saatteki performance istatistiklerini getir
        
        Args:
            hours: Kaç saatlik veri (default: 24)
            
        Returns:
            Dict: Performance istatistikleri
        """
        try:
            from models import MLMetric
            
            # Son X saatteki metrikleri al
            cutoff_time = datetime.now(timezone.utc) - timedelta(hours=hours)
            
            metrics = MLMetric.query.filter(
                MLMetric.timestamp >= cutoff_time,
                MLMetric.extra_data.isnot(None)
            ).all()
            
            # İstatistikleri hesapla
            save_times = []
            load_times = []
            save_sizes = []
            save_success = 0
            save_fail = 0
            load_success = 0
            load_fail = 0
            
            for metric in metrics:
                if not metric.extra_data:
                    continue
                
                operation = metric.extra_data.get('operation')
                duration = metric.extra_data.get('duration_ms', 0)
                size = metric.extra_data.get('file_size_mb', 0)
                success = metric.extra_data.get('success', False)
                
                if operation == 'model_save':
                    save_times.append(duration)
                    save_sizes.append(size)
                    if success:
                        save_success += 1
                    else:
                        save_fail += 1
                        
                elif operation == 'model_load':
                    load_times.append(duration)
                    if success:
                        load_success += 1
                    else:
                        load_fail += 1
            
            # Ortalama hesapla
            avg_save_time = sum(save_times) / len(save_times) if save_times else 0
            avg_load_time = sum(load_times) / len(load_times) if load_times else 0
            avg_file_size = sum(save_sizes) / len(save_sizes) if save_sizes else 0
            
            # Success rate
            total_save = save_success + save_fail
            total_load = load_success + load_fail
            save_success_rate = (save_success / total_save * 100) if total_save > 0 else 0
            load_success_rate = (load_success / total_load * 100) if total_load > 0 else 0
            
            return {
                'period_hours': hours,
                'save': {
                    'count': total_save,
                    'success': save_success,
                    'fail': save_fail,
                    'success_rate': round(save_success_rate, 1),
                    'avg_time_ms': round(avg_save_time, 0),
                    'avg_size_mb': round(avg_file_size, 2)
                },
                'load': {
                    'count': total_load,
                    'success': load_success,
                    'fail': load_fail,
                    'success_rate': round(load_success_rate, 1),
                    'avg_time_ms': round(avg_load_time, 0)
                },
                'disk': self._check_disk_space()
            }
            
        except Exception as e:
            self.logger.error(f"❌ Performance stats hatası: {str(e)}")
            return {
                'period_hours': hours,
                'save': {'count': 0, 'success': 0, 'fail': 0, 'success_rate': 0, 'avg_time_ms': 0, 'avg_size_mb': 0},
                'load': {'count': 0, 'success': 0, 'fail': 0, 'success_rate': 0, 'avg_time_ms': 0},
                'disk': {'total_gb': 0, 'used_gb': 0, 'free_gb': 0, 'percent': 0}
            }
