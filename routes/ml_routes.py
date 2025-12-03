"""
ML Routes - ML Anomaly Detection System
ML dashboard ve API endpoint'leri
"""

from flask import Blueprint, render_template, jsonify, request
from utils.decorators import login_required, role_required
from utils.helpers import get_current_user
from utils.ml.alert_manager import AlertManager
from utils.ml.metrics_calculator import MetricsCalculator
from models import db, MLAlert, MLModel, MLMetric, MLTrainingLog
from datetime import datetime, timezone, timedelta
import pytz

# KKTC Timezone
KKTC_TZ = pytz.timezone('Europe/Nicosia')
def get_kktc_now():
    return datetime.now(KKTC_TZ)
import logging

logger = logging.getLogger(__name__)

ml_bp = Blueprint('ml', __name__, url_prefix='/ml')


@ml_bp.route('/dashboard')
@login_required
@role_required('admin', 'sistem_yoneticisi')
def dashboard():
    """ML Dashboard - Ana sayfa"""
    try:
        # Her işlem için ayrı try-catch
        dashboard_metrics = {}
        active_alerts = []
        alert_stats = {}
        models = []
        
        try:
            alert_manager = AlertManager(db)
            metrics_calculator = MetricsCalculator(db)
            
            # Dashboard metrikleri
            dashboard_metrics = metrics_calculator.get_dashboard_metrics()
        except Exception as e:
            logger.error(f"❌ Dashboard metrikleri hatası: {str(e)}")
            db.session.rollback()
        
        try:
            # Aktif alertler (ilk 10)
            alert_manager = AlertManager(db)
            active_alerts = alert_manager.get_active_alerts(limit=10)
        except Exception as e:
            logger.error(f"❌ Aktif alertler hatası: {str(e)}")
            db.session.rollback()
        
        try:
            # Alert istatistikleri (son 30 gün)
            alert_manager = AlertManager(db)
            alert_stats = alert_manager.get_alert_statistics(days=30)
        except Exception as e:
            logger.error(f"❌ Alert istatistikleri hatası: {str(e)}")
            db.session.rollback()
        
        try:
            # Model performans bilgileri
            models = MLModel.query.filter_by(is_active=True).all()
        except Exception as e:
            logger.error(f"❌ Model sorgusu hatası: {str(e)}")
            db.session.rollback()
        
        return render_template('admin/ml_dashboard.html',
                             dashboard_metrics=dashboard_metrics,
                             alerts=active_alerts,
                             alert_stats=alert_stats,
                             models=models)
    
    except Exception as e:
        logger.error(f"❌ ML Dashboard genel hatası: {str(e)}")
        # Transaction'ı rollback et
        try:
            db.session.rollback()
        except:
            pass
        return render_template('admin/ml_dashboard.html',
                             dashboard_metrics={},
                             alerts=[],
                             alert_stats={},
                             models=[])


@ml_bp.route('/api/alerts')
@login_required
@role_required('admin', 'sistem_yoneticisi')
def api_get_alerts():
    """Aktif alertleri getir (JSON)"""
    try:
        severity = request.args.get('severity')
        limit = request.args.get('limit', type=int)
        
        alert_manager = AlertManager(db)
        alerts = alert_manager.get_active_alerts(severity=severity, limit=limit)
        
        alerts_data = []
        for alert in alerts:
            try:
                # Entity tipini alert_type'dan çıkar
                entity_type = infer_entity_type_from_alert(alert.alert_type)
                entity_name = get_entity_name(entity_type, alert.entity_id)
                
                alerts_data.append({
                    'id': alert.id,
                    'alert_type': alert.alert_type,
                    'severity': alert.severity,
                    'entity_type': entity_type,
                    'entity_id': alert.entity_id,
                    'entity_name': entity_name,
                    'metric_value': alert.metric_value,
                    'expected_value': alert.expected_value,
                    'deviation_percent': alert.deviation_percent,
                    'message': alert.message,
                    'suggested_action': alert.suggested_action,
                    'created_at': alert.created_at.isoformat(),
                    'is_read': alert.is_read
                })
            except Exception as e:
                logger.error(f"❌ Alert işleme hatası (ID: {alert.id}): {str(e)}")
                # Bu alert'i atla, devam et
                continue
        
        return jsonify({
            'success': True,
            'alerts': alerts_data,
            'count': len(alerts_data)
        })
    
    except Exception as e:
        logger.error(f"❌ Alert API hatası: {str(e)}")
        try:
            db.session.rollback()
        except:
            pass
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@ml_bp.route('/api/alerts/<int:alert_id>/read', methods=['POST'])
@login_required
@role_required('admin', 'sistem_yoneticisi')
def api_mark_alert_read(alert_id):
    """Alert'i okundu işaretle"""
    try:
        user = get_current_user()
        alert_manager = AlertManager(db)
        
        success = alert_manager.mark_as_read(alert_id, user.id)
        
        if success:
            return jsonify({
                'success': True,
                'message': 'Alert okundu olarak işaretlendi'
            })
        else:
            return jsonify({
                'success': False,
                'error': 'Alert bulunamadı'
            }), 404
    
    except Exception as e:
        logger.error(f"❌ Alert okuma hatası: {str(e)}")
        try:
            db.session.rollback()
        except:
            pass
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@ml_bp.route('/api/alerts/<int:alert_id>/false-positive', methods=['POST'])
@login_required
@role_required('admin', 'sistem_yoneticisi')
def api_mark_false_positive(alert_id):
    """Yanlış pozitif olarak işaretle"""
    try:
        user = get_current_user()
        alert_manager = AlertManager(db)
        
        success = alert_manager.mark_as_false_positive(alert_id, user.id)
        
        if success:
            return jsonify({
                'success': True,
                'message': 'Alert yanlış pozitif olarak işaretlendi'
            })
        else:
            return jsonify({
                'success': False,
                'error': 'Alert bulunamadı'
            }), 404
    
    except Exception as e:
        logger.error(f"❌ Yanlış pozitif işaretleme hatası: {str(e)}")
        try:
            db.session.rollback()
        except:
            pass
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@ml_bp.route('/api/metrics')
@login_required
@role_required('admin', 'sistem_yoneticisi')
def api_get_metrics():
    """Son metrikleri getir"""
    try:
        days = request.args.get('days', 7, type=int)
        metric_type = request.args.get('type')
        
        cutoff_date = get_kktc_now() - timedelta(days=days)
        
        query = MLMetric.query.filter(MLMetric.timestamp >= cutoff_date)
        
        if metric_type:
            query = query.filter_by(metric_type=metric_type)
        
        query = query.order_by(MLMetric.timestamp.desc()).limit(1000)
        
        metrics = query.all()
        
        metrics_data = []
        for metric in metrics:
            try:
                # Entity tipini metric_type'dan çıkar
                entity_type = infer_entity_type_from_metric(metric.metric_type)
                
                metrics_data.append({
                    'id': metric.id,
                    'metric_type': metric.metric_type,
                    'entity_type': entity_type,
                    'entity_id': metric.entity_id,
                    'metric_value': metric.metric_value,
                    'timestamp': metric.timestamp.isoformat(),
                    'extra_data': metric.extra_data
                })
            except Exception as e:
                logger.error(f"❌ Metrik işleme hatası (ID: {metric.id}): {str(e)}")
                continue
        
        return jsonify({
            'success': True,
            'metrics': metrics_data,
            'count': len(metrics_data)
        })
    
    except Exception as e:
        logger.error(f"❌ Metrik API hatası: {str(e)}")
        try:
            db.session.rollback()
        except:
            pass
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@ml_bp.route('/api/model-performance')
@login_required
@role_required('admin', 'sistem_yoneticisi')
def api_model_performance():
    """Model performans metrikleri"""
    try:
        models = MLModel.query.filter_by(is_active=True).all()
        
        models_data = []
        for model in models:
            try:
                # Son eğitim logu
                last_training = MLTrainingLog.query.filter_by(
                    model_id=model.id,
                    success=True
                ).order_by(MLTrainingLog.training_end.desc()).first()
                
                models_data.append({
                    'id': model.id,
                    'model_type': model.model_type,
                    'metric_type': model.metric_type,
                    'accuracy': model.accuracy,
                    'precision': model.precision,
                    'recall': model.recall,
                    'training_date': model.training_date.isoformat(),
                    'last_training': {
                        'data_points': last_training.data_points if last_training else 0,
                        'training_time': (last_training.training_end - last_training.training_start).total_seconds() if last_training else 0
                    } if last_training else None
                })
            except Exception as e:
                logger.error(f"❌ Model işleme hatası (ID: {model.id}): {str(e)}")
                continue
        
        return jsonify({
            'success': True,
            'models': models_data,
            'count': len(models_data)
        })
    
    except Exception as e:
        logger.error(f"❌ Model performans API hatası: {str(e)}")
        try:
            db.session.rollback()
        except:
            pass
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@ml_bp.route('/api/statistics')
@login_required
@role_required('admin', 'sistem_yoneticisi')
def api_statistics():
    """Genel istatistikler"""
    try:
        days = request.args.get('days', 30, type=int)
        
        alert_stats = {}
        dashboard_metrics = {}
        
        try:
            alert_manager = AlertManager(db)
            alert_stats = alert_manager.get_alert_statistics(days=days)
        except Exception as e:
            logger.error(f"❌ Alert istatistikleri hatası: {str(e)}")
            db.session.rollback()
        
        try:
            metrics_calculator = MetricsCalculator(db)
            dashboard_metrics = metrics_calculator.get_dashboard_metrics()
        except Exception as e:
            logger.error(f"❌ Dashboard metrikleri hatası: {str(e)}")
            db.session.rollback()
        
        return jsonify({
            'success': True,
            'alert_statistics': alert_stats,
            'dashboard_metrics': dashboard_metrics
        })
    
    except Exception as e:
        logger.error(f"❌ İstatistik API hatası: {str(e)}")
        try:
            db.session.rollback()
        except:
            pass
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


def infer_entity_type_from_alert(alert_type):
    """Alert tipinden entity tipini çıkar"""
    if alert_type in ['stok_anomali', 'stok_bitis_uyari']:
        return 'urun'
    elif alert_type in ['tuketim_anomali', 'dolum_gecikme']:
        return 'oda'
    else:
        return 'unknown'


def infer_entity_type_from_metric(metric_type):
    """Metric tipinden entity tipini çıkar"""
    if metric_type in ['stok_seviye', 'stok_bitis_tahmini']:
        return 'urun'
    elif metric_type in ['tuketim_miktar', 'dolum_sure', 'doluluk_oran', 'bosta_tuketim']:
        return 'oda'
    elif metric_type in ['zimmet_kullanim', 'zimmet_fire', 'qr_okutma_siklik', 'qr_okutma_performans']:
        return 'kat_sorumlusu'
    else:
        return 'unknown'


def get_entity_name(entity_type, entity_id):
    """Entity adını getir - Transaction-safe"""
    try:
        if entity_type == 'urun':
            from models import Urun
            urun = Urun.query.filter_by(id=entity_id).first()
            return urun.urun_adi if urun else f"Ürün #{entity_id}"
        
        elif entity_type == 'oda':
            from models import Oda
            oda = Oda.query.filter_by(id=entity_id).first()
            return f"Oda {oda.oda_no}" if oda else f"Oda #{entity_id}"
        
        elif entity_type == 'kat_sorumlusu':
            from models import Kullanici
            kullanici = Kullanici.query.filter_by(id=entity_id).first()
            return f"{kullanici.ad} {kullanici.soyad}" if kullanici else f"Personel #{entity_id}"
        
        else:
            return f"#{entity_id}"
    
    except Exception as e:
        logger.error(f"❌ Entity adı getirme hatası: {str(e)}")
        # Transaction'ı rollback et
        try:
            db.session.rollback()
        except:
            pass
        return f"#{entity_id}"


@ml_bp.route('/api/collect-data', methods=['POST'])
@login_required
@role_required('admin', 'sistem_yoneticisi')
def api_collect_data():
    """Manuel veri toplama tetikle"""
    try:
        from utils.ml.data_collector import DataCollector
        
        collector = DataCollector(db)
        
        # Veri topla
        stok_count = collector.collect_stok_metrics()
        tuketim_count = collector.collect_tuketim_metrics()
        dolum_count = collector.collect_dolum_metrics()
        
        return jsonify({
            'success': True,
            'message': 'Veri toplama başarılı',
            'collected': {
                'stok': stok_count,
                'tuketim': tuketim_count,
                'dolum': dolum_count,
                'total': stok_count + tuketim_count + dolum_count
            }
        })
    
    except Exception as e:
        logger.error(f"❌ Manuel veri toplama hatası: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@ml_bp.route('/api/run-anomaly-detection', methods=['POST'])
@login_required
@role_required('admin', 'sistem_yoneticisi')
def api_run_anomaly_detection():
    """Manuel sapma analizi tetikle"""
    try:
        from utils.ml.anomaly_detector import AnomalyDetector
        
        detector = AnomalyDetector(db)
        
        # Anomali tespiti yap
        stok_alerts = detector.detect_stok_anomalies()
        tuketim_alerts = detector.detect_tuketim_anomalies()
        dolum_alerts = detector.detect_dolum_anomalies()
        
        return jsonify({
            'success': True,
            'message': 'Sapma analizi başarılı',
            'alerts': {
                'stok': stok_alerts,
                'tuketim': tuketim_alerts,
                'dolum': dolum_alerts,
                'total': stok_alerts + tuketim_alerts + dolum_alerts
            }
        })
    
    except Exception as e:
        logger.error(f"❌ Manuel sapma analizi hatası: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@ml_bp.route('/api/train-models', methods=['POST'])
@login_required
@role_required('admin', 'sistem_yoneticisi')
def api_train_models():
    """Manuel model eğitimi tetikle"""
    try:
        from utils.ml.model_trainer import ModelTrainer
        
        trainer = ModelTrainer(db)
        
        # Modelleri eğit
        results = trainer.train_all_models()
        
        return jsonify({
            'success': True,
            'message': 'Model eğitimi başarılı',
            'results': results
        })
    
    except Exception as e:
        logger.error(f"❌ Manuel model eğitimi hatası: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


def register_ml_routes(app):
    """ML routes'ları app'e kaydet"""
    app.register_blueprint(ml_bp)

