"""
Flask uygulamasını tamamen yeniden yükle
Tüm cache'leri temizle
"""
import sys
import os

# Bytecode yazımını devre dışı bırak
sys.dont_write_bytecode = True

# Tüm import edilmiş modülleri temizle
modules_to_remove = [
    key for key in sys.modules.keys() 
    if key.startswith('utils.') or key.startswith('routes.') or key.startswith('models')
]

for module in modules_to_remove:
    del sys.modules[module]
    print(f"✅ Modül temizlendi: {module}")

print(f"\n✅ Toplam {len(modules_to_remove)} modül cache'den temizlendi")
print("✅ Şimdi Flask'ı başlatabilirsin: python app.py")
