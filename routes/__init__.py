"""
Routes Package - Merkezi Route Registration

Bu modül tüm route modüllerini tek bir yerden register eder.
"""


def register_all_routes(app):
    """Tüm route modüllerini register et"""
    
    # Error Handlers
    from routes.error_handlers import register_error_handlers
    register_error_handlers(app)
    
    # Auth Routes
    from routes.auth_routes import register_auth_routes
    register_auth_routes(app)
    
    # Dashboard Routes
    from routes.dashboard_routes import register_dashboard_routes
    register_dashboard_routes(app)
    
    # Sistem Yöneticisi Routes
    from routes.sistem_yoneticisi_routes import register_sistem_yoneticisi_routes
    register_sistem_yoneticisi_routes(app)
    
    # Admin Routes
    from routes.admin_routes import register_admin_routes
    register_admin_routes(app)
    
    # Admin User Routes
    from routes.admin_user_routes import register_admin_user_routes
    register_admin_user_routes(app)
    
    # Admin Minibar Routes
    from routes.admin_minibar_routes import register_admin_minibar_routes
    register_admin_minibar_routes(app)
    
    # Admin Stok Routes
    from routes.admin_stok_routes import register_admin_stok_routes
    register_admin_stok_routes(app)
    
    # Admin Zimmet Routes
    from routes.admin_zimmet_routes import register_admin_zimmet_routes
    register_admin_zimmet_routes(app)
    
    # Depo Routes
    from routes.depo_routes import register_depo_routes
    register_depo_routes(app)
    
    # Doluluk Yönetimi Routes
    from routes.doluluk_routes import register_doluluk_routes
    register_doluluk_routes(app)
    
    # Mevcut route modülleri (zaten ayrı dosyalarda)
    from routes.admin_qr_routes import register_admin_qr_routes
    register_admin_qr_routes(app)
    
    from routes.kat_sorumlusu_qr_routes import register_kat_sorumlusu_qr_routes
    register_kat_sorumlusu_qr_routes(app)
    
    from routes.kat_sorumlusu_ilk_dolum_routes import register_kat_sorumlusu_ilk_dolum_routes
    register_kat_sorumlusu_ilk_dolum_routes(app)
    
    from routes.misafir_qr_routes import register_misafir_qr_routes
    register_misafir_qr_routes(app)
    
    from routes.dolum_talebi_routes import register_dolum_talebi_routes
    register_dolum_talebi_routes(app)
    
    # API Routes
    from routes.api_routes import register_api_routes
    register_api_routes(app)
    
    # Kat Sorumlusu Routes
    from routes.kat_sorumlusu_routes import register_kat_sorumlusu_routes
    register_kat_sorumlusu_routes(app)
    
    # Health Check Routes
    from routes.health_routes import health_bp
    app.register_blueprint(health_bp)
    
    # Rapor Routes
    from routes.rapor_routes import register_rapor_routes
    register_rapor_routes(app)
    
    # ML Routes
    from routes.ml_routes import register_ml_routes
    register_ml_routes(app)
    
    # Restore Routes
    from routes.restore_routes import restore_bp
    app.register_blueprint(restore_bp)
    
    # Restore V2 Routes (Gelişmiş)
    from routes.restore_routes_v2 import restore_v2_bp
    app.register_blueprint(restore_v2_bp)
    
    # Developer Routes
    from routes.developer_routes import developer_bp
    app.register_blueprint(developer_bp)
    
    # Fiyatlandırma Routes
    from routes.fiyatlandirma_routes import fiyatlandirma_bp
    app.register_blueprint(fiyatlandirma_bp)
    
    # Karlılık Routes
    from routes.karlilik_routes import karlilik_bp
    app.register_blueprint(karlilik_bp)
    
    # Stok Yönetimi Routes
    from routes.stok_routes import stok_bp
    app.register_blueprint(stok_bp)
    
    # Celery Task Yönetimi Routes
    from routes.celery_routes import celery_bp
    app.register_blueprint(celery_bp)
    
    # Database Optimizasyon Routes
    from routes.db_optimization_routes import db_optimization_bp
    app.register_blueprint(db_optimization_bp)
    
    # API endpoint'lerini CSRF'den muaf tut
    # Blueprint'leri register ettikten sonra CSRF exempt yap
    if hasattr(app, 'extensions') and 'csrf' in app.extensions:
        csrf_protect = app.extensions['csrf']
        csrf_protect.exempt(restore_bp)
        csrf_protect.exempt(restore_v2_bp)
        csrf_protect.exempt(developer_bp)
        csrf_protect.exempt(fiyatlandirma_bp)
        csrf_protect.exempt(karlilik_bp)
        csrf_protect.exempt(stok_bp)
        csrf_protect.exempt(celery_bp)
        csrf_protect.exempt(db_optimization_bp)
        print("✅ CSRF exemptions uygulandı (restore, restore_v2, developer, fiyatlandirma, karlilik, stok, celery, db_optimization)")
    else:
        print("⚠️ CSRF extension bulunamadı")
    
    print("✅ Tüm route modülleri başarıyla register edildi!")
