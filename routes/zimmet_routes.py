"""
Zimmet Route'ları (Depo Sorumlusu)

Bu modül zimmet detay, iptal ve iade endpoint'lerini içerir.

Endpoint'ler:
- /zimmet-detay/<int:zimmet_id> - Zimmet detay görüntüleme
- /zimmet-iptal/<int:zimmet_id> - Zimmet iptal etme
- /zimmet-iade/<int:detay_id> - Zimmet ürün iadesi

Roller:
- depo_sorumlusu
"""

from flask import render_template, request, redirect, url_for, flash
from models import db, PersonelZimmet, PersonelZimmetDetay, StokHareket
from models import get_kktc_now
from utils.decorators import login_required, role_required
from utils.helpers import get_current_user


def register_zimmet_routes(app):
    @app.route("/zimmet-detay/<int:zimmet_id>")
    @login_required
    @role_required("depo_sorumlusu")
    def zimmet_detay(zimmet_id):
        zimmet = PersonelZimmet.query.get_or_404(zimmet_id)
        return render_template("depo_sorumlusu/zimmet_detay.html", zimmet=zimmet)

    @app.route("/zimmet-iptal/<int:zimmet_id>", methods=["POST"])
    @login_required
    @role_required("depo_sorumlusu")
    def zimmet_iptal(zimmet_id):
        """Zimmeti tamamen iptal et ve kullanılmayan ürünleri depoya iade et"""
        try:
            zimmet = PersonelZimmet.query.get_or_404(zimmet_id)
            islem_yapan = get_current_user()
            if not islem_yapan:
                flash(
                    "Kullanıcı oturumu bulunamadı. Lütfen tekrar giriş yapın.", "danger"
                )
                return redirect(url_for("logout"))

            # Sadece aktif zimmetler iptal edilebilir
            if zimmet.durum != "aktif":
                flash("Sadece aktif zimmetler iptal edilebilir.", "warning")
                return redirect(url_for("personel_zimmet"))

            # Tüm zimmet detaylarını kontrol et ve kullanılmayan ürünleri depoya iade et
            for detay in zimmet.detaylar:
                kalan = (
                    detay.kalan_miktar
                    if detay.kalan_miktar is not None
                    else (detay.miktar - detay.kullanilan_miktar)
                )

                if kalan > 0:
                    # Stok hareketi oluştur (depoya giriş)
                    stok_hareket = StokHareket(
                        urun_id=detay.urun_id,
                        hareket_tipi="giris",
                        miktar=kalan,
                        aciklama=f"Zimmet iptali - {zimmet.personel.ad} {zimmet.personel.soyad} - Zimmet #{zimmet.id}",
                        islem_yapan_id=islem_yapan.id,
                    )
                    db.session.add(stok_hareket)

                    # İade edilen miktarı kaydet
                    detay.iade_edilen_miktar = (detay.iade_edilen_miktar or 0) + kalan
                    detay.kalan_miktar = 0

            # Zimmet durumunu güncelle
            zimmet.durum = "iptal"
            zimmet.iade_tarihi = get_kktc_now()

            db.session.commit()
            flash(
                f"{zimmet.personel.ad} {zimmet.personel.soyad} adlı personelin zimmeti iptal edildi ve kullanılmayan ürünler depoya iade edildi.",
                "success",
            )

        except Exception as e:
            db.session.rollback()
            flash(f"Zimmet iptal edilirken hata oluştu: {str(e)}", "danger")

        return redirect(url_for("personel_zimmet"))

    @app.route("/zimmet-iade/<int:detay_id>", methods=["POST"])
    @login_required
    @role_required("depo_sorumlusu")
    def zimmet_iade(detay_id):
        """Belirli bir ürünü kısmen veya tamamen iade al"""
        zimmet = None
        try:
            detay = PersonelZimmetDetay.query.get_or_404(detay_id)
            zimmet = detay.zimmet
            islem_yapan = get_current_user()
            if not islem_yapan:
                flash(
                    "Kullanıcı oturumu bulunamadı. Lütfen tekrar giriş yapın.", "danger"
                )
                return redirect(url_for("logout"))

            # Sadece aktif zimmetlerden iade alınabilir
            if zimmet.durum != "aktif":
                flash("Sadece aktif zimmetlerden ürün iadesi alınabilir.", "warning")
                return redirect(url_for("zimmet_detay", zimmet_id=zimmet.id))

            try:
                iade_miktar = int(request.form.get("iade_miktar", 0))
            except (ValueError, TypeError):
                flash("Geçersiz iade miktarı.", "warning")
                return redirect(url_for("zimmet_detay", zimmet_id=zimmet.id))
            aciklama = request.form.get("aciklama", "")

            if iade_miktar <= 0 or iade_miktar > 10000:
                flash("İade miktarı 1 ile 10.000 arasında olmalıdır.", "warning")
                return redirect(url_for("zimmet_detay", zimmet_id=zimmet.id))

            # Kalan miktarı kontrol et
            kalan = (
                detay.kalan_miktar
                if detay.kalan_miktar is not None
                else (detay.miktar - detay.kullanilan_miktar)
            )

            if iade_miktar > kalan:
                flash(
                    f"İade miktarı kalan miktardan fazla olamaz. Kalan: {kalan}",
                    "danger",
                )
                return redirect(url_for("zimmet_detay", zimmet_id=zimmet.id))

            # Stok hareketi oluştur (depoya giriş)
            stok_hareket = StokHareket(
                urun_id=detay.urun_id,
                hareket_tipi="giris",
                miktar=iade_miktar,
                aciklama=f"Zimmet iadesi - {zimmet.personel.ad} {zimmet.personel.soyad} - {aciklama}",
                islem_yapan_id=islem_yapan.id,
            )
            db.session.add(stok_hareket)

            # Zimmet detayını güncelle
            detay.iade_edilen_miktar = (detay.iade_edilen_miktar or 0) + iade_miktar
            detay.kalan_miktar = kalan - iade_miktar

            db.session.commit()
            flash(
                f"{detay.urun.urun_adi} ürününden {iade_miktar} adet iade alındı.",
                "success",
            )

        except Exception as e:
            db.session.rollback()
            flash(f"İade işlemi sırasında hata oluştu: {str(e)}", "danger")

        if zimmet is not None:
            return redirect(url_for("zimmet_detay", zimmet_id=zimmet.id))
        return redirect(url_for("personel_zimmet"))
