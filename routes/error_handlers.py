"""
Error Handler Route'ları

Bu modül uygulama genelindeki hata yönetimi endpoint'lerini içerir.

Error Handler'lar:
- 404 - Sayfa Bulunamadı
- 400 - Hatalı İstek
- 429 - Rate Limit Hatası
- 500 - Sunucu Hatası
- CSRFError - CSRF Token Hatası
"""

import logging
logger = logging.getLogger(__name__)

from flask import render_template, redirect, url_for, flash, request, jsonify
from flask_wtf.csrf import CSRFError
from utils.helpers import log_hata
from models import db


def register_error_handlers(app):
    """Error handler'ları kaydet"""
    
    @app.errorhandler(404)
    def not_found(error):
        """404 - Sayfa bulunamadı"""
        return render_template('errors/404.html'), 404
    
    @app.errorhandler(400)
    def bad_request(error):
        """400 - Hatalı istek (CSRF ve diğer 400 hataları)"""
        if request.is_json:
            return jsonify({'success': False, 'error': str(error)}), 400
        return render_template('errors/404.html'), 400
    
    @app.errorhandler(429)
    def ratelimit_handler(e):
        """429 - Rate limit aşıldığında gösterilecek hata sayfası"""
        # Audit Trail - Rate limit ihlali
        from utils.audit import log_audit
        log_audit(
            islem_tipi='view',
            tablo_adi='rate_limit',
            aciklama=f'Rate limit aşıldı: {request.endpoint}',
            basarili=False,
            hata_mesaji=str(e)
        )

        return render_template('errors/429.html', error=e), 429
    
    @app.errorhandler(500)
    def internal_error(error):
        """500 - Sunucu hatası"""
        import traceback
        import sys
        
        # Hatayı stderr'e yazdır (Railway loglarında görünür)
        logger.error("=== 500 ERROR ===")
        logger.error(f"Error: {error}")
        logger.error("Traceback:")
        traceback.print_exc(file=sys.stderr)
        logger.error("=== END ERROR ===")
        
        db.session.rollback()
        return render_template('errors/500.html'), 500
    
    @app.errorhandler(CSRFError)
    def handle_csrf_error(e):
        """CSRF error handler - record and inform user"""
        try:
            # Log the CSRF error for diagnostics
            log_hata(e, modul='csrf', extra_info={'path': request.path, 'method': request.method})
        except Exception:
            # If logging fails, swallow to avoid masking the original error
            pass

        # Inform the user and redirect back
        flash('Form doğrulaması başarısız oldu (CSRF). Lütfen sayfayı yenileyip tekrar deneyin.', 'danger')
        return redirect(request.referrer or url_for('index'))
