"""
Excel İşleme Servisi
Otel doluluk Excel dosyalarını işler ve veritabanına kaydeder

Desteklenen formatlar:
1. Standart format: Header 1. satırda (Room no, Arrival, Departure, Adult)
2. P4001 formatı (Depo yöneticisi): Header 8. satırda (R.No, Arrival, Departure, Adl)
"""

import logging
import openpyxl
import pandas as pd
import traceback
import re
import pytz
from datetime import datetime, date, time
from models import db, MisafirKayit, Oda, Kat

# KKTC Timezone
KKTC_TZ = pytz.timezone('Europe/Nicosia')

def get_kktc_now():
    """Kıbrıs saat diliminde şu anki zamanı döndürür."""
    return datetime.now(KKTC_TZ)

logger = logging.getLogger(__name__)


class ExcelProcessingService:
    """Excel dosyalarını işleyen servis sınıfı"""
    
    # Beklenen sütun adları - Standart format
    IN_HOUSE_COLUMNS = ['Name', 'Room no', 'R.Type', 'Arrival', 'Departure', 'Adult']
    ARRIVALS_COLUMNS = ['Name', 'Room no', 'R.Type', 'Hsk.St.', 'Arr.Time', 'Arrival', 'Departure', 'Adult']
    DEPARTURES_COLUMNS = ['Name', 'Room no', 'R.Type', 'Arrival', 'Departure', 'Dep.Time', 'Source', 'Adults']
    
    # P4001 formatı (Depo yöneticisi) - dosya tipi algılama pattern'leri
    P4001_TYPE_PATTERNS = {
        'arrivals': r'Arrival\s*:\s*(\d{1,2}\.\d{1,2}\.\d{4})',
        'departures': r'Departure\s*(?:date)?\s*:\s*(\d{1,2}\.\d{1,2}\.\d{4})',
        'in_house': r'Date:\s*(\d{1,2}\.\d{1,2}\.\d{4})'
    }
    
    @staticmethod
    def detect_file_type(headers):
        """
        Excel sütun başlıklarından dosya tipini otomatik algılar
        
        Args:
            headers: Excel'in ilk satırındaki sütun başlıkları (list)
            
        Returns:
            str: 'arrivals', 'departures' veya 'in_house'
        
        Logic:
            - Eğer 'Dep.Time' varsa -> 'departures'
            - Eğer 'Hsk.St.' veya 'Arr.Time' varsa -> 'arrivals'
            - Yoksa -> 'in_house'
        """
        headers_str = [str(h).strip() if h else '' for h in headers]
        headers_lower = [h.lower() for h in headers_str]
        
        # Debug log
        logger.info(f"📋 Excel Headers: {headers_str}")
        
        # DEPARTURES dosyası için özel sütunlar (case-insensitive)
        if 'Dep.Time' in headers_str or 'dep.time' in headers_lower or 'deptime' in headers_lower:
            logger.info("✅ Dosya tipi: DEPARTURES")
            return 'departures'
        
        # ARRIVALS dosyası için özel sütunlar (case-insensitive)
        if 'Hsk.St.' in headers_str or 'Arr.Time' in headers_str or 'arr.time' in headers_lower or 'hsk.st.' in headers_lower:
            logger.info("✅ Dosya tipi: ARRIVALS")
            return 'arrivals'

        logger.info("✅ Dosya tipi: IN HOUSE")
        return 'in_house'
    
    @staticmethod
    def process_excel_file(file_path, islem_kodu, user_id, otel_id=None, override_dosya_tipi=None):
        """
        Excel dosyasını işler ve veritabanına kaydeder
        
        Desteklenen formatlar:
        1. Standart format: Header 1. satırda
        2. P4001 formatı (Depo yöneticisi): Header 8. satırda
        
        Args:
            file_path: Dosya yolu
            islem_kodu: Benzersiz işlem kodu
            user_id: Yükleyen kullanıcı ID
            otel_id: Otel ID (opsiyonel, filtreleme için)
            override_dosya_tipi: Kullanıcının onayladığı dosya tipi (opsiyonel)
            
        Returns:
            dict: {
                'success': bool,
                'dosya_tipi': str,
                'toplam_satir': int,
                'basarili_satir': int,
                'hatali_satir': int,
                'hatalar': list
            }
        """
        try:
            # Önce P4001 (depo yöneticisi) formatını kontrol et
            p4001_info = ExcelProcessingService._detect_p4001_format(file_path)
            
            if p4001_info.get('is_p4001'):
                logger.info("📋 P4001 formatı tespit edildi, özel işleme başlıyor...")
                # Override varsa P4001 info'ya ekle
                if override_dosya_tipi:
                    p4001_info['dosya_tipi'] = override_dosya_tipi
                    logger.info(f"📋 Kullanıcı override: {override_dosya_tipi}")
                return ExcelProcessingService._process_p4001_file(
                    file_path, islem_kodu, user_id, otel_id, p4001_info
                )
            
            # Standart format - Excel dosyasını aç
            workbook = openpyxl.load_workbook(file_path, data_only=True)
            sheet = workbook.active
            
            # İlk satırdan başlıkları al
            headers = []
            for cell in sheet[1]:  # type: ignore[index]
                headers.append(cell.value)
            
            # Kullanıcı override ettiyse direkt onu kullan
            if override_dosya_tipi and override_dosya_tipi in ['in_house', 'arrivals', 'departures']:
                dosya_tipi = override_dosya_tipi
                logger.info(f"✅ Kullanıcı onaylı dosya tipi: {dosya_tipi}")
            else:
                # Önce header bazlı dosya tipini algıla
                header_dosya_tipi = ExcelProcessingService.detect_file_type(headers)
                
                # Tarih bazlı akıllı algılama için verileri oku
                try:
                    df_std = pd.read_excel(file_path, header=0)
                    
                    # Arrival ve Departure sütun adlarını bul
                    arrival_col = 'Arrival' if 'Arrival' in df_std.columns else None
                    departure_col = 'Departure' if 'Departure' in df_std.columns else None
                    
                    if arrival_col and departure_col:
                        smart_dosya_tipi = ExcelProcessingService._detect_file_type_by_dates_standard(
                            df_std, arrival_col, departure_col
                        )
                        
                        if smart_dosya_tipi:
                            dosya_tipi = smart_dosya_tipi
                            logger.info(
                                f"✅ Standart format - Tarih bazlı akıllı algılama: {dosya_tipi}"
                            )
                        else:
                            dosya_tipi = header_dosya_tipi
                            logger.info(
                                f"✅ Standart format - Header bazlı algılama: {dosya_tipi}"
                            )
                    else:
                        dosya_tipi = header_dosya_tipi
                except Exception as e:
                    logger.error(f"⚠️ Standart format akıllı algılama hatası: {str(e)}")
                    dosya_tipi = header_dosya_tipi
            
            # Kayıt tipini belirle
            if dosya_tipi == 'arrivals':
                kayit_tipi = 'arrival'
            elif dosya_tipi == 'departures':
                kayit_tipi = 'departure'
            else:
                kayit_tipi = 'in_house'
            
            # Sütun indekslerini bul
            col_indices = ExcelProcessingService._get_column_indices(headers)
            
            if not col_indices:
                return {
                    'success': False,
                    'error': 'Gerekli sütunlar bulunamadı',
                    'dosya_tipi': dosya_tipi,
                    'toplam_satir': 0,
                    'basarili_satir': 0,
                    'hatali_satir': 0,
                    'hatalar': ['Gerekli sütunlar (Room no, Arrival, Departure) bulunamadı']
                }
            
            # Satırları işle
            toplam_satir = 0
            basarili_satir = 0
            hatali_satir = 0
            hatalar = []

            for row_idx, row in enumerate(
                sheet.iter_rows(min_row=2, values_only=True), start=2  # type: ignore[union-attr]
            ):
                toplam_satir += 1
                
                try:
                    # Satır verilerini çıkar
                    row_data = ExcelProcessingService._extract_row_data(
                        row, col_indices, dosya_tipi
                    )
                    
                    # Veriyi doğrula
                    is_valid, error_msg = ExcelProcessingService.validate_row(row_data, dosya_tipi)
                    
                    if not is_valid:
                        hatali_satir += 1
                        hatalar.append(f"Satır {row_idx}: {error_msg}")
                        continue
                    
                    # Odayı bul veya oluştur
                    oda = ExcelProcessingService.get_or_create_oda(
                        row_data['oda_no'], otel_id
                    )
                    
                    if not oda:
                        hatali_satir += 1
                        hatalar.append(f"Satır {row_idx}: Oda '{row_data['oda_no']}' bulunamadı veya oluşturulamadı")
                        continue
                    
                    # UPSERT MANTIĞI - Aynı oda + kayıt tipi için:
                    # 1. Mevcut kayıt varsa GÜNCELLE (en güncel bilgi)
                    # 2. Yoksa yeni kayıt EKLE
                    # NOT: Oda bazlı unique kayıt tutuyoruz, tarih farkı önemli değil
                    giris_date = row_data['giris_tarihi'].date() if isinstance(row_data['giris_tarihi'], datetime) else row_data['giris_tarihi']
                    cikis_date = row_data['cikis_tarihi'].date() if isinstance(row_data['cikis_tarihi'], datetime) else row_data['cikis_tarihi']
                    
                    # Aynı oda + kayıt tipi için mevcut kayıt var mı?
                    # Tarih kontrolü: Yeni yüklenen dosyanın tarihleri ile çakışan kayıt
                    mevcut_kayit = MisafirKayit.query.filter(
                        MisafirKayit.oda_id == oda.id,
                        MisafirKayit.kayit_tipi == kayit_tipi,
                        # Tarih çakışması kontrolü: mevcut kayıt ile yeni kayıt aynı döneme denk geliyor mu?
                        MisafirKayit.giris_tarihi <= cikis_date,
                        MisafirKayit.cikis_tarihi >= giris_date
                    ).first()
                    
                    if mevcut_kayit:
                        # UPSERT: Mevcut kaydı güncelle (en güncel bilgi)
                        mevcut_kayit.giris_tarihi = giris_date
                        mevcut_kayit.cikis_tarihi = cikis_date
                        mevcut_kayit.misafir_sayisi = row_data['misafir_sayisi']
                        mevcut_kayit.islem_kodu = islem_kodu  # Son yükleme kodu
                        if row_data.get('giris_saati'):
                            mevcut_kayit.giris_saati = row_data['giris_saati']
                        if row_data.get('cikis_saati'):
                            mevcut_kayit.cikis_saati = row_data['cikis_saati']
                        # Güncelleme zamanını kaydet
                        mevcut_kayit.guncelleme_tarihi = get_kktc_now()
                        basarili_satir += 1
                    else:
                        # INSERT: Yeni kayıt oluştur
                        misafir_kayit = MisafirKayit(
                            oda_id=oda.id,
                            islem_kodu=islem_kodu,
                            misafir_sayisi=row_data['misafir_sayisi'],
                            giris_tarihi=giris_date,
                            giris_saati=row_data.get('giris_saati'),
                            cikis_tarihi=cikis_date,
                            cikis_saati=row_data.get('cikis_saati'),
                            kayit_tipi=kayit_tipi,
                            olusturan_id=user_id
                        )
                        db.session.add(misafir_kayit)
                        basarili_satir += 1
                    basarili_satir += 1
                    
                except Exception as e:
                    hatali_satir += 1
                    hatalar.append(f"Satır {row_idx}: {str(e)}")
                    continue
            
            # Toplu kaydet
            db.session.commit()
            
            # Görevlendirme sistemi hook'u - Görevleri oluştur
            try:
                ExcelProcessingService._create_tasks_after_upload(
                    otel_id=otel_id,
                    dosya_tipi=dosya_tipi,
                    basarili_satir=basarili_satir
                )
            except Exception as hook_error:
                # Hook hatası ana işlemi etkilemesin
                logger.error(f"Görev oluşturma hook hatası: {str(hook_error)}")
            
            return {
                'success': True,
                'dosya_tipi': dosya_tipi,
                'toplam_satir': toplam_satir,
                'basarili_satir': basarili_satir,
                'hatali_satir': hatali_satir,
                'hatalar': hatalar[:50]  # İlk 50 hatayı döndür
            }
            
        except Exception as e:
            db.session.rollback()
            return {
                'success': False,
                'error': f'Excel işleme hatası: {str(e)}',
                'dosya_tipi': None,
                'toplam_satir': 0,
                'basarili_satir': 0,
                'hatali_satir': 0,
                'hatalar': [str(e), traceback.format_exc()]
            }
    
    @staticmethod
    def _get_column_indices(headers):
        """Sütun başlıklarından indeksleri bul"""
        indices = {}
        
        for idx, header in enumerate(headers):
            header_str = str(header).strip() if header else ''
            
            if header_str == 'Room no':
                indices['oda_no'] = idx
            elif header_str == 'Arrival':
                indices['giris_tarihi'] = idx
            elif header_str == 'Departure':
                indices['cikis_tarihi'] = idx
            elif header_str == 'Adult' or header_str == 'Adults':
                indices['misafir_sayisi'] = idx
            elif header_str == 'Arr.Time':
                indices['giris_saati'] = idx
            elif header_str == 'Dep.Time':
                indices['cikis_saati'] = idx
        
        # Zorunlu sütunlar var mı kontrol et
        # Departures için misafir_sayisi zorunlu değil
        required = ['oda_no', 'giris_tarihi', 'cikis_tarihi']
        if all(key in indices for key in required):
            return indices
        
        return None
    
    @staticmethod
    def _extract_row_data(row, col_indices, dosya_tipi):
        """Satırdan veri çıkar"""
        data = {
            'oda_no': str(row[col_indices['oda_no']]).strip() if row[col_indices['oda_no']] else None,
            'giris_tarihi': row[col_indices['giris_tarihi']],
            'cikis_tarihi': row[col_indices['cikis_tarihi']],
        }
        
        # Misafir sayısı - Departures için zorunlu değil
        if 'misafir_sayisi' in col_indices:
            data['misafir_sayisi'] = row[col_indices['misafir_sayisi']]
        elif dosya_tipi == 'departures':
            data['misafir_sayisi'] = 1  # Departures için varsayılan 1
        else:
            data['misafir_sayisi'] = row[col_indices.get('misafir_sayisi', 0)]
        
        # ARRIVALS için giriş saati
        if dosya_tipi == 'arrivals' and 'giris_saati' in col_indices:
            data['giris_saati'] = row[col_indices['giris_saati']]
        
        # DEPARTURES için çıkış saati
        if dosya_tipi == 'departures' and 'cikis_saati' in col_indices:
            data['cikis_saati'] = row[col_indices['cikis_saati']]
        
        return data
    
    @staticmethod
    def validate_row(row_data, dosya_tipi='in_house'):
        """
        Satır verilerini doğrular
        
        Args:
            row_data: Satır verileri
            dosya_tipi: 'in_house', 'arrivals' veya 'departures'
        
        Returns:
            tuple: (is_valid, error_message)
        """
        # Oda numarası kontrolü
        if not row_data.get('oda_no'):
            return False, "Oda numarası boş"
        
        # Giriş tarihi kontrolü
        giris_tarihi = ExcelProcessingService.parse_date(row_data.get('giris_tarihi'))
        if not giris_tarihi:
            return False, "Geçersiz giriş tarihi"
        
        # Çıkış tarihi kontrolü
        cikis_tarihi = ExcelProcessingService.parse_date(row_data.get('cikis_tarihi'))
        if not cikis_tarihi:
            return False, "Geçersiz çıkış tarihi"
        
        # Tarih sırası kontrolü - her ikisini de date'e çevir
        giris_date = giris_tarihi.date() if isinstance(giris_tarihi, datetime) else giris_tarihi
        cikis_date = cikis_tarihi.date() if isinstance(cikis_tarihi, datetime) else cikis_tarihi
        if giris_date >= cikis_date:
            return False, "Giriş tarihi çıkış tarihinden önce olmalı"
        
        # Misafir sayısı kontrolü - Departures için zorunlu değil
        if dosya_tipi == 'departures':
            # Departures için misafir sayısı yoksa varsayılan 1
            misafir_sayisi = row_data.get('misafir_sayisi')
            if misafir_sayisi is None or misafir_sayisi == '' or misafir_sayisi == '-':
                row_data['misafir_sayisi'] = 1
            else:
                try:
                    row_data['misafir_sayisi'] = int(misafir_sayisi) if int(misafir_sayisi) > 0 else 1
                except (ValueError, TypeError):
                    row_data['misafir_sayisi'] = 1
        else:
            # In House ve Arrivals için misafir sayısı zorunlu
            try:
                misafir_sayisi = int(row_data.get('misafir_sayisi', 0))
                if misafir_sayisi <= 0:
                    return False, "Misafir sayısı eksik"
                row_data['misafir_sayisi'] = misafir_sayisi
            except (ValueError, TypeError):
                return False, "Geçersiz misafir sayısı"
        
        # Tarihleri güncelle
        row_data['giris_tarihi'] = giris_tarihi
        row_data['cikis_tarihi'] = cikis_tarihi
        
        # Giriş saati kontrolü (varsa)
        if 'giris_saati' in row_data and row_data['giris_saati']:
            giris_saati = ExcelProcessingService.parse_time(row_data['giris_saati'])
            row_data['giris_saati'] = giris_saati
        
        # Çıkış saati kontrolü (varsa - Departures için)
        if 'cikis_saati' in row_data and row_data['cikis_saati']:
            cikis_saati = ExcelProcessingService.parse_time(row_data['cikis_saati'])
            row_data['cikis_saati'] = cikis_saati
        
        return True, None
    
    @staticmethod
    def parse_date(date_value):
        """Tarih değerini parse eder"""
        if not date_value:
            return None
        
        # Zaten date objesi ise
        if isinstance(date_value, date):
            return date_value
        
        # datetime objesi ise
        if isinstance(date_value, datetime):
            return date_value.date()
        
        # String ise parse et
        if isinstance(date_value, str):
            date_value = date_value.strip()
            
            # Yaygın tarih formatları
            formats = [
                '%Y-%m-%d',
                '%d.%m.%Y',
                '%d/%m/%Y',
                '%d-%m-%Y',
                '%Y/%m/%d',
            ]
            
            for fmt in formats:
                try:
                    return datetime.strptime(date_value, fmt).date()
                except ValueError:
                    continue
        
        return None
    
    @staticmethod
    def parse_time(time_value):
        """Saat değerini parse eder"""
        if not time_value:
            return None
        
        # Zaten time objesi ise
        if isinstance(time_value, time):
            return time_value
        
        # datetime objesi ise
        if isinstance(time_value, datetime):
            return time_value.time()
        
        # String ise parse et
        if isinstance(time_value, str):
            time_value = time_value.strip()
            
            # Yaygın saat formatları
            formats = [
                '%H:%M',
                '%H:%M:%S',
                '%I:%M %p',  # 12 saat formatı (AM/PM)
            ]
            
            for fmt in formats:
                try:
                    return datetime.strptime(time_value, fmt).time()
                except ValueError:
                    continue
        
        return None
    
    @staticmethod
    def get_or_create_oda(oda_no, otel_id=None):
        """
        Oda numarasına göre oda kaydını getirir veya oluşturur
        
        Args:
            oda_no: Oda numarası
            otel_id: Otel ID (opsiyonel)
            
        Returns:
            Oda: Oda objesi veya None
        """
        try:
            # Önce odayı bul
            query = Oda.query.filter_by(oda_no=oda_no)
            
            # Otel filtresi varsa ekle
            if otel_id:
                query = query.join(Kat).filter(Kat.otel_id == otel_id)
            
            oda = query.first()
            
            if oda:
                return oda
            
            # Oda bulunamadı - uyarı ver ama None döndür
            # (Oda oluşturma işlemi manuel yapılmalı)
            return None
            
        except Exception as e:
            logger.error(f"Oda arama hatası: {str(e)}")
            return None

    @staticmethod
    def _create_tasks_after_upload(otel_id, dosya_tipi, basarili_satir):
        """
        Excel yükleme sonrası görevleri oluşturur.
        
        MANTIK: 3 dosya da (inhouse, arrivals, departures) yüklenince görevler oluşturulur.
        Her dosya yüklendiğinde YuklemeGorev tablosu kontrol edilir.
        3'ü de 'completed' ise görevler oluşturulur.
        
        NOT: Bu fonksiyon process_excel_file() içinden çağrılıyor ve YuklemeGorev tablosu
        henüz güncellenmemiş oluyor. Bu yüzden mevcut yüklenen dosya tipini de 'completed'
        olarak sayıyoruz.
        
        Args:
            otel_id: Otel ID
            dosya_tipi: 'in_house', 'arrivals' veya 'departures'
            basarili_satir: Başarıyla yüklenen satır sayısı
        """
        if not otel_id or basarili_satir == 0:
            return
        
        try:
            from models import YuklemeGorev
            from datetime import date
            
            tarih = date.today()
            
            # Mevcut yüklenen dosya tipini YuklemeGorev formatına çevir
            # (process_excel_file 'in_house' döndürür, YuklemeGorev 'inhouse' bekler)
            dosya_tipi_map = {
                'in_house': 'inhouse',
                'arrivals': 'arrivals',
                'departures': 'departures'
            }
            mevcut_dosya_tipi = dosya_tipi_map.get(dosya_tipi, dosya_tipi)

            logger.debug(
                f"📊 Otel {otel_id} - Mevcut yüklenen dosya: {mevcut_dosya_tipi}"
            )
            
            # 3 dosya tipi için yükleme durumlarını kontrol et
            # NOT: Mevcut yüklenen dosyayı 'completed' olarak say (henüz DB'de güncellenmemiş)
            yukleme_durumlari = {}
            for tip in ['inhouse', 'arrivals', 'departures']:
                if tip == mevcut_dosya_tipi:
                    # Mevcut yüklenen dosya - başarılı olduğu için 'completed' say
                    yukleme_durumlari[tip] = 'completed'
                else:
                    # Diğer dosyalar - DB'den kontrol et
                    yukleme = YuklemeGorev.query.filter(
                        YuklemeGorev.otel_id == otel_id,
                        YuklemeGorev.gorev_tarihi == tarih,
                        YuklemeGorev.dosya_tipi == tip
                    ).first()
                    yukleme_durumlari[tip] = yukleme.durum if yukleme else 'pending'

            logger.debug(
                f"📊 Otel {otel_id} - Yükleme durumları (mevcut dahil): {yukleme_durumlari}"
            )
            
            # 3 dosya da yüklendi mi kontrol et
            tum_dosyalar_yuklendi = all(
                durum == 'completed' for durum in yukleme_durumlari.values()
            )
            
            if not tum_dosyalar_yuklendi:
                eksik_dosyalar = [tip for tip, durum in yukleme_durumlari.items() if durum != 'completed']
                print(f"⏳ Otel {otel_id} - Eksik dosyalar: {eksik_dosyalar}. Görevler henüz oluşturulmayacak.")
                return
            
            # 3 dosya da yüklendi - görevleri oluştur
            logger.info(
                f"✅ Otel {otel_id} - 3 dosya da yüklendi! Görevler oluşturuluyor..."
            )
            
            from utils.gorev_service import GorevService
            from utils.bildirim_service import BildirimService
            
            result = GorevService.create_daily_tasks(otel_id, tarih)
            
            # Kat sorumlularına bildirim gönder
            if result.get('toplam_oda_sayisi', 0) > 0:
                from models import Kullanici
                kat_sorumluları = Kullanici.query.filter(
                    Kullanici.otel_id == otel_id,
                    Kullanici.rol == "kat_sorumlusu",
                    Kullanici.aktif,
                ).all()
                
                # Tüm görev tipleri için bildirim gönder
                gorev_tipleri = [
                    ('inhouse_kontrol', result.get('inhouse_gorev_sayisi', 0)),
                    ('arrival_kontrol', result.get('arrival_gorev_sayisi', 0)),
                    ('departure_kontrol', result.get('departure_gorev_sayisi', 0))
                ]
                
                for ks in kat_sorumluları:
                    for gorev_tipi, oda_sayisi in gorev_tipleri:
                        if oda_sayisi > 0:
                            BildirimService.send_task_created_notification(  # pyright: ignore[reportAttributeAccessIssue]
                                personel_id=ks.id,
                                gorev_tipi=gorev_tipi,
                                oda_sayisi=oda_sayisi,
                            )

            logger.info(f"✅ Görevler oluşturuldu: {result}")
            
        except Exception as e:
            logger.error(f"⚠️ Görev oluşturma hatası: {str(e)}")

    # ==================== TARİH BAZLI AKILLI ALGILAMA ====================
    
    @staticmethod
    def _detect_file_type_by_dates_standard(df, arrival_col, departure_col):
        """
        Standart format için dosya tipini tarihlere göre akıllı algılar
        
        Mantık (öncelik sırasıyla):
        1. IN HOUSE: Giriş < Bugün VE Çıkış > Bugün (misafir otelde kalıyor)
        2. DEPARTURES: Çıkış = Bugün (bugün çıkış yapacaklar)
        3. ARRIVALS: Giriş = Bugün (bugün giriş yapacaklar)
        
        Args:
            df: DataFrame
            arrival_col: Arrival sütun adı
            departure_col: Departure sütun adı
            
        Returns:
            str: 'arrivals', 'departures', 'in_house' veya None
        """
        try:
            bugun = get_kktc_now().date()
            
            # İlk 20 satırı analiz et
            sample_size = min(20, len(df))
            
            arrivals_list = []
            departures_list = []
            
            for idx in range(sample_size):
                try:
                    row = df.iloc[idx]
                    
                    # Oda numarası boşsa atla
                    oda_no = row.get('Room no')
                    if pd.isna(oda_no) or str(oda_no).strip() == '':
                        continue
                    
                    arrival_raw = row.get(arrival_col)
                    departure_raw = row.get(departure_col)
                    
                    # Tarihleri parse et - pandas datetime64 desteği
                    arrival_date = ExcelProcessingService._safe_parse_date(arrival_raw)
                    departure_date = ExcelProcessingService._safe_parse_date(departure_raw)
                    
                    if arrival_date:
                        arrivals_list.append(arrival_date)
                    if departure_date:
                        departures_list.append(departure_date)
                        
                except Exception as e:
                    logger.error(f"⚠️ Satır {idx} parse hatası: {str(e)}")
                    continue
            
            if not arrivals_list or not departures_list:
                logger.warning(
                    f"⚠️ Tarih listesi boş - arrivals: {len(arrivals_list)}, departures: {len(departures_list)}"
                )
                return None
            
            # Debug: İlk birkaç tarihi göster
            logger.debug(f"📊 Tarih analizi - Bugün: {bugun}")
            logger.debug(f"📊 İlk 3 Arrival: {arrivals_list[:3]}")
            logger.debug(f"📊 İlk 3 Departure: {departures_list[:3]}")
            
            # Sayaçlar - her kayıt için ayrı ayrı say
            inhouse_count = 0  # Giriş < Bugün VE Çıkış > Bugün
            departure_count = 0  # Çıkış = Bugün (giriş tarihi önemli değil)
            arrival_count = 0  # Giriş = Bugün (çıkış tarihi önemli değil)
            
            for i in range(min(len(arrivals_list), len(departures_list))):
                arr = arrivals_list[i]
                dep = departures_list[i]
                
                # DEPARTURES: Çıkış = Bugün (giriş tarihi ne olursa olsun)
                if dep == bugun:
                    departure_count += 1
                # ARRIVALS: Giriş = Bugün (çıkış tarihi ne olursa olsun)
                elif arr == bugun:
                    arrival_count += 1
                # IN HOUSE: Giriş < Bugün VE Çıkış > Bugün (misafir şu an otelde)
                elif arr < bugun and dep > bugun:
                    inhouse_count += 1
            
            total_valid = min(len(arrivals_list), len(departures_list))
            logger.debug(
                f"📊 Sonuçlar - IN HOUSE: {inhouse_count}, DEPARTURES: {departure_count}, ARRIVALS: {arrival_count} / Toplam: {total_valid}"
            )
            
            # ÖNCELİK SIRASI VE EŞİKLER:
            # - DEPARTURES: %100 (tüm çıkışlar bugün olmalı)
            # - ARRIVALS: %100 (tüm girişler bugün olmalı)
            # - IN HOUSE: %50 (çoğunluk otelde kalıyor olmalı)
            
            # 1. DEPARTURES: Çıkış = Bugün (%100 - tüm kayıtlar)
            if departure_count == total_valid and total_valid > 0:
                logger.debug(
                    f"📊 Standart format - Tarih analizi: Çıkış = Bugün ({departure_count}/{total_valid}) → DEPARTURES"
                )
                return 'departures'
            
            # 2. ARRIVALS: Giriş = Bugün (%100 - tüm kayıtlar)
            if arrival_count == total_valid and total_valid > 0:
                logger.debug(
                    f"📊 Standart format - Tarih analizi: Giriş = Bugün ({arrival_count}/{total_valid}) → ARRIVALS"
                )
                return 'arrivals'
            
            # 3. IN HOUSE: Giriş < Bugün VE Çıkış > Bugün (%70)
            if inhouse_count >= total_valid * 0.7:
                logger.debug(
                    f"📊 Standart format - Tarih analizi: Giriş < Bugün VE Çıkış > Bugün ({inhouse_count}/{total_valid}) → IN HOUSE"
                )
                return 'in_house'
            
            # Hiçbiri eşiği geçmediyse, varsayılan IN HOUSE (en güvenli seçenek)
            logger.debug("📊 Standart format - Eşik geçilemedi, varsayılan IN HOUSE")
            return 'in_house'
            
        except Exception as e:
            logger.error(f"⚠️ Standart format tarih bazlı algılama hatası: {str(e)}")
            import traceback
            traceback.print_exc()
            return None
    
    @staticmethod
    def _safe_parse_date(date_value):
        """
        Tarihi güvenli şekilde parse eder - pandas datetime64, datetime, date ve string destekler
        
        Args:
            date_value: Tarih değeri (herhangi bir formatta)
            
        Returns:
            date: Parse edilmiş tarih veya None
        """
        if date_value is None or (isinstance(date_value, float) and pd.isna(date_value)):
            return None
        
        # pandas Timestamp veya datetime64
        if hasattr(date_value, 'date'):
            try:
                return date_value.date()  # type: ignore[union-attr]
            except Exception:
                logger.debug("Sessiz hata yakalandi", exc_info=True)
        
        # pandas NaT kontrolü
        if pd.isna(date_value):
            return None
        
        # Zaten date objesi ise
        if isinstance(date_value, date) and not isinstance(date_value, datetime):
            return date_value
        
        # datetime objesi ise
        if isinstance(date_value, datetime):
            return date_value.date()
        
        # String ise parse et
        if isinstance(date_value, str):
            return ExcelProcessingService.parse_date(date_value)
        
        # numpy datetime64
        try:
            import numpy as np
            if isinstance(date_value, np.datetime64):
                return pd.Timestamp(date_value).date()
        except Exception:
            logger.debug("Sessiz hata yakalandi", exc_info=True)
        
        return None
    
    # ==================== P4001 FORMAT (DEPO YÖNETİCİSİ) ====================
    
    @staticmethod
    def _detect_file_type_by_dates(df, arrival_col, departure_col, rapor_tarihi=None):
        """
        Dosya tipini tarihlere göre akıllı algılar
        
        Mantık:
        - Departure = Bugün (tüm odalar için aynı) → DEPARTURES
        - Arrival < Bugün VE Departure > Bugün → IN HOUSE
        - Arrival = Bugün VE Departure > Bugün → ARRIVALS
        
        Args:
            df: DataFrame
            arrival_col: Arrival sütun adı
            departure_col: Departure sütun adı
            rapor_tarihi: Rapor tarihi (yıl referansı için)
            
        Returns:
            str: 'arrivals', 'departures' veya 'in_house'
        """
        try:
            bugun = get_kktc_now().date()
            
            # İlk 20 satırı analiz et (yeterli örnek)
            sample_size = min(20, len(df))
            
            arrivals_list = []
            departures_list = []
            
            for idx in range(sample_size):
                try:
                    row = df.iloc[idx]
                    
                    # Oda numarası boşsa atla
                    oda_no = row.get('R.No') if 'R.No' in df.columns else row.get('Room no')
                    if pd.isna(oda_no) or str(oda_no).strip() == '':
                        continue
                    
                    arrival_raw = row.get(arrival_col)
                    departure_raw = row.get(departure_col)
                    
                    # Tarihleri parse et
                    arrival_date = ExcelProcessingService._parse_p4001_date(arrival_raw, rapor_tarihi)
                    departure_date = ExcelProcessingService._parse_p4001_date(departure_raw, rapor_tarihi)
                    
                    if arrival_date:
                        arrivals_list.append(arrival_date)
                    if departure_date:
                        departures_list.append(departure_date)
                        
                except Exception:
                    continue
            
            if not arrivals_list or not departures_list:
                return None  # Yeterli veri yok, header bazlı algılamaya devam et
            
            # Analiz yap - ÖNCELİK SIRASI ÖNEMLİ!
            
            # 1. DEPARTURES: Çıkış tarihi = Bugün (en az %70)
            departure_count = 0
            for d in departures_list:
                if d == bugun:
                    departure_count += 1
            
            if departure_count >= len(departures_list) * 0.7:
                logger.debug(
                    f"📊 P4001 - Tarih analizi: Çıkış = Bugün ({departure_count}/{len(departures_list)}) → DEPARTURES"
                )
                return 'departures'
            
            # 2. ARRIVALS: Giriş tarihi = Bugün (en az %70)
            arrival_count = 0
            for a in arrivals_list:
                if a == bugun:
                    arrival_count += 1
            
            if arrival_count >= len(arrivals_list) * 0.7:
                logger.debug(
                    f"📊 P4001 - Tarih analizi: Giriş = Bugün ({arrival_count}/{len(arrivals_list)}) → ARRIVALS"
                )
                return 'arrivals'
            
            # 3. IN HOUSE: Giriş < Bugün VE Çıkış > Bugün (en az %70)
            inhouse_count = 0
            for i in range(min(len(arrivals_list), len(departures_list))):
                if arrivals_list[i] < bugun and departures_list[i] > bugun:
                    inhouse_count += 1
            
            if inhouse_count >= len(arrivals_list) * 0.7:
                logger.debug(
                    f"📊 P4001 - Tarih analizi: Giriş < Bugün VE Çıkış > Bugün ({inhouse_count}/{len(arrivals_list)}) → IN HOUSE"
                )
                return 'in_house'
            
            return None  # Belirlenemedi, header bazlı algılamaya devam et
            
        except Exception as e:
            logger.error(f"⚠️ Tarih bazlı dosya tipi algılama hatası: {str(e)}")
            return None
    
    @staticmethod
    def _detect_p4001_format(file_path):
        """
        P4001 (Depo yöneticisi) formatını algılar
        
        P4001 formatı özellikleri:
        - İlk satırda otel adı (örn: MERIT ROYAL DIAMOND)
        - 2. satırda rapor tipi (P4001 Guests in house, P4001 Arrivals)
        - 8. satırda (index 7) header: R.No, R.Typ, Arrival, Departure, Adl
        - 9. satırda (index 8) tarih bilgisi: "Arrival :01.12.2025", "Date: 01.12.2025"
        - 10. satırdan (index 9) itibaren veri
        - Aralarda "(continued)" satırları olabilir
        
        Dosya tipi algılama önceliği:
        1. Önce verilerdeki tarihlere göre akıllı algılama
        2. Eğer belirlenemezse header pattern'lerine göre algılama
        
        Returns:
            dict: {'is_p4001': bool, 'dosya_tipi': str, 'rapor_tarihi': date, ...}
        """
        try:
            # pandas ile oku (xls desteği için)
            df = pd.read_excel(file_path, header=None, nrows=15)
            
            if len(df) < 10:
                return {'is_p4001': False}
            
            # Satır 8'de (index 7) P4001 header'ları var mı kontrol et
            row7 = df.iloc[7].tolist()
            row7_str = [str(x).strip() if pd.notna(x) else '' for x in row7]
            
            # P4001 header kontrolü - R.No ve Adl sütunları var mı?
            has_rno = 'R.No' in row7_str
            has_adl = 'Adl' in row7_str
            
            if not (has_rno and has_adl):
                return {'is_p4001': False}
            
            # Satır 9'dan (index 8) rapor tarihini al (header pattern'den)
            row8 = df.iloc[8].tolist()
            row8_str = ' '.join([str(x) for x in row8 if pd.notna(x)])
            
            header_dosya_tipi = None
            rapor_tarihi = None
            
            for tip, pattern in ExcelProcessingService.P4001_TYPE_PATTERNS.items():
                match = re.search(pattern, row8_str, re.IGNORECASE)
                if match:
                    header_dosya_tipi = tip
                    tarih_str = match.group(1)
                    try:
                        rapor_tarihi = datetime.strptime(tarih_str, '%d.%m.%Y').date()
                    except ValueError:
                        pass
                    break
            
            # Veri satırlarını oku ve tarih bazlı akıllı algılama yap
            try:
                df_data = pd.read_excel(file_path, header=7)
                df_data = df_data.iloc[1:].reset_index(drop=True)  # İlk satırı atla (rapor tarihi)
                
                # Tarih bazlı akıllı algılama
                smart_dosya_tipi = ExcelProcessingService._detect_file_type_by_dates(
                    df_data, 'Arrival', 'Departure', rapor_tarihi
                )
                
                if smart_dosya_tipi:
                    dosya_tipi = smart_dosya_tipi
                    logger.info(f"✅ Tarih bazlı akıllı algılama: {dosya_tipi}")
                else:
                    dosya_tipi = header_dosya_tipi
                    logger.info(f"✅ Header bazlı algılama: {dosya_tipi}")
                    
            except Exception as e:
                logger.error(f"⚠️ Akıllı algılama hatası, header bazlı devam: {str(e)}")
                dosya_tipi = header_dosya_tipi

            logger.info(
                f"📋 P4001 Format algılandı: {dosya_tipi}, Rapor tarihi: {rapor_tarihi}"
            )
            
            return {
                'is_p4001': True,
                'dosya_tipi': dosya_tipi or 'in_house',
                'rapor_tarihi': rapor_tarihi,
                'header_row': 7,
                'data_start_row': 9
            }
            
        except Exception as e:
            logger.error(f"P4001 format algılama hatası: {str(e)}")
            return {'is_p4001': False}
    
    @staticmethod
    def _parse_p4001_date(date_value, rapor_tarihi=None):
        """
        P4001 formatındaki tarihi parse eder
        
        Formatlar: "1.12. 8:59:", "24.11 03:16", "3.12. 2:00:"
        
        Args:
            date_value: Tarih değeri
            rapor_tarihi: Rapor tarihi (yıl için referans)
            
        Returns:
            date: Parse edilmiş tarih veya None
        """
        if not date_value or pd.isna(date_value):
            return None
        
        # Zaten date/datetime ise
        if isinstance(date_value, date):
            return date_value if not isinstance(date_value, datetime) else date_value.date()
        
        if isinstance(date_value, datetime):
            return date_value.date()
        
        # String ise parse et
        date_str = str(date_value).strip()
        
        # Yılı belirle
        yil = rapor_tarihi.year if rapor_tarihi else get_kktc_now().year
        
        # P4001 formatları: "1.12. 8:59:", "24.11 03:16", "3.12. 2:00:"
        patterns = [
            r'(\d{1,2})\.(\d{1,2})\.\s*\d{1,2}:\d{1,2}',  # 1.12. 8:59:
            r'(\d{1,2})\.(\d{1,2})\s+\d{1,2}:\d{1,2}',    # 24.11 03:16
            r'(\d{1,2})\.(\d{1,2})\.',                     # 1.12.
        ]
        
        for pattern in patterns:
            match = re.match(pattern, date_str)
            if match:
                gun = int(match.group(1))
                ay = int(match.group(2))
                
                # Yıl geçişi kontrolü (Aralık -> Ocak)
                if rapor_tarihi:
                    if rapor_tarihi.month == 12 and ay == 1:
                        yil = rapor_tarihi.year + 1
                    elif rapor_tarihi.month == 1 and ay == 12:
                        yil = rapor_tarihi.year - 1
                
                try:
                    return date(yil, ay, gun)
                except ValueError:
                    continue
        
        # Standart formatları dene
        return ExcelProcessingService.parse_date(date_value)
    
    @staticmethod
    def _process_p4001_file(file_path, islem_kodu, user_id, otel_id, p4001_info):
        """
        P4001 (depo yöneticisi) formatındaki Excel dosyasını işler
        
        Args:
            file_path: Dosya yolu
            islem_kodu: Benzersiz işlem kodu
            user_id: Yükleyen kullanıcı ID
            otel_id: Otel ID
            p4001_info: Format bilgileri
            
        Returns:
            dict: İşlem sonucu
        """
        try:
            dosya_tipi = p4001_info['dosya_tipi']
            rapor_tarihi = p4001_info['rapor_tarihi']
            
            # Kayıt tipini belirle
            if dosya_tipi == 'arrivals':
                kayit_tipi = 'arrival'
            elif dosya_tipi == 'departures':
                kayit_tipi = 'departure'
            else:
                kayit_tipi = 'in_house'
            
            # pandas ile oku - header satır 8 (index 7)
            df = pd.read_excel(file_path, header=7)
            
            # İlk satırı atla (rapor tarihi satırı)
            df = df.iloc[1:].reset_index(drop=True)
            
            # Gerekli sütunlar var mı kontrol et
            required_cols = ['R.No', 'Arrival', 'Departure', 'Adl']
            missing_cols = [col for col in required_cols if col not in df.columns]
            
            if missing_cols:
                return {
                    'success': False,
                    'error': f'Gerekli sütunlar bulunamadı: {missing_cols}',
                    'dosya_tipi': dosya_tipi,
                    'toplam_satir': 0,
                    'basarili_satir': 0,
                    'hatali_satir': 0,
                    'hatalar': []
                }
            
            toplam_satir = 0
            basarili_satir = 0
            hatali_satir = 0
            hatalar = []
            
            for idx, row in df.iterrows():
                # Oda numarası boşsa atla (2. misafir adı satırları)
                oda_no = row.get('R.No')
                if pd.isna(oda_no) or str(oda_no).strip() == '':
                    continue
                
                # "(continued)" ve tarih satırlarını atla
                first_col = str(df.iloc[idx, 0]) if pd.notna(df.iloc[idx, 0]) else ""  # type: ignore[call-overload]
                if 'continued' in first_col.lower():
                    continue
                if re.search(r'(Arrival|Departure|Date)\s*:', first_col, re.IGNORECASE):
                    continue
                
                toplam_satir += 1
                excel_row = idx + 10  # Excel satır numarası  # type: ignore[operator]

                try:
                    oda_no_str = str(int(oda_no) if isinstance(oda_no, float) else oda_no).strip()
                    
                    # Tarihleri parse et
                    giris_raw = row.get('Arrival')
                    cikis_raw = row.get('Departure')
                    
                    giris_tarihi = ExcelProcessingService._parse_p4001_date(giris_raw, rapor_tarihi)
                    cikis_tarihi = ExcelProcessingService._parse_p4001_date(cikis_raw, rapor_tarihi)
                    
                    if not giris_tarihi:
                        hatali_satir += 1
                        hatalar.append(f"Satır {excel_row}: Geçersiz giriş tarihi '{giris_raw}'")
                        continue
                    
                    if not cikis_tarihi:
                        hatali_satir += 1
                        hatalar.append(f"Satır {excel_row}: Geçersiz çıkış tarihi '{cikis_raw}'")
                        continue
                    
                    # Misafir sayısı
                    misafir_sayisi_raw = row.get('Adl')
                    try:
                        misafir_sayisi = int(misafir_sayisi_raw) if pd.notna(misafir_sayisi_raw) else 1
                        if misafir_sayisi <= 0:
                            misafir_sayisi = 1
                    except (ValueError, TypeError):
                        misafir_sayisi = 1
                    
                    # Tarih sırası kontrolü
                    if giris_tarihi >= cikis_tarihi:
                        hatali_satir += 1
                        hatalar.append(f"Satır {excel_row}: Giriş tarihi çıkış tarihinden önce olmalı")
                        continue
                    
                    # Odayı bul
                    oda = ExcelProcessingService.get_or_create_oda(oda_no_str, otel_id)
                    
                    if not oda:
                        hatali_satir += 1
                        hatalar.append(f"Satır {excel_row}: Oda '{oda_no_str}' bulunamadı")
                        continue
                    
                    # Duplicate kontrolü - kayıt tipini de kontrol et
                    mevcut_kayit = MisafirKayit.query.filter(
                        MisafirKayit.oda_id == oda.id,
                        db.func.date(MisafirKayit.giris_tarihi) == giris_tarihi,
                        db.func.date(MisafirKayit.cikis_tarihi) == cikis_tarihi,
                        MisafirKayit.kayit_tipi == kayit_tipi  # Kayıt tipini de kontrol et
                    ).first()
                    
                    if mevcut_kayit:
                        hatali_satir += 1
                        hatalar.append(f"Satır {excel_row}: Oda {oda_no_str} için {kayit_tipi} kaydı zaten mevcut (Duplicate)")
                        continue
                    
                    # MisafirKayit oluştur
                    misafir_kayit = MisafirKayit(
                        oda_id=oda.id,
                        islem_kodu=islem_kodu,
                        misafir_sayisi=misafir_sayisi,
                        giris_tarihi=giris_tarihi,
                        cikis_tarihi=cikis_tarihi,
                        kayit_tipi=kayit_tipi,
                        olusturan_id=user_id
                    )
                    
                    db.session.add(misafir_kayit)
                    basarili_satir += 1
                    
                except Exception as e:
                    hatali_satir += 1
                    hatalar.append(f"Satır {excel_row}: {str(e)}")
                    continue
            
            # Toplu kaydet
            db.session.commit()
            
            # Görevlendirme hook'u
            try:
                ExcelProcessingService._create_tasks_after_upload(
                    otel_id=otel_id,
                    dosya_tipi=dosya_tipi,
                    basarili_satir=basarili_satir
                )
            except Exception as hook_error:
                logger.error(f"Görev oluşturma hook hatası: {str(hook_error)}")
            
            return {
                'success': True,
                'dosya_tipi': dosya_tipi,
                'format': 'P4001',
                'rapor_tarihi': rapor_tarihi.strftime('%d.%m.%Y') if rapor_tarihi else None,
                'toplam_satir': toplam_satir,
                'basarili_satir': basarili_satir,
                'hatali_satir': hatali_satir,
                'hatalar': hatalar[:50]
            }
            
        except Exception as e:
            db.session.rollback()
            return {
                'success': False,
                'error': f'P4001 Excel işleme hatası: {str(e)}',
                'dosya_tipi': p4001_info.get('dosya_tipi'),
                'toplam_satir': 0,
                'basarili_satir': 0,
                'hatali_satir': 0,
                'hatalar': [str(e), traceback.format_exc()]
            }
