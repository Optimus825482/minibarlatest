"""
Executive Report Routes
Üst yönetici raporlama merkezi route'ları
"""

from flask import render_template, jsonify, request, make_response
from utils.decorators import login_required, role_required
from utils.executive_report_service import ExecutiveReportService, parse_date
from models import Otel
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
        """PDF rapor oluştur — reportlab ile"""
        try:
            from reportlab.lib.pagesizes import A4, landscape
            from reportlab.lib import colors
            from reportlab.lib.units import mm, cm
            from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
            from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
            from reportlab.platypus import (
                SimpleDocTemplate, Table, TableStyle, Paragraph,
                Spacer, PageBreak, HRFlowable
            )
            from reportlab.pdfbase import pdfmetrics
            from reportlab.pdfbase.ttfonts import TTFont
            import io
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

            buffer = io.BytesIO()

            doc = SimpleDocTemplate(
                buffer,
                pagesize=landscape(A4),
                topMargin=2 * cm,
                bottomMargin=2 * cm,
                leftMargin=1.5 * cm,
                rightMargin=1.5 * cm,
                title=report_title,
                author='Merit Royal Hotel Group'
            )

            styles = getSampleStyleSheet()

            # Özel stiller
            title_style = ParagraphStyle(
                'CustomTitle',
                parent=styles['Title'],
                fontSize=18,
                spaceAfter=6,
                textColor=colors.HexColor('#1e293b'),
                alignment=TA_CENTER
            )
            subtitle_style = ParagraphStyle(
                'CustomSubtitle',
                parent=styles['Normal'],
                fontSize=10,
                textColor=colors.HexColor('#64748b'),
                alignment=TA_CENTER,
                spaceAfter=4
            )
            section_style = ParagraphStyle(
                'SectionTitle',
                parent=styles['Heading2'],
                fontSize=13,
                textColor=colors.HexColor('#334155'),
                spaceBefore=12,
                spaceAfter=6
            )
            normal_style = ParagraphStyle(
                'CustomNormal',
                parent=styles['Normal'],
                fontSize=9,
                textColor=colors.HexColor('#334155')
            )
            footer_style = ParagraphStyle(
                'FooterStyle',
                parent=styles['Normal'],
                fontSize=7,
                textColor=colors.HexColor('#94a3b8'),
                alignment=TA_CENTER
            )

            elements = []

            # --- BAŞLIK ---
            elements.append(Paragraph('Merit Royal Hotel Group', subtitle_style))
            elements.append(Paragraph(report_title, title_style))
            if date_range:
                elements.append(Paragraph(f'Dönem: {date_range}', subtitle_style))
            now_str = datetime.now().strftime('%d.%m.%Y %H:%M')
            elements.append(Paragraph(f'Oluşturulma: {now_str}', subtitle_style))
            elements.append(Spacer(1, 8 * mm))
            elements.append(HRFlowable(
                width="100%", thickness=1,
                color=colors.HexColor('#e2e8f0'),
                spaceAfter=6 * mm
            ))

            # --- ÖZET KARTLARI ---
            if summary:
                elements.append(Paragraph('Özet', section_style))
                summary_data = []
                summary_labels = []
                for item in summary:
                    summary_data.append(str(item.get('value', '')))
                    summary_labels.append(str(item.get('label', '')))

                # Özet tablosu — tek satır değerler, altında etiketler
                col_count = len(summary_data)
                if col_count > 0:
                    avail_width = doc.width
                    col_w = avail_width / col_count

                    val_cells = [Paragraph(
                        f'<b>{v}</b>', ParagraphStyle(
                            'SummaryVal', parent=normal_style,
                            fontSize=14, alignment=TA_CENTER,
                            textColor=colors.HexColor('#1e293b')
                        )
                    ) for v in summary_data]

                    label_cells = [Paragraph(
                        lbl, ParagraphStyle(
                            'SummaryLbl', parent=normal_style,
                            fontSize=8, alignment=TA_CENTER,
                            textColor=colors.HexColor('#64748b')
                        )
                    ) for lbl in summary_labels]

                    summary_table = Table(
                        [val_cells, label_cells],
                        colWidths=[col_w] * col_count
                    )
                    summary_table.setStyle(TableStyle([
                        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#f8fafc')),
                        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#e2e8f0')),
                        ('TOPPADDING', (0, 0), (-1, 0), 10),
                        ('BOTTOMPADDING', (0, 0), (-1, 0), 10),
                        ('TOPPADDING', (0, 1), (-1, 1), 4),
                        ('BOTTOMPADDING', (0, 1), (-1, 1), 6),
                        ('ROUNDEDCORNERS', [4, 4, 4, 4]),
                    ]))
                    elements.append(summary_table)
                    elements.append(Spacer(1, 8 * mm))

            # --- VERİ TABLOSU ---
            if table_headers and table_rows:
                elements.append(Paragraph('Detay Tablosu', section_style))

                # Header
                header_cells = [Paragraph(
                    f'<b>{h}</b>', ParagraphStyle(
                        'TH', parent=normal_style,
                        fontSize=8, textColor=colors.HexColor('#475569')
                    )
                ) for h in table_headers]

                # Rows
                all_rows = [header_cells]
                for row in table_rows:
                    cells = [Paragraph(
                        str(cell), ParagraphStyle(
                            'TD', parent=normal_style, fontSize=8
                        )
                    ) for cell in row]
                    all_rows.append(cells)

                col_count = len(table_headers)
                avail_width = doc.width
                col_w = avail_width / col_count

                data_table = Table(all_rows, colWidths=[col_w] * col_count, repeatRows=1)
                data_table.setStyle(TableStyle([
                    # Header
                    ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#f1f5f9')),
                    ('TEXTCOLOR', (0, 0), (-1, 0), colors.HexColor('#334155')),
                    ('FONTSIZE', (0, 0), (-1, 0), 8),
                    ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
                    ('TOPPADDING', (0, 0), (-1, 0), 8),
                    # Body
                    ('FONTSIZE', (0, 1), (-1, -1), 8),
                    ('TOPPADDING', (0, 1), (-1, -1), 5),
                    ('BOTTOMPADDING', (0, 1), (-1, -1), 5),
                    # Zebra striping
                    *[('BACKGROUND', (0, i), (-1, i), colors.HexColor('#f8fafc'))
                      for i in range(2, len(all_rows), 2)],
                    # Grid
                    ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#e2e8f0')),
                    ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                    ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                    ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f8fafc')]),
                ]))
                elements.append(data_table)

            # --- FOOTER ---
            elements.append(Spacer(1, 10 * mm))
            elements.append(HRFlowable(
                width="100%", thickness=0.5,
                color=colors.HexColor('#e2e8f0'),
                spaceBefore=4 * mm, spaceAfter=4 * mm
            ))
            elements.append(Paragraph(
                f'Merit Royal Hotel Group — Minibar Takip Sistemi — {report_title} — {now_str}',
                footer_style
            ))

            # Build PDF
            doc.build(elements)
            buffer.seek(0)

            response = make_response(buffer.getvalue())
            safe_title = report_title.replace(' ', '_')
            response.headers['Content-Type'] = 'application/pdf'
            response.headers['Content-Disposition'] = f'attachment; filename={safe_title}_{datetime.now().strftime("%Y%m%d_%H%M")}.pdf'
            return response

        except Exception as e:
            logger.error(f"PDF oluşturma hatası: {e}", exc_info=True)
            return jsonify({'success': False, 'error': str(e)}), 500
