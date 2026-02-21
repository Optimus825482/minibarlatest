"""
Executive Dashboard Routes
Üst yönetici paneli route'ları
"""

from flask import render_template, jsonify, request, session
from utils.decorators import login_required, role_required
from utils.executive_dashboard_service import ExecutiveDashboardService
import logging

logger = logging.getLogger(__name__)


def register_executive_dashboard_routes(app):
    """Executive dashboard route'larını register et"""

    @app.route('/executive-dashboard')
    @login_required
    @role_required('superadmin')
    def executive_dashboard():
        """Ana executive dashboard sayfası"""
        try:
            period = request.args.get('period', 'today')
            kpi = ExecutiveDashboardService.get_kpi_summary(period=period)
            hotel_comparison = ExecutiveDashboardService.get_hotel_comparison(period=period)
            user_stats = ExecutiveDashboardService.get_user_activity_stats()
            weekly = ExecutiveDashboardService.get_weekly_summary()
            task_completion = ExecutiveDashboardService.get_task_completion_by_hotel(period=period)

            return render_template(
                'sistem_yoneticisi/executive_dashboard.html',
                kpi=kpi,
                hotel_comparison=hotel_comparison,
                user_stats=user_stats,
                weekly=weekly,
                task_completion=task_completion,
                current_period=period
            )
        except Exception as e:
            logger.error(f"Executive dashboard hatası: {e}")
            return render_template(
                'sistem_yoneticisi/executive_dashboard.html',
                kpi={}, hotel_comparison=[], user_stats=[],
                weekly={}, task_completion=[], current_period='today'
            )

    # ---- API Endpoints ----

    @app.route('/api/executive/kpi')
    @login_required
    @role_required('superadmin')
    def api_executive_kpi():
        """KPI verileri - period destekli"""
        try:
            period = request.args.get('period', 'today')
            data = ExecutiveDashboardService.get_kpi_summary(period=period)
            return jsonify({'success': True, 'data': data})
        except Exception as e:
            logger.error(f"KPI API hatası: {e}")
            return jsonify({'success': False, 'error': str(e)}), 500

    @app.route('/api/executive/activity-feed')
    @login_required
    @role_required('superadmin')
    def api_executive_activity_feed():
        """Anlık aktivite feed'i"""
        try:
            limit = request.args.get('limit', 50, type=int)
            activities = ExecutiveDashboardService.get_recent_activity(limit=limit)
            return jsonify({'success': True, 'data': activities})
        except Exception as e:
            logger.error(f"Activity feed API hatası: {e}")
            return jsonify({'success': False, 'error': str(e)}), 500

    @app.route('/api/executive/consumption-trends')
    @login_required
    @role_required('superadmin')
    def api_executive_consumption_trends():
        """Tüketim trend verileri"""
        try:
            period = request.args.get('period', 'this_week')
            data = ExecutiveDashboardService.get_consumption_trends(period=period)
            return jsonify({'success': True, 'data': data})
        except Exception as e:
            logger.error(f"Consumption trends API hatası: {e}")
            return jsonify({'success': False, 'error': str(e)}), 500

    @app.route('/api/executive/top-products')
    @login_required
    @role_required('superadmin')
    def api_executive_top_products():
        """En çok tüketilen ürünler"""
        try:
            limit = request.args.get('limit', 10, type=int)
            period = request.args.get('period', 'this_month')
            data = ExecutiveDashboardService.get_top_consumed_products(limit=limit, period=period)
            return jsonify({'success': True, 'data': data})
        except Exception as e:
            logger.error(f"Top products API hatası: {e}")
            return jsonify({'success': False, 'error': str(e)}), 500

    @app.route('/api/executive/room-controls')
    @login_required
    @role_required('superadmin')
    def api_executive_room_controls():
        """Oda kontrol istatistikleri"""
        try:
            period = request.args.get('period', 'this_week')
            data = ExecutiveDashboardService.get_room_control_stats(period=period)
            return jsonify({'success': True, 'data': data})
        except Exception as e:
            logger.error(f"Room controls API hatası: {e}")
            return jsonify({'success': False, 'error': str(e)}), 500

    @app.route('/api/executive/hourly-activity')
    @login_required
    @role_required('superadmin')
    def api_executive_hourly_activity():
        """Saatlik aktivite dağılımı"""
        try:
            period = request.args.get('period', 'today')
            data = ExecutiveDashboardService.get_hourly_activity(period=period)
            return jsonify({'success': True, 'data': data})
        except Exception as e:
            logger.error(f"Hourly activity API hatası: {e}")
            return jsonify({'success': False, 'error': str(e)}), 500

    @app.route('/api/executive/hotel-comparison')
    @login_required
    @role_required('superadmin')
    def api_executive_hotel_comparison():
        """Otel karşılaştırma verileri"""
        try:
            period = request.args.get('period', 'today')
            data = ExecutiveDashboardService.get_hotel_comparison(period=period)
            return jsonify({'success': True, 'data': [
                {
                    'ad': h['ad'],
                    'oda_sayisi': h['oda_sayisi'],
                    'kontrol': h['bugun_kontrol'],
                    'tuketim': h['bugun_tuketim'],
                    'gorev_oran': h['gorev_oran']
                } for h in data
            ]})
        except Exception as e:
            logger.error(f"Hotel comparison API hatası: {e}")
            return jsonify({'success': False, 'error': str(e)}), 500

    @app.route('/api/executive/task-completion')
    @login_required
    @role_required('superadmin')
    def api_executive_task_completion():
        """Görev tamamlanma oranları"""
        try:
            period = request.args.get('period', 'today')
            data = ExecutiveDashboardService.get_task_completion_by_hotel(period=period)
            return jsonify({'success': True, 'data': data})
        except Exception as e:
            logger.error(f"Task completion API hatası: {e}")
            return jsonify({'success': False, 'error': str(e)}), 500
