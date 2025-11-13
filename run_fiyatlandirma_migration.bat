@echo off
REM Fiyatlandirma ve Karlilik Sistemi Migration Script
REM Erkan icin - Kolay kullanim

REM Proje kök dizinine git
cd /d "%~dp0"

echo.
echo ========================================
echo FIYATLANDIRMA MIGRATION ARACI
echo ========================================
echo.
echo Mevcut dizin: %CD%
echo.
echo 1. Migration Calistir (Upgrade)
echo 2. Rollback (Downgrade)
echo 3. Cikis
echo.

set /p choice="Seciminiz (1-3): "

if "%choice%"=="1" (
    echo.
    echo Migration baslatiliyor...
    python migrations\add_fiyatlandirma_karlilik_sistemi.py
    echo.
    if %ERRORLEVEL% EQU 0 (
        echo.
        echo ========================================
        echo BASARILI! Migration tamamlandi.
        echo ========================================
    ) else (
        echo.
        echo ========================================
        echo HATA! Migration basarisiz oldu.
        echo ========================================
    )
    echo.
    pause
) else if "%choice%"=="2" (
    echo.
    echo ========================================
    echo UYARI: Bu islem tum fiyatlandirma verilerini silecek!
    echo ========================================
    echo.
    python migrations\add_fiyatlandirma_karlilik_sistemi.py downgrade
    echo.
    if %ERRORLEVEL% EQU 0 (
        echo.
        echo ========================================
        echo BASARILI! Rollback tamamlandi.
        echo ========================================
    ) else (
        echo.
        echo ========================================
        echo HATA! Rollback basarisiz oldu.
        echo ========================================
    )
    echo.
    pause
) else if "%choice%"=="3" (
    exit
) else (
    echo.
    echo Gecersiz secim!
    echo.
    pause
)
