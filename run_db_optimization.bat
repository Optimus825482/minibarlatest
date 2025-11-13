@echo off
REM Database Optimizasyon Script - Windows
REM Erkan için - Database Performance Tool

echo.
echo ========================================
echo Database Optimizasyon Tool
echo ========================================
echo.

:menu
echo Seçenekler:
echo 1. Sağlık Kontrolü
echo 2. Index Kontrolü
echo 3. Index Oluştur
echo 4. Tabloları Optimize Et
echo 5. Performans Analizi
echo 6. Tam Optimizasyon
echo 7. Çıkış
echo.

set /p choice="Seçiminiz (1-7): "

if "%choice%"=="1" goto health
if "%choice%"=="2" goto check_indexes
if "%choice%"=="3" goto create_indexes
if "%choice%"=="4" goto optimize
if "%choice%"=="5" goto performance
if "%choice%"=="6" goto full
if "%choice%"=="7" goto end
goto menu

:health
echo.
python run_db_optimization.py --check-health
pause
goto menu

:check_indexes
echo.
python run_db_optimization.py --check-indexes
pause
goto menu

:create_indexes
echo.
python run_db_optimization.py --create-indexes
pause
goto menu

:optimize
echo.
python run_db_optimization.py --optimize-tables
pause
goto menu

:performance
echo.
python run_db_optimization.py --analyze-performance
pause
goto menu

:full
echo.
python run_db_optimization.py --full-optimization
pause
goto menu

:end
echo.
echo Çıkılıyor...
exit
