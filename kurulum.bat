@echo off
chcp 65001 >nul
echo.
echo ============================================================
echo ⚡ OTEL MİNİBAR TAKİP SİSTEMİ - HIZLI KURULUM
echo ============================================================
echo.
echo Bu script sıfırdan sistem kurulumu yapar:
echo   1. Veritabanı ve tabloları oluşturur
echo   2. Varsayılan admin oluşturur
echo   3. Örnek veriler ekler (opsiyonel)
echo.
echo Varsayılan Giriş:
echo   Kullanıcı: admin
echo   Şifre: admin123
echo.
pause

python quick_setup.py

if %ERRORLEVEL% EQU 0 (
    echo.
    echo ============================================================
    echo ✅ KURULUM BAŞARILI!
    echo ============================================================
    echo.
    echo Uygulamayı başlatmak için:
    echo   python app.py
    echo.
    echo veya
    echo   docker.bat
    echo.
) else (
    echo.
    echo ============================================================
    echo ❌ KURULUM BAŞARISIZ!
    echo ============================================================
    echo.
    echo Lütfen hata mesajlarını kontrol edin.
    echo.
)

pause
