"""
Superadmin Routes

Superadmin rolüne özel endpoint'ler.
Tüm kullanıcıları görüntüleme, şifre hash'leri, roller ve yetkiler.

Endpoint'ler:
- /superadmin/users - Tüm kullanıcıları listeleme
- /api/superadmin/users - Kullanıcı verileri API
"""

import hmac
import io
import os

from flask import (
    render_template,
    jsonify,
    request,
    redirect,
    url_for,
    flash,
    session,
    send_file,
)
from utils.decorators import login_required, role_required
from models import (
    db,
    get_kktc_now,
    Kullanici,
    Otel,
    Kat,
    Oda,
    UrunGrup,
    Urun,
    StokHareket,
    MinibarIslem,
    MinibarIslemDetay,
    PersonelZimmet,
    PersonelZimmetDetay,
    SistemLog,
    HataLog,
)
import logging

RESET_PASSWORD = os.environ.get("SYSTEM_RESET_PASSWORD")

logger = logging.getLogger(__name__)


def register_superadmin_routes(app):
    """Superadmin route'larını register et"""

    @app.route('/superadmin/users')
    @login_required
    @role_required('superadmin')
    def superadmin_users():
        """Superadmin - Tüm kullanıcıları görüntüleme"""
        try:
            kullanicilar = Kullanici.query.order_by(
                Kullanici.aktif.desc(),
                Kullanici.olusturma_tarihi.desc()
            ).all()

            user_data = []
            for k in kullanicilar:
                otel_bilgisi = _get_otel_bilgisi(k)
                user_data.append({
                    'kullanici': k,
                    'otel_bilgisi': otel_bilgisi
                })

            oteller = Otel.query.filter_by(aktif=True).order_by(Otel.ad).all()
            roller = ['superadmin', 'sistem_yoneticisi', 'admin', 'depo_sorumlusu', 'kat_sorumlusu']

            return render_template(
                'sistem_yoneticisi/superadmin_users.html',
                user_data=user_data,
                oteller=oteller,
                roller=roller,
                toplam=len(kullanicilar),
                aktif=sum(1 for k in kullanicilar if k.aktif),
                pasif=sum(1 for k in kullanicilar if not k.aktif)
            )
        except Exception as e:
            logger.error(f"Superadmin users hatası: {e}")
            return render_template(
                'sistem_yoneticisi/superadmin_users.html',
                user_data=[], oteller=[], roller=[],
                toplam=0, aktif=0, pasif=0
            )

    @app.route('/api/superadmin/users')
    @login_required
    @role_required('superadmin')
    def api_superadmin_users():
        """Superadmin - Kullanıcı verileri API"""
        try:
            kullanicilar = Kullanici.query.order_by(
                Kullanici.olusturma_tarihi.desc()
            ).all()

            data = []
            for k in kullanicilar:
                data.append({
                    'id': k.id,
                    'kullanici_adi': k.kullanici_adi,
                    'ad': k.ad,
                    'soyad': k.soyad,
                    'email': k.email or '-',
                    'telefon': k.telefon or '-',
                    'rol': k.rol,
                    'aktif': k.aktif,
                    'sifre_hash': k.sifre_hash[:20] + '...' if k.sifre_hash else '-',
                    'sifre_hash_full': k.sifre_hash or '-',
                    'otel_bilgisi': _get_otel_bilgisi(k),
                    'son_giris': k.son_giris.strftime('%d.%m.%Y %H:%M') if k.son_giris else 'Hiç giriş yapmadı',
                    'olusturma_tarihi': k.olusturma_tarihi.strftime('%d.%m.%Y %H:%M') if k.olusturma_tarihi else '-'
                })

            return jsonify({'success': True, 'data': data, 'toplam': len(data)})
        except Exception as e:
            logger.error(f"Superadmin users API hatası: {e}")
            return jsonify({"success": False, "error": "Sunucu hatasi olustu"}), 500

    # ========================================================================
    # SİSTEM SIFIRLAMA - ÖZEL ŞİFRE İLE KORUMALI
    # ========================================================================

    @app.route("/resetsystem", methods=["GET", "POST"])
    @login_required
    @role_required("superadmin")
    def reset_system():
        """Sistem sıfırlama sayfası - Özel şifre ile korumalı"""

        if request.method == "GET":
            return render_template("reset_system.html", show_stats=False)

        # POST işlemi
        action = request.form.get("action")
        reset_password = request.form.get("reset_password", "")

        # Şifre kontrolü - timing-safe karşılaştırma
        if not RESET_PASSWORD or not hmac.compare_digest(
            reset_password, RESET_PASSWORD
        ):
            flash("❌ Hatalı sistem sıfırlama şifresi!", "error")
            return render_template("reset_system.html", show_stats=False)

        # İstatistikleri göster
        if action == "check":
            try:
                stats = {
                    "kullanici_sayisi": Kullanici.query.count(),
                    "otel_sayisi": Otel.query.count(),
                    "kat_sayisi": Kat.query.count(),
                    "oda_sayisi": Oda.query.count(),
                    "urun_grubu_sayisi": UrunGrup.query.count(),
                    "urun_sayisi": Urun.query.count(),
                    "stok_hareket_sayisi": StokHareket.query.count(),
                    "zimmet_sayisi": PersonelZimmet.query.count(),
                    "zimmet_detay_sayisi": PersonelZimmetDetay.query.count(),
                    "minibar_islem_sayisi": MinibarIslem.query.count(),
                    "minibar_detay_sayisi": MinibarIslemDetay.query.count(),
                    "log_sayisi": SistemLog.query.count(),
                    "hata_sayisi": HataLog.query.count(),
                    "audit_sayisi": db.session.execute(
                        db.text("SELECT COUNT(*) FROM audit_logs")
                    ).scalar()
                    or 0,
                }

                return render_template(
                    "reset_system.html",
                    show_stats=True,
                    stats=stats,
                )

            except Exception as e:
                flash(f"❌ İstatistikler alınırken hata: {str(e)}", "error")
                return render_template("reset_system.html", show_stats=False)

        # Sistem sıfırlama işlemi
        elif action == "reset":
            if not request.form.get("confirm_reset"):
                flash("❌ Sıfırlama onayı verilmedi!", "error")
                return redirect(url_for("reset_system"))

            try:
                logger.info("SİSTEM SIFIRLAMA BAŞLADI")

                # 1. MinibarIslemDetay (foreign key: minibar_islemleri)
                count = db.session.execute(
                    db.text("DELETE FROM minibar_islem_detay")
                ).rowcount
                logger.info(f"MinibarIslemDetay silindi: {count} kayıt")

                # 2. MinibarIslem
                count = db.session.execute(
                    db.text("DELETE FROM minibar_islemleri")
                ).rowcount
                logger.info(f"MinibarIslem silindi: {count} kayıt")

                # 3. PersonelZimmetDetay (foreign key: personel_zimmet)
                count = db.session.execute(
                    db.text("DELETE FROM personel_zimmet_detay")
                ).rowcount
                logger.info(f"PersonelZimmetDetay silindi: {count} kayıt")

                # 4. PersonelZimmet
                count = db.session.execute(
                    db.text("DELETE FROM personel_zimmet")
                ).rowcount
                logger.info(f"PersonelZimmet silindi: {count} kayıt")

                # 5. StokHareket
                count = db.session.execute(
                    db.text("DELETE FROM stok_hareketleri")
                ).rowcount
                logger.info(f"StokHareket silindi: {count} kayıt")

                # 6. Urun (foreign key: urun_gruplari)
                count = db.session.execute(db.text("DELETE FROM urunler")).rowcount
                logger.info(f"Urun silindi: {count} kayıt")

                # 7. UrunGrup
                count = db.session.execute(
                    db.text("DELETE FROM urun_gruplari")
                ).rowcount
                logger.info(f"UrunGrup silindi: {count} kayıt")

                # 8. Oda (foreign key: katlar)
                count = db.session.execute(db.text("DELETE FROM odalar")).rowcount
                logger.info(f"Oda silindi: {count} kayıt")

                # 9. Kat (foreign key: oteller)
                count = db.session.execute(db.text("DELETE FROM katlar")).rowcount
                logger.info(f"Kat silindi: {count} kayıt")

                # 10. LOG VE AUDIT TABLOLARI (foreign key: kullanicilar)
                count = db.session.execute(
                    db.text("DELETE FROM sistem_loglari")
                ).rowcount
                logger.info(f"SistemLog silindi: {count} kayıt")

                count = db.session.execute(db.text("DELETE FROM hata_loglari")).rowcount
                logger.info(f"HataLog silindi: {count} kayıt")

                count = db.session.execute(db.text("DELETE FROM audit_logs")).rowcount
                logger.info(f"AuditLog silindi: {count} kayıt")

                # 11. OtomatikRapor
                count = db.session.execute(
                    db.text("DELETE FROM otomatik_raporlar")
                ).rowcount
                logger.info(f"OtomatikRapor silindi: {count} kayıt")

                # 12. Kullanici (foreign key: oteller)
                count = db.session.execute(db.text("DELETE FROM kullanicilar")).rowcount
                logger.info(f"Kullanici silindi: {count} kayıt")

                # 13. Otel
                count = db.session.execute(db.text("DELETE FROM oteller")).rowcount
                logger.info(f"Otel silindi: {count} kayıt")

                # 14. SistemAyar - setup_tamamlandi'yi sıfırla
                db.session.execute(
                    db.text(
                        "DELETE FROM sistem_ayarlari WHERE anahtar = 'setup_tamamlandi'"
                    )
                )
                logger.info("Setup ayarı sıfırlandı")

                # Auto-increment değerlerini sıfırla
                tables = [
                    "minibar_islem_detay",
                    "minibar_islemleri",
                    "personel_zimmet_detay",
                    "personel_zimmet",
                    "stok_hareketleri",
                    "urunler",
                    "urun_gruplari",
                    "odalar",
                    "katlar",
                    "kullanicilar",
                    "oteller",
                    "sistem_loglari",
                    "hata_loglari",
                    "audit_logs",
                    "otomatik_raporlar",
                ]

                for table in tables:
                    try:
                        db.session.execute(
                            db.text(
                                "SELECT setval(pg_get_serial_sequence(:tbl, 'id'), 1, false)"
                            ),
                            {"tbl": table},
                        )
                    except Exception:
                        pass

                logger.info("Sequence değerleri sıfırlandı")

                db.session.commit()

                logger.info("SİSTEM SIFIRLAMA TAMAMLANDI")

                session.clear()

                flash(
                    "✅ Sistem başarıyla sıfırlandı! Tüm veriler silindi ve sistem ilk kurulum aşamasına döndü.",
                    "success",
                )
                flash("🔄 Şimdi ilk kurulum sayfasına yönlendiriliyorsunuz...", "info")

                return redirect(url_for("setup"))

            except Exception as e:
                db.session.rollback()
                logger.error(f"Sistem sıfırlanırken hata: {str(e)}")
                flash(f"❌ Sistem sıfırlanırken hata oluştu: {str(e)}", "error")
                return redirect(url_for("reset_system"))

        # Geçersiz action
        flash("❌ Geçersiz işlem!", "error")
        return redirect(url_for("reset_system"))

    # ========================================================================
    # SYSTEM BACKUP - SUPER ADMIN ENDPOINT (GİZLİ)
    # ========================================================================

    @app.route("/systembackupsuperadmin", methods=["GET", "POST"])
    def system_backup_login():
        """Gizli super admin backup login sayfası - Sadece şifre ile giriş - LOGLANMAZ"""
        if request.method == "POST":
            access_code = request.form.get("access_code", "").strip()

            expected_code = os.environ.get("SUPER_ADMIN_ACCESS_CODE")
            if not expected_code:
                flash("Sistem yapılandırma hatası!", "error")
                return render_template("super_admin_login.html")
            if hmac.compare_digest(access_code, expected_code):
                session["super_admin_logged_in"] = True
                session["super_admin_login_time"] = get_kktc_now().isoformat()
                return redirect(url_for("system_backup_panel"))
            else:
                flash("❌ Invalid access code!", "error")

        return render_template("super_admin_login.html")

    @app.route("/systembackupsuperadmin/panel")
    @login_required
    def system_backup_panel():
        """Super admin backup panel - istatistikler ve backup özellikleri"""
        if not session.get("super_admin_logged_in"):
            return redirect(url_for("system_backup_login"))

        try:
            stats = {
                "otel_count": Otel.query.count(),
                "kat_count": Kat.query.count(),
                "oda_count": Oda.query.count(),
                "urun_grup_count": UrunGrup.query.count(),
                "urun_count": Urun.query.count(),
                "kullanici_count": Kullanici.query.count(),
                "stok_hareket_count": StokHareket.query.count(),
                "minibar_kontrol_count": MinibarIslem.query.count(),
                "database_name": app.config["SQLALCHEMY_DATABASE_URI"]
                .split("/")[-1]
                .split("?")[0],
                "current_time": get_kktc_now().strftime("%d.%m.%Y %H:%M:%S"),
                "last_backup": session.get("last_backup_time"),
            }

            stats["table_details"] = {
                "oteller": stats["otel_count"],
                "katlar": stats["kat_count"],
                "odalar": stats["oda_count"],
                "urun_gruplari": stats["urun_grup_count"],
                "urunler": stats["urun_count"],
                "kullanicilar": stats["kullanici_count"],
                "stok_hareketleri": stats["stok_hareket_count"],
                "minibar_islemleri": stats["minibar_kontrol_count"],
                "minibar_islem_detaylari": MinibarIslemDetay.query.count(),
                "personel_zimmetleri": PersonelZimmet.query.count(),
                "personel_zimmet_detaylari": PersonelZimmetDetay.query.count(),
            }

            stats["table_count"] = len(stats["table_details"])
            stats["total_records"] = sum(stats["table_details"].values())

            return render_template("system_backup.html", stats=stats)

        except Exception as e:
            flash(f"❌ İstatistikler yüklenirken hata: {str(e)}", "error")
            return redirect(url_for("system_backup_login"))

    @app.route("/systembackupsuperadmin/download", methods=["POST"])
    @login_required
    def system_backup_download():
        """SQL backup dosyasını indir - Python ile direkt export"""
        if not session.get("super_admin_logged_in"):
            return redirect(url_for("system_backup_login"))

        backup_type = request.form.get("backup_type", "full")

        try:
            from io import StringIO
            from datetime import datetime
            from sqlalchemy import text

            sql_dump = StringIO()

            timestamp = get_kktc_now().strftime("%Y-%m-%d %H:%M:%S")
            sql_dump.write("-- Minibar Takip Sistemi Database Backup\n")
            sql_dump.write(f"-- Backup Date: {timestamp}\n")
            sql_dump.write(f"-- Backup Type: {backup_type}\n")
            sql_dump.write("-- Generated by: Super Admin Panel\n\n")
            sql_dump.write("SET FOREIGN_KEY_CHECKS=0;\n")
            sql_dump.write("SET SQL_MODE='NO_AUTO_VALUE_ON_ZERO';\n")
            sql_dump.write("SET NAMES utf8mb4;\n\n")

            tables_query = text("SHOW TABLES")
            tables = db.session.execute(tables_query).fetchall()

            for table_tuple in tables:
                table_name = table_tuple[0]
                sql_dump.write(f"-- Table: {table_name}\n")

                if backup_type == "full":
                    create_query = text(f"SHOW CREATE TABLE `{table_name}`")
                    create_result = db.session.execute(create_query).fetchone()
                    sql_dump.write(f"DROP TABLE IF EXISTS `{table_name}`;\n")
                    sql_dump.write(f"{create_result[1]};\n\n")

                select_query = text(f"SELECT * FROM `{table_name}`")
                rows = db.session.execute(select_query).fetchall()

                if rows:
                    columns_query = text(f"SHOW COLUMNS FROM `{table_name}`")
                    columns = db.session.execute(columns_query).fetchall()
                    column_names = [col[0] for col in columns]

                    sql_dump.write(
                        f"INSERT INTO `{table_name}` (`{'`, `'.join(column_names)}`) VALUES\n"
                    )

                    for i, row in enumerate(rows):
                        values = []
                        for val in row:
                            if val is None:
                                values.append("NULL")
                            elif isinstance(val, (int, float)):
                                values.append(str(val))
                            elif isinstance(val, datetime):
                                values.append(f"'{val.strftime('%Y-%m-%d %H:%M:%S')}'")
                            else:
                                escaped = (
                                    str(val).replace("\\", "\\\\").replace("'", "\\'")
                                )
                                values.append(f"'{escaped}'")

                        comma = "," if i < len(rows) - 1 else ";"
                        sql_dump.write(f"({', '.join(values)}){comma}\n")

                    sql_dump.write("\n")

            sql_dump.write("SET FOREIGN_KEY_CHECKS=1;\n")

            sql_content = sql_dump.getvalue()
            sql_bytes = io.BytesIO(sql_content.encode("utf-8"))

            session["last_backup_time"] = get_kktc_now().strftime("%d.%m.%Y %H:%M:%S")

            filename = f"minibar_backup_{backup_type}_{get_kktc_now().strftime('%Y%m%d_%H%M%S')}.sql"

            return send_file(
                sql_bytes,
                as_attachment=True,
                download_name=filename,
                mimetype="application/sql",
            )

        except Exception as e:
            flash(f"❌ Backup oluşturulurken hata: {str(e)}", "error")
            return redirect(url_for("system_backup_panel"))


def _get_otel_bilgisi(kullanici):
    """Kullanıcının otel bilgisini döndür"""
    try:
        if kullanici.rol in ['superadmin', 'sistem_yoneticisi', 'admin']:
            return 'Tüm Oteller'
        elif kullanici.rol == 'depo_sorumlusu':
            oteller_list = [atama.otel.ad for atama in kullanici.atanan_oteller if atama.otel]
            return ', '.join(oteller_list) if oteller_list else '-'
        elif kullanici.rol == 'kat_sorumlusu':
            return kullanici.otel.ad if kullanici.otel else '-'
        return '-'
    except Exception:
        return '⚠️ Hata'
