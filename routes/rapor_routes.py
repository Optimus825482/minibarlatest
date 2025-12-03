"""
Rapor Routes Modülü

Bu modül tüm rapor endpoint'lerini içerir.
Excel formatında indirilebilir raporlar.

Endpoint'ler:
- /raporlar/doluluk - Doluluk raporları
- /raporlar/stok - Stok raporları
- /raporlar/minibar - Minibar raporları
- /raporlar/zimmet - Zimmet raporları
- /raporlar/gelir - Gelir raporları
- /raporlar/performans - Performans raporları

Roller:
- sistem_yoneticisi
- admin
"""

from flask import Blueprint, render_template, request, send_file, flash, redirect, url_for
from datetime import datetime, timedelta, date
from io import BytesIO
from sqlalchemy import func, and_, or_
from models import db, Otel, Kat, Oda, Urun, StokHareket, MinibarIslem, MinibarIslemDetay, PersonelZimmet, PersonelZimmetDetay, Kullanici
from utils.decorators import login_required, role_required
from utils.helpers import log_islem, log_hata
from utils.authorization import get_kullanici_otelleri
import pytz

# KKTC Timezone
KKTC_TZ = pytz.timezone('Europe/Nicosia')

def get_kktc_now():
    """Kıbrıs saat diliminde şu anki zamanı döndürür."""
    return datetime.now(KKTC_TZ)

# Blueprint oluştur
raporlar_bp = Blueprint('raporlar', __name__, url_prefix='/raporlar')


def register_rapor_routes(app):
    """Rapor route'larını register et"""
    app.register_blueprint(raporlar_bp)


@raporlar_bp.route('/doluluk-raporlari')
@login_required
@role_required('sistem_yoneticisi', 'admin', 'depo_sorumlusu')
def doluluk_raporlari():
    """Doluluk raporları sayfası"""
    try:
        oteller = get_kullanici_otelleri()
        
        # URL'den otel_id parametresini al
        otel_id = request.args.get('otel_id', type=int)
        
        return render_template('raporlar/doluluk_raporlari.html', 
                             oteller=oteller,
                             secili_otel_id=otel_id)
    except Exception as e:
        log_hata(e, modul='doluluk_raporlari')
        flash('Sayfa yüklenirken hata oluştu.', 'danger')
        return redirect(url_for('sistem_yoneticisi_dashboard'))


@raporlar_bp.route('/doluluk-raporu-olustur', methods=['POST'])
@login_required
@role_required('sistem_yoneticisi', 'admin', 'depo_sorumlusu')
def doluluk_raporu_olustur():
    """Doluluk raporu oluştur ve önizle"""
    try:
        from utils.occupancy_service import OccupancyService
        
        otel_id = request.form.get('otel_id', type=int)
        baslangic = request.form.get('baslangic')
        bitis = request.form.get('bitis')
        
        if not all([otel_id, baslangic, bitis]):
            flash('Lütfen tüm alanları doldurun.', 'warning')
            return redirect(url_for('raporlar.doluluk_raporlari'))
        
        baslangic_tarih = datetime.strptime(baslangic, '%Y-%m-%d').date()
        bitis_tarih = datetime.strptime(bitis, '%Y-%m-%d').date()
        
        otel = Otel.query.get(otel_id)
        if not otel:
            flash('Otel bulunamadı.', 'danger')
            return redirect(url_for('raporlar.doluluk_raporlari'))
        
        # Rapor verilerini hazırla
        gun_adlari = ['Pazartesi', 'Salı', 'Çarşamba', 'Perşembe', 'Cuma', 'Cumartesi', 'Pazar']
        gunler = []
        current_date = baslangic_tarih
        toplam_doluluk = 0
        max_doluluk = 0
        min_doluluk = 100
        
        while current_date <= bitis_tarih:
            rapor = OccupancyService.get_gunluk_doluluk_raporu(current_date, otel_id)
            doluluk_orani = round((rapor['dolu_oda'] / rapor['toplam_oda'] * 100) if rapor['toplam_oda'] > 0 else 0, 1)
            
            gunler.append({
                'tarih': current_date.strftime('%d.%m.%Y'),
                'gun_adi': gun_adlari[current_date.weekday()],
                'toplam_oda': rapor['toplam_oda'],
                'dolu_oda': rapor['dolu_oda'],
                'bos_oda': rapor['bos_oda'],
                'doluluk_orani': doluluk_orani
            })
            
            toplam_doluluk += doluluk_orani
            max_doluluk = max(max_doluluk, doluluk_orani)
            min_doluluk = min(min_doluluk, doluluk_orani)
            
            current_date += timedelta(days=1)
        
        gun_sayisi = len(gunler)
        ortalama_doluluk = round(toplam_doluluk / gun_sayisi, 1) if gun_sayisi > 0 else 0
        
        rapor_verisi = {
            'otel_id': otel_id,
            'otel_ad': otel.ad,
            'otel_logo': otel.logo,
            'baslangic': baslangic,
            'bitis': bitis,
            'gun_sayisi': gun_sayisi,
            'ortalama_doluluk': ortalama_doluluk,
            'max_doluluk': max_doluluk,
            'min_doluluk': min_doluluk,
            'toplam_oda': gunler[0]['toplam_oda'] if gunler else 0,
            'gunler': gunler
        }
        
        oteller = get_kullanici_otelleri()
        
        log_islem('view', 'doluluk_raporu', {
            'otel_id': otel_id,
            'baslangic': baslangic,
            'bitis': bitis
        })
        
        return render_template('raporlar/doluluk_raporlari.html', 
                             oteller=oteller, 
                             rapor_verisi=rapor_verisi)
        
    except Exception as e:
        log_hata(e, modul='doluluk_raporu_olustur')
        flash('Rapor oluşturulamadı.', 'danger')
        return redirect(url_for('raporlar.doluluk_raporlari'))


@raporlar_bp.route('/stok-raporlari')
@login_required
@role_required('sistem_yoneticisi', 'admin')
def stok_raporlari():
    """Stok raporları sayfası"""
    try:
        oteller = get_kullanici_otelleri()
        return render_template('raporlar/stok_raporlari.html', oteller=oteller)
    except Exception as e:
        log_hata(e, modul='stok_raporlari')
        flash('Sayfa yüklenirken hata oluştu.', 'danger')
        return redirect(url_for('sistem_yoneticisi_dashboard'))


@raporlar_bp.route('/minibar-raporlari')
@login_required
@role_required('sistem_yoneticisi', 'admin')
def minibar_raporlari():
    """Minibar raporları sayfası"""
    try:
        oteller = get_kullanici_otelleri()
        return render_template('raporlar/minibar_raporlari.html', oteller=oteller)
    except Exception as e:
        log_hata(e, modul='minibar_raporlari')
        flash('Sayfa yüklenirken hata oluştu.', 'danger')
        return redirect(url_for('sistem_yoneticisi_dashboard'))


@raporlar_bp.route('/zimmet-raporlari')
@login_required
@role_required('sistem_yoneticisi', 'admin')
def zimmet_raporlari():
    """Zimmet raporları sayfası"""
    try:
        oteller = get_kullanici_otelleri()
        personeller = Kullanici.query.filter(
            Kullanici.rol.in_(['kat_sorumlusu', 'depo_sorumlusu']),
            Kullanici.aktif.is_(True)
        ).order_by(Kullanici.ad, Kullanici.soyad).all()
        return render_template('raporlar/zimmet_raporlari.html', oteller=oteller, personeller=personeller)
    except Exception as e:
        log_hata(e, modul='zimmet_raporlari')
        flash('Sayfa yüklenirken hata oluştu.', 'danger')
        return redirect(url_for('sistem_yoneticisi_dashboard'))


@raporlar_bp.route('/performans-raporlari')
@login_required
@role_required('sistem_yoneticisi', 'admin')
def performans_raporlari():
    """Performans raporları sayfası"""
    try:
        oteller = get_kullanici_otelleri()
        personeller = Kullanici.query.filter(
            Kullanici.rol == 'kat_sorumlusu',
            Kullanici.aktif.is_(True)
        ).order_by(Kullanici.ad, Kullanici.soyad).all()
        return render_template('raporlar/performans_raporlari.html', oteller=oteller, personeller=personeller)
    except Exception as e:
        log_hata(e, modul='performans_raporlari')
        flash('Sayfa yüklenirken hata oluştu.', 'danger')
        return redirect(url_for('sistem_yoneticisi_dashboard'))


# ============================================================================
# EXCEL EXPORT FONKSİYONLARI
# ============================================================================

@raporlar_bp.route('/doluluk-excel')
@login_required
@role_required('sistem_yoneticisi', 'admin', 'depo_sorumlusu')
def doluluk_excel():
    """Doluluk raporu Excel export"""
    try:
        from openpyxl import Workbook
        from openpyxl.styles import Font, Alignment, PatternFill
        from utils.occupancy_service import OccupancyService
        
        otel_id = request.args.get('otel_id', type=int)
        baslangic = request.args.get('baslangic')
        bitis = request.args.get('bitis')
        
        if not all([otel_id, baslangic, bitis]):
            flash('Lütfen tüm alanları doldurun.', 'warning')
            return redirect(url_for('raporlar.doluluk_raporlari'))
        
        baslangic_tarih = datetime.strptime(baslangic, '%Y-%m-%d').date()
        bitis_tarih = datetime.strptime(bitis, '%Y-%m-%d').date()
        
        otel = Otel.query.get(otel_id)
        if not otel:
            flash('Otel bulunamadı.', 'danger')
            return redirect(url_for('raporlar.doluluk_raporlari'))
        
        # Excel oluştur
        wb = Workbook()
        ws = wb.active
        ws.title = "Doluluk Raporu"
        
        # Başlık
        ws.merge_cells('A1:F1')
        ws['A1'] = f'{otel.ad} - Doluluk Raporu'
        ws['A1'].font = Font(size=16, bold=True)
        ws['A1'].alignment = Alignment(horizontal='center')
        
        ws.merge_cells('A2:F2')
        ws['A2'] = f'{baslangic_tarih.strftime("%d.%m.%Y")} - {bitis_tarih.strftime("%d.%m.%Y")}'
        ws['A2'].alignment = Alignment(horizontal='center')
        
        # Tablo başlıkları
        headers = ['Tarih', 'Gün', 'Toplam Oda', 'Dolu Oda', 'Boş Oda', 'Doluluk %']
        for col, header in enumerate(headers, 1):
            cell = ws.cell(row=4, column=col)
            cell.value = header
            cell.font = Font(bold=True, color='FFFFFF')
            cell.fill = PatternFill(start_color='4472C4', end_color='4472C4', fill_type='solid')
            cell.alignment = Alignment(horizontal='center')
        
        # Veriler
        gun_adlari = ['Pazartesi', 'Salı', 'Çarşamba', 'Perşembe', 'Cuma', 'Cumartesi', 'Pazar']
        row = 5
        current_date = baslangic_tarih
        
        while current_date <= bitis_tarih:
            rapor = OccupancyService.get_gunluk_doluluk_raporu(current_date, otel_id)
            
            ws.cell(row=row, column=1, value=current_date.strftime('%d.%m.%Y'))
            ws.cell(row=row, column=2, value=gun_adlari[current_date.weekday()])
            ws.cell(row=row, column=3, value=rapor['toplam_oda'])
            ws.cell(row=row, column=4, value=rapor['dolu_oda'])
            ws.cell(row=row, column=5, value=rapor['bos_oda'])
            
            doluluk_orani = round((rapor['dolu_oda'] / rapor['toplam_oda'] * 100) if rapor['toplam_oda'] > 0 else 0, 1)
            ws.cell(row=row, column=6, value=f"{doluluk_orani}%")
            
            current_date += timedelta(days=1)
            row += 1
        
        # Sütun genişlikleri
        for col in ['A', 'B', 'C', 'D', 'E', 'F']:
            ws.column_dimensions[col].width = 12
        
        # Excel'i memory'ye kaydet
        excel_buffer = BytesIO()
        wb.save(excel_buffer)
        excel_buffer.seek(0)
        
        filename = f'doluluk_raporu_{otel.ad}_{baslangic}_{bitis}.xlsx'
        
        log_islem('export', 'doluluk_raporu', {
            'otel_id': otel_id,
            'baslangic': baslangic,
            'bitis': bitis
        })
        
        return send_file(
            excel_buffer,
            as_attachment=True,
            download_name=filename,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        
    except Exception as e:
        log_hata(e, modul='doluluk_excel')
        flash('Excel dosyası oluşturulamadı.', 'danger')
        return redirect(url_for('raporlar.doluluk_raporlari'))


@raporlar_bp.route('/mevcut-stok-raporu-olustur', methods=['POST'])
@login_required
@role_required('sistem_yoneticisi', 'admin')
def mevcut_stok_raporu_olustur():
    """Mevcut stok raporu oluştur ve önizle"""
    try:
        otel_id = request.form.get('otel_id', type=int)
        
        # Veriler - Kat sorumlusunun zimmetindeki kalan stoklar
        query = db.session.query(
            Otel.ad.label('otel_ad'),
            Urun.urun_adi.label('urun_ad'),
            Urun.barkod,
            Urun.birim,
            Kullanici.ad.label('personel_ad'),
            Kullanici.soyad.label('personel_soyad'),
            func.sum(PersonelZimmetDetay.kalan_miktar).label('toplam_stok')
        ).join(PersonelZimmetDetay, Urun.id == PersonelZimmetDetay.urun_id)\
         .join(PersonelZimmet, PersonelZimmetDetay.zimmet_id == PersonelZimmet.id)\
         .join(Kullanici, PersonelZimmet.personel_id == Kullanici.id)\
         .join(Otel, Kullanici.otel_id == Otel.id)\
         .filter(PersonelZimmet.durum == 'aktif')
        
        if otel_id:
            query = query.filter(Kullanici.otel_id == otel_id)
        
        urunler_data = query.group_by(
            Otel.ad, Urun.urun_adi, Urun.barkod, Urun.birim, 
            Kullanici.ad, Kullanici.soyad
        ).order_by(Otel.ad, Urun.urun_adi).all()
        
        urunler = []
        for u in urunler_data:
            # Durum belirleme
            stok = u.toplam_stok or 0
            if stok <= 0:
                durum = 'Tükendi'
            elif stok < 10:
                durum = 'Kritik'
            elif stok < 50:
                durum = 'Düşük'
            else:
                durum = 'Normal'
            
            urunler.append({
                'otel': u.otel_ad,
                'urun_ad': u.urun_ad,
                'barkod': u.barkod or '-',
                'birim': u.birim,
                'personel': f'{u.personel_ad} {u.personel_soyad}',
                'stok': stok,
                'durum': durum
            })
        
        # Otel adını al
        otel_ad = None
        if otel_id:
            otel = Otel.query.get(otel_id)
            if otel:
                otel_ad = otel.ad
        
        rapor_verisi = {
            'otel_id': otel_id,
            'otel_ad': otel_ad or 'Tüm Oteller',
            'toplam_urun': len(urunler),
            'urunler': urunler
        }
        
        oteller = get_kullanici_otelleri()
        
        log_islem('view', 'mevcut_stok_raporu', {'otel_id': otel_id})
        
        return render_template('raporlar/stok_raporlari.html',
                             oteller=oteller,
                             mevcut_stok_raporu=rapor_verisi)
        
    except Exception as e:
        log_hata(e, modul='mevcut_stok_raporu_olustur')
        flash('Rapor oluşturulamadı.', 'danger')
        return redirect(url_for('raporlar.stok_raporlari'))


@raporlar_bp.route('/stok-hareketleri-raporu-olustur', methods=['POST'])
@login_required
@role_required('sistem_yoneticisi', 'admin')
def stok_hareketleri_raporu_olustur():
    """Stok hareketleri raporu oluştur ve önizle"""
    try:
        otel_id = request.form.get('otel_id', type=int)
        baslangic = request.form.get('baslangic')
        bitis = request.form.get('bitis')
        
        if not all([baslangic, bitis]):
            flash('Lütfen tarih aralığı seçin.', 'warning')
            return redirect(url_for('raporlar.stok_raporlari'))
        
        baslangic_tarih = datetime.strptime(baslangic, '%Y-%m-%d')
        bitis_tarih = datetime.strptime(bitis, '%Y-%m-%d')
        
        # Veriler
        query = db.session.query(
            StokHareket.islem_tarihi,
            Otel.ad.label('otel_ad'),
            Urun.urun_adi.label('urun_ad'),
            StokHareket.hareket_tipi,
            StokHareket.miktar,
            Kullanici.ad.label('kullanici_ad'),
            Kullanici.soyad.label('kullanici_soyad')
        ).join(Urun, StokHareket.urun_id == Urun.id)\
         .join(Kullanici, StokHareket.islem_yapan_id == Kullanici.id)\
         .join(Otel, Kullanici.otel_id == Otel.id)\
         .filter(
            StokHareket.islem_tarihi >= baslangic_tarih,
            StokHareket.islem_tarihi <= bitis_tarih
        )
        
        if otel_id:
            query = query.filter(Kullanici.otel_id == otel_id)
        
        hareketler_data = query.order_by(StokHareket.islem_tarihi.desc()).all()
        
        hareketler = []
        for h in hareketler_data:
            hareketler.append({
                'tarih': h.islem_tarihi.strftime('%d.%m.%Y %H:%M'),
                'otel': h.otel_ad,
                'urun': h.urun_ad,
                'islem_tipi': h.hareket_tipi.upper(),
                'miktar': h.miktar,
                'kullanici': f'{h.kullanici_ad} {h.kullanici_soyad}'
            })
        
        # Otel adını al
        otel_ad = None
        if otel_id:
            otel = Otel.query.get(otel_id)
            if otel:
                otel_ad = otel.ad
        
        rapor_verisi = {
            'otel_id': otel_id,
            'otel_ad': otel_ad or 'Tüm Oteller',
            'baslangic': baslangic,
            'bitis': bitis,
            'toplam_hareket': len(hareketler),
            'hareketler': hareketler
        }
        
        oteller = get_kullanici_otelleri()
        
        log_islem('view', 'stok_hareketleri_raporu', {'otel_id': otel_id, 'baslangic': baslangic, 'bitis': bitis})
        
        return render_template('raporlar/stok_raporlari.html',
                             oteller=oteller,
                             stok_hareketleri_raporu=rapor_verisi)
        
    except Exception as e:
        log_hata(e, modul='stok_hareketleri_raporu_olustur')
        flash('Rapor oluşturulamadı.', 'danger')
        return redirect(url_for('raporlar.stok_raporlari'))


@raporlar_bp.route('/stok-excel')
@login_required
@role_required('sistem_yoneticisi', 'admin')
def stok_excel():
    """Stok raporu Excel export"""
    try:
        from openpyxl import Workbook
        from openpyxl.styles import Font, Alignment, PatternFill
        
        tip = request.args.get('tip', 'mevcut')
        otel_id = request.args.get('otel_id', type=int)
        
        wb = Workbook()
        ws = wb.active
        
        if tip == 'mevcut':
            # Mevcut stok durumu
            ws.title = "Mevcut Stok"
            
            # Başlık
            ws.merge_cells('A1:F1')
            ws['A1'] = 'Mevcut Stok Durumu'
            ws['A1'].font = Font(size=16, bold=True)
            ws['A1'].alignment = Alignment(horizontal='center')
            
            ws.merge_cells('A2:F2')
            ws['A2'] = f'Rapor Tarihi: {get_kktc_now().strftime("%d.%m.%Y %H:%M")}'
            ws['A2'].alignment = Alignment(horizontal='center')
            
            # Tablo başlıkları
            headers = ['Otel', 'Ürün Adı', 'Barkod', 'Mevcut Stok', 'Birim', 'Durum']
            for col, header in enumerate(headers, 1):
                cell = ws.cell(row=4, column=col)
                cell.value = header
                cell.font = Font(bold=True, color='FFFFFF')
                cell.fill = PatternFill(start_color='4472C4', end_color='4472C4', fill_type='solid')
                cell.alignment = Alignment(horizontal='center')
            
            # Veriler - Kat sorumlusunun zimmetindeki kalan stoklar
            query = db.session.query(
                Otel.ad.label('otel_ad'),
                Urun.urun_adi.label('urun_ad'),
                Urun.barkod,
                Urun.birim,
                func.sum(PersonelZimmetDetay.kalan_miktar).label('stok_miktari')
            ).join(PersonelZimmetDetay, Urun.id == PersonelZimmetDetay.urun_id)\
             .join(PersonelZimmet, PersonelZimmetDetay.zimmet_id == PersonelZimmet.id)\
             .join(Kullanici, PersonelZimmet.personel_id == Kullanici.id)\
             .join(Otel, Kullanici.otel_id == Otel.id)\
             .filter(PersonelZimmet.durum == 'aktif')
            
            if otel_id:
                query = query.filter(Kullanici.otel_id == otel_id)
            
            urunler = query.group_by(Otel.ad, Urun.urun_adi, Urun.barkod, Urun.birim)\
                          .order_by(Otel.ad, Urun.urun_adi).all()
            
            row = 5
            for urun in urunler:
                ws.cell(row=row, column=1, value=urun.otel_ad)
                ws.cell(row=row, column=2, value=urun.urun_ad)
                ws.cell(row=row, column=3, value=urun.barkod)
                ws.cell(row=row, column=4, value=urun.stok_miktari)
                ws.cell(row=row, column=5, value=urun.birim)
                
                # Durum
                if urun.stok_miktari <= 0:
                    durum = 'Tükendi'
                elif urun.stok_miktari < 10:
                    durum = 'Kritik'
                elif urun.stok_miktari < 50:
                    durum = 'Düşük'
                else:
                    durum = 'Normal'
                ws.cell(row=row, column=6, value=durum)
                
                row += 1
            
            filename = f'mevcut_stok_{get_kktc_now().strftime("%Y%m%d_%H%M")}.xlsx'
            
        else:
            # Stok hareketleri
            ws.title = "Stok Hareketleri"
            
            baslangic = request.args.get('baslangic')
            bitis = request.args.get('bitis')
            
            if not all([baslangic, bitis]):
                flash('Lütfen tarih aralığı seçin.', 'warning')
                return redirect(url_for('raporlar.stok_raporlari'))
            
            baslangic_tarih = datetime.strptime(baslangic, '%Y-%m-%d')
            bitis_tarih = datetime.strptime(bitis, '%Y-%m-%d')
            
            # Başlık
            ws.merge_cells('A1:G1')
            ws['A1'] = 'Stok Hareketleri Raporu'
            ws['A1'].font = Font(size=16, bold=True)
            ws['A1'].alignment = Alignment(horizontal='center')
            
            ws.merge_cells('A2:G2')
            ws['A2'] = f'{baslangic_tarih.strftime("%d.%m.%Y")} - {bitis_tarih.strftime("%d.%m.%Y")}'
            ws['A2'].alignment = Alignment(horizontal='center')
            
            # Tablo başlıkları
            headers = ['Tarih', 'Otel', 'Ürün', 'İşlem Tipi', 'Miktar', 'Açıklama', 'Kullanıcı']
            for col, header in enumerate(headers, 1):
                cell = ws.cell(row=4, column=col)
                cell.value = header
                cell.font = Font(bold=True, color='FFFFFF')
                cell.fill = PatternFill(start_color='4472C4', end_color='4472C4', fill_type='solid')
                cell.alignment = Alignment(horizontal='center')
            
            # Veriler
            query = db.session.query(
                StokHareket.islem_tarihi,
                Otel.ad.label('otel_ad'),
                Urun.urun_adi.label('urun_ad'),
                StokHareket.hareket_tipi,
                StokHareket.miktar,
                StokHareket.aciklama,
                Kullanici.ad.label('kullanici_ad'),
                Kullanici.soyad.label('kullanici_soyad')
            ).join(Urun, StokHareket.urun_id == Urun.id)\
             .join(Kullanici, StokHareket.islem_yapan_id == Kullanici.id)\
             .join(Otel, Kullanici.otel_id == Otel.id)\
             .filter(
                StokHareket.islem_tarihi >= baslangic_tarih,
                StokHareket.islem_tarihi <= bitis_tarih
            )
            
            if otel_id:
                query = query.filter(Kullanici.otel_id == otel_id)
            
            hareketler = query.order_by(StokHareket.islem_tarihi.desc()).all()
            
            row = 5
            for hareket in hareketler:
                ws.cell(row=row, column=1, value=hareket.islem_tarihi.strftime('%d.%m.%Y %H:%M'))
                ws.cell(row=row, column=2, value=hareket.otel_ad)
                ws.cell(row=row, column=3, value=hareket.urun_ad)
                ws.cell(row=row, column=4, value=hareket.hareket_tipi.upper())
                ws.cell(row=row, column=5, value=hareket.miktar)
                ws.cell(row=row, column=6, value=hareket.aciklama or '')
                ws.cell(row=row, column=7, value=f'{hareket.kullanici_ad} {hareket.kullanici_soyad}')
                row += 1
            
            filename = f'stok_hareketleri_{baslangic}_{bitis}.xlsx'
        
        # Sütun genişlikleri
        ws.column_dimensions['A'].width = 15
        ws.column_dimensions['B'].width = 20
        ws.column_dimensions['C'].width = 25
        ws.column_dimensions['D'].width = 12
        ws.column_dimensions['E'].width = 10
        ws.column_dimensions['F'].width = 30
        if tip == 'hareketler':
            ws.column_dimensions['G'].width = 20
        
        # Excel'i memory'ye kaydet
        excel_buffer = BytesIO()
        wb.save(excel_buffer)
        excel_buffer.seek(0)
        
        log_islem('export', 'stok_raporu', {'tip': tip, 'otel_id': otel_id})
        
        return send_file(
            excel_buffer,
            as_attachment=True,
            download_name=filename,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        
    except Exception as e:
        log_hata(e, modul='stok_excel')
        flash('Excel dosyası oluşturulamadı.', 'danger')
        return redirect(url_for('raporlar.stok_raporlari'))


@raporlar_bp.route('/minibar-detayli-raporu-olustur', methods=['POST'])
@login_required
@role_required('sistem_yoneticisi', 'admin')
def minibar_detayli_raporu_olustur():
    """Minibar detaylı raporu oluştur ve önizle"""
    try:
        otel_id = request.form.get('otel_id', type=int)
        baslangic = request.form.get('baslangic')
        bitis = request.form.get('bitis')
        
        if not all([otel_id, baslangic, bitis]):
            flash('Lütfen tüm alanları doldurun.', 'warning')
            return redirect(url_for('raporlar.minibar_raporlari'))
        
        baslangic_tarih = datetime.strptime(baslangic, '%Y-%m-%d')
        bitis_tarih = datetime.strptime(bitis, '%Y-%m-%d')
        
        otel = Otel.query.get(otel_id)
        if not otel:
            flash('Otel bulunamadı.', 'danger')
            return redirect(url_for('raporlar.minibar_raporlari'))
        
        # Veriler
        query = db.session.query(
            MinibarIslem.islem_tarihi,
            Oda.oda_no,
            Urun.urun_adi.label('urun_ad'),
            MinibarIslemDetay.tuketim,
            Kullanici.ad.label('personel_ad'),
            Kullanici.soyad.label('personel_soyad')
        ).join(MinibarIslemDetay, MinibarIslem.id == MinibarIslemDetay.islem_id)\
         .join(Oda, MinibarIslem.oda_id == Oda.id)\
         .join(Kat, Oda.kat_id == Kat.id)\
         .join(Urun, MinibarIslemDetay.urun_id == Urun.id)\
         .join(Kullanici, MinibarIslem.personel_id == Kullanici.id)\
         .filter(
            Kat.otel_id == otel_id,
            MinibarIslem.islem_tarihi >= baslangic_tarih,
            MinibarIslem.islem_tarihi <= bitis_tarih
        ).order_by(MinibarIslem.islem_tarihi.desc())
        
        islemler_data = query.all()
        
        islemler = []
        toplam_urun = 0
        for i in islemler_data:
            islemler.append({
                'tarih': i.islem_tarihi.strftime('%d.%m.%Y %H:%M'),
                'oda': i.oda_no,
                'urun': i.urun_ad,
                'miktar': i.tuketim,
                'personel': f'{i.personel_ad} {i.personel_soyad}'
            })
            toplam_urun += i.tuketim
        
        rapor_verisi = {
            'otel_id': otel_id,
            'otel_ad': otel.ad,
            'otel_logo': otel.logo,
            'baslangic': baslangic,
            'bitis': bitis,
            'toplam_islem': len(islemler),
            'toplam_urun': toplam_urun,
            'islemler': islemler
        }
        
        oteller = get_kullanici_otelleri()
        
        log_islem('view', 'minibar_detayli_raporu', {'otel_id': otel_id, 'baslangic': baslangic, 'bitis': bitis})
        
        return render_template('raporlar/minibar_raporlari.html',
                             oteller=oteller,
                             detayli_rapor=rapor_verisi)
        
    except Exception as e:
        log_hata(e, modul='minibar_detayli_raporu_olustur')
        flash('Rapor oluşturulamadı.', 'danger')
        return redirect(url_for('raporlar.minibar_raporlari'))


@raporlar_bp.route('/minibar-ozet-raporu-olustur', methods=['POST'])
@login_required
@role_required('sistem_yoneticisi', 'admin')
def minibar_ozet_raporu_olustur():
    """Minibar özet raporu oluştur ve önizle"""
    try:
        otel_id = request.form.get('otel_id', type=int)
        baslangic = request.form.get('baslangic')
        bitis = request.form.get('bitis')
        
        if not all([otel_id, baslangic, bitis]):
            flash('Lütfen tüm alanları doldurun.', 'warning')
            return redirect(url_for('raporlar.minibar_raporlari'))
        
        baslangic_tarih = datetime.strptime(baslangic, '%Y-%m-%d')
        bitis_tarih = datetime.strptime(bitis, '%Y-%m-%d')
        
        otel = Otel.query.get(otel_id)
        if not otel:
            flash('Otel bulunamadı.', 'danger')
            return redirect(url_for('raporlar.minibar_raporlari'))
        
        # Veriler
        query = db.session.query(
            Urun.urun_adi.label('urun_ad'),
            func.sum(MinibarIslemDetay.tuketim).label('toplam_miktar'),
            Urun.birim
        ).join(MinibarIslem, MinibarIslemDetay.islem_id == MinibarIslem.id)\
         .join(Oda, MinibarIslem.oda_id == Oda.id)\
         .join(Kat, Oda.kat_id == Kat.id)\
         .join(Urun, MinibarIslemDetay.urun_id == Urun.id)\
         .filter(
            Kat.otel_id == otel_id,
            MinibarIslem.islem_tarihi >= baslangic_tarih,
            MinibarIslem.islem_tarihi <= bitis_tarih
        ).group_by(Urun.urun_adi, Urun.birim)\
         .order_by(func.sum(MinibarIslemDetay.tuketim).desc())
        
        urunler_data = query.all()
        
        urunler = []
        genel_toplam = 0
        for u in urunler_data:
            urunler.append({
                'urun': u.urun_ad,
                'miktar': u.toplam_miktar,
                'birim': u.birim
            })
            genel_toplam += u.toplam_miktar
        
        rapor_verisi = {
            'otel_id': otel_id,
            'otel_ad': otel.ad,
            'otel_logo': otel.logo,
            'baslangic': baslangic,
            'bitis': bitis,
            'toplam_urun_cesidi': len(urunler),
            'genel_toplam': genel_toplam,
            'urunler': urunler
        }
        
        oteller = get_kullanici_otelleri()
        
        log_islem('view', 'minibar_ozet_raporu', {'otel_id': otel_id, 'baslangic': baslangic, 'bitis': bitis})
        
        return render_template('raporlar/minibar_raporlari.html',
                             oteller=oteller,
                             ozet_rapor=rapor_verisi)
        
    except Exception as e:
        log_hata(e, modul='minibar_ozet_raporu_olustur')
        flash('Rapor oluşturulamadı.', 'danger')
        return redirect(url_for('raporlar.minibar_raporlari'))


@raporlar_bp.route('/minibar-excel')
@login_required
@role_required('sistem_yoneticisi', 'admin')
def minibar_excel():
    try:
        from openpyxl import Workbook
        from openpyxl.styles import Font, Alignment, PatternFill
        
        otel_id = request.args.get('otel_id', type=int)
        baslangic = request.args.get('baslangic')
        bitis = request.args.get('bitis')
        tip = request.args.get('tip', 'detayli')
        
        if not all([otel_id, baslangic, bitis]):
            flash('Lütfen tüm alanları doldurun.', 'warning')
            return redirect(url_for('raporlar.minibar_raporlari'))
        
        baslangic_tarih = datetime.strptime(baslangic, '%Y-%m-%d')
        bitis_tarih = datetime.strptime(bitis, '%Y-%m-%d')
        
        otel = Otel.query.get(otel_id)
        if not otel:
            flash('Otel bulunamadı.', 'danger')
            return redirect(url_for('raporlar.minibar_raporlari'))
        
        wb = Workbook()
        ws = wb.active
        
        if tip == 'detayli':
            ws.title = 'Minibar Detay'
            ws.merge_cells('A1:H1')
            ws['A1'] = f'{otel.ad} - Minibar İşlemleri Detay Raporu'
            ws['A1'].font = Font(size=16, bold=True)
            ws['A1'].alignment = Alignment(horizontal='center')
            
            ws.merge_cells('A2:H2')
            tarih_str = f'{baslangic_tarih.strftime("%d.%m.%Y")} - {bitis_tarih.strftime("%d.%m.%Y")}'
            ws['A2'] = tarih_str
            ws['A2'].alignment = Alignment(horizontal='center')
            
            headers = ['Tarih', 'Oda', 'Ürün', 'Tüketim', 'Personel']
            for col, header in enumerate(headers, 1):
                cell = ws.cell(row=4, column=col)
                cell.value = header
                cell.font = Font(bold=True, color='FFFFFF')
                cell.fill = PatternFill(start_color='4472C4', end_color='4472C4', fill_type='solid')
                cell.alignment = Alignment(horizontal='center')
            
            query = db.session.query(
                MinibarIslem.islem_tarihi,
                Oda.oda_no,
                Urun.urun_adi.label('urun_ad'),
                MinibarIslemDetay.tuketim,
                Kullanici.ad.label('personel_ad'),
                Kullanici.soyad.label('personel_soyad')
            ).join(MinibarIslemDetay, MinibarIslem.id == MinibarIslemDetay.islem_id)\
             .join(Oda, MinibarIslem.oda_id == Oda.id)\
             .join(Kat, Oda.kat_id == Kat.id)\
             .join(Urun, MinibarIslemDetay.urun_id == Urun.id)\
             .join(Kullanici, MinibarIslem.personel_id == Kullanici.id)\
             .filter(
                Kat.otel_id == otel_id,
                MinibarIslem.islem_tarihi >= baslangic_tarih,
                MinibarIslem.islem_tarihi <= bitis_tarih
            ).order_by(MinibarIslem.islem_tarihi.desc())
            
            islemler = query.all()
            
            row = 5
            for islem in islemler:
                ws.cell(row=row, column=1, value=islem.islem_tarihi.strftime('%d.%m.%Y %H:%M'))
                ws.cell(row=row, column=2, value=islem.oda_no)
                ws.cell(row=row, column=3, value=islem.urun_ad)
                ws.cell(row=row, column=4, value=islem.tuketim)
                ws.cell(row=row, column=5, value=f'{islem.personel_ad} {islem.personel_soyad}')
                row += 1
            
            filename = f'minibar_detay_{otel.ad}_{baslangic}_{bitis}.xlsx'
            
        else:
            ws.title = 'Minibar Özet'
            ws.merge_cells('A1:E1')
            ws['A1'] = f'{otel.ad} - Minibar Özet Raporu'
            ws['A1'].font = Font(size=16, bold=True)
            ws['A1'].alignment = Alignment(horizontal='center')
            
            ws.merge_cells('A2:E2')
            tarih_str = f'{baslangic_tarih.strftime("%d.%m.%Y")} - {bitis_tarih.strftime("%d.%m.%Y")}'
            ws['A2'] = tarih_str
            ws['A2'].alignment = Alignment(horizontal='center')
            
            headers = ['Ürün', 'Toplam Tüketim', 'Birim']
            for col, header in enumerate(headers, 1):
                cell = ws.cell(row=4, column=col)
                cell.value = header
                cell.font = Font(bold=True, color='FFFFFF')
                cell.fill = PatternFill(start_color='4472C4', end_color='4472C4', fill_type='solid')
                cell.alignment = Alignment(horizontal='center')
            
            query = db.session.query(
                Urun.urun_adi.label('urun_ad'),
                func.sum(MinibarIslemDetay.tuketim).label('toplam_miktar'),
                Urun.birim
            ).join(MinibarIslem, MinibarIslemDetay.islem_id == MinibarIslem.id)\
             .join(Oda, MinibarIslem.oda_id == Oda.id)\
             .join(Kat, Oda.kat_id == Kat.id)\
             .join(Urun, MinibarIslemDetay.urun_id == Urun.id)\
             .filter(
                Kat.otel_id == otel_id,
                MinibarIslem.islem_tarihi >= baslangic_tarih,
                MinibarIslem.islem_tarihi <= bitis_tarih
            ).group_by(Urun.urun_adi, Urun.birim)\
             .order_by(func.sum(MinibarIslemDetay.tuketim).desc())
            
            urunler = query.all()
            
            row = 5
            for urun in urunler:
                ws.cell(row=row, column=1, value=urun.urun_ad)
                ws.cell(row=row, column=2, value=urun.toplam_miktar)
                ws.cell(row=row, column=3, value=urun.birim)
                row += 1
            
            filename = f'minibar_ozet_{otel.ad}_{baslangic}_{bitis}.xlsx'
        
        for col in ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H']:
            ws.column_dimensions[col].width = 15
        
        excel_buffer = BytesIO()
        wb.save(excel_buffer)
        excel_buffer.seek(0)
        
        log_islem('export', 'minibar_raporu', {'otel_id': otel_id, 'tip': tip})
        
        return send_file(excel_buffer, as_attachment=True, download_name=filename,
                        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
        
    except Exception as e:
        log_hata(e, modul='minibar_excel')
        flash('Excel dosyası oluşturulamadı.', 'danger')
        return redirect(url_for('raporlar.minibar_raporlari'))


def register_rapor_routes(app):
    app.register_blueprint(raporlar_bp)
@raporlar_bp.route('/zimmet-raporu-olustur', methods=['POST'])
@login_required
@role_required('sistem_yoneticisi', 'admin')
def zimmet_raporu_olustur():
    """Zimmet raporu oluştur ve önizle"""
    try:
        personel_id = request.form.get('personel_id', type=int)
        durum = request.form.get('durum', 'aktif')
        
        # Veriler - Otel bilgisi personel üzerinden
        query = db.session.query(
            Kullanici.ad.label('personel_ad'),
            Kullanici.soyad.label('personel_soyad'),
            Otel.ad.label('otel_ad'),
            Urun.urun_adi.label('urun_ad'),
            PersonelZimmetDetay.miktar.label('verilen_miktar'),
            PersonelZimmetDetay.kalan_miktar,
            PersonelZimmetDetay.kullanilan_miktar,
            PersonelZimmet.zimmet_tarihi,
            PersonelZimmet.iade_tarihi,
            PersonelZimmet.durum
        ).join(PersonelZimmetDetay, PersonelZimmet.id == PersonelZimmetDetay.zimmet_id)\
         .join(Kullanici, PersonelZimmet.personel_id == Kullanici.id)\
         .join(Urun, PersonelZimmetDetay.urun_id == Urun.id)\
         .join(Otel, Kullanici.otel_id == Otel.id)
        
        if personel_id:
            query = query.filter(PersonelZimmet.personel_id == personel_id)
        
        if durum == 'aktif':
            query = query.filter(PersonelZimmet.durum == 'aktif')
        elif durum == 'iade':
            query = query.filter(PersonelZimmet.durum == 'iade_edildi')
        
        zimmetler_data = query.order_by(PersonelZimmet.zimmet_tarihi.desc()).all()
        
        zimmetler = []
        for z in zimmetler_data:
            zimmetler.append({
                'personel': f'{z.personel_ad} {z.personel_soyad}',
                'otel': z.otel_ad,
                'urun': z.urun_ad,
                'verilen_miktar': z.verilen_miktar,
                'kullanilan_miktar': z.kullanilan_miktar or 0,
                'kalan_miktar': z.kalan_miktar or 0,
                'zimmet_tarihi': z.zimmet_tarihi.strftime('%d.%m.%Y'),
                'iade_tarihi': z.iade_tarihi.strftime('%d.%m.%Y') if z.iade_tarihi else None,
                'durum': z.durum
            })
        
        rapor_verisi = {
            'personel_id': personel_id,
            'durum': durum,
            'toplam_kayit': len(zimmetler),
            'zimmetler': zimmetler
        }
        
        oteller = get_kullanici_otelleri()
        personeller = Kullanici.query.filter(
            Kullanici.rol.in_(['kat_sorumlusu', 'depo_sorumlusu']),
            Kullanici.aktif.is_(True)
        ).order_by(Kullanici.ad, Kullanici.soyad).all()
        
        log_islem('view', 'zimmet_raporu', {'personel_id': personel_id, 'durum': durum})
        
        return render_template('raporlar/zimmet_raporlari.html', 
                             oteller=oteller,
                             personeller=personeller,
                             rapor_verisi=rapor_verisi)
        
    except Exception as e:
        log_hata(e, modul='zimmet_raporu_olustur')
        flash('Rapor oluşturulamadı.', 'danger')
        return redirect(url_for('raporlar.zimmet_raporlari'))


@raporlar_bp.route('/zimmet-excel')
@login_required
@role_required('sistem_yoneticisi', 'admin')
def zimmet_excel():
    """Zimmet raporu Excel export"""
    try:
        from openpyxl import Workbook
        from openpyxl.styles import Font, Alignment, PatternFill
        
        personel_id = request.args.get('personel_id', type=int)
        durum = request.args.get('durum', 'aktif')
        
        wb = Workbook()
        ws = wb.active
        ws.title = "Zimmet Raporu"
        
        # Başlık
        ws.merge_cells('A1:G1')
        ws['A1'] = 'Personel Zimmet Raporu'
        ws['A1'].font = Font(size=16, bold=True)
        ws['A1'].alignment = Alignment(horizontal='center')
        
        ws.merge_cells('A2:G2')
        ws['A2'] = f'Rapor Tarihi: {datetime.now().strftime("%d.%m.%Y %H:%M")}'
        ws['A2'].alignment = Alignment(horizontal='center')
        
        # Tablo başlıkları
        headers = ['Personel', 'Otel', 'Ürün', 'Miktar', 'Zimmet Tarihi', 'İade Tarihi', 'Durum']
        for col, header in enumerate(headers, 1):
            cell = ws.cell(row=4, column=col)
            cell.value = header
            cell.font = Font(bold=True, color='FFFFFF')
            cell.fill = PatternFill(start_color='4472C4', end_color='4472C4', fill_type='solid')
            cell.alignment = Alignment(horizontal='center')
        
        # Veriler
        query = db.session.query(
            Kullanici.ad.label('personel_ad'),
            Kullanici.soyad.label('personel_soyad'),
            Otel.ad.label('otel_ad'),
            Urun.urun_adi.label('urun_ad'),
            PersonelZimmetDetay.miktar,
            PersonelZimmet.zimmet_tarihi,
            PersonelZimmet.iade_tarihi,
            PersonelZimmet.durum
        ).join(PersonelZimmetDetay, PersonelZimmet.id == PersonelZimmetDetay.zimmet_id)\
         .join(Kullanici, PersonelZimmet.personel_id == Kullanici.id)\
         .join(Otel, Kullanici.otel_id == Otel.id)\
         .join(Urun, PersonelZimmetDetay.urun_id == Urun.id)
        
        if personel_id:
            query = query.filter(PersonelZimmet.personel_id == personel_id)
        
        if durum == 'aktif':
            query = query.filter(PersonelZimmet.durum == 'aktif')
        elif durum == 'iade':
            query = query.filter(PersonelZimmet.durum == 'iade_edildi')
        
        zimmetler = query.order_by(PersonelZimmet.zimmet_tarihi.desc()).all()
        
        row = 5
        for zimmet in zimmetler:
            ws.cell(row=row, column=1, value=f'{zimmet.personel_ad} {zimmet.personel_soyad}')
            ws.cell(row=row, column=2, value=zimmet.otel_ad)
            ws.cell(row=row, column=3, value=zimmet.urun_ad)
            ws.cell(row=row, column=4, value=zimmet.miktar)
            ws.cell(row=row, column=5, value=zimmet.zimmet_tarihi.strftime('%d.%m.%Y'))
            ws.cell(row=row, column=6, value=zimmet.iade_tarihi.strftime('%d.%m.%Y') if zimmet.iade_tarihi else '-')
            ws.cell(row=row, column=7, value=zimmet.durum.upper())
            row += 1
        
        # Sütun genişlikleri
        ws.column_dimensions['A'].width = 20
        ws.column_dimensions['B'].width = 20
        ws.column_dimensions['C'].width = 25
        ws.column_dimensions['D'].width = 10
        ws.column_dimensions['E'].width = 15
        ws.column_dimensions['F'].width = 15
        ws.column_dimensions['G'].width = 15
        
        # Excel'i memory'ye kaydet
        excel_buffer = BytesIO()
        wb.save(excel_buffer)
        excel_buffer.seek(0)
        
        filename = f'zimmet_raporu_{get_kktc_now().strftime("%Y%m%d_%H%M")}.xlsx'
        
        log_islem('export', 'zimmet_raporu', {'personel_id': personel_id, 'durum': durum})
        
        return send_file(
            excel_buffer,
            as_attachment=True,
            download_name=filename,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        
    except Exception as e:
        log_hata(e, modul='zimmet_excel')
        flash('Excel dosyası oluşturulamadı.', 'danger')
        return redirect(url_for('raporlar.zimmet_raporlari'))


@raporlar_bp.route('/performans-raporu-olustur', methods=['POST'])
@login_required
@role_required('sistem_yoneticisi', 'admin')
def performans_raporu_olustur():
    """Performans raporu oluştur ve önizle"""
    try:
        otel_id = request.form.get('otel_id', type=int)
        baslangic = request.form.get('baslangic')
        bitis = request.form.get('bitis')
        
        if not all([otel_id, baslangic, bitis]):
            flash('Lütfen tüm alanları doldurun.', 'warning')
            return redirect(url_for('raporlar.performans_raporlari'))
        
        baslangic_tarih = datetime.strptime(baslangic, '%Y-%m-%d')
        bitis_tarih = datetime.strptime(bitis, '%Y-%m-%d')
        
        otel = Otel.query.get(otel_id)
        if not otel:
            flash('Otel bulunamadı.', 'danger')
            return redirect(url_for('raporlar.performans_raporlari'))
        
        # Veriler - MinibarIslem'de durum yok, sadece toplam işlem sayısı
        query = db.session.query(
            Kullanici.ad.label('personel_ad'),
            Kullanici.soyad.label('personel_soyad'),
            func.count(MinibarIslem.id).label('toplam_islem')
        ).join(MinibarIslem, Kullanici.id == MinibarIslem.personel_id)\
         .join(Oda, MinibarIslem.oda_id == Oda.id)\
         .join(Kat, Oda.kat_id == Kat.id)\
         .filter(
            Kat.otel_id == otel_id,
            Kullanici.rol == 'kat_sorumlusu',
            MinibarIslem.islem_tarihi >= baslangic_tarih,
            MinibarIslem.islem_tarihi <= bitis_tarih
        ).group_by(Kullanici.id, Kullanici.ad, Kullanici.soyad)\
         .order_by(func.count(MinibarIslem.id).desc()).all()
        
        performanslar = []
        for p in query:
            # MinibarIslem'de durum yok, sadece toplam işlem sayısı var
            performanslar.append({
                'personel': f'{p.personel_ad} {p.personel_soyad}',
                'toplam_islem': p.toplam_islem,
                'tamamlanan': p.toplam_islem,  # Tüm işlemler tamamlanmış sayılıyor
                'bekleyen': 0,
                'iptal': 0,
                'basari_orani': 100.0  # Tüm işlemler başarılı sayılıyor
            })
        
        rapor_verisi = {
            'otel_id': otel_id,
            'otel_ad': otel.ad,
            'otel_logo': otel.logo,
            'baslangic': baslangic,
            'bitis': bitis,
            'personel_sayisi': len(performanslar),
            'performanslar': performanslar
        }
        
        oteller = get_kullanici_otelleri()
        personeller = Kullanici.query.filter(
            Kullanici.rol == 'kat_sorumlusu',
            Kullanici.aktif.is_(True)
        ).order_by(Kullanici.ad, Kullanici.soyad).all()
        
        log_islem('view', 'performans_raporu', {'otel_id': otel_id, 'baslangic': baslangic, 'bitis': bitis})
        
        return render_template('raporlar/performans_raporlari.html',
                             oteller=oteller,
                             personeller=personeller,
                             rapor_verisi=rapor_verisi)
        
    except Exception as e:
        log_hata(e, modul='performans_raporu_olustur')
        flash('Rapor oluşturulamadı.', 'danger')
        return redirect(url_for('raporlar.performans_raporlari'))


@raporlar_bp.route('/performans-excel')
@login_required
@role_required('sistem_yoneticisi', 'admin')
def performans_excel():
    """Performans raporu Excel export"""
    try:
        from openpyxl import Workbook
        from openpyxl.styles import Font, Alignment, PatternFill
        
        otel_id = request.args.get('otel_id', type=int)
        baslangic = request.args.get('baslangic')
        bitis = request.args.get('bitis')
        
        if not all([otel_id, baslangic, bitis]):
            flash('Lütfen tüm alanları doldurun.', 'warning')
            return redirect(url_for('raporlar.performans_raporlari'))
        
        baslangic_tarih = datetime.strptime(baslangic, '%Y-%m-%d')
        bitis_tarih = datetime.strptime(bitis, '%Y-%m-%d')
        
        otel = Otel.query.get(otel_id)
        if not otel:
            flash('Otel bulunamadı.', 'danger')
            return redirect(url_for('raporlar.performans_raporlari'))
        
        wb = Workbook()
        ws = wb.active
        ws.title = "Performans Raporu"
        
        # Başlık
        ws.merge_cells('A1:F1')
        ws['A1'] = f'{otel.ad} - Kat Sorumlusu Performans Raporu'
        ws['A1'].font = Font(size=16, bold=True)
        ws['A1'].alignment = Alignment(horizontal='center')
        
        ws.merge_cells('A2:F2')
        ws['A2'] = f'{baslangic_tarih.strftime("%d.%m.%Y")} - {bitis_tarih.strftime("%d.%m.%Y")}'
        ws['A2'].alignment = Alignment(horizontal='center')
        
        # Tablo başlıkları
        headers = ['Personel', 'Toplam İşlem', 'Tamamlanan', 'Bekleyen', 'İptal', 'Başarı %']
        for col, header in enumerate(headers, 1):
            cell = ws.cell(row=4, column=col)
            cell.value = header
            cell.font = Font(bold=True, color='FFFFFF')
            cell.fill = PatternFill(start_color='4472C4', end_color='4472C4', fill_type='solid')
            cell.alignment = Alignment(horizontal='center')
        
        # Veriler
        query = db.session.query(
            Kullanici.ad.label('personel_ad'),
            Kullanici.soyad.label('personel_soyad'),
            func.count(MinibarIslem.id).label('toplam_islem')
        ).join(MinibarIslem, Kullanici.id == MinibarIslem.personel_id)\
         .join(Oda, MinibarIslem.oda_id == Oda.id)\
         .join(Kat, Oda.kat_id == Kat.id)\
         .filter(
            Kat.otel_id == otel_id,
            Kullanici.rol == 'kat_sorumlusu',
            MinibarIslem.islem_tarihi >= baslangic_tarih,
            MinibarIslem.islem_tarihi <= bitis_tarih
        ).group_by(Kullanici.id, Kullanici.ad, Kullanici.soyad)\
         .order_by(func.count(MinibarIslem.id).desc())
        
        performanslar = query.all()
        
        row = 5
        for perf in performanslar:
            ws.cell(row=row, column=1, value=f'{perf.personel_ad} {perf.personel_soyad}')
            ws.cell(row=row, column=2, value=perf.toplam_islem)
            ws.cell(row=row, column=3, value=perf.toplam_islem)  # Tamamlanan = Toplam
            ws.cell(row=row, column=4, value=0)  # Bekleyen
            ws.cell(row=row, column=5, value=0)  # İptal
            ws.cell(row=row, column=6, value='100.0%')  # Başarı oranı
            row += 1
        
        # Sütun genişlikleri
        ws.column_dimensions['A'].width = 25
        for col in ['B', 'C', 'D', 'E', 'F']:
            ws.column_dimensions[col].width = 15
        
        # Excel'i memory'ye kaydet
        excel_buffer = BytesIO()
        wb.save(excel_buffer)
        excel_buffer.seek(0)
        
        filename = f'performans_raporu_{otel.ad}_{baslangic}_{bitis}.xlsx'
        
        log_islem('export', 'performans_raporu', {'otel_id': otel_id, 'baslangic': baslangic, 'bitis': bitis})
        
        return send_file(
            excel_buffer,
            as_attachment=True,
            download_name=filename,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        
    except Exception as e:
        log_hata(e, modul='performans_excel')
        flash('Excel dosyası oluşturulamadı.', 'danger')
        return redirect(url_for('raporlar.performans_raporlari'))


def register_rapor_routes(app):
    """Rapor route'larını kaydet"""
    app.register_blueprint(raporlar_bp)
