"""
Dashboard Route'ları

Bu modül tüm kullanıcı rollerine ait dashboard endpoint'lerini içerir.

Endpoint'ler:
- /dashboard - Rol bazlı yönlendirme
- /sistem-yoneticisi - Sistem yöneticisi dashboard
- /depo - Depo sorumlusu dashboard
- /kat-sorumlusu - Kat sorumlusu dashboard
- /kat-sorumlusu/dashboard - Kat sorumlusu dashboard (alternatif)

Roller:
- sistem_yoneticisi
- admin
- depo_sorumlusu
- kat_sorumlusu
"""

from flask import render_template, redirect, url_for, flash, session
from datetime import datetime, timedelta

from models import db, Kat, Oda, Kullanici, UrunGrup, Urun, StokHareket, PersonelZimmet, PersonelZimmetDetay, MinibarIslem, MinibarIslemDetay
from utils.decorators import login_required, role_required
from utils.helpers import get_kritik_stok_urunler, get_tum_urunler_stok_durumlari, get_kat_sorumlusu_kritik_stoklar

# Dashboard bildirim servisini import et
try:
    from utils.dashboard_servisleri import DashboardBildirimServisi
except ImportError:
    DashboardBildirimServisi = None


def register_dashboard_routes(app):
    """Dashboard route'larını kaydet"""
    
    @app.route('/dashboard')
    @login_required
    def dashboard():
        """Rol bazlı dashboard yönlendirmesi"""
        rol = session.get('rol')
        
        if rol == 'sistem_yoneticisi':
            return redirect(url_for('sistem_yoneticisi_dashboard'))
        elif rol == 'admin':
            return redirect(url_for('sistem_yoneticisi_dashboard'))  # Admin de sistem yöneticisi panelini kullanır
        elif rol == 'depo_sorumlusu':
            return redirect(url_for('depo_dashboard'))
        elif rol == 'kat_sorumlusu':
            return redirect(url_for('kat_sorumlusu_dashboard'))
        else:
            flash('Geçersiz kullanıcı rolü!', 'danger')
            return redirect(url_for('logout'))

    
    @app.route('/sistem-yoneticisi')
    @login_required
    @role_required('sistem_yoneticisi', 'admin')
    def sistem_yoneticisi_dashboard():
        """Sistem yöneticisi dashboard"""
        try:
            from utils.occupancy_service import OccupancyService
            from utils.authorization import get_kullanici_otelleri
            from datetime import date
            import os
            
            # ML Alertleri (ML_ENABLED ise)
            ml_alerts = []
            ml_alert_count = 0
            ml_enabled = os.getenv('ML_ENABLED', 'false').lower() == 'true'
            
            if ml_enabled:
                try:
                    from models import MLAlert
                    from utils.ml.alert_manager import AlertManager
                
                    alert_manager = AlertManager(db)
                    # Son 5 kritik/yüksek alert
                    ml_alerts = alert_manager.get_active_alerts(limit=5)
                    ml_alert_count = len(alert_manager.get_active_alerts())
                except Exception as e:
                    print(f"ML alert hatası: {str(e)}")
        
            # Tüm oteller için doluluk raporları
            otel_doluluk_raporlari = []
            try:
                kullanici_otelleri = get_kullanici_otelleri()
                for otel in kullanici_otelleri:
                    doluluk = OccupancyService.get_gunluk_doluluk_raporu(date.today(), otel.id)
                    # Doluluk oranı hesapla
                    if doluluk['toplam_oda'] > 0:
                        doluluk['doluluk_orani'] = round((doluluk['dolu_oda'] / doluluk['toplam_oda']) * 100)
                    else:
                        doluluk['doluluk_orani'] = 0
                
                    # Otel bilgilerini ekle
                    doluluk['otel'] = otel
                    otel_doluluk_raporlari.append(doluluk)
            except Exception as e:
                print(f"Doluluk raporları hatası: {str(e)}")
        
            # İstatistikler
            toplam_kat = Kat.query.count()
            toplam_oda = Oda.query.count()
            toplam_kullanici = Kullanici.query.filter(
                Kullanici.rol.in_(['admin', 'depo_sorumlusu', 'kat_sorumlusu']),
                Kullanici.aktif.is_(True)
            ).count()
            toplam_personel = Kullanici.query.filter(
                Kullanici.rol.in_(['depo_sorumlusu', 'kat_sorumlusu']),
                Kullanici.aktif.is_(True)
            ).count()
        
            # Son eklenen katlar
            son_katlar = Kat.query.order_by(Kat.olusturma_tarihi.desc()).limit(5).all()
        
            # Son eklenen odalar
            son_odalar = Oda.query.order_by(Oda.olusturma_tarihi.desc()).limit(5).all()
        
            # Grafik verileri
            # Kullanıcı rol dağılımı
            admin_count = Kullanici.query.filter_by(rol='admin', aktif=True).count()
            depo_count = Kullanici.query.filter_by(rol='depo_sorumlusu', aktif=True).count()
            kat_count = Kullanici.query.filter_by(rol='kat_sorumlusu', aktif=True).count()
        
            # Kat bazlı oda sayıları
            katlar = Kat.query.filter_by(aktif=True).all()
            kat_labels = [kat.kat_adi for kat in katlar]
            kat_oda_sayilari = [len(kat.odalar) for kat in katlar]
        
            # Ürün grup sayıları (admin için)
            toplam_urun_grup = UrunGrup.query.filter_by(aktif=True).count()
            toplam_urun = Urun.query.filter_by(aktif=True).count()
            kritik_urunler = get_kritik_stok_urunler()
        
            # Gelişmiş stok durumları
            try:
                stok_durumlari = get_tum_urunler_stok_durumlari()
            except Exception as e:
                print(f"Stok durumları hatası: {str(e)}")
                flash(f'Stok durumları yüklenirken hata oluştu: {str(e)}', 'warning')
                stok_durumlari = {
                    'kritik': [],
                    'dikkat': [],
                    'normal': [],
                    'istatistik': {
                        'toplam': 0,
                        'kritik_sayi': 0,
                        'dikkat_sayi': 0,
                        'normal_sayi': 0
                    }
                }
        
            # Son eklenen personeller (admin için)
            son_personeller = Kullanici.query.filter(
                Kullanici.rol.in_(['depo_sorumlusu', 'kat_sorumlusu']),
                Kullanici.aktif.is_(True)
            ).order_by(Kullanici.olusturma_tarihi.desc()).limit(5).all()
        
            # Son eklenen ürünler (admin için)
            son_urunler = Urun.query.filter_by(aktif=True).order_by(Urun.olusturma_tarihi.desc()).limit(5).all()
        
            # Dashboard bildirimleri (Satın Alma Modülü)
            dashboard_bildirimleri = []
            bildirim_sayilari = {
                'kritik_stok': 0,
                'geciken_siparis': 0,
                'onay_bekleyen': 0,
                'toplam': 0
            }
            if DashboardBildirimServisi:
                try:
                    kullanici_id = session.get('kullanici_id')
                    dashboard_bildirimleri = DashboardBildirimServisi.get_dashboard_bildirimleri(
                        kullanici_id, 'sistem_yoneticisi'
                    )
                    bildirim_sayilari = DashboardBildirimServisi.get_bildirim_sayilari(
                        kullanici_id, 'sistem_yoneticisi'
                    )
                except Exception as e:
                    print(f"Dashboard bildirimleri hatası: {str(e)}")
                    db.session.rollback()  # Transaction'ı temizle
        
            # Sipariş istatistikleri
            from models import SatinAlmaSiparisi
            istatistikler = {
                'onaylandi': 0
            }
            try:
                istatistikler['onaylandi'] = SatinAlmaSiparisi.query.filter_by(durum='onaylandi').count()
            except Exception as e:
                print(f"Sipariş istatistikleri hatası: {str(e)}")
                db.session.rollback()
        
            # Ürün bazlı tüketim verileri (Son 30 günün en çok tüketilen ürünleri)
            urun_labels = []
            urun_tuketim_miktarlari = []
            try:
                bugun = datetime.now().date()
                otuz_gun_once = bugun - timedelta(days=30)
            
                # Minibar işlemlerinden en çok tüketilen ürünleri al
                urun_tuketim = db.session.query(
                    Urun.urun_adi,
                    db.func.sum(MinibarIslemDetay.tuketim).label('toplam_tuketim')
                ).join(
                    MinibarIslemDetay, MinibarIslemDetay.urun_id == Urun.id
                ).join(
                    MinibarIslem, MinibarIslem.id == MinibarIslemDetay.islem_id
                ).filter(
                    db.func.date(MinibarIslem.islem_tarihi) >= otuz_gun_once,
                    MinibarIslemDetay.tuketim > 0
                ).group_by(
                    Urun.id, Urun.urun_adi
                ).order_by(
                    db.desc('toplam_tuketim')
                ).limit(10).all()
            
                urun_labels = [u[0] for u in urun_tuketim]
                urun_tuketim_miktarlari = [float(u[1] or 0) for u in urun_tuketim]
            except Exception as e:
                print(f"Ürün tüketim verileri hatası: {str(e)}")
                db.session.rollback()  # Transaction'ı temizle
        
            # Günlük Yükleme Görev Özeti (Sistem Yöneticisi için)
            yukleme_gorev_ozeti = None
            try:
                from models import YuklemeGorev
                kullanici_otelleri = get_kullanici_otelleri()
                otel_ids = [o.id for o in kullanici_otelleri] if kullanici_otelleri else []
                
                if otel_ids:
                    # Bugünkü yükleme görevlerini kontrol et
                    inhouse_gorev = YuklemeGorev.query.filter(
                        YuklemeGorev.otel_id.in_(otel_ids),
                        db.func.date(YuklemeGorev.gorev_tarihi) == bugun,
                        YuklemeGorev.dosya_tipi == 'inhouse'
                    ).first()
                    
                    arrivals_gorev = YuklemeGorev.query.filter(
                        YuklemeGorev.otel_id.in_(otel_ids),
                        db.func.date(YuklemeGorev.gorev_tarihi) == bugun,
                        YuklemeGorev.dosya_tipi == 'arrivals'
                    ).first()
                    
                    departures_gorev = YuklemeGorev.query.filter(
                        YuklemeGorev.otel_id.in_(otel_ids),
                        db.func.date(YuklemeGorev.gorev_tarihi) == bugun,
                        YuklemeGorev.dosya_tipi == 'departures'
                    ).first()
                    
                    tamamlanan = 0
                    inhouse_durum = 'pending'
                    arrivals_durum = 'pending'
                    departures_durum = 'pending'
                    
                    if inhouse_gorev and inhouse_gorev.durum == 'completed':
                        tamamlanan += 1
                        inhouse_durum = 'completed'
                    
                    if arrivals_gorev and arrivals_gorev.durum == 'completed':
                        tamamlanan += 1
                        arrivals_durum = 'completed'
                    
                    if departures_gorev and departures_gorev.durum == 'completed':
                        tamamlanan += 1
                        departures_durum = 'completed'
                    
                    yukleme_gorev_ozeti = {
                        'toplam': 3,
                        'tamamlanan': tamamlanan,
                        'bekleyen': 3 - tamamlanan,
                        'tamamlanma_orani': int((tamamlanan / 3) * 100),
                        'inhouse_durum': inhouse_durum,
                        'arrivals_durum': arrivals_durum,
                        'departures_durum': departures_durum
                    }
            except Exception as e:
                print(f"Sistem yöneticisi yükleme görev özeti hatası: {str(e)}")
            
            # Kat Sorumlusu Görevleri Özeti (Sistem Yöneticisi için)
            kat_sorumlusu_gorev_ozeti = None
            try:
                from models import GunlukGorev
                kullanici_otelleri = get_kullanici_otelleri()
                otel_ids = [o.id for o in kullanici_otelleri] if kullanici_otelleri else []
                
                if otel_ids:
                    # Bugünkü görevleri say - GunlukGorev üzerinden
                    bugun_gorevler = GunlukGorev.query.filter(
                        GunlukGorev.otel_id.in_(otel_ids),
                        db.func.date(GunlukGorev.gorev_tarihi) == bugun
                    ).all()
                    
                    toplam_gorev = len(bugun_gorevler)
                    tamamlanan_gorev = len([g for g in bugun_gorevler if g.durum == 'completed'])
                    bekleyen_gorev = len([g for g in bugun_gorevler if g.durum == 'pending'])
                    devam_eden = len([g for g in bugun_gorevler if g.durum == 'in_progress'])
                    dnd_gorev = len([g for g in bugun_gorevler if g.durum == 'dnd_pending'])
                    
                    # Görev tiplerine göre say
                    inhouse = len([g for g in bugun_gorevler if g.gorev_tipi == 'inhouse_kontrol'])
                    arrival = len([g for g in bugun_gorevler if g.gorev_tipi == 'arrival_kontrol'])
                    departure = len([g for g in bugun_gorevler if g.gorev_tipi == 'departure_kontrol'])
                    
                    inhouse_tamamlanan = len([g for g in bugun_gorevler if g.gorev_tipi == 'inhouse_kontrol' and g.durum == 'completed'])
                    arrival_tamamlanan = len([g for g in bugun_gorevler if g.gorev_tipi == 'arrival_kontrol' and g.durum == 'completed'])
                    departure_tamamlanan = len([g for g in bugun_gorevler if g.gorev_tipi == 'departure_kontrol' and g.durum == 'completed'])
                    
                    kat_sorumlusu_gorev_ozeti = {
                        'toplam': toplam_gorev,
                        'tamamlanan': tamamlanan_gorev,
                        'bekleyen': bekleyen_gorev,
                        'devam_eden': devam_eden,
                        'dnd': dnd_gorev,
                        'tamamlanma_orani': int((tamamlanan_gorev / toplam_gorev) * 100) if toplam_gorev > 0 else 0,
                        'inhouse': {'toplam': inhouse, 'tamamlanan': inhouse_tamamlanan},
                        'arrival': {'toplam': arrival, 'tamamlanan': arrival_tamamlanan},
                        'departure': {'toplam': departure, 'tamamlanan': departure_tamamlanan}
                    }
            except Exception as e:
                print(f"Kat sorumlusu görev özeti hatası: {str(e)}")
            
            return render_template('sistem_yoneticisi/dashboard.html',
                                 otel_doluluk_raporlari=otel_doluluk_raporlari,
                                 toplam_kat=toplam_kat,
                                 toplam_oda=toplam_oda,
                                 toplam_kullanici=toplam_kullanici,
                                 toplam_personel=toplam_personel,
                                 son_katlar=son_katlar,
                                 son_odalar=son_odalar,
                                 admin_count=admin_count,
                                 depo_count=depo_count,
                                 kat_count=kat_count,
                                 kat_labels=kat_labels,
                                 kat_oda_sayilari=kat_oda_sayilari,
                                 toplam_urun_grup=toplam_urun_grup,
                                 toplam_urun=toplam_urun,
                                 kritik_urunler=kritik_urunler,
                                 stok_durumlari=stok_durumlari,
                                 son_personeller=son_personeller,
                                 son_urunler=son_urunler,
                                 urun_labels=urun_labels,
                                 urun_tuketim_miktarlari=urun_tuketim_miktarlari,
                                 ml_enabled=ml_enabled,
                                 ml_alerts=ml_alerts,
                                 ml_alert_count=ml_alert_count,
                                 dashboard_bildirimleri=dashboard_bildirimleri,
                                 bildirim_sayilari=bildirim_sayilari,
                                 istatistikler=istatistikler,
                                 yukleme_gorev_ozeti=yukleme_gorev_ozeti,
                                 kat_sorumlusu_gorev_ozeti=kat_sorumlusu_gorev_ozeti)
        except Exception as e:
            print(f"Sistem yöneticisi dashboard hatası: {str(e)}")
            import traceback
            traceback.print_exc()
            flash(f'Dashboard yüklenirken hata oluştu: {str(e)}', 'danger')
            # Minimal dashboard göster
            return render_template('sistem_yoneticisi/dashboard.html',
                                 otel_doluluk_raporlari=[],
                                 toplam_kat=0,
                                 toplam_oda=0,
                                 toplam_kullanici=0,
                                 toplam_personel=0,
                                 son_katlar=[],
                                 son_odalar=[],
                                 admin_count=0,
                                 depo_count=0,
                                 kat_count=0,
                                 kat_labels=[],
                                 kat_oda_sayilari=[],
                                 toplam_urun_grup=0,
                                 toplam_urun=0,
                                 kritik_urunler=[],
                                 stok_durumlari={'kritik': [], 'dikkat': [], 'normal': [], 'istatistik': {'toplam': 0, 'kritik_sayi': 0, 'dikkat_sayi': 0, 'normal_sayi': 0}},
                                 son_personeller=[],
                                 son_urunler=[],
                                 urun_labels=[],
                                 urun_tuketim_miktarlari=[],
                                 ml_enabled=False,
                                 ml_alerts=[],
                                 ml_alert_count=0,
                                 dashboard_bildirimleri=[],
                                 bildirim_sayilari={'kritik_stok': 0, 'geciken_siparis': 0, 'onay_bekleyen': 0, 'toplam': 0},
                                 istatistikler={'onaylandi': 0},
                                 yukleme_gorev_ozeti=None,
                                 kat_sorumlusu_gorev_ozeti=None)

    
    @app.route('/depo')
    @login_required
    @role_required('depo_sorumlusu')
    def depo_dashboard():
        """Depo sorumlusu dashboard"""
        from utils.occupancy_service import OccupancyService
        from utils.authorization import get_kullanici_otelleri
        
        # Depo sorumlusunun atandığı otelleri al
        atanan_oteller = get_kullanici_otelleri()
        
        # Her otel için bugünkü doluluk bilgilerini al
        otel_doluluk_bilgileri = []
        bugun = datetime.now().date()
        
        for otel in atanan_oteller:
            doluluk_raporu = OccupancyService.get_gunluk_doluluk_raporu(bugun, otel.id)
            doluluk_orani = round((doluluk_raporu['dolu_oda'] / doluluk_raporu['toplam_oda'] * 100) if doluluk_raporu['toplam_oda'] > 0 else 0, 1)
            
            # Logo'yu kullan (boyut kontrolü kaldırıldı - template'de handle edilecek)
            logo = otel.logo
            
            otel_doluluk_bilgileri.append({
                'otel_id': otel.id,
                'otel_ad': otel.ad,
                'otel_logo': logo,
                'toplam_oda': doluluk_raporu['toplam_oda'],
                'dolu_oda': doluluk_raporu['dolu_oda'],
                'bos_oda': doluluk_raporu['bos_oda'],
                'doluluk_orani': doluluk_orani
            })
        
        # İstatistikler
        toplam_urun = Urun.query.filter_by(aktif=True).count()
        kritik_urunler = get_kritik_stok_urunler()
        aktif_zimmetler = PersonelZimmet.query.filter_by(durum='aktif').count()
        
        # Gelişmiş stok durumları
        try:
            stok_durumlari = get_tum_urunler_stok_durumlari()
        except Exception as e:
            print(f"Stok durumları hatası: {str(e)}")
            flash(f'Stok durumları yüklenirken hata oluştu: {str(e)}', 'warning')
            stok_durumlari = {
                'kritik': [],
                'dikkat': [],
                'normal': [],
                'istatistik': {
                    'toplam': 0,
                    'kritik_sayi': 0,
                    'dikkat_sayi': 0,
                    'normal_sayi': 0
                }
            }
        
        # Zimmet iade istatistikleri
        toplam_iade_edilen = db.session.query(db.func.sum(PersonelZimmetDetay.iade_edilen_miktar)).filter(
            PersonelZimmetDetay.iade_edilen_miktar > 0
        ).scalar() or 0
        
        # Bu ay yapılan iade işlemleri
        ay_basi = datetime.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        bu_ay_iadeler = StokHareket.query.filter(
            StokHareket.hareket_tipi == 'giris',
            StokHareket.aciklama.like('%Zimmet iadesi%'),
            StokHareket.islem_tarihi >= ay_basi
        ).count()
        
        # İptal edilen zimmetler
        iptal_zimmetler = PersonelZimmet.query.filter_by(durum='iptal').count()
        
        # Son stok hareketleri
        son_hareketler = StokHareket.query.order_by(StokHareket.islem_tarihi.desc()).limit(10).all()
        
        # Grafik verileri
        # Ürün grup bazlı stok durumu
        gruplar = UrunGrup.query.filter_by(aktif=True).all()
        grup_labels = []
        grup_stok_miktarlari = []
        
        for grup in gruplar:
            urunler = Urun.query.filter_by(grup_id=grup.id, aktif=True).all()
            toplam_stok = 0
            for urun in urunler:
                # Mevcut stok hesapla
                giris = db.session.query(db.func.sum(StokHareket.miktar)).filter(
                    StokHareket.urun_id == urun.id,
                    StokHareket.hareket_tipi == 'giris'
                ).scalar() or 0
                cikis = db.session.query(db.func.sum(StokHareket.miktar)).filter(
                    StokHareket.urun_id == urun.id,
                    StokHareket.hareket_tipi == 'cikis'
                ).scalar() or 0
                toplam_stok += (giris - cikis)
            
            if toplam_stok > 0:  # Sadece stoku olan grupları göster
                grup_labels.append(grup.grup_adi)
                grup_stok_miktarlari.append(toplam_stok)
        
        # Son 7 günün stok hareket istatistikleri
        bugun = datetime.now().date()
        gun_labels = []
        giris_verileri = []
        cikis_verileri = []
        
        for i in range(6, -1, -1):  # Son 7 gün
            tarih = bugun - timedelta(days=i)
            gun_labels.append(tarih.strftime('%d.%m'))
            
            # Giriş
            giris = db.session.query(db.func.sum(StokHareket.miktar)).filter(
                db.func.date(StokHareket.islem_tarihi) == tarih,
                StokHareket.hareket_tipi == 'giris'
            ).scalar() or 0
            giris_verileri.append(float(giris))
            
            # Çıkış
            cikis = db.session.query(db.func.sum(StokHareket.miktar)).filter(
                db.func.date(StokHareket.islem_tarihi) == tarih,
                StokHareket.hareket_tipi == 'cikis'
            ).scalar() or 0
            cikis_verileri.append(float(cikis))
        
        # Dashboard bildirimleri (Satın Alma Modülü)
        dashboard_bildirimleri = []
        bildirim_sayilari = {
            'kritik_stok': 0,
            'geciken_siparis': 0,
            'onay_bekleyen': 0,
            'toplam': 0
        }
        if DashboardBildirimServisi and atanan_oteller:
            try:
                kullanici_id = session.get('kullanici_id')
                # İlk atanan otel için bildirimleri al
                otel_id = atanan_oteller[0].id
                dashboard_bildirimleri = DashboardBildirimServisi.get_dashboard_bildirimleri(
                    kullanici_id, 'depo_sorumlusu', otel_id
                )
                bildirim_sayilari = DashboardBildirimServisi.get_bildirim_sayilari(
                    kullanici_id, 'depo_sorumlusu', otel_id
                )
            except Exception as e:
                print(f"Dashboard bildirimleri hatası: {str(e)}")
        
        # Ürün bazlı tüketim verileri (Son 30 günün en çok tüketilen ürünleri)
        otuz_gun_once = bugun - timedelta(days=30)
        
        # Minibar işlemlerinden en çok tüketilen ürünleri al
        urun_tuketim = db.session.query(
            Urun.urun_adi,
            db.func.sum(MinibarIslemDetay.tuketim).label('toplam_tuketim')
        ).join(
            MinibarIslemDetay, MinibarIslemDetay.urun_id == Urun.id
        ).join(
            MinibarIslem, MinibarIslem.id == MinibarIslemDetay.islem_id
        ).filter(
            db.func.date(MinibarIslem.islem_tarihi) >= otuz_gun_once,
            MinibarIslemDetay.tuketim > 0
        ).group_by(
            Urun.id, Urun.urun_adi
        ).order_by(
            db.desc('toplam_tuketim')
        ).limit(10).all()
        
        urun_labels = [u[0] for u in urun_tuketim]
        urun_tuketim_miktarlari = [float(u[1] or 0) for u in urun_tuketim]
        
        # Yükleme görev özeti
        yukleme_gorev_ozeti = {'toplam': 3, 'tamamlanan': 0, 'bekleyen': 3, 'tamamlanma_orani': 0, 'inhouse_durum': 'pending', 'arrivals_durum': 'pending', 'departures_durum': 'pending'}
        try:
            from models import YuklemeGorev
            from datetime import date
            
            bugun = date.today()
            kullanici_id = session.get('kullanici_id')
            
            # Bugünkü yükleme görevlerini al
            inhouse_gorev = YuklemeGorev.query.filter(
                YuklemeGorev.depo_sorumlusu_id == kullanici_id,
                YuklemeGorev.gorev_tarihi == bugun,
                YuklemeGorev.dosya_tipi == 'inhouse'
            ).first()
            
            arrivals_gorev = YuklemeGorev.query.filter(
                YuklemeGorev.depo_sorumlusu_id == kullanici_id,
                YuklemeGorev.gorev_tarihi == bugun,
                YuklemeGorev.dosya_tipi == 'arrivals'
            ).first()
            
            departures_gorev = YuklemeGorev.query.filter(
                YuklemeGorev.depo_sorumlusu_id == kullanici_id,
                YuklemeGorev.gorev_tarihi == bugun,
                YuklemeGorev.dosya_tipi == 'departures'
            ).first()
            
            tamamlanan = 0
            inhouse_durum = 'pending'
            arrivals_durum = 'pending'
            departures_durum = 'pending'
            
            if inhouse_gorev and inhouse_gorev.durum == 'completed':
                tamamlanan += 1
                inhouse_durum = 'completed'
            
            if arrivals_gorev and arrivals_gorev.durum == 'completed':
                tamamlanan += 1
                arrivals_durum = 'completed'
            
            if departures_gorev and departures_gorev.durum == 'completed':
                tamamlanan += 1
                departures_durum = 'completed'
            
            yukleme_gorev_ozeti = {
                'toplam': 3,
                'tamamlanan': tamamlanan,
                'bekleyen': 3 - tamamlanan,
                'tamamlanma_orani': int((tamamlanan / 3) * 100),
                'inhouse_durum': inhouse_durum,
                'arrivals_durum': arrivals_durum,
                'departures_durum': departures_durum
            }
        except Exception as e:
            print(f"Yükleme görev özeti hatası: {str(e)}")
        
        # Oda kontrol görevleri özeti (tüm yüklemeler tamamlandığında göster)
        oda_kontrol_ozeti = None
        try:
            if yukleme_gorev_ozeti and yukleme_gorev_ozeti.get('tamamlanma_orani') == 100:
                from models import GunlukGorev
                from utils.authorization import get_kullanici_otelleri
                
                kullanici_otelleri = get_kullanici_otelleri()
                otel_ids = [o.id for o in kullanici_otelleri] if kullanici_otelleri else []
                
                if otel_ids:
                    # Bugünkü görevleri say - GunlukGorev üzerinden
                    bugun_gorevler = GunlukGorev.query.filter(
                        GunlukGorev.otel_id.in_(otel_ids),
                        db.func.date(GunlukGorev.gorev_tarihi) == bugun
                    ).all()
                    
                    toplam = len(bugun_gorevler)
                    tamamlanan_gorev = len([g for g in bugun_gorevler if g.durum == 'completed'])
                    bekleyen_gorev = len([g for g in bugun_gorevler if g.durum == 'pending'])
                    devam_eden = len([g for g in bugun_gorevler if g.durum == 'in_progress'])
                    
                    # Görev tiplerine göre say
                    inhouse = len([g for g in bugun_gorevler if g.gorev_tipi == 'inhouse_kontrol'])
                    arrival = len([g for g in bugun_gorevler if g.gorev_tipi == 'arrival_kontrol'])
                    departure = len([g for g in bugun_gorevler if g.gorev_tipi == 'departure_kontrol'])
                    
                    inhouse_tamamlanan = len([g for g in bugun_gorevler if g.gorev_tipi == 'inhouse_kontrol' and g.durum == 'completed'])
                    arrival_tamamlanan = len([g for g in bugun_gorevler if g.gorev_tipi == 'arrival_kontrol' and g.durum == 'completed'])
                    departure_tamamlanan = len([g for g in bugun_gorevler if g.gorev_tipi == 'departure_kontrol' and g.durum == 'completed'])
                    
                    oda_kontrol_ozeti = {
                        'toplam': toplam,
                        'tamamlanan': tamamlanan_gorev,
                        'bekleyen': bekleyen_gorev,
                        'devam_eden': devam_eden,
                        'tamamlanma_orani': int((tamamlanan_gorev / toplam) * 100) if toplam > 0 else 0,
                        'inhouse': {'toplam': inhouse, 'tamamlanan': inhouse_tamamlanan},
                        'arrival': {'toplam': arrival, 'tamamlanan': arrival_tamamlanan},
                        'departure': {'toplam': departure, 'tamamlanan': departure_tamamlanan}
                    }
        except Exception as e:
            print(f"Oda kontrol özeti hatası: {str(e)}")
        
        return render_template('depo_sorumlusu/dashboard.html',
                             otel_doluluk_bilgileri=otel_doluluk_bilgileri,
                             toplam_urun=toplam_urun,
                             kritik_urunler=kritik_urunler,
                             stok_durumlari=stok_durumlari,
                             aktif_zimmetler=aktif_zimmetler,
                             toplam_iade_edilen=toplam_iade_edilen,
                             bu_ay_iadeler=bu_ay_iadeler,
                             iptal_zimmetler=iptal_zimmetler,
                             son_hareketler=son_hareketler,
                             grup_labels=grup_labels,
                             grup_stok_miktarlari=grup_stok_miktarlari,
                             gun_labels=gun_labels,
                             giris_verileri=giris_verileri,
                             cikis_verileri=cikis_verileri,
                             urun_labels=urun_labels,
                             urun_tuketim_miktarlari=urun_tuketim_miktarlari,
                             dashboard_bildirimleri=dashboard_bildirimleri,
                             bildirim_sayilari=bildirim_sayilari,
                             yukleme_gorev_ozeti=yukleme_gorev_ozeti,
                             oda_kontrol_ozeti=oda_kontrol_ozeti)

    
    @app.route('/kat-sorumlusu')
    @app.route('/kat-sorumlusu/dashboard')
    @login_required
    @role_required('kat_sorumlusu')
    def kat_sorumlusu_dashboard():
        """Kat sorumlusu dashboard"""
        from utils.occupancy_service import OccupancyService
        from utils.authorization import get_kullanici_otelleri
        from datetime import date
        
        kullanici_id = session['kullanici_id']
        
        # Görev özeti - Bugün için
        gorev_ozeti = None
        try:
            from utils.gorev_service import GorevService
            gorev_ozeti = GorevService.get_task_summary(kullanici_id, date.today())
        except Exception as e:
            print(f"Görev özeti hatası: {str(e)}")
            gorev_ozeti = {'toplam': 0, 'tamamlanan': 0, 'bekleyen': 0, 'dnd': 0, 'tamamlanma_orani': 0}
        
        # Doluluk raporu - Bugün için
        doluluk_raporu = None
        try:
            kullanici_otelleri = get_kullanici_otelleri()
            if kullanici_otelleri:
                otel_id = kullanici_otelleri[0].id
                doluluk_raporu = OccupancyService.get_gunluk_doluluk_raporu(date.today(), otel_id)
                # Doluluk oranı hesapla
                if doluluk_raporu['toplam_oda'] > 0:
                    doluluk_raporu['doluluk_orani'] = round((doluluk_raporu['dolu_oda'] / doluluk_raporu['toplam_oda']) * 100)
                else:
                    doluluk_raporu['doluluk_orani'] = 0
        except Exception as e:
            print(f"Doluluk raporu hatası: {str(e)}")
        
        # İstatistikler
        aktif_zimmetler = PersonelZimmet.query.filter_by(
            personel_id=kullanici_id, 
            durum='aktif'
        ).count()
        
        # Zimmetindeki toplam ürün miktarı
        zimmet_detaylari = db.session.query(
            db.func.sum(PersonelZimmetDetay.kalan_miktar)
        ).join(PersonelZimmet).filter(
            PersonelZimmet.personel_id == kullanici_id,
            PersonelZimmet.durum == 'aktif'
        ).scalar() or 0
        
        # Kritik stok bilgileri
        kritik_stoklar = get_kat_sorumlusu_kritik_stoklar(kullanici_id)
        kritik_stok_sayisi = kritik_stoklar['istatistik']['kritik_sayisi']
        stokout_sayisi = kritik_stoklar['istatistik']['stokout_sayisi']
        
        # Bugünkü kullanım (son 24 saat)
        bugun_baslangic = datetime.now() - timedelta(days=1)
        bugunun_kullanimi = db.session.query(
            db.func.sum(MinibarIslemDetay.eklenen_miktar)
        ).join(MinibarIslem).filter(
            MinibarIslem.personel_id == kullanici_id,
            MinibarIslem.islem_tarihi >= bugun_baslangic
        ).scalar() or 0
        
        # Son minibar işlemleri
        son_islemler = MinibarIslem.query.filter_by(
            personel_id=kullanici_id
        ).order_by(MinibarIslem.islem_tarihi.desc()).limit(10).all()
        
        # Grafik verileri - En çok kullanılan 5 ürün (son 7 gün)
        yedi_gun_once = datetime.now() - timedelta(days=7)
        en_cok_kullanilan = db.session.query(
            Urun.urun_adi,
            db.func.sum(MinibarIslemDetay.eklenen_miktar).label('toplam')
        ).join(MinibarIslemDetay, MinibarIslemDetay.urun_id == Urun.id).join(
            MinibarIslem, MinibarIslem.id == MinibarIslemDetay.islem_id
        ).filter(
            MinibarIslem.personel_id == kullanici_id,
            MinibarIslem.islem_tarihi >= yedi_gun_once
        ).group_by(Urun.id, Urun.urun_adi).order_by(
            db.desc('toplam')
        ).limit(5).all()
        
        en_cok_urun_labels = [u[0] for u in en_cok_kullanilan]
        en_cok_urun_miktarlar = [float(u[1] or 0) for u in en_cok_kullanilan]
        
        # Zimmet kullanım durumu (ürün bazlı)
        zimmet_urunler = db.session.query(
            Urun.urun_adi,
            db.func.sum(PersonelZimmetDetay.miktar).label('teslim_edilen'),
            db.func.sum(PersonelZimmetDetay.kullanilan_miktar).label('kullanilan'),
            db.func.sum(PersonelZimmetDetay.kalan_miktar).label('kalan')
        ).join(Urun, PersonelZimmetDetay.urun_id == Urun.id).join(
            PersonelZimmet, PersonelZimmetDetay.zimmet_id == PersonelZimmet.id
        ).filter(
            PersonelZimmet.personel_id == kullanici_id,
            PersonelZimmet.durum == 'aktif'
        ).group_by(Urun.id, Urun.urun_adi).all()
        
        zimmet_urun_labels = [u[0] for u in zimmet_urunler]
        zimmet_kullanilan = [float(u[2] or 0) for u in zimmet_urunler]
        zimmet_kalan = [float(u[3] or 0) for u in zimmet_urunler]
        
        # Günlük tüketim trendi (son 7 gün)
        gunluk_tuketim = []
        gunluk_labels = []
        for i in range(6, -1, -1):
            gun = datetime.now() - timedelta(days=i)
            gun_baslangic = gun.replace(hour=0, minute=0, second=0, microsecond=0)
            gun_bitis = gun_baslangic + timedelta(days=1)
            
            tuketim = db.session.query(
                db.func.sum(MinibarIslemDetay.eklenen_miktar)
            ).join(MinibarIslem).filter(
                MinibarIslem.personel_id == kullanici_id,
                MinibarIslem.islem_tarihi >= gun_baslangic,
                MinibarIslem.islem_tarihi < gun_bitis
            ).scalar() or 0
            
            gunluk_tuketim.append(float(tuketim))
            gunluk_labels.append(gun.strftime('%d.%m'))
        
        # Minibar işlem tipi dağılımı
        islem_ilk_dolum = MinibarIslem.query.filter_by(
            personel_id=kullanici_id,
            islem_tipi='ilk_dolum'
        ).count()
        islem_yeniden_dolum = MinibarIslem.query.filter_by(
            personel_id=kullanici_id,
            islem_tipi='yeniden_dolum'
        ).count()
        islem_eksik_tamamlama = MinibarIslem.query.filter_by(
            personel_id=kullanici_id,
            islem_tipi='eksik_tamamlama'
        ).count()
        
        return render_template('kat_sorumlusu/dashboard.html',
                             gorev_ozeti=gorev_ozeti,
                             doluluk_raporu=doluluk_raporu,
                             aktif_zimmetler=aktif_zimmetler,
                             zimmet_toplam=zimmet_detaylari,
                             kritik_stok_sayisi=kritik_stok_sayisi,
                             stokout_sayisi=stokout_sayisi,
                             bugunun_kullanimi=int(bugunun_kullanimi),
                             son_islemler=son_islemler,
                             en_cok_urun_labels=en_cok_urun_labels,
                             en_cok_urun_miktarlar=en_cok_urun_miktarlar,
                             zimmet_urun_labels=zimmet_urun_labels,
                             zimmet_kullanilan=zimmet_kullanilan,
                             zimmet_kalan=zimmet_kalan,
                             gunluk_tuketim=gunluk_tuketim,
                             gunluk_labels=gunluk_labels,
                             islem_ilk_dolum=islem_ilk_dolum,
                             islem_yeniden_dolum=islem_yeniden_dolum,
                             islem_eksik_tamamlama=islem_eksik_tamamlama)
