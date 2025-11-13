@echo off
REM Celery Beat Başlatma Script'i (Windows)
REM Periyodik task'ları zamanında çalıştırır (günlük, haftalık, aylık analizler)

echo ========================================
echo Celery Beat Baslatiliyor...
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

REM Celery beat'i başlat
echo Celery beat baslatiliyor...
echo Periyodik task'lar:
echo - Gunluk kar analizi (her gece 00:30)
echo - Haftalik trend analizi (her Pazartesi 06:00)
echo - Aylik stok devir analizi (her ayin 1'i 07:00)
echo.
echo Cikis icin: Ctrl+C
echo.

celery -A celery_app beat --loglevel=info

pause
