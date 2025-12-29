"""
Günlük Rapor Email Servisi

Her sabah saat 08:00'de (KKTC saati) gönderilen raporlar:
1. Görev Tamamlanma Raporu - Kat sorumlusu görevleri
2. Minibar Sarfiyat Raporu - Oda bazlı ürün sarfiyatı ve stok durumları

Raporlar:
- Bir gün önceki verileri içerir
- Grafikler ekli olarak gönderilir
- Profesyonel ve renkli tasarımlı HTML formatında
- Depo sorumlusu ve sistem yöneticisine gönderilir
"""

import logging
import base64
from io import BytesIO
from datetime import datetime, date, timedelta, timezone
from typing import Dict, Any, List, Optional
from decimal import Decimal
import pytz

# KKTC Timezone
KKTC_TZ = pytz.timezone('Europe/Nicosia')

def get_kktc_now():
    """Kıbrıs saat diliminde şu anki zamanı döndürür."""
    return datetime.now(KKTC_TZ)

logger = logging.getLogger(__name__)


class RaporEmailService:
    """Günlük rapor email servisi"""
    
    @staticmethod
    def generate_gorev_tamamlanma_raporu(kat_sorumlusu_id: int, rapor_tarihi: date) -> Dict[str, Any]:
        """
        Kat sorumlusu için görev tamamlanma raporu oluştur
        
        Args:
            kat_sorumlusu_id: Kat sorumlusu kullanıcı ID
            rapor_tarihi: Rapor tarihi (bir gün önceki veriler)
        
        Returns:
            dict: Rapor verileri
        """
        try:
            from models import (
                db, Kullanici, GunlukGorev, GorevDetay, Otel
            )
            from sqlalchemy import func
            
            # Kat sorumlusunu al
            kat_sorumlusu = Kullanici.query.get(kat_sorumlusu_id)
            if not kat_sorumlusu:
                return {'success': False, 'message': 'Kat sorumlusu bulunamadı'}
            
            # Otel bilgisi
            otel = kat_sorumlusu.otel
            otel_adi = otel.ad if otel else 'Bilinmiyor'
            
            # Görevleri al
            gorevler = GunlukGorev.query.filter(
                GunlukGorev.personel_id == kat_sorumlusu_id,
                GunlukGorev.gorev_tarihi == rapor_tarihi
            ).all()
            
            # İstatistikler
            toplam_gorev = len(gorevler)
            tamamlanan_gorev = len([g for g in gorevler if g.durum == 'completed'])
            bekleyen_gorev = len([g for g in gorevler if g.durum == 'pending'])
            devam_eden_gorev = len([g for g in gorevler if g.durum == 'in_progress'])
            dnd_gorev = len([g for g in gorevler if g.durum == 'dnd_pending'])
            tamamlanmayan_gorev = len([g for g in gorevler if g.durum == 'incomplete'])
            
            # Görev tipi bazlı istatistikler
            gorev_tipi_stats = {}
            for gorev in gorevler:
                tip = gorev.gorev_tipi
                if tip not in gorev_tipi_stats:
                    gorev_tipi_stats[tip] = {'toplam': 0, 'tamamlanan': 0}
                gorev_tipi_stats[tip]['toplam'] += 1
                if gorev.durum == 'completed':
                    gorev_tipi_stats[tip]['tamamlanan'] += 1
            
            # Oda bazlı detaylar
            oda_detaylari = []
            for gorev in gorevler:
                for detay in gorev.detaylar:
                    oda_detaylari.append({
                        'oda_no': detay.oda.oda_no if detay.oda else 'Bilinmiyor',
                        'gorev_tipi': gorev.gorev_tipi,
                        'durum': detay.durum,
                        'dnd_sayisi': detay.dnd_sayisi,
                        'kontrol_zamani': detay.kontrol_zamani.strftime('%H:%M') if detay.kontrol_zamani else '-'
                    })
            
            # Tamamlanma oranı
            tamamlanma_orani = (tamamlanan_gorev / toplam_gorev * 100) if toplam_gorev > 0 else 0
            
            return {
                'success': True,
                'kat_sorumlusu': {
                    'id': kat_sorumlusu.id,
                    'ad_soyad': f"{kat_sorumlusu.ad} {kat_sorumlusu.soyad}",
                    'email': kat_sorumlusu.email
                },
                'otel_adi': otel_adi,
                'rapor_tarihi': rapor_tarihi.strftime('%d.%m.%Y'),
                'istatistikler': {
                    'toplam_gorev': toplam_gorev,
                    'tamamlanan': tamamlanan_gorev,
                    'bekleyen': bekleyen_gorev,
                    'devam_eden': devam_eden_gorev,
                    'dnd': dnd_gorev,
                    'tamamlanmayan': tamamlanmayan_gorev,
                    'tamamlanma_orani': round(tamamlanma_orani, 1)
                },
                'gorev_tipi_stats': gorev_tipi_stats,
                'oda_detaylari': oda_detaylari
            }
            
        except Exception as e:
            logger.error(f"Görev tamamlanma raporu oluşturma hatası: {str(e)}")
            return {'success': False, 'message': str(e)}
    
    @staticmethod
    def generate_minibar_sarfiyat_raporu(otel_id: int, rapor_tarihi: date) -> Dict[str, Any]:
        """
        Minibar sarfiyat raporu oluştur
        
        Args:
            otel_id: Otel ID
            rapor_tarihi: Rapor tarihi (bir gün önceki veriler)
        
        Returns:
            dict: Rapor verileri
        """
        try:
            from models import (
                db, Otel, Oda, Kat, MinibarIslem, MinibarIslemDetay, 
                Urun, PersonelZimmet, PersonelZimmetDetay, Kullanici
            )
            from sqlalchemy import func
            
            # Otel bilgisi
            otel = Otel.query.get(otel_id)
            if not otel:
                return {'success': False, 'message': 'Otel bulunamadı'}
            
            # Rapor tarihi için başlangıç ve bitiş zamanları
            baslangic = datetime.combine(rapor_tarihi, datetime.min.time()).replace(tzinfo=timezone.utc)
            bitis = datetime.combine(rapor_tarihi, datetime.max.time()).replace(tzinfo=timezone.utc)
            
            # Oda bazlı sarfiyat
            oda_sarfiyat = db.session.query(
                Oda.oda_no,
                Urun.urun_adi,
                func.sum(MinibarIslemDetay.tuketim).label('toplam_tuketim'),
                func.sum(MinibarIslemDetay.satis_fiyati * MinibarIslemDetay.tuketim).label('toplam_tutar')
            ).join(
                MinibarIslem, MinibarIslem.oda_id == Oda.id
            ).join(
                MinibarIslemDetay, MinibarIslemDetay.islem_id == MinibarIslem.id
            ).join(
                Urun, Urun.id == MinibarIslemDetay.urun_id
            ).join(
                Kat, Kat.id == Oda.kat_id
            ).filter(
                Kat.otel_id == otel_id,
                MinibarIslem.islem_tarihi.between(baslangic, bitis),
                MinibarIslemDetay.tuketim > 0
            ).group_by(
                Oda.oda_no, Urun.urun_adi
            ).all()
            
            # Ürün bazlı toplam sarfiyat
            urun_sarfiyat = db.session.query(
                Urun.urun_adi,
                func.sum(MinibarIslemDetay.tuketim).label('toplam_tuketim'),
                func.sum(MinibarIslemDetay.satis_fiyati * MinibarIslemDetay.tuketim).label('toplam_tutar')
            ).join(
                MinibarIslemDetay, MinibarIslemDetay.urun_id == Urun.id
            ).join(
                MinibarIslem, MinibarIslem.id == MinibarIslemDetay.islem_id
            ).join(
                Oda, Oda.id == MinibarIslem.oda_id
            ).join(
                Kat, Kat.id == Oda.kat_id
            ).filter(
                Kat.otel_id == otel_id,
                MinibarIslem.islem_tarihi.between(baslangic, bitis),
                MinibarIslemDetay.tuketim > 0
            ).group_by(
                Urun.urun_adi
            ).order_by(
                func.sum(MinibarIslemDetay.tuketim).desc()
            ).all()
            
            # Kat sorumlusu stok durumları
            kat_sorumlusu_stok = []
            kat_sorumlulari = Kullanici.query.filter(
                Kullanici.otel_id == otel_id,
                Kullanici.rol == 'kat_sorumlusu',
                Kullanici.aktif == True
            ).all()
            
            for ks in kat_sorumlulari:
                aktif_zimmet = PersonelZimmet.query.filter(
                    PersonelZimmet.personel_id == ks.id,
                    PersonelZimmet.durum == 'aktif'
                ).first()
                
                if aktif_zimmet:
                    zimmet_detaylari = []
                    for detay in aktif_zimmet.detaylar:
                        kalan = detay.kalan_miktar if detay.kalan_miktar is not None else (detay.miktar - detay.kullanilan_miktar)
                        kritik = detay.kritik_stok_seviyesi or detay.urun.kritik_stok_seviyesi or 5
                        zimmet_detaylari.append({
                            'urun_adi': detay.urun.urun_adi,
                            'miktar': detay.miktar,
                            'kullanilan': detay.kullanilan_miktar,
                            'kalan': kalan,
                            'kritik_seviye': kritik,
                            'kritik_durumda': kalan <= kritik
                        })
                    
                    kat_sorumlusu_stok.append({
                        'ad_soyad': f"{ks.ad} {ks.soyad}",
                        'zimmet_detaylari': zimmet_detaylari
                    })
            
            # Depo stok durumu (bu otele ait ürünler için)
            # Not: Depo stoku otel bazlı değilse genel stok alınır
            
            # Toplam istatistikler
            toplam_tuketim = sum([s.toplam_tuketim or 0 for s in urun_sarfiyat])
            toplam_tutar = sum([float(s.toplam_tutar or 0) for s in urun_sarfiyat])
            
            # Oda bazlı sarfiyat listesi
            oda_sarfiyat_list = []
            for s in oda_sarfiyat:
                oda_sarfiyat_list.append({
                    'oda_no': s.oda_no,
                    'urun_adi': s.urun_adi,
                    'adet': s.toplam_tuketim or 0,
                    'tutar': float(s.toplam_tutar or 0)
                })
            
            # Ürün bazlı sarfiyat listesi
            urun_sarfiyat_list = []
            for s in urun_sarfiyat:
                urun_sarfiyat_list.append({
                    'urun_adi': s.urun_adi,
                    'adet': s.toplam_tuketim or 0,
                    'tutar': float(s.toplam_tutar or 0)
                })
            
            return {
                'success': True,
                'otel': {
                    'id': otel.id,
                    'ad': otel.ad
                },
                'rapor_tarihi': rapor_tarihi.strftime('%d.%m.%Y'),
                'istatistikler': {
                    'toplam_tuketim': toplam_tuketim,
                    'toplam_tutar': round(toplam_tutar, 2),
                    'urun_cesidi': len(urun_sarfiyat_list),
                    'islem_yapilan_oda': len(set([s['oda_no'] for s in oda_sarfiyat_list]))
                },
                'oda_sarfiyat': oda_sarfiyat_list,
                'urun_sarfiyat': urun_sarfiyat_list,
                'kat_sorumlusu_stok': kat_sorumlusu_stok
            }
            
        except Exception as e:
            logger.error(f"Minibar sarfiyat raporu oluşturma hatası: {str(e)}")
            return {'success': False, 'message': str(e)}


    @staticmethod
    def create_pie_chart_svg(data: Dict[str, int], colors: List[str], title: str = "") -> str:
        """
        SVG formatında pasta grafik oluştur (email için inline)
        
        Args:
            data: {'label': value} formatında veri
            colors: Renk listesi
            title: Grafik başlığı
        
        Returns:
            str: SVG kodu
        """
        import math
        
        total = sum(data.values())
        if total == 0:
            return '<svg width="200" height="200"><text x="100" y="100" text-anchor="middle">Veri yok</text></svg>'
        
        cx, cy, r = 100, 100, 80
        start_angle = -90
        
        paths = []
        legend_items = []
        
        for i, (label, value) in enumerate(data.items()):
            if value == 0:
                continue
            
            percentage = value / total
            angle = percentage * 360
            end_angle = start_angle + angle
            
            # SVG arc path
            large_arc = 1 if angle > 180 else 0
            
            x1 = cx + r * math.cos(math.radians(start_angle))
            y1 = cy + r * math.sin(math.radians(start_angle))
            x2 = cx + r * math.cos(math.radians(end_angle))
            y2 = cy + r * math.sin(math.radians(end_angle))
            
            color = colors[i % len(colors)]
            
            if percentage == 1:
                # Tam daire
                paths.append(f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="{color}"/>')
            else:
                path = f'M {cx},{cy} L {x1},{y1} A {r},{r} 0 {large_arc},1 {x2},{y2} Z'
                paths.append(f'<path d="{path}" fill="{color}"/>')
            
            # Legend
            legend_y = 220 + i * 20
            legend_items.append(f'''
                <rect x="10" y="{legend_y}" width="15" height="15" fill="{color}"/>
                <text x="30" y="{legend_y + 12}" font-size="12" fill="#333">{label}: {value} (%{round(percentage*100, 1)})</text>
            ''')
            
            start_angle = end_angle
        
        svg = f'''
        <svg width="250" height="{220 + len(data) * 20}" xmlns="http://www.w3.org/2000/svg">
            <text x="125" y="20" text-anchor="middle" font-size="14" font-weight="bold" fill="#333">{title}</text>
            <g transform="translate(25, 30)">
                {''.join(paths)}
            </g>
            {''.join(legend_items)}
        </svg>
        '''
        return svg
    
    @staticmethod
    def create_bar_chart_svg(data: List[Dict], x_key: str, y_key: str, title: str = "", color: str = "#3b82f6") -> str:
        """
        SVG formatında bar grafik oluştur
        
        Args:
            data: [{'label': 'x', 'value': y}] formatında veri
            x_key: X ekseni için key
            y_key: Y ekseni için key
            title: Grafik başlığı
            color: Bar rengi
        
        Returns:
            str: SVG kodu
        """
        if not data:
            return '<svg width="400" height="200"><text x="200" y="100" text-anchor="middle">Veri yok</text></svg>'
        
        # İlk 10 veriyi al
        data = data[:10]
        
        max_value = max([d.get(y_key, 0) for d in data]) or 1
        bar_width = 30
        gap = 10
        chart_height = 150
        chart_width = len(data) * (bar_width + gap) + 50
        
        bars = []
        labels = []
        
        for i, item in enumerate(data):
            value = item.get(y_key, 0)
            label = str(item.get(x_key, ''))[:10]  # Max 10 karakter
            
            bar_height = (value / max_value) * chart_height
            x = 40 + i * (bar_width + gap)
            y = 180 - bar_height
            
            bars.append(f'''
                <rect x="{x}" y="{y}" width="{bar_width}" height="{bar_height}" fill="{color}" rx="3"/>
                <text x="{x + bar_width/2}" y="{y - 5}" text-anchor="middle" font-size="10" fill="#333">{value}</text>
            ''')
            
            labels.append(f'''
                <text x="{x + bar_width/2}" y="195" text-anchor="middle" font-size="9" fill="#666" transform="rotate(-45, {x + bar_width/2}, 195)">{label}</text>
            ''')
        
        svg = f'''
        <svg width="{max(chart_width, 300)}" height="230" xmlns="http://www.w3.org/2000/svg">
            <text x="{chart_width/2}" y="20" text-anchor="middle" font-size="14" font-weight="bold" fill="#333">{title}</text>
            <line x1="35" y1="30" x2="35" y2="180" stroke="#ccc" stroke-width="1"/>
            <line x1="35" y1="180" x2="{chart_width - 10}" y2="180" stroke="#ccc" stroke-width="1"/>
            {''.join(bars)}
            {''.join(labels)}
        </svg>
        '''
        return svg
    
    @staticmethod
    def generate_gorev_raporu_html(rapor_data: Dict[str, Any]) -> str:
        """
        Görev tamamlanma raporu için HTML oluştur
        
        Args:
            rapor_data: Rapor verileri
        
        Returns:
            str: HTML içerik
        """
        if not rapor_data.get('success'):
            return f"<p>Rapor oluşturulamadı: {rapor_data.get('message', 'Bilinmeyen hata')}</p>"
        
        stats = rapor_data['istatistikler']
        
        # Pasta grafik için veri
        pie_data = {
            'Tamamlanan': stats['tamamlanan'],
            'Bekleyen': stats['bekleyen'],
            'Devam Eden': stats['devam_eden'],
            'DND': stats['dnd'],
            'Tamamlanmayan': stats['tamamlanmayan']
        }
        pie_colors = ['#22c55e', '#f59e0b', '#3b82f6', '#8b5cf6', '#ef4444']
        pie_chart = RaporEmailService.create_pie_chart_svg(pie_data, pie_colors, "Görev Durumları")
        
        # Görev tipi bar grafik
        gorev_tipi_data = []
        for tip, vals in rapor_data.get('gorev_tipi_stats', {}).items():
            tip_adi = {
                'inhouse_kontrol': 'In House',
                'arrival_kontrol': 'Arrivals',
                'departure_kontrol': 'Departures'
            }.get(tip, tip)
            gorev_tipi_data.append({'tip': tip_adi, 'tamamlanan': vals['tamamlanan']})
        
        bar_chart = RaporEmailService.create_bar_chart_svg(
            gorev_tipi_data, 'tip', 'tamamlanan', 
            "Görev Tipi Bazlı Tamamlanan", "#22c55e"
        )
        
        # Oda detayları tablosu
        oda_rows = ""
        for oda in rapor_data.get('oda_detaylari', [])[:20]:  # İlk 20 oda
            durum_renk = {
                'completed': '#22c55e',
                'pending': '#f59e0b',
                'in_progress': '#3b82f6',
                'dnd_pending': '#8b5cf6',
                'incomplete': '#ef4444'
            }.get(oda['durum'], '#6b7280')
            
            durum_text = {
                'completed': 'Tamamlandı',
                'pending': 'Bekliyor',
                'in_progress': 'Devam Ediyor',
                'dnd_pending': 'DND',
                'incomplete': 'Tamamlanmadı'
            }.get(oda['durum'], oda['durum'])
            
            gorev_tipi_text = {
                'inhouse_kontrol': 'In House',
                'arrival_kontrol': 'Arrivals',
                'departure_kontrol': 'Departures'
            }.get(oda['gorev_tipi'], oda['gorev_tipi'])
            
            oda_rows += f'''
            <tr>
                <td style="padding: 8px; border-bottom: 1px solid #e5e7eb;">{oda['oda_no']}</td>
                <td style="padding: 8px; border-bottom: 1px solid #e5e7eb;">{gorev_tipi_text}</td>
                <td style="padding: 8px; border-bottom: 1px solid #e5e7eb;">
                    <span style="background: {durum_renk}; color: white; padding: 2px 8px; border-radius: 12px; font-size: 12px;">{durum_text}</span>
                </td>
                <td style="padding: 8px; border-bottom: 1px solid #e5e7eb;">{oda['dnd_sayisi']}</td>
                <td style="padding: 8px; border-bottom: 1px solid #e5e7eb;">{oda['kontrol_zamani']}</td>
            </tr>
            '''
        
        html = f'''
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Görev Tamamlanma Raporu</title>
</head>
<body style="font-family: 'Segoe UI', Arial, sans-serif; line-height: 1.6; color: #333; margin: 0; padding: 0; background: #f3f4f6;">
    <div style="max-width: 800px; margin: 0 auto; padding: 20px;">
        <!-- Header -->
        <div style="background: linear-gradient(135deg, #3b82f6, #1d4ed8); padding: 30px; border-radius: 15px 15px 0 0; text-align: center;">
            <h1 style="color: white; margin: 0; font-size: 24px;">📋 Görev Tamamlanma Raporu</h1>
            <p style="color: rgba(255,255,255,0.9); margin: 10px 0 0 0; font-size: 16px;">{rapor_data['otel_adi']}</p>
            <p style="color: rgba(255,255,255,0.8); margin: 5px 0 0 0; font-size: 14px;">{rapor_data['rapor_tarihi']}</p>
        </div>
        
        <!-- Kat Sorumlusu Bilgisi -->
        <div style="background: white; padding: 20px; border-left: 4px solid #3b82f6; margin-top: 0;">
            <h3 style="margin: 0 0 10px 0; color: #1f2937;">👤 Kat Sorumlusu</h3>
            <p style="margin: 0; font-size: 18px; font-weight: 600; color: #3b82f6;">{rapor_data['kat_sorumlusu']['ad_soyad']}</p>
        </div>
        
        <!-- Özet Kartları -->
        <div style="background: white; padding: 20px; display: flex; flex-wrap: wrap; gap: 15px; justify-content: center;">
            <div style="background: linear-gradient(135deg, #22c55e, #16a34a); padding: 20px; border-radius: 10px; min-width: 120px; text-align: center;">
                <div style="font-size: 32px; font-weight: bold; color: white;">{stats['tamamlanan']}</div>
                <div style="color: rgba(255,255,255,0.9); font-size: 12px;">Tamamlanan</div>
            </div>
            <div style="background: linear-gradient(135deg, #f59e0b, #d97706); padding: 20px; border-radius: 10px; min-width: 120px; text-align: center;">
                <div style="font-size: 32px; font-weight: bold; color: white;">{stats['bekleyen']}</div>
                <div style="color: rgba(255,255,255,0.9); font-size: 12px;">Bekleyen</div>
            </div>
            <div style="background: linear-gradient(135deg, #8b5cf6, #7c3aed); padding: 20px; border-radius: 10px; min-width: 120px; text-align: center;">
                <div style="font-size: 32px; font-weight: bold; color: white;">{stats['dnd']}</div>
                <div style="color: rgba(255,255,255,0.9); font-size: 12px;">DND</div>
            </div>
            <div style="background: linear-gradient(135deg, #ef4444, #dc2626); padding: 20px; border-radius: 10px; min-width: 120px; text-align: center;">
                <div style="font-size: 32px; font-weight: bold; color: white;">{stats['tamamlanmayan']}</div>
                <div style="color: rgba(255,255,255,0.9); font-size: 12px;">Tamamlanmayan</div>
            </div>
        </div>
        
        <!-- Tamamlanma Oranı -->
        <div style="background: white; padding: 20px; text-align: center;">
            <h3 style="margin: 0 0 15px 0; color: #1f2937;">📊 Tamamlanma Oranı</h3>
            <div style="background: #e5e7eb; border-radius: 10px; height: 30px; overflow: hidden; max-width: 400px; margin: 0 auto;">
                <div style="background: linear-gradient(90deg, #22c55e, #16a34a); height: 100%; width: {stats['tamamlanma_orani']}%; display: flex; align-items: center; justify-content: center;">
                    <span style="color: white; font-weight: bold; font-size: 14px;">%{stats['tamamlanma_orani']}</span>
                </div>
            </div>
            <p style="margin: 10px 0 0 0; color: #6b7280; font-size: 14px;">Toplam {stats['toplam_gorev']} görevden {stats['tamamlanan']} tanesi tamamlandı</p>
        </div>
        
        <!-- Grafikler -->
        <div style="background: white; padding: 20px; display: flex; flex-wrap: wrap; gap: 20px; justify-content: center;">
            <div style="text-align: center;">
                {pie_chart}
            </div>
            <div style="text-align: center;">
                {bar_chart}
            </div>
        </div>
        
        <!-- Oda Detayları Tablosu -->
        <div style="background: white; padding: 20px; border-radius: 0 0 15px 15px;">
            <h3 style="margin: 0 0 15px 0; color: #1f2937;">🏨 Oda Detayları</h3>
            <div style="overflow-x: auto;">
                <table style="width: 100%; border-collapse: collapse; font-size: 14px;">
                    <thead>
                        <tr style="background: #f3f4f6;">
                            <th style="padding: 10px; text-align: left; border-bottom: 2px solid #e5e7eb;">Oda No</th>
                            <th style="padding: 10px; text-align: left; border-bottom: 2px solid #e5e7eb;">Görev Tipi</th>
                            <th style="padding: 10px; text-align: left; border-bottom: 2px solid #e5e7eb;">Durum</th>
                            <th style="padding: 10px; text-align: left; border-bottom: 2px solid #e5e7eb;">DND</th>
                            <th style="padding: 10px; text-align: left; border-bottom: 2px solid #e5e7eb;">Kontrol Zamanı</th>
                        </tr>
                    </thead>
                    <tbody>
                        {oda_rows}
                    </tbody>
                </table>
            </div>
        </div>
        
        <!-- Footer -->
        <div style="text-align: center; padding: 20px; color: #6b7280; font-size: 12px;">
            <p>Bu rapor otomatik olarak oluşturulmuştur.</p>
            <p>Minibar Takip Sistemi © {get_kktc_now().year}</p>
        </div>
    </div>
</body>
</html>
        '''
        return html


    @staticmethod
    def generate_minibar_raporu_html(rapor_data: Dict[str, Any]) -> str:
        """
        Minibar sarfiyat raporu için HTML oluştur
        
        Args:
            rapor_data: Rapor verileri
        
        Returns:
            str: HTML içerik
        """
        if not rapor_data.get('success'):
            return f"<p>Rapor oluşturulamadı: {rapor_data.get('message', 'Bilinmeyen hata')}</p>"
        
        stats = rapor_data['istatistikler']
        
        # Ürün sarfiyat bar grafik
        urun_chart_data = [{'urun': u['urun_adi'], 'adet': u['adet']} for u in rapor_data.get('urun_sarfiyat', [])[:10]]
        urun_bar_chart = RaporEmailService.create_bar_chart_svg(
            urun_chart_data, 'urun', 'adet',
            "En Çok Tüketilen Ürünler", "#f59e0b"
        )
        
        # Oda sarfiyat tablosu
        oda_rows = ""
        for oda in rapor_data.get('oda_sarfiyat', [])[:30]:  # İlk 30 kayıt
            oda_rows += f'''
            <tr>
                <td style="padding: 8px; border-bottom: 1px solid #e5e7eb;">{oda['oda_no']}</td>
                <td style="padding: 8px; border-bottom: 1px solid #e5e7eb;">{oda['urun_adi']}</td>
                <td style="padding: 8px; border-bottom: 1px solid #e5e7eb; text-align: center;">{oda['adet']}</td>
                <td style="padding: 8px; border-bottom: 1px solid #e5e7eb; text-align: right;">₺{oda['tutar']:.2f}</td>
            </tr>
            '''
        
        # Ürün özet tablosu
        urun_rows = ""
        for urun in rapor_data.get('urun_sarfiyat', []):
            urun_rows += f'''
            <tr>
                <td style="padding: 8px; border-bottom: 1px solid #e5e7eb;">{urun['urun_adi']}</td>
                <td style="padding: 8px; border-bottom: 1px solid #e5e7eb; text-align: center;">{urun['adet']}</td>
                <td style="padding: 8px; border-bottom: 1px solid #e5e7eb; text-align: right;">₺{urun['tutar']:.2f}</td>
            </tr>
            '''
        
        # Kat sorumlusu stok durumu
        stok_sections = ""
        for ks in rapor_data.get('kat_sorumlusu_stok', []):
            stok_rows = ""
            kritik_sayisi = 0
            for detay in ks.get('zimmet_detaylari', []):
                kritik_class = 'background: #fef2f2; color: #dc2626;' if detay['kritik_durumda'] else ''
                if detay['kritik_durumda']:
                    kritik_sayisi += 1
                stok_rows += f'''
                <tr style="{kritik_class}">
                    <td style="padding: 6px; border-bottom: 1px solid #e5e7eb; font-size: 13px;">{detay['urun_adi']}</td>
                    <td style="padding: 6px; border-bottom: 1px solid #e5e7eb; text-align: center; font-size: 13px;">{detay['miktar']}</td>
                    <td style="padding: 6px; border-bottom: 1px solid #e5e7eb; text-align: center; font-size: 13px;">{detay['kullanilan']}</td>
                    <td style="padding: 6px; border-bottom: 1px solid #e5e7eb; text-align: center; font-size: 13px; font-weight: bold;">{detay['kalan']}</td>
                </tr>
                '''
            
            kritik_badge = f'<span style="background: #ef4444; color: white; padding: 2px 8px; border-radius: 10px; font-size: 11px; margin-left: 10px;">⚠️ {kritik_sayisi} kritik</span>' if kritik_sayisi > 0 else ''
            
            stok_sections += f'''
            <div style="margin-bottom: 20px; border: 1px solid #e5e7eb; border-radius: 8px; overflow: hidden;">
                <div style="background: #f3f4f6; padding: 10px 15px; border-bottom: 1px solid #e5e7eb;">
                    <strong>👤 {ks['ad_soyad']}</strong>{kritik_badge}
                </div>
                <table style="width: 100%; border-collapse: collapse; font-size: 13px;">
                    <thead>
                        <tr style="background: #f9fafb;">
                            <th style="padding: 8px; text-align: left;">Ürün</th>
                            <th style="padding: 8px; text-align: center;">Zimmet</th>
                            <th style="padding: 8px; text-align: center;">Kullanılan</th>
                            <th style="padding: 8px; text-align: center;">Kalan</th>
                        </tr>
                    </thead>
                    <tbody>
                        {stok_rows}
                    </tbody>
                </table>
            </div>
            '''
        
        html = f'''
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Minibar Sarfiyat Raporu</title>
</head>
<body style="font-family: 'Segoe UI', Arial, sans-serif; line-height: 1.6; color: #333; margin: 0; padding: 0; background: #f3f4f6;">
    <div style="max-width: 800px; margin: 0 auto; padding: 20px;">
        <!-- Header -->
        <div style="background: linear-gradient(135deg, #f59e0b, #d97706); padding: 30px; border-radius: 15px 15px 0 0; text-align: center;">
            <h1 style="color: white; margin: 0; font-size: 24px;">🍫 Minibar Sarfiyat Raporu</h1>
            <p style="color: rgba(255,255,255,0.9); margin: 10px 0 0 0; font-size: 16px;">{rapor_data['otel']['ad']}</p>
            <p style="color: rgba(255,255,255,0.8); margin: 5px 0 0 0; font-size: 14px;">{rapor_data['rapor_tarihi']}</p>
        </div>
        
        <!-- Özet Kartları -->
        <div style="background: white; padding: 20px; display: flex; flex-wrap: wrap; gap: 15px; justify-content: center;">
            <div style="background: linear-gradient(135deg, #3b82f6, #1d4ed8); padding: 20px; border-radius: 10px; min-width: 140px; text-align: center;">
                <div style="font-size: 32px; font-weight: bold; color: white;">{stats['toplam_tuketim']}</div>
                <div style="color: rgba(255,255,255,0.9); font-size: 12px;">Toplam Tüketim</div>
            </div>
            <div style="background: linear-gradient(135deg, #22c55e, #16a34a); padding: 20px; border-radius: 10px; min-width: 140px; text-align: center;">
                <div style="font-size: 28px; font-weight: bold; color: white;">₺{stats['toplam_tutar']:,.2f}</div>
                <div style="color: rgba(255,255,255,0.9); font-size: 12px;">Toplam Tutar</div>
            </div>
            <div style="background: linear-gradient(135deg, #8b5cf6, #7c3aed); padding: 20px; border-radius: 10px; min-width: 140px; text-align: center;">
                <div style="font-size: 32px; font-weight: bold; color: white;">{stats['urun_cesidi']}</div>
                <div style="color: rgba(255,255,255,0.9); font-size: 12px;">Ürün Çeşidi</div>
            </div>
            <div style="background: linear-gradient(135deg, #ec4899, #db2777); padding: 20px; border-radius: 10px; min-width: 140px; text-align: center;">
                <div style="font-size: 32px; font-weight: bold; color: white;">{stats['islem_yapilan_oda']}</div>
                <div style="color: rgba(255,255,255,0.9); font-size: 12px;">İşlem Yapılan Oda</div>
            </div>
        </div>
        
        <!-- Ürün Grafiği -->
        <div style="background: white; padding: 20px; text-align: center;">
            <h3 style="margin: 0 0 15px 0; color: #1f2937;">📊 Ürün Bazlı Tüketim</h3>
            {urun_bar_chart}
        </div>
        
        <!-- Ürün Özet Tablosu -->
        <div style="background: white; padding: 20px;">
            <h3 style="margin: 0 0 15px 0; color: #1f2937;">📦 Ürün Sarfiyat Özeti</h3>
            <table style="width: 100%; border-collapse: collapse; font-size: 14px;">
                <thead>
                    <tr style="background: #f3f4f6;">
                        <th style="padding: 10px; text-align: left; border-bottom: 2px solid #e5e7eb;">Ürün Adı</th>
                        <th style="padding: 10px; text-align: center; border-bottom: 2px solid #e5e7eb;">Adet</th>
                        <th style="padding: 10px; text-align: right; border-bottom: 2px solid #e5e7eb;">Tutar</th>
                    </tr>
                </thead>
                <tbody>
                    {urun_rows}
                </tbody>
                <tfoot>
                    <tr style="background: #f9fafb; font-weight: bold;">
                        <td style="padding: 10px; border-top: 2px solid #e5e7eb;">TOPLAM</td>
                        <td style="padding: 10px; text-align: center; border-top: 2px solid #e5e7eb;">{stats['toplam_tuketim']}</td>
                        <td style="padding: 10px; text-align: right; border-top: 2px solid #e5e7eb;">₺{stats['toplam_tutar']:,.2f}</td>
                    </tr>
                </tfoot>
            </table>
        </div>
        
        <!-- Oda Bazlı Sarfiyat -->
        <div style="background: white; padding: 20px;">
            <h3 style="margin: 0 0 15px 0; color: #1f2937;">🏨 Oda Bazlı Sarfiyat Detayı</h3>
            <div style="overflow-x: auto;">
                <table style="width: 100%; border-collapse: collapse; font-size: 14px;">
                    <thead>
                        <tr style="background: #f3f4f6;">
                            <th style="padding: 10px; text-align: left; border-bottom: 2px solid #e5e7eb;">Oda No</th>
                            <th style="padding: 10px; text-align: left; border-bottom: 2px solid #e5e7eb;">Ürün</th>
                            <th style="padding: 10px; text-align: center; border-bottom: 2px solid #e5e7eb;">Adet</th>
                            <th style="padding: 10px; text-align: right; border-bottom: 2px solid #e5e7eb;">Tutar</th>
                        </tr>
                    </thead>
                    <tbody>
                        {oda_rows}
                    </tbody>
                </table>
            </div>
        </div>
        
        <!-- Kat Sorumlusu Stok Durumları -->
        <div style="background: white; padding: 20px; border-radius: 0 0 15px 15px;">
            <h3 style="margin: 0 0 15px 0; color: #1f2937;">👥 Kat Sorumlusu Stok Durumları</h3>
            {stok_sections if stok_sections else '<p style="color: #6b7280;">Stok bilgisi bulunamadı.</p>'}
        </div>
        
        <!-- Footer -->
        <div style="text-align: center; padding: 20px; color: #6b7280; font-size: 12px;">
            <p>Bu rapor otomatik olarak oluşturulmuştur.</p>
            <p>Minibar Takip Sistemi © {get_kktc_now().year}</p>
        </div>
    </div>
</body>
</html>
        '''
        return html
    
    @staticmethod
    def send_gorev_raporu(kat_sorumlusu_id: int, rapor_tarihi: date) -> Dict[str, Any]:
        """
        Görev tamamlanma raporunu email olarak gönder
        
        Args:
            kat_sorumlusu_id: Kat sorumlusu ID
            rapor_tarihi: Rapor tarihi
        
        Returns:
            dict: Gönderim sonucu
        """
        try:
            from models import Kullanici, KullaniciOtel
            from utils.email_service import EmailService
            
            # Kat sorumlusunun otelini bul ve bildirim kontrolü yap
            kat_sorumlusu = Kullanici.query.get(kat_sorumlusu_id)
            if kat_sorumlusu and kat_sorumlusu.otel_id:
                if not EmailService.is_otel_bildirim_aktif(kat_sorumlusu.otel_id, 'rapor'):
                    logger.info(f"Kat sorumlusu {kat_sorumlusu_id} oteli için rapor bildirimi kapalı, atlanıyor")
                    return {'success': False, 'message': 'Bu otel için rapor bildirimi kapalı'}
            
            # Rapor oluştur
            rapor_data = RaporEmailService.generate_gorev_tamamlanma_raporu(kat_sorumlusu_id, rapor_tarihi)
            
            if not rapor_data.get('success'):
                return rapor_data
            
            # HTML oluştur
            html_content = RaporEmailService.generate_gorev_raporu_html(rapor_data)
            
            # Kat sorumlusunun bağlı olduğu depo sorumlusunu bul
            kat_sorumlusu = Kullanici.query.get(kat_sorumlusu_id)
            if not kat_sorumlusu:
                return {'success': False, 'message': 'Kat sorumlusu bulunamadı'}
            
            alicilar = []
            
            # Depo sorumlusu
            if kat_sorumlusu.depo_sorumlusu and kat_sorumlusu.depo_sorumlusu.email:
                alicilar.append({
                    'email': kat_sorumlusu.depo_sorumlusu.email,
                    'kullanici_id': kat_sorumlusu.depo_sorumlusu.id
                })
            
            # Sistem yöneticileri
            sistem_yoneticileri = Kullanici.query.filter(
                Kullanici.rol.in_(['sistem_yoneticisi', 'admin']),
                Kullanici.aktif == True,
                Kullanici.email.isnot(None)
            ).all()
            
            for sy in sistem_yoneticileri:
                if sy.email and sy.email not in [a['email'] for a in alicilar]:
                    alicilar.append({
                        'email': sy.email,
                        'kullanici_id': sy.id
                    })
            
            if not alicilar:
                return {'success': False, 'message': 'Alıcı bulunamadı'}
            
            # Email gönder
            subject = f"📋 Görev Tamamlanma Raporu - {rapor_data['kat_sorumlusu']['ad_soyad']} - {rapor_data['rapor_tarihi']}"
            body = f"Görev tamamlanma raporu ekte yer almaktadır.\n\nKat Sorumlusu: {rapor_data['kat_sorumlusu']['ad_soyad']}\nTarih: {rapor_data['rapor_tarihi']}\nTamamlanma Oranı: %{rapor_data['istatistikler']['tamamlanma_orani']}"
            
            gonderim_sonuclari = []
            for alici in alicilar:
                result = EmailService.send_email(
                    to_email=alici['email'],
                    subject=subject,
                    body=body,
                    email_tipi='rapor',
                    kullanici_id=alici['kullanici_id'],
                    ilgili_tablo='gunluk_gorevler',
                    html_body=html_content,
                    ek_bilgiler={
                        'rapor_tipi': 'gorev_tamamlanma',
                        'kat_sorumlusu_id': kat_sorumlusu_id,
                        'rapor_tarihi': rapor_tarihi.isoformat()
                    }
                )
                gonderim_sonuclari.append({
                    'email': alici['email'],
                    'success': result['success']
                })
            
            basarili = len([r for r in gonderim_sonuclari if r['success']])
            
            return {
                'success': basarili > 0,
                'message': f'{basarili}/{len(alicilar)} alıcıya gönderildi',
                'sonuclar': gonderim_sonuclari
            }
            
        except Exception as e:
            logger.error(f"Görev raporu gönderim hatası: {str(e)}")
            return {'success': False, 'message': str(e)}
    
    @staticmethod
    def send_minibar_raporu(otel_id: int, rapor_tarihi: date) -> Dict[str, Any]:
        """
        Minibar sarfiyat raporunu email olarak gönder
        
        Args:
            otel_id: Otel ID
            rapor_tarihi: Rapor tarihi
        
        Returns:
            dict: Gönderim sonucu
        """
        try:
            from models import Kullanici, KullaniciOtel
            from utils.email_service import EmailService
            
            # Otel için rapor bildirimi aktif mi kontrol et
            if not EmailService.is_otel_bildirim_aktif(otel_id, 'rapor'):
                logger.info(f"Otel ID {otel_id} için rapor bildirimi kapalı, atlanıyor")
                return {'success': False, 'message': 'Bu otel için rapor bildirimi kapalı'}
            
            # Rapor oluştur
            rapor_data = RaporEmailService.generate_minibar_sarfiyat_raporu(otel_id, rapor_tarihi)
            
            if not rapor_data.get('success'):
                return rapor_data
            
            # HTML oluştur
            html_content = RaporEmailService.generate_minibar_raporu_html(rapor_data)
            
            alicilar = []
            
            # Bu otele atanmış depo sorumluları
            depo_atamalari = KullaniciOtel.query.join(Kullanici).filter(
                KullaniciOtel.otel_id == otel_id,
                Kullanici.rol == 'depo_sorumlusu',
                Kullanici.aktif == True,
                Kullanici.email.isnot(None)
            ).all()
            
            for atama in depo_atamalari:
                if atama.kullanici.email:
                    alicilar.append({
                        'email': atama.kullanici.email,
                        'kullanici_id': atama.kullanici.id
                    })
            
            # Sistem yöneticileri
            sistem_yoneticileri = Kullanici.query.filter(
                Kullanici.rol.in_(['sistem_yoneticisi', 'admin']),
                Kullanici.aktif == True,
                Kullanici.email.isnot(None)
            ).all()
            
            for sy in sistem_yoneticileri:
                if sy.email and sy.email not in [a['email'] for a in alicilar]:
                    alicilar.append({
                        'email': sy.email,
                        'kullanici_id': sy.id
                    })
            
            if not alicilar:
                return {'success': False, 'message': 'Alıcı bulunamadı'}
            
            # Email gönder
            subject = f"🍫 Minibar Sarfiyat Raporu - {rapor_data['otel']['ad']} - {rapor_data['rapor_tarihi']}"
            body = f"Minibar sarfiyat raporu ekte yer almaktadır.\n\nOtel: {rapor_data['otel']['ad']}\nTarih: {rapor_data['rapor_tarihi']}\nToplam Tüketim: {rapor_data['istatistikler']['toplam_tuketim']} adet\nToplam Tutar: ₺{rapor_data['istatistikler']['toplam_tutar']:,.2f}"
            
            gonderim_sonuclari = []
            for alici in alicilar:
                result = EmailService.send_email(
                    to_email=alici['email'],
                    subject=subject,
                    body=body,
                    email_tipi='rapor',
                    kullanici_id=alici['kullanici_id'],
                    ilgili_tablo='minibar_islemleri',
                    html_body=html_content,
                    ek_bilgiler={
                        'rapor_tipi': 'minibar_sarfiyat',
                        'otel_id': otel_id,
                        'rapor_tarihi': rapor_tarihi.isoformat()
                    }
                )
                gonderim_sonuclari.append({
                    'email': alici['email'],
                    'success': result['success']
                })
            
            basarili = len([r for r in gonderim_sonuclari if r['success']])
            
            return {
                'success': basarili > 0,
                'message': f'{basarili}/{len(alicilar)} alıcıya gönderildi',
                'sonuclar': gonderim_sonuclari
            }
            
        except Exception as e:
            logger.error(f"Minibar raporu gönderim hatası: {str(e)}")
            return {'success': False, 'message': str(e)}

    # ============================================
    # TOPLU RAPOR FONKSİYONLARI (TEK MAİL)
    # ============================================
    
    @staticmethod
    def send_toplu_gorev_raporu(rapor_tarihi: date) -> Dict[str, Any]:
        """
        Tüm kat sorumlularının görev tamamlanma raporunu TEK mail olarak gönder
        
        Args:
            rapor_tarihi: Rapor tarihi
        
        Returns:
            dict: Gönderim sonucu
        """
        try:
            from models import Kullanici, KullaniciOtel, Otel
            from utils.email_service import EmailService
            
            # Tüm aktif kat sorumlularını al
            kat_sorumlulari = Kullanici.query.filter(
                Kullanici.rol == 'kat_sorumlusu',
                Kullanici.aktif == True
            ).all()
            
            if not kat_sorumlulari:
                return {'success': False, 'message': 'Aktif kat sorumlusu bulunamadı'}
            
            # Her kat sorumlusu için rapor verisi topla
            tum_raporlar = []
            for ks in kat_sorumlulari:
                rapor_data = RaporEmailService.generate_gorev_tamamlanma_raporu(ks.id, rapor_tarihi)
                if rapor_data.get('success'):
                    tum_raporlar.append(rapor_data)
            
            if not tum_raporlar:
                return {'success': False, 'message': 'Rapor verisi oluşturulamadı'}
            
            # Toplu HTML oluştur
            html_content = RaporEmailService._generate_toplu_gorev_html(tum_raporlar, rapor_tarihi)
            
            # Alıcıları belirle (depo sorumluları + sistem yöneticileri)
            alicilar = []
            
            # Depo sorumluları
            depo_sorumlulari = Kullanici.query.filter(
                Kullanici.rol == 'depo_sorumlusu',
                Kullanici.aktif == True,
                Kullanici.email.isnot(None)
            ).all()

            for ds in depo_sorumlulari:
                if ds.email:
                    alicilar.append({
                        'email': ds.email,
                        'kullanici_id': ds.id
                    })
            
            # Sistem yöneticileri
            sistem_yoneticileri = Kullanici.query.filter(
                Kullanici.rol.in_(['sistem_yoneticisi', 'admin']),
                Kullanici.aktif == True,
                Kullanici.email.isnot(None)
            ).all()
            
            for sy in sistem_yoneticileri:
                if sy.email and sy.email not in [a['email'] for a in alicilar]:
                    alicilar.append({
                        'email': sy.email,
                        'kullanici_id': sy.id
                    })
            
            if not alicilar:
                return {'success': False, 'message': 'Alıcı bulunamadı'}
            
            # Özet istatistikler
            toplam_gorev = sum(r['istatistikler']['toplam_gorev'] for r in tum_raporlar)
            toplam_tamamlanan = sum(r['istatistikler']['tamamlanan_gorev'] for r in tum_raporlar)
            genel_oran = (toplam_tamamlanan / toplam_gorev * 100) if toplam_gorev > 0 else 0
            
            # Email gönder
            subject = f"📋 Günlük Görev Tamamlanma Raporu - {rapor_tarihi.strftime('%d.%m.%Y')} - {len(tum_raporlar)} Personel"
            body = f"""Günlük görev tamamlanma raporu ekte yer almaktadır.

Tarih: {rapor_tarihi.strftime('%d.%m.%Y')}
Personel Sayısı: {len(tum_raporlar)}
Toplam Görev: {toplam_gorev}
Tamamlanan: {toplam_tamamlanan}
Genel Tamamlanma Oranı: %{genel_oran:.1f}"""
            
            gonderim_sonuclari = []
            for alici in alicilar:
                result = EmailService.send_email(
                    to_email=alici['email'],
                    subject=subject,
                    body=body,
                    email_tipi='rapor',
                    kullanici_id=alici['kullanici_id'],
                    ilgili_tablo='gunluk_gorevler',
                    html_body=html_content,
                    ek_bilgiler={
                        'rapor_tipi': 'toplu_gorev_tamamlanma',
                        'personel_sayisi': len(tum_raporlar),
                        'rapor_tarihi': rapor_tarihi.isoformat()
                    },
                    read_receipt=True  # Okundu bilgisi talep et
                )
                gonderim_sonuclari.append({
                    'email': alici['email'],
                    'success': result['success']
                })
            
            basarili = len([r for r in gonderim_sonuclari if r['success']])
            
            logger.info(f"✅ Toplu görev raporu gönderildi: {basarili}/{len(alicilar)} alıcı, {len(tum_raporlar)} personel")
            
            return {
                'success': basarili > 0,
                'message': f'{basarili}/{len(alicilar)} alıcıya gönderildi ({len(tum_raporlar)} personel)',
                'sonuclar': gonderim_sonuclari,
                'personel_sayisi': len(tum_raporlar)
            }
            
        except Exception as e:
            logger.error(f"Toplu görev raporu gönderim hatası: {str(e)}")
            return {'success': False, 'message': str(e)}

    @staticmethod
    def send_toplu_minibar_raporu(rapor_tarihi: date) -> Dict[str, Any]:
        """
        Tüm otellerin minibar sarfiyat raporunu TEK mail olarak gönder
        
        Args:
            rapor_tarihi: Rapor tarihi
        
        Returns:
            dict: Gönderim sonucu
        """
        try:
            from models import Kullanici, KullaniciOtel, Otel
            from utils.email_service import EmailService
            
            # Tüm aktif otelleri al
            oteller = Otel.query.filter_by(aktif=True).all()
            
            if not oteller:
                return {'success': False, 'message': 'Aktif otel bulunamadı'}
            
            # Her otel için rapor verisi topla
            tum_raporlar = []
            for otel in oteller:
                # Otel için rapor bildirimi aktif mi kontrol et
                if not EmailService.is_otel_bildirim_aktif(otel.id, 'rapor'):
                    continue
                    
                rapor_data = RaporEmailService.generate_minibar_sarfiyat_raporu(otel.id, rapor_tarihi)
                if rapor_data.get('success'):
                    tum_raporlar.append(rapor_data)
            
            if not tum_raporlar:
                return {'success': False, 'message': 'Rapor verisi oluşturulamadı'}
            
            # Toplu HTML oluştur
            html_content = RaporEmailService._generate_toplu_minibar_html(tum_raporlar, rapor_tarihi)
            
            # Alıcıları belirle
            alicilar = []
            
            # Depo sorumluları
            depo_sorumlulari = Kullanici.query.filter(
                Kullanici.rol == 'depo_sorumlusu',
                Kullanici.aktif == True,
                Kullanici.email.isnot(None)
            ).all()
            
            for ds in depo_sorumlulari:
                if ds.email:
                    alicilar.append({
                        'email': ds.email,
                        'kullanici_id': ds.id
                    })

            # Sistem yöneticileri
            sistem_yoneticileri = Kullanici.query.filter(
                Kullanici.rol.in_(['sistem_yoneticisi', 'admin']),
                Kullanici.aktif == True,
                Kullanici.email.isnot(None)
            ).all()
            
            for sy in sistem_yoneticileri:
                if sy.email and sy.email not in [a['email'] for a in alicilar]:
                    alicilar.append({
                        'email': sy.email,
                        'kullanici_id': sy.id
                    })
            
            if not alicilar:
                return {'success': False, 'message': 'Alıcı bulunamadı'}
            
            # Özet istatistikler
            toplam_tuketim = sum(r['istatistikler']['toplam_tuketim'] for r in tum_raporlar)
            toplam_tutar = sum(r['istatistikler']['toplam_tutar'] for r in tum_raporlar)
            
            # Email gönder
            subject = f"🍫 Günlük Minibar Sarfiyat Raporu - {rapor_tarihi.strftime('%d.%m.%Y')} - {len(tum_raporlar)} Otel"
            body = f"""Günlük minibar sarfiyat raporu ekte yer almaktadır.

Tarih: {rapor_tarihi.strftime('%d.%m.%Y')}
Otel Sayısı: {len(tum_raporlar)}
Toplam Tüketim: {toplam_tuketim} adet
Toplam Tutar: ₺{toplam_tutar:,.2f}"""
            
            gonderim_sonuclari = []
            for alici in alicilar:
                result = EmailService.send_email(
                    to_email=alici['email'],
                    subject=subject,
                    body=body,
                    email_tipi='rapor',
                    kullanici_id=alici['kullanici_id'],
                    ilgili_tablo='minibar_islemleri',
                    html_body=html_content,
                    ek_bilgiler={
                        'rapor_tipi': 'toplu_minibar_sarfiyat',
                        'otel_sayisi': len(tum_raporlar),
                        'rapor_tarihi': rapor_tarihi.isoformat()
                    },
                    read_receipt=True  # Okundu bilgisi talep et
                )
                gonderim_sonuclari.append({
                    'email': alici['email'],
                    'success': result['success']
                })

            basarili = len([r for r in gonderim_sonuclari if r['success']])
            
            logger.info(f"✅ Toplu minibar raporu gönderildi: {basarili}/{len(alicilar)} alıcı, {len(tum_raporlar)} otel")
            
            return {
                'success': basarili > 0,
                'message': f'{basarili}/{len(alicilar)} alıcıya gönderildi ({len(tum_raporlar)} otel)',
                'sonuclar': gonderim_sonuclari,
                'otel_sayisi': len(tum_raporlar)
            }
            
        except Exception as e:
            logger.error(f"Toplu minibar raporu gönderim hatası: {str(e)}")
            return {'success': False, 'message': str(e)}

    @staticmethod
    def _generate_toplu_gorev_html(raporlar: List[Dict], rapor_tarihi: date) -> str:
        """Toplu görev tamamlanma raporu HTML'i oluştur"""
        
        # Genel istatistikler
        toplam_personel = len(raporlar)
        toplam_gorev = sum(r['istatistikler']['toplam_gorev'] for r in raporlar)
        toplam_tamamlanan = sum(r['istatistikler']['tamamlanan_gorev'] for r in raporlar)
        toplam_bekleyen = sum(r['istatistikler']['bekleyen_gorev'] for r in raporlar)
        genel_oran = (toplam_tamamlanan / toplam_gorev * 100) if toplam_gorev > 0 else 0
        
        # Personel satırları
        personel_rows = ''
        for i, rapor in enumerate(sorted(raporlar, key=lambda x: x['istatistikler']['tamamlanma_orani'], reverse=True)):
            stats = rapor['istatistikler']
            ks = rapor['kat_sorumlusu']
            oran = stats['tamamlanma_orani']
            
            # Renk belirleme
            if oran >= 90:
                renk = '#22c55e'
                bg = '#f0fdf4'
            elif oran >= 70:
                renk = '#f59e0b'
                bg = '#fffbeb'
            else:
                renk = '#ef4444'
                bg = '#fef2f2'
            
            personel_rows += f'''
            <tr style="background: {bg if i % 2 == 0 else 'white'};">
                <td style="padding: 12px; border-bottom: 1px solid #e5e7eb;">{ks['ad_soyad']}</td>
                <td style="padding: 12px; border-bottom: 1px solid #e5e7eb;">{ks.get('otel_adi', '-')}</td>
                <td style="padding: 12px; text-align: center; border-bottom: 1px solid #e5e7eb;">{stats['toplam_gorev']}</td>
                <td style="padding: 12px; text-align: center; border-bottom: 1px solid #e5e7eb; color: #22c55e; font-weight: bold;">{stats['tamamlanan_gorev']}</td>
                <td style="padding: 12px; text-align: center; border-bottom: 1px solid #e5e7eb; color: #f59e0b;">{stats['bekleyen_gorev']}</td>
                <td style="padding: 12px; text-align: center; border-bottom: 1px solid #e5e7eb;">
                    <span style="background: {renk}; color: white; padding: 4px 12px; border-radius: 20px; font-weight: bold;">%{oran:.0f}</span>
                </td>
            </tr>'''

        html = f'''
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Toplu Görev Tamamlanma Raporu</title>
</head>
<body style="font-family: 'Segoe UI', Arial, sans-serif; line-height: 1.6; color: #333; margin: 0; padding: 0; background: #f3f4f6;">
    <div style="max-width: 900px; margin: 0 auto; padding: 20px;">
        <!-- Header -->
        <div style="background: linear-gradient(135deg, #3b82f6, #1d4ed8); padding: 30px; border-radius: 15px 15px 0 0; text-align: center;">
            <h1 style="color: white; margin: 0; font-size: 26px;">📋 Günlük Görev Tamamlanma Raporu</h1>
            <p style="color: rgba(255,255,255,0.9); margin: 10px 0 0 0; font-size: 18px;">Tüm Personel Özeti</p>
            <p style="color: rgba(255,255,255,0.8); margin: 5px 0 0 0; font-size: 14px;">{rapor_tarihi.strftime('%d.%m.%Y')}</p>
        </div>
        
        <!-- Genel Özet Kartları -->
        <div style="background: white; padding: 25px; display: flex; flex-wrap: wrap; gap: 15px; justify-content: center;">
            <div style="background: linear-gradient(135deg, #8b5cf6, #7c3aed); padding: 20px 30px; border-radius: 12px; text-align: center; min-width: 120px;">
                <div style="font-size: 36px; font-weight: bold; color: white;">{toplam_personel}</div>
                <div style="color: rgba(255,255,255,0.9); font-size: 13px;">Personel</div>
            </div>
            <div style="background: linear-gradient(135deg, #3b82f6, #1d4ed8); padding: 20px 30px; border-radius: 12px; text-align: center; min-width: 120px;">
                <div style="font-size: 36px; font-weight: bold; color: white;">{toplam_gorev}</div>
                <div style="color: rgba(255,255,255,0.9); font-size: 13px;">Toplam Görev</div>
            </div>
            <div style="background: linear-gradient(135deg, #22c55e, #16a34a); padding: 20px 30px; border-radius: 12px; text-align: center; min-width: 120px;">
                <div style="font-size: 36px; font-weight: bold; color: white;">{toplam_tamamlanan}</div>
                <div style="color: rgba(255,255,255,0.9); font-size: 13px;">Tamamlanan</div>
            </div>
            <div style="background: linear-gradient(135deg, #f59e0b, #d97706); padding: 20px 30px; border-radius: 12px; text-align: center; min-width: 120px;">
                <div style="font-size: 36px; font-weight: bold; color: white;">{toplam_bekleyen}</div>
                <div style="color: rgba(255,255,255,0.9); font-size: 13px;">Bekleyen</div>
            </div>
            <div style="background: linear-gradient(135deg, {'#22c55e' if genel_oran >= 80 else '#f59e0b' if genel_oran >= 60 else '#ef4444'}, {'#16a34a' if genel_oran >= 80 else '#d97706' if genel_oran >= 60 else '#dc2626'}); padding: 20px 30px; border-radius: 12px; text-align: center; min-width: 120px;">
                <div style="font-size: 36px; font-weight: bold; color: white;">%{genel_oran:.0f}</div>
                <div style="color: rgba(255,255,255,0.9); font-size: 13px;">Genel Oran</div>
            </div>
        </div>

        <!-- Personel Detay Tablosu -->
        <div style="background: white; padding: 25px; border-radius: 0 0 15px 15px;">
            <h3 style="margin: 0 0 20px 0; color: #1f2937; font-size: 18px;">👥 Personel Bazlı Detay</h3>
            <div style="overflow-x: auto;">
                <table style="width: 100%; border-collapse: collapse; font-size: 14px;">
                    <thead>
                        <tr style="background: linear-gradient(135deg, #f8fafc, #f1f5f9);">
                            <th style="padding: 14px; text-align: left; border-bottom: 2px solid #e5e7eb; font-weight: 600;">Personel</th>
                            <th style="padding: 14px; text-align: left; border-bottom: 2px solid #e5e7eb; font-weight: 600;">Otel</th>
                            <th style="padding: 14px; text-align: center; border-bottom: 2px solid #e5e7eb; font-weight: 600;">Toplam</th>
                            <th style="padding: 14px; text-align: center; border-bottom: 2px solid #e5e7eb; font-weight: 600;">Tamamlanan</th>
                            <th style="padding: 14px; text-align: center; border-bottom: 2px solid #e5e7eb; font-weight: 600;">Bekleyen</th>
                            <th style="padding: 14px; text-align: center; border-bottom: 2px solid #e5e7eb; font-weight: 600;">Oran</th>
                        </tr>
                    </thead>
                    <tbody>
                        {personel_rows}
                    </tbody>
                    <tfoot>
                        <tr style="background: linear-gradient(135deg, #1e40af, #1d4ed8); color: white; font-weight: bold;">
                            <td style="padding: 14px; border-radius: 0 0 0 10px;">TOPLAM</td>
                            <td style="padding: 14px;">{toplam_personel} Personel</td>
                            <td style="padding: 14px; text-align: center;">{toplam_gorev}</td>
                            <td style="padding: 14px; text-align: center;">{toplam_tamamlanan}</td>
                            <td style="padding: 14px; text-align: center;">{toplam_bekleyen}</td>
                            <td style="padding: 14px; text-align: center; border-radius: 0 0 10px 0;">%{genel_oran:.0f}</td>
                        </tr>
                    </tfoot>
                </table>
            </div>
        </div>
        
        <!-- Footer -->
        <div style="text-align: center; padding: 25px; color: #6b7280; font-size: 12px;">
            <p style="margin: 0;">Bu rapor otomatik olarak oluşturulmuştur.</p>
            <p style="margin: 5px 0 0 0;">Minibar Takip Sistemi © {get_kktc_now().year}</p>
        </div>
    </div>
</body>
</html>
        '''
        return html

    @staticmethod
    def _generate_toplu_minibar_html(raporlar: List[Dict], rapor_tarihi: date) -> str:
        """Toplu minibar sarfiyat raporu HTML'i oluştur"""
        
        # Genel istatistikler
        toplam_otel = len(raporlar)
        toplam_tuketim = sum(r['istatistikler']['toplam_tuketim'] for r in raporlar)
        toplam_tutar = sum(r['istatistikler']['toplam_tutar'] for r in raporlar)
        toplam_urun_cesidi = sum(r['istatistikler']['urun_cesidi'] for r in raporlar)
        toplam_oda = sum(r['istatistikler']['islem_yapilan_oda'] for r in raporlar)
        
        # Otel satırları
        otel_rows = ''
        for i, rapor in enumerate(sorted(raporlar, key=lambda x: x['istatistikler']['toplam_tutar'], reverse=True)):
            stats = rapor['istatistikler']
            otel = rapor['otel']
            
            otel_rows += f'''
            <tr style="background: {'#f8fafc' if i % 2 == 0 else 'white'};">
                <td style="padding: 12px; border-bottom: 1px solid #e5e7eb; font-weight: 500;">{otel['ad']}</td>
                <td style="padding: 12px; text-align: center; border-bottom: 1px solid #e5e7eb;">{stats['toplam_tuketim']}</td>
                <td style="padding: 12px; text-align: center; border-bottom: 1px solid #e5e7eb;">{stats['urun_cesidi']}</td>
                <td style="padding: 12px; text-align: center; border-bottom: 1px solid #e5e7eb;">{stats['islem_yapilan_oda']}</td>
                <td style="padding: 12px; text-align: right; border-bottom: 1px solid #e5e7eb; font-weight: bold; color: #059669;">₺{stats['toplam_tutar']:,.2f}</td>
            </tr>'''

        # Ürün bazlı özet (tüm oteller birleşik)
        urun_toplam = {}
        for rapor in raporlar:
            for urun in rapor.get('urun_ozeti', []):
                urun_adi = urun['urun_adi']
                if urun_adi not in urun_toplam:
                    urun_toplam[urun_adi] = {'adet': 0, 'tutar': 0}
                urun_toplam[urun_adi]['adet'] += urun['adet']
                urun_toplam[urun_adi]['tutar'] += urun['tutar']
        
        # En çok tüketilen 10 ürün
        top_urunler = sorted(urun_toplam.items(), key=lambda x: x[1]['adet'], reverse=True)[:10]
        
        urun_rows = ''
        for urun_adi, data in top_urunler:
            urun_rows += f'''
            <tr>
                <td style="padding: 10px; border-bottom: 1px solid #e5e7eb;">{urun_adi}</td>
                <td style="padding: 10px; text-align: center; border-bottom: 1px solid #e5e7eb; font-weight: bold;">{data['adet']}</td>
                <td style="padding: 10px; text-align: right; border-bottom: 1px solid #e5e7eb;">₺{data['tutar']:,.2f}</td>
            </tr>'''

        html = f'''
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Toplu Minibar Sarfiyat Raporu</title>
</head>
<body style="font-family: 'Segoe UI', Arial, sans-serif; line-height: 1.6; color: #333; margin: 0; padding: 0; background: #f3f4f6;">
    <div style="max-width: 900px; margin: 0 auto; padding: 20px;">
        <!-- Header -->
        <div style="background: linear-gradient(135deg, #f59e0b, #d97706); padding: 30px; border-radius: 15px 15px 0 0; text-align: center;">
            <h1 style="color: white; margin: 0; font-size: 26px;">🍫 Günlük Minibar Sarfiyat Raporu</h1>
            <p style="color: rgba(255,255,255,0.9); margin: 10px 0 0 0; font-size: 18px;">Tüm Oteller Özeti</p>
            <p style="color: rgba(255,255,255,0.8); margin: 5px 0 0 0; font-size: 14px;">{rapor_tarihi.strftime('%d.%m.%Y')}</p>
        </div>
        
        <!-- Genel Özet Kartları -->
        <div style="background: white; padding: 25px; display: flex; flex-wrap: wrap; gap: 15px; justify-content: center;">
            <div style="background: linear-gradient(135deg, #8b5cf6, #7c3aed); padding: 20px 30px; border-radius: 12px; text-align: center; min-width: 120px;">
                <div style="font-size: 36px; font-weight: bold; color: white;">{toplam_otel}</div>
                <div style="color: rgba(255,255,255,0.9); font-size: 13px;">Otel</div>
            </div>
            <div style="background: linear-gradient(135deg, #3b82f6, #1d4ed8); padding: 20px 30px; border-radius: 12px; text-align: center; min-width: 120px;">
                <div style="font-size: 36px; font-weight: bold; color: white;">{toplam_tuketim}</div>
                <div style="color: rgba(255,255,255,0.9); font-size: 13px;">Toplam Tüketim</div>
            </div>
            <div style="background: linear-gradient(135deg, #ec4899, #db2777); padding: 20px 30px; border-radius: 12px; text-align: center; min-width: 120px;">
                <div style="font-size: 36px; font-weight: bold; color: white;">{toplam_oda}</div>
                <div style="color: rgba(255,255,255,0.9); font-size: 13px;">İşlem Yapılan Oda</div>
            </div>
            <div style="background: linear-gradient(135deg, #22c55e, #16a34a); padding: 20px 30px; border-radius: 12px; text-align: center; min-width: 140px;">
                <div style="font-size: 32px; font-weight: bold; color: white;">₺{toplam_tutar:,.0f}</div>
                <div style="color: rgba(255,255,255,0.9); font-size: 13px;">Toplam Tutar</div>
            </div>
        </div>

        <!-- Otel Detay Tablosu -->
        <div style="background: white; padding: 25px;">
            <h3 style="margin: 0 0 20px 0; color: #1f2937; font-size: 18px;">🏨 Otel Bazlı Detay</h3>
            <div style="overflow-x: auto;">
                <table style="width: 100%; border-collapse: collapse; font-size: 14px;">
                    <thead>
                        <tr style="background: linear-gradient(135deg, #f8fafc, #f1f5f9);">
                            <th style="padding: 14px; text-align: left; border-bottom: 2px solid #e5e7eb; font-weight: 600;">Otel</th>
                            <th style="padding: 14px; text-align: center; border-bottom: 2px solid #e5e7eb; font-weight: 600;">Tüketim</th>
                            <th style="padding: 14px; text-align: center; border-bottom: 2px solid #e5e7eb; font-weight: 600;">Ürün Çeşidi</th>
                            <th style="padding: 14px; text-align: center; border-bottom: 2px solid #e5e7eb; font-weight: 600;">Oda Sayısı</th>
                            <th style="padding: 14px; text-align: right; border-bottom: 2px solid #e5e7eb; font-weight: 600;">Tutar</th>
                        </tr>
                    </thead>
                    <tbody>
                        {otel_rows}
                    </tbody>
                    <tfoot>
                        <tr style="background: linear-gradient(135deg, #d97706, #b45309); color: white; font-weight: bold;">
                            <td style="padding: 14px; border-radius: 0 0 0 10px;">TOPLAM</td>
                            <td style="padding: 14px; text-align: center;">{toplam_tuketim}</td>
                            <td style="padding: 14px; text-align: center;">-</td>
                            <td style="padding: 14px; text-align: center;">{toplam_oda}</td>
                            <td style="padding: 14px; text-align: right; border-radius: 0 0 10px 0;">₺{toplam_tutar:,.2f}</td>
                        </tr>
                    </tfoot>
                </table>
            </div>
        </div>
        
        <!-- En Çok Tüketilen Ürünler -->
        <div style="background: white; padding: 25px; border-radius: 0 0 15px 15px;">
            <h3 style="margin: 0 0 20px 0; color: #1f2937; font-size: 18px;">🏆 En Çok Tüketilen 10 Ürün (Tüm Oteller)</h3>
            <table style="width: 100%; border-collapse: collapse; font-size: 14px;">
                <thead>
                    <tr style="background: #fef3c7;">
                        <th style="padding: 12px; text-align: left; border-bottom: 2px solid #fcd34d;">Ürün</th>
                        <th style="padding: 12px; text-align: center; border-bottom: 2px solid #fcd34d;">Toplam Adet</th>
                        <th style="padding: 12px; text-align: right; border-bottom: 2px solid #fcd34d;">Toplam Tutar</th>
                    </tr>
                </thead>
                <tbody>
                    {urun_rows if urun_rows else '<tr><td colspan="3" style="padding: 20px; text-align: center; color: #6b7280;">Ürün verisi bulunamadı</td></tr>'}
                </tbody>
            </table>
        </div>
        
        <!-- Footer -->
        <div style="text-align: center; padding: 25px; color: #6b7280; font-size: 12px;">
            <p style="margin: 0;">Bu rapor otomatik olarak oluşturulmuştur.</p>
            <p style="margin: 5px 0 0 0;">Minibar Takip Sistemi © {get_kktc_now().year}</p>
        </div>
    </div>
</body>
</html>
        '''
        return html
