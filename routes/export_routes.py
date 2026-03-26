"""
Async Export API Routes

Celery uzerinden arka plan export islemleri icin API endpoint'leri.
POST /api/export/async - Yeni export task'i baslat
GET /api/export/status/<task_id> - Task durumunu kontrol et
GET /api/export/download/<task_id> - Tamamlanan dosyayi indir
"""

import os
import logging
from flask import jsonify, request, send_file, abort

from utils.decorators import login_required

logger = logging.getLogger(__name__)


def register_export_routes(app):
    """Export API route'larini register et."""

    @app.route("/api/export/async", methods=["POST"])
    @login_required
    def api_export_async():
        """Arka planda export task'i baslat."""
        try:
            from celery_app import excel_export_task, pdf_export_task
            from utils.rapor_export_service import VALID_RAPOR_TIPLERI

            data = request.get_json()
            if not data:
                return jsonify({"status": "error", "message": "JSON body gerekli"}), 400

            rapor_tipi = data.get("rapor_tipi")
            export_format = data.get("format", "excel")

            if rapor_tipi not in VALID_RAPOR_TIPLERI:
                return jsonify(
                    {"status": "error", "message": "Gecersiz rapor tipi"}
                ), 400

            if export_format not in ("excel", "pdf"):
                return jsonify({"status": "error", "message": "Gecersiz format"}), 400

            filters = {
                "baslangic_tarihi": data.get("baslangic_tarihi"),
                "bitis_tarihi": data.get("bitis_tarihi"),
                "urun_grup_id": data.get("urun_grup_id"),
                "urun_id": data.get("urun_id"),
                "personel_id": data.get("personel_id"),
                "hareket_tipi": data.get("hareket_tipi"),
            }

            if export_format == "excel":
                task = excel_export_task.delay(rapor_tipi, filters)  # pyright: ignore[reportFunctionMemberAccess]
            else:
                task = pdf_export_task.delay(rapor_tipi, filters)  # pyright: ignore[reportFunctionMemberAccess]

            return jsonify(
                {
                    "status": "accepted",
                    "task_id": task.id,
                    "message": "Export islemi baslatildi",
                }
            ), 202

        except Exception as e:
            logger.error("Async export hatasi: %s", str(e), exc_info=True)
            return jsonify({"status": "error", "message": "Sunucu hatasi olustu"}), 500

    @app.route("/api/export/status/<task_id>")
    @login_required
    def api_export_status(task_id):
        """Export task durumunu kontrol et."""
        try:
            from celery_app import celery

            task = celery.AsyncResult(task_id)

            if task.state == "PENDING":
                return jsonify({"status": "pending", "message": "Kuyrukta bekliyor"})
            elif task.state == "STARTED":
                return jsonify({"status": "started", "message": "Isleniyor"})
            elif task.state == "SUCCESS":
                result = task.result
                if result and result.get("status") == "success":
                    return jsonify(
                        {
                            "status": "completed",
                            "filename": result.get("filename"),
                            "download_url": f"/api/export/download/{task_id}",
                        }
                    )
                return jsonify(
                    {
                        "status": "error",
                        "message": result.get("message", "Bilinmeyen hata"),
                    }
                )
            elif task.state == "FAILURE":
                return jsonify(
                    {"status": "error", "message": "Export islemi basarisiz oldu"}
                )
            else:
                return jsonify({"status": task.state.lower()})

        except Exception as e:
            logger.error("Export status hatasi: %s", str(e), exc_info=True)
            return jsonify({"status": "error", "message": "Sunucu hatasi olustu"}), 500

    @app.route("/api/export/download/<task_id>")
    @login_required
    def api_export_download(task_id):
        """Tamamlanan export dosyasini indir."""
        try:
            from celery_app import celery

            task = celery.AsyncResult(task_id)

            if task.state != "SUCCESS":
                abort(404)

            result = task.result
            if not result or result.get("status") != "success":
                abort(404)

            filepath = result.get("filepath")
            if not filepath:
                abort(404)

            exports_dir = os.path.join(app.root_path, "exports")
            real_path = os.path.realpath(filepath)
            if not real_path.startswith(os.path.realpath(exports_dir)):
                abort(403)

            if not os.path.exists(real_path):
                abort(404)

            filename = result.get("filename", os.path.basename(real_path))
            return send_file(real_path, as_attachment=True, download_name=filename)

        except Exception as e:
            logger.error("Export download hatasi: %s", str(e), exc_info=True)
            abort(500)
