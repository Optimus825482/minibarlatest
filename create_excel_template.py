"""
Satın Alma Excel Şablonu Oluşturma Script
"""

import pandas as pd
import os

def create_satin_alma_template():
    """Satın alma için Excel şablonu oluştur"""
    
    # Şablon verileri
    data = {
        'urun_adi': ['Coca Cola 330ml', 'Fanta 330ml', 'Sprite 330ml'],
        'birim': ['Adet', 'Adet', 'Adet'],
        'satin_alinan_miktar': [100, 50, 75],
        'birim_fiyat': [5.50, 5.00, 5.25],
        'kdv_orani': [18, 18, 18]
    }
    
    df = pd.DataFrame(data)
    
    # Klasörü oluştur
    template_dir = 'static/templates'
    os.makedirs(template_dir, exist_ok=True)
    
    # Excel dosyasını oluştur
    file_path = os.path.join(template_dir, 'satin_alma_sablonu.xlsx')
    
    # Excel writer ile stil ekle
    with pd.ExcelWriter(file_path, engine='openpyxl') as writer:
        df.to_excel(writer, sheet_name='Satın Alma', index=False)
        
        # Worksheet'i al
        worksheet = writer.sheets['Satın Alma']
        
        # Sütun genişliklerini ayarla
        worksheet.column_dimensions['A'].width = 30  # urun_adi
        worksheet.column_dimensions['B'].width = 12  # birim
        worksheet.column_dimensions['C'].width = 20  # satin_alinan_miktar
        worksheet.column_dimensions['D'].width = 15  # birim_fiyat
        worksheet.column_dimensions['E'].width = 12  # kdv_orani
        
        # Başlık satırını kalınlaştır
        from openpyxl.styles import Font, PatternFill, Alignment
        
        header_font = Font(bold=True, color='FFFFFF')
        header_fill = PatternFill(start_color='4472C4', end_color='4472C4', fill_type='solid')
        header_alignment = Alignment(horizontal='center', vertical='center')
        
        for cell in worksheet[1]:
            cell.font = header_font
            cell.fill = header_fill
            cell.alignment = header_alignment
        
        # Açıklama sayfası ekle
        instructions = pd.DataFrame({
            'Sütun Adı': ['urun_adi', 'birim', 'satin_alinan_miktar', 'birim_fiyat', 'kdv_orani'],
            'Açıklama': [
                'Ürün adı (Zorunlu) - Sistemde kayıtlı ürün adı (tam eşleşme)',
                'Birim (Bilgi) - Ürün birimi',
                'Satın Alınan Miktar (Zorunlu) - Satın alınan miktar',
                'Birim Fiyat (Zorunlu) - KDV hariç birim fiyat',
                'KDV Oranı (Opsiyonel) - Varsayılan: 18'
            ],
            'Örnek': ['Coca Cola 330ml', 'Adet', '100', '5.50', '18']
        })
        
        instructions.to_excel(writer, sheet_name='Kullanım Kılavuzu', index=False)
        
        # Kullanım kılavuzu sayfasını düzenle
        guide_sheet = writer.sheets['Kullanım Kılavuzu']
        guide_sheet.column_dimensions['A'].width = 20
        guide_sheet.column_dimensions['B'].width = 50
        guide_sheet.column_dimensions['C'].width = 20
        
        for cell in guide_sheet[1]:
            cell.font = header_font
            cell.fill = header_fill
            cell.alignment = header_alignment
    
    print(f"✅ Excel şablonu oluşturuldu: {file_path}")
    return file_path

if __name__ == '__main__':
    try:
        create_satin_alma_template()
        print("\n📋 Şablon Bilgileri:")
        print("-" * 60)
        print("Dosya: static/templates/satin_alma_sablonu.xlsx")
        print("\nGerekli Sütunlar:")
        print("  • urun_adi             : Ürün adı (Zorunlu)")
        print("  • birim                : Birim (Bilgi)")
        print("  • satin_alinan_miktar  : Satın alınan miktar (Zorunlu)")
        print("  • birim_fiyat          : Birim fiyat (Zorunlu)")
        print("  • kdv_orani            : KDV oranı (Opsiyonel, varsayılan: 18)")
        print("\n✅ Şablon başarıyla oluşturuldu!")
        
    except Exception as e:
        print(f"❌ Hata: {str(e)}")
