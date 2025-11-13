@echo off
REM Celery Worker Başlatma Script'i (Windows)
REM Fiyatlandırma ve Karlılık Sistemi için asenkron task işleyici

echo ========================================
echo Celery Worker Baslatiliyor...
echo ========================================
echo.

REM Redis'in çalıştığını kontrol et
echo Redis baglantisi kontrol ediliyor...
redis-cli ping >nul 2>&1
if errorlevel 1 (
    echo [HATA] Redis calismiyor! Lutfen Redis'i baslatin.
    echo Redis baslat: redis-server
    pause
    exit /b 1
)
echo [OK] Redis baglantisi basarili
echo.

REM Celery worker'ı başlat
echo Celery worker baslatiliyor...
echo Cikis icin: Ctrl+C
echo.

celery -A celery_app worker --loglevel=info --pool=solo

pause
