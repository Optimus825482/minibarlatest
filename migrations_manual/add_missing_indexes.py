"""
Eksik Index'lerin Eklenmesi - Performance Migration
Tarih: 2026-03-22
Aciklama: FK kolonlari, sik sorgulanan alanlar ve composite index'ler eklenir.
           IF NOT EXISTS kullanilarak idempotent calisir.
"""

from app import app, db


# Index tanimlari: (index_adi, tablo, kolonlar)
INDEXES = [
    # === kullanici_otel ===
    ("ix_kullanici_otel_kullanici_id", "kullanici_otel", ["kullanici_id"]),
    ("ix_kullanici_otel_otel_id", "kullanici_otel", ["otel_id"]),

    # === kullanicilar ===
    ("ix_kullanicilar_otel_id", "kullanicilar", ["otel_id"]),
    ("ix_kullanicilar_rol", "kullanicilar", ["rol"]),
    ("ix_kullanicilar_aktif", "kullanicilar", ["aktif"]),

    # === katlar ===
    ("ix_katlar_otel_id", "katlar", ["otel_id"]),

    # === setup_icerik ===
    ("ix_setup_icerik_setup_id", "setup_icerik", ["setup_id"]),
    ("ix_setup_icerik_urun_id", "setup_icerik", ["urun_id"]),

    # === odalar ===
    ("ix_odalar_kat_id", "odalar", ["kat_id"]),
    ("ix_odalar_oda_tipi_id", "odalar", ["oda_tipi_id"]),
    ("ix_odalar_aktif", "odalar", ["aktif"]),

    # === urunler ===
    ("ix_urunler_grup_id", "urunler", ["grup_id"]),
    ("ix_urunler_aktif", "urunler", ["aktif"]),

    # === stok_hareketleri ===
    ("ix_stok_hareketleri_urun_id", "stok_hareketleri", ["urun_id"]),
    ("ix_stok_hareketleri_islem_yapan_id", "stok_hareketleri", ["islem_yapan_id"]),
    ("ix_stok_hareketleri_tarih", "stok_hareketleri", ["tarih"]),
    ("ix_stok_hareketleri_hareket_tipi", "stok_hareketleri", ["hareket_tipi"]),

    # === personel_zimmet ===
    ("ix_personel_zimmet_personel_id", "personel_zimmet", ["personel_id"]),
    ("ix_personel_zimmet_otel_id", "personel_zimmet", ["otel_id"]),
    ("ix_personel_zimmet_durum", "personel_zimmet", ["durum"]),
    ("ix_personel_zimmet_tarih", "personel_zimmet", ["tarih"]),

    # === personel_zimmet_detay ===
    ("ix_personel_zimmet_detay_zimmet_id", "personel_zimmet_detay", ["zimmet_id"]),
    ("ix_personel_zimmet_detay_urun_id", "personel_zimmet_detay", ["urun_id"]),

    # === minibar_islemleri ===
    ("ix_minibar_islemleri_oda_id", "minibar_islemleri", ["oda_id"]),
    ("ix_minibar_islemleri_personel_id", "minibar_islemleri", ["personel_id"]),
    ("ix_minibar_islemleri_islem_tipi", "minibar_islemleri", ["islem_tipi"]),
    ("ix_minibar_islemleri_tarih", "minibar_islemleri", ["tarih"]),

    # === minibar_islem_detay ===
    ("ix_minibar_islem_detay_islem_id", "minibar_islem_detay", ["islem_id"]),
    ("ix_minibar_islem_detay_urun_id", "minibar_islem_detay", ["urun_id"]),

    # === sistem_loglari ===
    ("ix_sistem_loglari_kullanici_id", "sistem_loglari", ["kullanici_id"]),
    ("ix_sistem_loglari_tarih", "sistem_loglari", ["tarih"]),
    ("ix_sistem_loglari_seviye", "sistem_loglari", ["seviye"]),

    # === hata_loglari ===
    ("ix_hata_loglari_kullanici_id", "hata_loglari", ["kullanici_id"]),
    ("ix_hata_loglari_tarih", "hata_loglari", ["tarih"]),

    # === audit_logs ===
    ("ix_audit_logs_kullanici_id", "audit_logs", ["kullanici_id"]),
    ("ix_audit_logs_tablo_adi", "audit_logs", ["tablo_adi"]),
    ("ix_audit_logs_islem_tarihi", "audit_logs", ["islem_tarihi"]),
    ("ix_audit_logs_islem_tipi", "audit_logs", ["islem_tipi"]),

    # === otomatik_raporlar ===
    ("ix_otomatik_raporlar_olusturma_tarihi", "otomatik_raporlar", ["olusturma_tarihi"]),
    ("ix_otomatik_raporlar_rapor_tipi", "otomatik_raporlar", ["rapor_tipi"]),

    # === minibar_dolum_talepleri ===
    ("ix_minibar_dolum_talepleri_oda_id", "minibar_dolum_talepleri", ["oda_id"]),
    ("ix_minibar_dolum_talepleri_durum", "minibar_dolum_talepleri", ["durum"]),

    # === qr_kod_okutma_loglari ===
    ("ix_qr_kod_okutma_loglari_oda_id", "qr_kod_okutma_loglari", ["oda_id"]),
    ("ix_qr_kod_okutma_loglari_kullanici_id", "qr_kod_okutma_loglari", ["kullanici_id"]),
    ("ix_qr_kod_okutma_loglari_tarih", "qr_kod_okutma_loglari", ["okutma_tarihi"]),

    # === misafir_kayitlari ===
    ("ix_misafir_kayitlari_oda_id", "misafir_kayitlari", ["oda_id"]),

    # === dosya_yuklemeleri ===
    ("ix_dosya_yuklemeleri_otel_id", "dosya_yuklemeleri", ["otel_id"]),
    ("ix_dosya_yuklemeleri_yuklenen_kullanici_id", "dosya_yuklemeleri", ["yuklenen_kullanici_id"]),

    # === ml_metrics ===
    ("ix_ml_metrics_metric_type", "ml_metrics", ["metric_type"]),
    ("ix_ml_metrics_timestamp", "ml_metrics", ["timestamp"]),

    # === ml_alerts ===
    ("ix_ml_alerts_alert_type", "ml_alerts", ["alert_type"]),
    ("ix_ml_alerts_is_resolved", "ml_alerts", ["is_resolved"]),
    ("ix_ml_alerts_created_at", "ml_alerts", ["created_at"]),

    # === ml_training_logs ===
    ("ix_ml_training_logs_model_id", "ml_training_logs", ["model_id"]),

    # === ml_features ===
    ("ix_ml_features_feature_date", "ml_features", ["feature_date"]),

    # === urun_stok ===
    ("ix_urun_stok_urun_id", "urun_stok", ["urun_id"]),
    ("ix_urun_stok_otel_id", "urun_stok", ["otel_id"]),

    # === gunluk_gorevler ===
    ("ix_gunluk_gorevler_otel_id", "gunluk_gorevler", ["otel_id"]),
    ("ix_gunluk_gorevler_personel_id", "gunluk_gorevler", ["personel_id"]),
    ("ix_gunluk_gorevler_tarih", "gunluk_gorevler", ["tarih"]),
    ("ix_gunluk_gorevler_durum", "gunluk_gorevler", ["durum"]),

    # === gorev_detaylari ===
    ("ix_gorev_detaylari_gorev_id", "gorev_detaylari", ["gorev_id"]),
    ("ix_gorev_detaylari_oda_id", "gorev_detaylari", ["oda_id"]),
    ("ix_gorev_detaylari_durum", "gorev_detaylari", ["durum"]),

    # === dnd_kontroller ===
    ("ix_dnd_kontroller_gorev_detay_id", "dnd_kontroller", ["gorev_detay_id"]),

    # === yukleme_gorevleri ===
    ("ix_yukleme_gorevleri_otel_id", "yukleme_gorevleri", ["otel_id"]),
    ("ix_yukleme_gorevleri_depo_sorumlusu_id", "yukleme_gorevleri", ["depo_sorumlusu_id"]),
    ("ix_yukleme_gorevleri_tarih", "yukleme_gorevleri", ["tarih"]),

    # === gorev_durum_loglari ===
    ("ix_gorev_durum_loglari_gorev_detay_id", "gorev_durum_loglari", ["gorev_detay_id"]),

    # === oda_kontrol_kayitlari ===
    ("ix_oda_kontrol_kayitlari_oda_id", "oda_kontrol_kayitlari", ["oda_id"]),
    ("ix_oda_kontrol_kayitlari_personel_id", "oda_kontrol_kayitlari", ["personel_id"]),

    # === oda_dnd_kayitlari ===
    ("ix_oda_dnd_kayitlari_oda_id", "oda_dnd_kayitlari", ["oda_id"]),
    ("ix_oda_dnd_kayitlari_otel_id", "oda_dnd_kayitlari", ["otel_id"]),
    ("ix_oda_dnd_kayitlari_durum", "oda_dnd_kayitlari", ["durum"]),

    # === oda_dnd_kontroller ===
    ("ix_oda_dnd_kontroller_dnd_kayit_id", "oda_dnd_kontroller", ["dnd_kayit_id"]),

    # === kat_sorumlusu_siparis_talepleri ===
    ("ix_kat_sor_sip_talep_kat_sorumlusu_id", "kat_sorumlusu_siparis_talepleri", ["kat_sorumlusu_id"]),
    ("ix_kat_sor_sip_talep_durum", "kat_sorumlusu_siparis_talepleri", ["durum"]),

    # === kat_sorumlusu_siparis_talep_detaylari ===
    ("ix_kat_sor_sip_talep_det_talep_id", "kat_sorumlusu_siparis_talep_detaylari", ["talep_id"]),
    ("ix_kat_sor_sip_talep_det_urun_id", "kat_sorumlusu_siparis_talep_detaylari", ["urun_id"]),

    # === query_logs ===
    ("ix_query_logs_user_id", "query_logs", ["user_id"]),
    ("ix_query_logs_created_at", "query_logs", ["created_at"]),

    # === background_jobs ===
    ("ix_background_jobs_status", "background_jobs", ["status"]),
]

# Composite indexler - sik kullanilan sorgu pattern'leri
COMPOSITE_INDEXES = [
    # Minibar islem sorgulari: oda + tarih
    ("ix_minibar_islemleri_oda_tarih", "minibar_islemleri", ["oda_id", "tarih"]),
    # Stok hareketleri: urun + tarih
    ("ix_stok_hareketleri_urun_tarih", "stok_hareketleri", ["urun_id", "tarih"]),
    # Gorev detay: gorev + durum (filtre)
    ("ix_gorev_detaylari_gorev_durum", "gorev_detaylari", ["gorev_id", "durum"]),
    # Audit log: tablo + tarih (admin panelde filtreleme)
    ("ix_audit_logs_tablo_tarih", "audit_logs", ["tablo_adi", "islem_tarihi"]),
    # Urun stok: unique-like composite (urun + otel)
    ("ix_urun_stok_urun_otel", "urun_stok", ["urun_id", "otel_id"]),
    # Gunluk gorevler: otel + tarih (en sik sorgu)
    ("ix_gunluk_gorevler_otel_tarih", "gunluk_gorevler", ["otel_id", "tarih"]),
    # Personel zimmet: personel + durum
    ("ix_personel_zimmet_personel_durum", "personel_zimmet", ["personel_id", "durum"]),
    # Misafir kayit: oda + giris_tarihi
    ("ix_misafir_kayitlari_oda_giris", "misafir_kayitlari", ["oda_id", "giris_tarihi"]),
]


def upgrade():
    """Eksik index'leri ekle"""
    with app.app_context():
        from sqlalchemy import inspect, text
        inspector = inspect(db.engine)
        tables = inspector.get_table_names()

        created = 0
        skipped = 0
        errors = 0

        all_indexes = INDEXES + COMPOSITE_INDEXES

        for idx_name, table, columns in all_indexes:
            if table not in tables:
                print(f"  SKIP  {table} tablosu mevcut degil")
                skipped += 1
                continue

            cols = ", ".join(columns)
            sql = f"CREATE INDEX IF NOT EXISTS {idx_name} ON {table} ({cols})"
            try:
                db.session.execute(text(sql))
                created += 1
            except Exception as e:
                print(f"  HATA  {idx_name}: {e}")
                errors += 1

        db.session.commit()
        print(f"\nIndex migration tamamlandi: {created} olusturuldu, {skipped} atlandi, {errors} hata")


def downgrade():
    """Eklenen index'leri kaldir"""
    with app.app_context():
        from sqlalchemy import text
        all_indexes = INDEXES + COMPOSITE_INDEXES

        for idx_name, table, _ in all_indexes:
            try:
                db.session.execute(text(f"DROP INDEX IF EXISTS {idx_name}"))
            except Exception as e:
                print(f"  HATA  {idx_name}: {e}")

        db.session.commit()
        print("Index rollback tamamlandi")


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "downgrade":
        downgrade()
    else:
        upgrade()
