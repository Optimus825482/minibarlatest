"""
Executive Report Routes
Üst yönetici raporlama merkezi route'ları
"""

from flask import render_template, jsonify, request, make_response
from utils.decorators import login_required, role_required
from utils.executive_report_service import ExecutiveReportService, parse_date
from models import Otel, db
import logging
import json

logger = logging.getLogger(__name__)


# Tab konfigürasyonları — sidebar menü öğesine göre dinamik başlık/ikon
TAB_CONFIGS = {
    'product': {
        'title': 'Ürün Tüketim Raporu',
        'subtitle': 'Ürün bazlı tüketim analizi ve raporlama',
        'icon': 'fas fa-wine-bottle'
    },
    'personnel': {
        'title': 'Personel Performans Raporu',
        'subtitle': 'Personel bazlı performans analizi',
        'icon': 'fas fa-user-tie'
    },
    'hotel': {
        'title': 'Otel Raporu',
        'subtitle': 'Otel bazlı kapsamlı analiz ve karşılaştırma',
        'icon': 'fas fa-hotel'
    },
    'task': {
        'title': 'Görev Performans Raporu',
        'subtitle': 'Görev tipi bazlı performans analizi',
        'icon': 'fas fa-tasks'
    },
    'comparative': {
        'title': 'Karşılaştırmalı Analiz',
        'subtitle': 'İki dönem karşılaştırmalı performans analizi',
        'icon': 'fas fa-balance-scale'
    },
    'dnd': {
        'title': 'DND Raporlama',
        'subtitle': 'Do Not Disturb kayıtları ve tüketim analizi',
        'icon': 'fas fa-moon'
    },
    'audit': {
        'title': 'Denetim İzi',
        'subtitle': 'Sistem genelinde kullanıcı işlem kayıtları ve denetim izleri',
        'icon': 'fas fa-shield-alt'
    },
}


def register_executive_report_routes(app):
    """Executive report route'larını register et"""

    @app.route('/executive-reports')
    @login_required
    @role_required('superadmin')
    def executive_reports():
        """Ana raporlama merkezi sayfası — sidebar'dan tab parametresi alır"""
        try:
            active_tab = request.args.get('tab', 'product')
            if active_tab not in TAB_CONFIGS:
                active_tab = 'product'
            tab_config = TAB_CONFIGS[active_tab]
            filters = ExecutiveReportService.get_filter_options()
            return render_template(
                'sistem_yoneticisi/executive_reports.html',
                filters=filters,
                tab_config=tab_config,
                active_tab=active_tab
            )
        except Exception as e:
            logger.error(f"Executive reports sayfa hatası: {e}")
            return render_template(
                'sistem_yoneticisi/executive_reports.html',
                filters={'oteller': [], 'urun_gruplari': [], 'urunler': []},
                tab_config=TAB_CONFIGS.get('product'),
                active_tab='product'
            )

    # ---- RAPOR API'leri ----

    @app.route('/api/executive/reports/product-consumption')
    @login_required
    @role_required('superadmin')
    def api_report_product_consumption():
        """Ürün tüketim raporu API"""
        try:
            result = ExecutiveReportService.get_product_consumption_report(
                start_date=parse_date(request.args.get('start_date')),
                end_date=parse_date(request.args.get('end_date')),
                otel_id=request.args.get('otel_id', type=int),
                kat_id=request.args.get('kat_id', type=int),
                oda_id=request.args.get('oda_id', type=int),
                urun_id=request.args.get('urun_id', type=int),
                grup_id=request.args.get('grup_id', type=int),
                group_by=request.args.get('group_by', 'urun')
            )
            return jsonify(result)
        except Exception as e:
            logger.error(f"Ürün tüketim raporu API hatası: {e}")
            return jsonify({'success': False, 'error': str(e)}), 500


    @app.route('/api/executive/reports/personnel')
    @login_required
    @role_required('superadmin')
    def api_report_personnel():
        """Personel performans raporu API"""
        try:
            result = ExecutiveReportService.get_personnel_report(
                start_date=parse_date(request.args.get('start_date')),
                end_date=parse_date(request.args.get('end_date')),
                otel_id=request.args.get('otel_id', type=int),
                personel_id=request.args.get('personel_id', type=int),
                rol=request.args.get('rol')
            )
            return jsonify(result)
        except Exception as e:
            logger.error(f"Personel raporu API hatası: {e}")
            return jsonify({'success': False, 'error': str(e)}), 500

    @app.route('/api/executive/reports/hotel')
    @login_required
    @role_required('superadmin')
    def api_report_hotel():
        """Otel raporu API"""
        try:
            result = ExecutiveReportService.get_hotel_report(
                start_date=parse_date(request.args.get('start_date')),
                end_date=parse_date(request.args.get('end_date')),
                otel_id=request.args.get('otel_id', type=int)
            )
            return jsonify(result)
        except Exception as e:
            logger.error(f"Otel raporu API hatası: {e}")
            return jsonify({'success': False, 'error': str(e)}), 500

    @app.route('/api/executive/reports/daily-trend')
    @login_required
    @role_required('superadmin')
    def api_report_daily_trend():
        """Günlük tüketim trend API"""
        try:
            result = ExecutiveReportService.get_daily_consumption_trend(
                start_date=parse_date(request.args.get('start_date')),
                end_date=parse_date(request.args.get('end_date')),
                otel_id=request.args.get('otel_id', type=int),
                urun_id=request.args.get('urun_id', type=int)
            )
            return jsonify(result)
        except Exception as e:
            logger.error(f"Günlük trend API hatası: {e}")
            return jsonify({'success': False, 'error': str(e)}), 500

    @app.route('/api/executive/reports/task-performance')
    @login_required
    @role_required('superadmin')
    def api_report_task_performance():
        """Görev performans raporu API"""
        try:
            result = ExecutiveReportService.get_task_performance_report(
                start_date=parse_date(request.args.get('start_date')),
                end_date=parse_date(request.args.get('end_date')),
                otel_id=request.args.get('otel_id', type=int),
                gorev_tipi=request.args.get('gorev_tipi')
            )
            return jsonify(result)
        except Exception as e:
            logger.error(f"Görev performans API hatası: {e}")
            return jsonify({'success': False, 'error': str(e)}), 500

    @app.route('/api/executive/reports/comparative')
    @login_required
    @role_required('superadmin')
    def api_report_comparative():
        """Karşılaştırmalı analiz API"""
        try:
            result = ExecutiveReportService.get_comparative_analysis(
                period1_start=parse_date(request.args.get('p1_start')),
                period1_end=parse_date(request.args.get('p1_end')),
                period2_start=parse_date(request.args.get('p2_start')),
                period2_end=parse_date(request.args.get('p2_end')),
                otel_id=request.args.get('otel_id', type=int)
            )
            return jsonify(result)
        except Exception as e:
            logger.error(f"Karşılaştırmalı analiz API hatası: {e}")
            return jsonify({'success': False, 'error': str(e)}), 500

    @app.route('/api/executive/reports/dnd')
    @login_required
    @role_required('superadmin')
    def api_report_dnd():
        """DND raporlama API"""
        try:
            result = ExecutiveReportService.get_dnd_report(
                start_date=parse_date(request.args.get('start_date')),
                end_date=parse_date(request.args.get('end_date')),
                otel_id=request.args.get('otel_id', type=int),
                kat_id=request.args.get('kat_id', type=int),
                oda_id=request.args.get('oda_id', type=int),
                personel_id=request.args.get('personel_id', type=int),
                group_by=request.args.get('group_by', 'oda')
            )
            return jsonify(result)
        except Exception as e:
            logger.error(f"DND raporu API hatası: {e}")
            return jsonify({'success': False, 'error': str(e)}), 500

    # ---- AUDIT TRAIL API ----

    @app.route('/api/executive/reports/audit-trail')
    @login_required
    @role_required('superadmin')
    def api_report_audit_trail():
        """Audit Trail (Denetim İzi) API — Executive dashboard: superadmin dahil TÜM kayıtlar"""
        try:
            from models import AuditLog, Kullanici
            from datetime import datetime, timedelta

            page = request.args.get('page', 1, type=int)
            per_page = request.args.get('per_page', 50, type=int)
            kullanici_id = request.args.get('kullanici_id', type=int)
            islem_tipi = request.args.get('islem_tipi')
            tablo_adi = request.args.get('tablo_adi')
            arama = request.args.get('arama', '').strip()
            start_date = request.args.get('start_date')
            end_date = request.args.get('end_date')

            # Executive dashboard — superadmin dahil TÜM kayıtlar (filtreleme YOK)
            query = AuditLog.query

            if kullanici_id:
                query = query.filter(AuditLog.kullanici_id == kullanici_id)
            if islem_tipi:
                query = query.filter(AuditLog.islem_tipi == islem_tipi)
            if tablo_adi:
                query = query.filter(AuditLog.tablo_adi == tablo_adi)
            if arama:
                query = query.filter(
                    db.or_(
                        AuditLog.kullanici_adi.ilike(f'%{arama}%'),
                        AuditLog.degisiklik_ozeti.ilike(f'%{arama}%'),
                        AuditLog.tablo_adi.ilike(f'%{arama}%')
                    )
                )
            if start_date:
                try:
                    sd = datetime.strptime(start_date, '%Y-%m-%d')
                    query = query.filter(AuditLog.islem_tarihi >= sd)
                except ValueError:
                    pass
            if end_date:
                try:
                    ed = datetime.strptime(end_date, '%Y-%m-%d') + timedelta(days=1)
                    query = query.filter(AuditLog.islem_tarihi < ed)
                except ValueError:
                    pass

            # Sıralama ve sayfalama
            query = query.order_by(AuditLog.islem_tarihi.desc())
            total = query.count()
            logs = query.offset((page - 1) * per_page).limit(per_page).all()

            # İstatistikler
            from utils.helpers import get_kktc_now
            bugun = get_kktc_now().replace(hour=0, minute=0, second=0, microsecond=0)
            bu_hafta = bugun - timedelta(days=bugun.weekday())
            bu_ay = bugun.replace(day=1)

            stats = {
                'today': AuditLog.query.filter(AuditLog.islem_tarihi >= bugun).count(),
                'week': AuditLog.query.filter(AuditLog.islem_tarihi >= bu_hafta).count(),
                'month': AuditLog.query.filter(AuditLog.islem_tarihi >= bu_ay).count(),
                'total': total
            }

            # Filtre seçenekleri
            users = Kullanici.query.filter_by(aktif=True).order_by(Kullanici.kullanici_adi).all()
            tables = [t[0] for t in db.session.query(AuditLog.tablo_adi).distinct().order_by(AuditLog.tablo_adi).all()]

            # İşlem tipi etiketleri
            islem_tipi_labels = {
                'login': 'Giriş', 'logout': 'Çıkış', 'create': 'Oluşturma',
                'update': 'Güncelleme', 'delete': 'Silme', 'view': 'Görüntüleme',
                'export': 'Dışa Aktarma', 'import': 'İçe Aktarma',
                'backup': 'Yedekleme', 'restore': 'Geri Yükleme'
            }

            # Rol renkleri
            rol_colors = {
                'superadmin': 'purple', 'sistem_yoneticisi': 'blue',
                'admin': 'cyan', 'depo_sorumlusu': 'amber', 'kat_sorumlusu': 'emerald'
            }

            data = []
            for log in logs:
                islem_label = islem_tipi_labels.get(log.islem_tipi, log.islem_tipi)
                rol_color = rol_colors.get(log.kullanici_rol, 'slate')
                data.append({
                    'id': log.id,
                    'kullanici_adi': log.kullanici_adi,
                    'kullanici_rol': log.kullanici_rol,
                    'rol_color': rol_color,
                    'islem_tipi': log.islem_tipi,
                    'islem_label': islem_label,
                    'tablo_adi': log.tablo_adi,
                    'kayit_id': log.kayit_id,
                    'degisiklik_ozeti': log.degisiklik_ozeti or '',
                    'http_method': log.http_method or '',
                    'ip_adresi': log.ip_adresi or '',
                    'tarih': log.islem_tarihi.strftime('%d.%m.%Y %H:%M:%S') if log.islem_tarihi else '',
                    'tarih_kisa': log.islem_tarihi.strftime('%d.%m.%Y %H:%M') if log.islem_tarihi else '',
                    'eski_deger': log.eski_deger,
                    'yeni_deger': log.yeni_deger
                })

            return jsonify({
                'success': True,
                'data': data,
                'stats': stats,
                'filters': {
                    'users': [{'id': u.id, 'ad': u.kullanici_adi, 'rol': u.rol} for u in users],
                    'tables': tables,
                    'islem_tipleri': [{'value': k, 'label': v} for k, v in islem_tipi_labels.items()]
                },
                'pagination': {
                    'page': page,
                    'per_page': per_page,
                    'total': total,
                    'pages': (total + per_page - 1) // per_page
                }
            })
        except Exception as e:
            logger.error(f"Audit trail API hatası: {e}", exc_info=True)
            return jsonify({'success': False, 'error': str(e)}), 500

    # ---- FİLTRE API'leri ----

    @app.route('/api/executive/reports/filters/floors')
    @login_required
    @role_required('superadmin')
    def api_report_floors():
        """Otel'e göre katlar"""
        otel_id = request.args.get('otel_id', type=int)
        if not otel_id:
            return jsonify([])
        return jsonify(ExecutiveReportService.get_floors_by_hotel(otel_id))

    @app.route('/api/executive/reports/filters/rooms')
    @login_required
    @role_required('superadmin')
    def api_report_rooms():
        """Kat'a göre odalar"""
        kat_id = request.args.get('kat_id', type=int)
        if not kat_id:
            return jsonify([])
        return jsonify(ExecutiveReportService.get_rooms_by_floor(kat_id))

    @app.route('/api/executive/reports/filters/personnel')
    @login_required
    @role_required('superadmin')
    def api_report_personnel_list():
        """Personel listesi"""
        return jsonify(ExecutiveReportService.get_personnel_list(
            otel_id=request.args.get('otel_id', type=int),
            rol=request.args.get('rol')
        ))

    # ---- PDF EXPORT ----

    @app.route('/api/executive/reports/pdf', methods=['POST'])
    @login_required
    @role_required('superadmin')
    def api_report_pdf():
        """PDF rapor oluştur — Merit Royal antetli, Türkçe destekli, sayfalı"""
        try:
            from reportlab.lib.pagesizes import A4, landscape
            from reportlab.lib import colors
            from reportlab.lib.units import mm, cm
            from reportlab.lib.styles import ParagraphStyle
            from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
            from reportlab.platypus import (
                BaseDocTemplate, Frame, PageTemplate, Table, TableStyle,
                Paragraph, Spacer, HRFlowable, Image
            )
            from reportlab.pdfbase import pdfmetrics
            from reportlab.pdfbase.ttfonts import TTFont
            import io, os
            from datetime import datetime

            data = request.get_json()
            if not data:
                return jsonify({'success': False, 'error': 'Veri gönderilmedi'}), 400

            report_type = data.get('report_type', 'product')
            report_title = data.get('title', 'Rapor')
            date_range = data.get('date_range', '')
            summary = data.get('summary', [])
            table_headers = data.get('table_headers', [])
            table_rows = data.get('table_rows', [])
            now_str = datetime.now().strftime('%d.%m.%Y %H:%M')

            # --- Türkçe font kayıt ---
            font_dir = os.path.join(app.root_path, 'static', 'fonts')
            font_regular = os.path.join(font_dir, 'DejaVuSans.ttf')
            font_bold = os.path.join(font_dir, 'DejaVuSans-Bold.ttf')

            try:
                pdfmetrics.registerFont(TTFont('DejaVu', font_regular))
                pdfmetrics.registerFont(TTFont('DejaVu-Bold', font_bold))
            except Exception:
                pass  # Zaten kayıtlıysa devam

            FONT = 'DejaVu'
            FONT_BOLD = 'DejaVu-Bold'

            # Merit Royal renk paleti
            MERIT_GOLD = colors.HexColor('#C5A55A')
            MERIT_DARK = colors.HexColor('#1a1a2e')
            MERIT_NAVY = colors.HexColor('#16213e')
            MERIT_GRAY = colors.HexColor('#64748b')
            MERIT_LIGHT = colors.HexColor('#f8fafc')
            MERIT_BORDER = colors.HexColor('#e2e8f0')
            MERIT_TEXT = colors.HexColor('#1e293b')
            MERIT_TEXT_LIGHT = colors.HexColor('#475569')

            # Logo yolu
            logo_path = os.path.join(app.root_path, 'static', 'icons', 'icon-for-pdf-18.png')
            has_logo = os.path.exists(logo_path)

            buffer = io.BytesIO()
            page_w, page_h = landscape(A4)

            # --- Sayfa header/footer çizen fonksiyon ---
            def draw_page(canvas, doc):
                canvas.saveState()
                # --- HEADER ---
                header_y = page_h - 1.2 * cm

                # Üst altın çizgi
                canvas.setStrokeColor(MERIT_GOLD)
                canvas.setLineWidth(2)
                canvas.line(1.5 * cm, header_y, page_w - 1.5 * cm, header_y)

                # Logo (sol)
                if has_logo:
                    try:
                        canvas.drawImage(
                            logo_path,
                            1.5 * cm, header_y + 2 * mm,
                            width=14 * mm, height=14 * mm,
                            preserveAspectRatio=True, mask='auto'
                        )
                    except Exception:
                        pass

                # Şirket adı (logo yanı)
                canvas.setFont(FONT_BOLD, 11)
                canvas.setFillColor(MERIT_DARK)
                text_x = (1.5 * cm + 16 * mm) if has_logo else 1.5 * cm
                canvas.drawString(text_x, header_y + 6 * mm, 'Merit Royal')

                canvas.setFont(FONT, 7)
                canvas.setFillColor(MERIT_GRAY)
                canvas.drawString(text_x, header_y + 1.5 * mm, 'Minibar Takip Sistemi')

                # Rapor başlığı (sağ)
                canvas.setFont(FONT_BOLD, 9)
                canvas.setFillColor(MERIT_TEXT)
                canvas.drawRightString(page_w - 1.5 * cm, header_y + 6 * mm, report_title)

                canvas.setFont(FONT, 7)
                canvas.setFillColor(MERIT_GRAY)
                if date_range:
                    canvas.drawRightString(page_w - 1.5 * cm, header_y + 1.5 * mm, date_range)

                # --- FOOTER ---
                footer_y = 1.2 * cm

                # Alt altın çizgi
                canvas.setStrokeColor(MERIT_GOLD)
                canvas.setLineWidth(1)
                canvas.line(1.5 * cm, footer_y, page_w - 1.5 * cm, footer_y)

                # Sol: şirket bilgisi
                canvas.setFont(FONT, 6.5)
                canvas.setFillColor(MERIT_GRAY)
                canvas.drawString(1.5 * cm, footer_y - 3.5 * mm,
                                  f'Merit Royal \u2014 {report_title}')

                # Orta: tarih
                canvas.setFont(FONT, 6.5)
                canvas.drawCentredString(page_w / 2, footer_y - 3.5 * mm,
                                         now_str)

                # Sağ: sayfa numarası
                page_num = canvas.getPageNumber()
                canvas.setFont(FONT_BOLD, 7)
                canvas.setFillColor(MERIT_TEXT)
                canvas.drawRightString(page_w - 1.5 * cm, footer_y - 3.5 * mm,
                                       f'Sayfa {page_num}')

                canvas.restoreState()

            # --- Document template ---
            frame = Frame(
                1.5 * cm, 2 * cm,
                page_w - 3 * cm, page_h - 4 * cm,
                id='main'
            )
            template = PageTemplate(id='merit', frames=frame, onPage=draw_page)

            doc = BaseDocTemplate(
                buffer,
                pagesize=landscape(A4),
                title=report_title,
                author='Merit Royal'
            )
            doc.addPageTemplates([template])

            # --- Stiller (Türkçe font) ---
            title_style = ParagraphStyle(
                'MeritTitle', fontName=FONT_BOLD, fontSize=16,
                spaceAfter=4, textColor=MERIT_DARK, alignment=TA_CENTER
            )
            subtitle_style = ParagraphStyle(
                'MeritSubtitle', fontName=FONT, fontSize=9,
                textColor=MERIT_GRAY, alignment=TA_CENTER, spaceAfter=3
            )
            section_style = ParagraphStyle(
                'MeritSection', fontName=FONT_BOLD, fontSize=11,
                textColor=MERIT_DARK, spaceBefore=10, spaceAfter=6
            )
            normal_style = ParagraphStyle(
                'MeritNormal', fontName=FONT, fontSize=8,
                textColor=MERIT_TEXT
            )

            elements = []

            # --- KAPAK BAŞLIK ---
            elements.append(Spacer(1, 6 * mm))
            elements.append(Paragraph(report_title, title_style))
            if date_range:
                elements.append(Paragraph(date_range, subtitle_style))
            elements.append(Paragraph(f'Oluşturulma: {now_str}', subtitle_style))
            elements.append(Spacer(1, 4 * mm))
            elements.append(HRFlowable(
                width="100%", thickness=0.5,
                color=MERIT_GOLD, spaceAfter=6 * mm
            ))

            # --- ÖZET KARTLARI ---
            if summary:
                elements.append(Paragraph('Özet', section_style))
                summary_data = []
                summary_labels = []
                for item in summary:
                    summary_data.append(str(item.get('value', '')))
                    summary_labels.append(str(item.get('label', '')))

                col_count = len(summary_data)
                if col_count > 0:
                    avail_width = frame._width
                    col_w = avail_width / col_count

                    val_cells = [Paragraph(
                        v, ParagraphStyle(
                            'SV', fontName=FONT_BOLD,
                            fontSize=14, alignment=TA_CENTER,
                            textColor=MERIT_DARK
                        )
                    ) for v in summary_data]

                    label_cells = [Paragraph(
                        lbl, ParagraphStyle(
                            'SL', fontName=FONT,
                            fontSize=7.5, alignment=TA_CENTER,
                            textColor=MERIT_GRAY
                        )
                    ) for lbl in summary_labels]

                    summary_table = Table(
                        [val_cells, label_cells],
                        colWidths=[col_w] * col_count
                    )
                    summary_table.setStyle(TableStyle([
                        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                        ('BACKGROUND', (0, 0), (-1, 0), MERIT_LIGHT),
                        ('LINEBELOW', (0, 0), (-1, 0), 0.5, MERIT_GOLD),
                        ('GRID', (0, 0), (-1, -1), 0.5, MERIT_BORDER),
                        ('TOPPADDING', (0, 0), (-1, 0), 10),
                        ('BOTTOMPADDING', (0, 0), (-1, 0), 10),
                        ('TOPPADDING', (0, 1), (-1, 1), 5),
                        ('BOTTOMPADDING', (0, 1), (-1, 1), 7),
                    ]))
                    elements.append(summary_table)
                    elements.append(Spacer(1, 8 * mm))

            # --- VERİ TABLOSU ---
            if table_headers and table_rows:
                elements.append(Paragraph('Detay Tablosu', section_style))

                header_cells = [Paragraph(
                    h, ParagraphStyle(
                        'TH', fontName=FONT_BOLD,
                        fontSize=7.5, textColor=colors.white
                    )
                ) for h in table_headers]

                all_rows = [header_cells]
                for row in table_rows:
                    cells = [Paragraph(
                        str(cell), ParagraphStyle(
                            'TD', fontName=FONT, fontSize=7.5,
                            textColor=MERIT_TEXT
                        )
                    ) for cell in row]
                    all_rows.append(cells)

                col_count = len(table_headers)
                avail_width = frame._width
                col_w = avail_width / col_count

                data_table = Table(
                    all_rows, colWidths=[col_w] * col_count,
                    repeatRows=1
                )
                data_table.setStyle(TableStyle([
                    # Header — koyu lacivert arka plan, beyaz yazı
                    ('BACKGROUND', (0, 0), (-1, 0), MERIT_NAVY),
                    ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                    ('FONTNAME', (0, 0), (-1, 0), FONT_BOLD),
                    ('FONTSIZE', (0, 0), (-1, 0), 7.5),
                    ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
                    ('TOPPADDING', (0, 0), (-1, 0), 8),
                    # Body
                    ('FONTNAME', (0, 1), (-1, -1), FONT),
                    ('FONTSIZE', (0, 1), (-1, -1), 7.5),
                    ('TOPPADDING', (0, 1), (-1, -1), 5),
                    ('BOTTOMPADDING', (0, 1), (-1, -1), 5),
                    # Zebra striping
                    ('ROWBACKGROUNDS', (0, 1), (-1, -1),
                     [colors.white, MERIT_LIGHT]),
                    # Grid
                    ('GRID', (0, 0), (-1, -1), 0.4, MERIT_BORDER),
                    ('LINEBELOW', (0, 0), (-1, 0), 1, MERIT_GOLD),
                    ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                    ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ]))
                elements.append(data_table)

            # Build PDF
            doc.build(elements)
            buffer.seek(0)

            response = make_response(buffer.getvalue())
            safe_title = report_title.replace(' ', '_')
            response.headers['Content-Type'] = 'application/pdf'
            response.headers['Content-Disposition'] = \
                f'attachment; filename={safe_title}_{datetime.now().strftime("%Y%m%d_%H%M")}.pdf'
            return response

        except Exception as e:
            logger.error(f"PDF oluşturma hatası: {e}", exc_info=True)
            return jsonify({'success': False, 'error': str(e)}), 500
