/**
 * Minibar Takip Sistemi - Kullanım Kılavuzu Sistemi
 * Sayfa bazlı mini kılavuz + Genel sistem rehberi
 * ROL BAZLI FİLTRELEME DESTEĞİ
 */

// ============================================
// SAYFA BAZLI KILAVUZ VERİLERİ
// ============================================

const PAGE_GUIDES = {
  // Sistem Yöneticisi Sayfaları
  sistem_yoneticisi_dashboard: {
    title: "Dashboard",
    icon: "fa-home",
    roles: ["sistem_yoneticisi", "admin"],
    tips: [
      {
        icon: "fa-chart-line",
        text: "Günlük özet kartlarından anlık durumu takip edin",
      },
      { icon: "fa-bell", text: "Kritik uyarıları kontrol edin" },
      { icon: "fa-tasks", text: "Bekleyen görevleri görüntüleyin" },
      {
        icon: "fa-hotel",
        text: "Otel bazlı performans metriklerini inceleyin",
      },
    ],
  },
  otel_listesi: {
    title: "Otel Yönetimi",
    icon: "fa-hotel",
    roles: ["sistem_yoneticisi", "admin"],
    tips: [
      { icon: "fa-plus", text: '"Yeni Otel" butonu ile otel ekleyin' },
      { icon: "fa-edit", text: "Otel satırına tıklayarak düzenleyin" },
      {
        icon: "fa-layer-group",
        text: "Kat ve oda tanımlarını otel detayından yapın",
      },
    ],
  },
  kat_tanimla: {
    title: "Kat Tanımlama",
    icon: "fa-layer-group",
    roles: ["sistem_yoneticisi", "admin"],
    tips: [
      { icon: "fa-hotel", text: "Önce otel seçin" },
      { icon: "fa-plus", text: "Kat numarası ve adı girin" },
      { icon: "fa-sort", text: "Katlar otomatik sıralanır" },
    ],
  },
  oda_tanimla: {
    title: "Oda Tanımlama",
    icon: "fa-door-open",
    roles: ["sistem_yoneticisi", "admin"],
    tips: [
      { icon: "fa-layer-group", text: "Önce kat seçin" },
      { icon: "fa-qrcode", text: "QR kod otomatik oluşturulur" },
      { icon: "fa-cog", text: "Oda tipini setup ile eşleştirin" },
    ],
  },
  setup_yonetimi: {
    title: "Setup Yönetimi",
    icon: "fa-cog",
    roles: ["sistem_yoneticisi", "admin"],
    tips: [
      { icon: "fa-box", text: "Setup = Minibar ürün şablonu" },
      { icon: "fa-list", text: "Her setup için ürün ve adet belirleyin" },
      { icon: "fa-link", text: "Oda tiplerine setup atayın" },
    ],
  },
  personel_tanimla: {
    title: "Kullanıcı Yönetimi",
    icon: "fa-users",
    roles: ["sistem_yoneticisi", "admin"],
    tips: [
      { icon: "fa-user-plus", text: "Yeni kullanıcı ekleyin" },
      {
        icon: "fa-user-tag",
        text: "Rol atayın: Sistem Yöneticisi, Depo Sorumlusu, Kat Sorumlusu",
      },
      { icon: "fa-hotel", text: "Otel ataması yapın" },
    ],
  },
  urunler: {
    title: "Ürün Yönetimi",
    icon: "fa-box",
    roles: ["sistem_yoneticisi", "admin"],
    tips: [
      { icon: "fa-tags", text: "Önce ürün grubu oluşturun" },
      { icon: "fa-barcode", text: "Barkod ile hızlı arama yapın" },
      { icon: "fa-dollar-sign", text: "Alış ve satış fiyatı girin" },
    ],
  },
  urun_gruplari: {
    title: "Ürün Grupları",
    icon: "fa-tags",
    roles: ["sistem_yoneticisi", "admin"],
    tips: [
      { icon: "fa-folder", text: "Kategorilere göre gruplandırın" },
      {
        icon: "fa-wine-bottle",
        text: "Örnek: İçecekler, Atıştırmalıklar, Alkollü",
      },
      { icon: "fa-chart-pie", text: "Raporlarda grup bazlı analiz yapın" },
    ],
  },
  admin_depo_stoklari: {
    title: "Depo Stokları",
    icon: "fa-warehouse",
    roles: ["sistem_yoneticisi", "admin"],
    tips: [
      { icon: "fa-search", text: "Ürün adı veya barkod ile arayın" },
      { icon: "fa-exclamation-triangle", text: "Kritik stokları takip edin" },
      { icon: "fa-file-excel", text: "Excel'e aktarın" },
    ],
  },
  admin_personel_zimmetleri: {
    title: "Zimmet Yönetimi",
    icon: "fa-clipboard-check",
    roles: ["sistem_yoneticisi", "admin"],
    tips: [
      { icon: "fa-user", text: "Personel seçerek zimmet atayın" },
      { icon: "fa-boxes", text: "Toplu zimmet atama yapabilirsiniz" },
      { icon: "fa-history", text: "Zimmet geçmişini görüntüleyin" },
    ],
  },
  admin_minibar_islemleri: {
    title: "Minibar İşlemleri",
    icon: "fa-clipboard-list",
    roles: ["sistem_yoneticisi", "admin"],
    tips: [
      { icon: "fa-filter", text: "Tarih ve otel bazlı filtreleyin" },
      { icon: "fa-eye", text: "Detay için satıra tıklayın" },
      { icon: "fa-file-export", text: "Rapor olarak dışa aktarın" },
    ],
  },
  "ml.dashboard": {
    title: "ML Analiz Sistemi",
    icon: "fa-brain",
    roles: ["sistem_yoneticisi", "admin"],
    tips: [
      { icon: "fa-chart-line", text: "Talep tahminlerini inceleyin" },
      {
        icon: "fa-exclamation-triangle",
        text: "Anomali uyarılarını kontrol edin",
      },
      { icon: "fa-lightbulb", text: "AI önerilerini değerlendirin" },
      { icon: "fa-sync", text: "Modeller otomatik güncellenir" },
    ],
  },

  // Rapor Sayfaları - Tüm roller
  "raporlar.doluluk_raporlari": {
    title: "Doluluk Raporları",
    icon: "fa-calendar-alt",
    roles: ["sistem_yoneticisi", "admin", "depo_sorumlusu"],
    tips: [
      { icon: "fa-hotel", text: "Otel ve tarih aralığı seçin" },
      { icon: "fa-chart-bar", text: "Günlük doluluk oranlarını görün" },
      { icon: "fa-file-excel", text: "Excel'e aktarın" },
    ],
  },
  "raporlar.stok_raporlari": {
    title: "Stok Raporları",
    icon: "fa-boxes",
    roles: ["sistem_yoneticisi", "admin", "depo_sorumlusu"],
    tips: [
      { icon: "fa-warehouse", text: "Mevcut stok durumunu görün" },
      { icon: "fa-exchange-alt", text: "Stok hareketlerini takip edin" },
      { icon: "fa-exclamation", text: "Kritik stokları listeleyin" },
    ],
  },
  "raporlar.zimmet_raporlari": {
    title: "Zimmet Raporları",
    icon: "fa-user-tag",
    roles: ["sistem_yoneticisi", "admin", "depo_sorumlusu"],
    tips: [
      { icon: "fa-user", text: "Personel bazlı zimmet görün" },
      { icon: "fa-box", text: "Ürün bazlı dağılımı inceleyin" },
      { icon: "fa-calendar", text: "Tarih aralığı filtreleyin" },
    ],
  },
  "raporlar.performans_raporlari": {
    title: "Performans Raporları",
    icon: "fa-chart-line",
    roles: ["sistem_yoneticisi", "admin", "depo_sorumlusu"],
    tips: [
      { icon: "fa-user-check", text: "Personel performansını ölçün" },
      { icon: "fa-tasks", text: "Görev tamamlama oranlarını görün" },
      { icon: "fa-trophy", text: "En iyi performansları belirleyin" },
    ],
  },
  "raporlar.otel_zimmet_stok_raporlari": {
    title: "Otel Zimmet Stokları",
    icon: "fa-hotel",
    roles: ["sistem_yoneticisi", "admin", "depo_sorumlusu"],
    tips: [
      { icon: "fa-boxes", text: "Otel bazlı stok durumunu görün" },
      { icon: "fa-exclamation-triangle", text: "Kritik ürünleri takip edin" },
      { icon: "fa-percentage", text: "Kullanım oranlarını analiz edin" },
    ],
  },
  "raporlar.kat_sorumlusu_kullanim_raporlari": {
    title: "Kat Sorumlusu Kullanım",
    icon: "fa-user-check",
    roles: ["sistem_yoneticisi", "admin", "depo_sorumlusu"],
    tips: [
      { icon: "fa-user", text: "Personel seçerek filtreleyin" },
      { icon: "fa-box", text: "Ürün bazlı kullanımı görün" },
      { icon: "fa-undo", text: "İade miktarlarını takip edin" },
    ],
  },
  "raporlar.oda_bazli_tuketim_raporlari": {
    title: "Oda Bazlı Tüketim",
    icon: "fa-door-open",
    roles: ["sistem_yoneticisi", "admin", "depo_sorumlusu"],
    tips: [
      { icon: "fa-hotel", text: "Otel seçimi zorunludur" },
      { icon: "fa-sort", text: "En çok tüketen odaları görün" },
      { icon: "fa-lira-sign", text: "Tutar bazlı analiz yapın" },
    ],
  },
  "raporlar.gunluk_gorev_detay_raporlari": {
    title: "Günlük Görev Detay",
    icon: "fa-tasks",
    roles: ["sistem_yoneticisi", "admin", "depo_sorumlusu"],
    tips: [
      { icon: "fa-calendar", text: "Tarih aralığı seçin" },
      { icon: "fa-check-circle", text: "Tamamlanma oranlarını görün" },
      { icon: "fa-user", text: "Personel bazlı performans" },
    ],
  },
  "raporlar.otel_karsilastirma_raporlari": {
    title: "Otel Karşılaştırma",
    icon: "fa-balance-scale",
    roles: ["sistem_yoneticisi", "admin"],
    tips: [
      { icon: "fa-hotel", text: "Tüm otelleri karşılaştırın" },
      { icon: "fa-chart-bar", text: "Performans metriklerini görün" },
      { icon: "fa-trophy", text: "En iyi oteli belirleyin" },
    ],
  },

  // Depo Sorumlusu Sayfaları
  depo_dashboard: {
    title: "Depo Dashboard",
    icon: "fa-warehouse",
    roles: ["depo_sorumlusu"],
    tips: [
      {
        icon: "fa-tasks",
        text: "Günlük görevlerinizi ve bekleyen işleri görün",
      },
      {
        icon: "fa-bell",
        text: "Kat sorumlularından gelen talepleri kontrol edin",
      },
      {
        icon: "fa-chart-pie",
        text: "Stok özetini ve kritik ürünleri takip edin",
      },
      { icon: "fa-truck", text: "Bekleyen siparişleri hızlıca görüntüleyin" },
    ],
  },
  ana_depo_tedarik: {
    title: "Ana Depo Tedarik",
    icon: "fa-truck-loading",
    roles: ["depo_sorumlusu"],
    tips: [
      { icon: "fa-box", text: "Ana depodan ürün tedarik edin" },
      { icon: "fa-list", text: "Tedarik edilecek ürünleri seçin" },
      { icon: "fa-calculator", text: "Miktar belirleyin ve onaylayın" },
      { icon: "fa-history", text: "Geçmiş tedarikleri görüntüleyin" },
    ],
  },
  depo_stoklarim: {
    title: "Stoklarım",
    icon: "fa-boxes",
    roles: ["depo_sorumlusu"],
    tips: [
      { icon: "fa-search", text: "Ürün adı veya barkod ile arayın" },
      {
        icon: "fa-exclamation-triangle",
        text: "Kritik stok seviyelerini takip edin",
      },
      { icon: "fa-file-excel", text: "Stok listesini Excel'e aktarın" },
      { icon: "fa-sync", text: "Stok sayımı yapın ve güncelleyin" },
    ],
  },
  personel_zimmet: {
    title: "Personel Zimmet",
    icon: "fa-clipboard-check",
    roles: ["depo_sorumlusu"],
    tips: [
      { icon: "fa-user", text: "Kat sorumlusu seçin" },
      { icon: "fa-box", text: "Zimmetlenecek ürün ve miktarı belirleyin" },
      { icon: "fa-check", text: "Zimmet işlemini onaylayın" },
      { icon: "fa-history", text: "Zimmet geçmişini görüntüleyin" },
    ],
  },
  kat_sorumlusu_siparisler: {
    title: "Kat Sorumlusu Siparişleri",
    icon: "fa-shopping-cart",
    roles: ["depo_sorumlusu"],
    tips: [
      { icon: "fa-bell", text: "Bekleyen siparişleri görün" },
      { icon: "fa-check", text: "Siparişleri onaylayın veya reddedin" },
      { icon: "fa-truck", text: "Teslimatı tamamlayın" },
      { icon: "fa-comment", text: "Sipariş notlarını inceleyin" },
    ],
  },
  kat_bazli_rapor: {
    title: "Kat Tüketim Raporu",
    icon: "fa-layer-group",
    roles: ["depo_sorumlusu"],
    tips: [
      { icon: "fa-hotel", text: "Otel ve kat seçin" },
      { icon: "fa-calendar", text: "Tarih aralığı belirleyin" },
      { icon: "fa-chart-bar", text: "Kat bazlı tüketim analizi yapın" },
    ],
  },
  depo_raporlar: {
    title: "Depo Raporları",
    icon: "fa-chart-bar",
    roles: ["depo_sorumlusu"],
    tips: [
      { icon: "fa-list", text: "Rapor tipini seçin" },
      { icon: "fa-filter", text: "Filtreleri uygulayın" },
      { icon: "fa-file-excel", text: "Excel/PDF olarak indirin" },
    ],
  },
  "doluluk.doluluk_yonetimi": {
    title: "Doluluk Yönetimi",
    icon: "fa-calendar-check",
    roles: ["depo_sorumlusu"],
    tips: [
      {
        icon: "fa-file-excel",
        text: "Opera'dan alınan Excel dosyasını yükleyin",
      },
      {
        icon: "fa-list",
        text: "Dosya tipini seçin: IN HOUSE, ARRIVALS veya DEPARTURES",
      },
      { icon: "fa-eye", text: "Önizleme yapın ve verileri kontrol edin" },
      { icon: "fa-upload", text: "Onaylayın ve sisteme yükleyin" },
      { icon: "fa-tasks", text: "Yükleme sonrası görevler otomatik oluşur" },
    ],
  },
  "doluluk.gunluk_doluluk": {
    title: "Günlük Doluluk",
    icon: "fa-bed",
    roles: ["depo_sorumlusu", "kat_sorumlusu"],
    tips: [
      { icon: "fa-calendar", text: "Tarih seçerek görüntüleyin" },
      { icon: "fa-door-open", text: "Oda durumlarını kontrol edin" },
      { icon: "fa-user", text: "Misafir bilgilerini görün" },
      { icon: "fa-filter", text: "Durum bazlı filtreleyin" },
    ],
  },

  // Sistem Sayfaları - Sadece Admin
  sistem_ayarlari: {
    title: "Sistem Ayarları",
    icon: "fa-cogs",
    roles: ["sistem_yoneticisi", "admin"],
    tips: [
      { icon: "fa-envelope", text: "Email ayarlarını yapılandırın" },
      { icon: "fa-bell", text: "Bildirim tercihlerini ayarlayın" },
      { icon: "fa-shield-alt", text: "Güvenlik ayarlarını kontrol edin" },
    ],
  },
  audit_trail: {
    title: "Audit Trail",
    icon: "fa-shield-alt",
    roles: ["sistem_yoneticisi", "admin"],
    tips: [
      { icon: "fa-search", text: "İşlem geçmişini arayın" },
      { icon: "fa-user", text: "Kullanıcı bazlı filtreleyin" },
      { icon: "fa-calendar", text: "Tarih aralığı belirleyin" },
    ],
  },
  sistem_loglari: {
    title: "Sistem Logları",
    icon: "fa-file-alt",
    roles: ["sistem_yoneticisi", "admin"],
    tips: [
      { icon: "fa-exclamation-circle", text: "Hata loglarını inceleyin" },
      { icon: "fa-filter", text: "Seviyeye göre filtreleyin" },
      { icon: "fa-download", text: "Logları indirin" },
    ],
  },
};

// ============================================
// ROL BAZLI SİSTEM REHBERİ VERİLERİ
// ============================================

const SYSTEM_GUIDE_BY_ROLE = {
  // Sistem Yöneticisi / Admin için tam rehber
  admin: {
    sections: [
      {
        id: "baslarken",
        title: "Başlarken",
        icon: "fa-rocket",
        color: "indigo",
        items: [
          {
            title: "Sisteme Hoş Geldiniz!",
            description:
              "Minibar Takip Sistemi, otel minibar operasyonlarınızı dijitalleştiren kapsamlı bir çözümdür.",
            steps: [
              "Bu sistem ile otel, oda ve minibar yapınızı yönetebilirsiniz",
              "Stok takibi ve zimmet işlemlerini kolayca yapabilirsiniz",
              "Günlük doluluk verilerini yükleyerek otomatik görev oluşturabilirsiniz",
              "Detaylı raporlar ile operasyonlarınızı analiz edebilirsiniz",
              "AI destekli öneriler ile verimliliğinizi artırabilirsiniz",
            ],
          },
          {
            title: "İlk Kurulum Adımları",
            description:
              "Sistemi kullanmaya başlamak için sırasıyla bu adımları takip edin.",
            steps: [
              "1. Önce otelleri tanımlayın (Otel & Yapı → Oteller)",
              "2. Her otel için katları ekleyin (Otel & Yapı → Katlar)",
              "3. Katlara odaları ekleyin (Otel & Yapı → Odalar)",
              "4. Ürün grupları ve ürünleri tanımlayın (Ürün & Stok)",
              "5. Minibar setup'larını oluşturun (Otel & Yapı → Setup'lar)",
              "6. Kullanıcıları ekleyin ve rolleri atayın",
              "7. İlk stok girişini yapın",
            ],
          },
          {
            title: "Günlük İş Akışı",
            description: "Her gün yapılması gereken temel işlemler.",
            steps: [
              "Sabah: Dashboard'dan günlük özeti kontrol edin",
              "Sabah: Opera'dan doluluk verilerini yükleyin",
              "Gün içi: Kat sorumlularının görev durumlarını takip edin",
              "Gün içi: Dolum taleplerini onaylayın",
              "Akşam: Günlük raporları inceleyin",
              "Haftalık: Stok durumunu kontrol edin ve tedarik planlayın",
            ],
          },
          {
            title: "Menü Yapısı",
            description: "Sol menüdeki bölümlerin kısa açıklaması.",
            steps: [
              "Dashboard: Günlük özet ve kritik uyarılar",
              "Otel & Yapı: Otel, kat, oda, setup ve kullanıcı yönetimi",
              "Ürün & Stok: Ürün tanımları, stok ve zimmet işlemleri",
              "Minibar: Minibar işlemleri ve dolum talepleri",
              "AI & Analitik: Yapay zeka destekli analizler",
              "Raporlar: Tüm raporlama ve analiz araçları",
              "Sistem: Ayarlar, loglar ve güvenlik",
            ],
          },
        ],
      },
      {
        id: "otel-yapi",
        title: "Otel & Yapı Yönetimi",
        icon: "fa-hotel",
        color: "blue",
        items: [
          {
            title: "Otel Tanımlama",
            description:
              "Sisteme yeni otel ekleyin, mevcut otelleri düzenleyin veya pasife alın.",
            steps: [
              'Sol menüden "Otel & Yapı" bölümünü açın',
              '"Oteller" seçeneğine tıklayın',
              '"Yeni Otel Ekle" butonuna tıklayın',
              "Otel adı, adresi ve iletişim bilgilerini girin",
              "Logo yükleyin (opsiyonel)",
              "Kaydet butonuna tıklayın",
            ],
          },
          {
            title: "Kat Tanımlama",
            description:
              "Otellere kat ekleyin ve düzenleyin. Her otel için ayrı kat yapısı oluşturabilirsiniz.",
            steps: [
              '"Katlar" sayfasına gidin',
              "Üst kısımdan otel seçin",
              "Kat numarası ve adı girin (örn: 1, Zemin Kat)",
              '"Ekle" butonuna tıklayın',
              "Katlar otomatik sıralanır",
            ],
          },
          {
            title: "Oda Tanımlama",
            description:
              "Katlara oda ekleyin, oda tiplerini belirleyin. QR kodlar otomatik oluşturulur.",
            steps: [
              '"Odalar" sayfasına gidin',
              "Otel ve kat seçin",
              "Oda numarası girin (örn: 101, 102)",
              "Oda tipini seçin (Setup ile eşleşir)",
              "QR kod otomatik oluşturulur",
              "Toplu oda ekleme için Excel yükleyebilirsiniz",
            ],
          },
          {
            title: "Setup Yönetimi",
            description:
              "Minibar şablonları oluşturun. Her oda tipi için farklı setup tanımlayabilirsiniz.",
            steps: [
              '"Setup\'lar" sayfasına gidin',
              '"Yeni Setup" butonuna tıklayın',
              "Setup adı girin (örn: Standart Oda, Suite)",
              "Ürünleri ve adetleri belirleyin",
              "Oda tiplerine atayın",
              "Değişiklikler tüm odalara yansır",
            ],
          },
          {
            title: "Kullanıcı Yönetimi",
            description:
              "Sistem kullanıcılarını ekleyin, düzenleyin ve yetkilendirin.",
            steps: [
              '"Kullanıcılar" sayfasına gidin',
              '"Yeni Kullanıcı" butonuna tıklayın',
              "Ad, soyad, email ve şifre girin",
              "Rol seçin: Sistem Yöneticisi, Depo Sorumlusu veya Kat Sorumlusu",
              "Otel ataması yapın (birden fazla otel seçilebilir)",
              "Kullanıcıyı aktif/pasif yapabilirsiniz",
            ],
          },
        ],
      },
      {
        id: "urun-stok",
        title: "Ürün & Stok Yönetimi",
        icon: "fa-boxes",
        color: "emerald",
        items: [
          {
            title: "Ürün Grupları Oluşturma",
            description:
              "Ürünleri kategorilere ayırarak düzenli bir yapı oluşturun.",
            steps: [
              '"Ürün Grupları" sayfasına gidin',
              '"Yeni Grup" butonuna tıklayın',
              "Grup adı girin (örn: İçecekler, Atıştırmalıklar)",
              "Açıklama ekleyin (opsiyonel)",
              "Raporlarda grup bazlı analiz yapabilirsiniz",
            ],
          },
          {
            title: "Ürün Tanımlama",
            description:
              "Sisteme yeni ürün ekleyin. Barkod, fiyat ve stok bilgilerini girin.",
            steps: [
              '"Ürünler" sayfasına gidin',
              '"Yeni Ürün" butonuna tıklayın',
              "Ürün grubunu seçin",
              "Ürün adı, barkod ve birim girin",
              "Alış fiyatı (maliyet) girin",
              "Satış fiyatı girin",
              "Kritik stok seviyesi belirleyin",
            ],
          },
          {
            title: "Depo Stok Takibi",
            description:
              "Tüm otellerin depo stoklarını görüntüleyin ve yönetin.",
            steps: [
              '"Depo Stokları" sayfasına gidin',
              "Otel seçerek filtreleyin",
              "Ürün adı veya barkod ile arayın",
              "Kritik stokları kırmızı renkte görün",
              "Excel'e aktarın",
            ],
          },
          {
            title: "İlk Stok Yükleme (FIFO)",
            description:
              "Otellere ilk stok girişi yapın. FIFO yöntemi ile stok takibi.",
            steps: [
              '"İlk Stok Yükleme" sayfasına gidin',
              "Otel seçin",
              "Ürün ve miktar girin",
              "Alış fiyatını belirleyin",
              "Stok girişini onaylayın",
            ],
          },
          {
            title: "Zimmet Yönetimi",
            description: "Kat sorumlularına ürün zimmetleyin ve takip edin.",
            steps: [
              '"Zimmetler" sayfasına gidin',
              "Otel ve personel seçin",
              "Zimmetlenecek ürünleri seçin",
              "Miktar belirleyin",
              "Zimmet işlemini onaylayın",
              "Zimmet geçmişini görüntüleyin",
            ],
          },
        ],
      },
      {
        id: "doluluk-gorev",
        title: "Doluluk & Görev Yönetimi",
        icon: "fa-tasks",
        color: "amber",
        items: [
          {
            title: "Doluluk Yükleme",
            description:
              "Opera sisteminden alınan Excel ile günlük doluluk bilgilerini yükleyin.",
            steps: [
              '"Doluluk Yönetimi" sayfasına gidin',
              "Otel seçin",
              "Dosya tipini seçin:",
              "  • IN HOUSE: Kalmaya devam eden misafirler",
              "  • ARRIVALS: Bugün giriş yapacaklar",
              "  • DEPARTURES: Bugün çıkış yapacaklar",
              "Excel dosyasını yükleyin",
              "Önizleme yapın ve verileri kontrol edin",
              "Onaylayın - Görevler otomatik oluşur",
            ],
          },
          {
            title: "Görev Sistemi",
            description:
              "Doluluk yüklendiğinde kat sorumlularına otomatik görev atanır.",
            steps: [
              "Doluluk yüklendiğinde sistem otomatik görev oluşturur",
              "Her oda için minibar kontrol görevi atanır",
              "Kat sorumlusu görevleri mobil uygulamadan görür",
              "Görev tamamlandığında sistem güncellenir",
              "DND (Rahatsız Etmeyin) durumu işaretlenebilir",
            ],
          },
          {
            title: "Görev Takibi",
            description:
              "Kat sorumlusu görevlerini ve performansını takip edin.",
            steps: [
              '"Günlük Görev Detay" raporuna gidin',
              "Tarih aralığı ve otel seçin",
              "Tamamlanma oranlarını görün",
              "DND ve incomplete durumları takip edin",
              "Personel bazlı performans analizi yapın",
            ],
          },
        ],
      },
      {
        id: "minibar",
        title: "Minibar Operasyonları",
        icon: "fa-wine-bottle",
        color: "purple",
        items: [
          {
            title: "Minibar Kontrol Süreci",
            description: "Kat sorumlusunun minibar kontrol işlem akışı.",
            steps: [
              "Kat sorumlusu görev listesinden oda seçer",
              "Odaya gider ve minibarı kontrol eder",
              "Setup'a göre eksik ürünleri görür",
              "Eksikleri zimmetinden tamamlar",
              "Tüketim kaydı otomatik oluşur",
              "Görevi tamamlar",
            ],
          },
          {
            title: "Tüketim Takibi",
            description: "Minibar tüketimlerini izleyin ve raporlayın.",
            steps: [
              '"Minibar İşlemleri" sayfasına gidin',
              "Tarih aralığı ve otel seçin",
              "Oda bazlı tüketimleri görün",
              "Ürün bazlı analiz yapın",
              "Raporları Excel/PDF olarak indirin",
            ],
          },
          {
            title: "Dolum Talepleri",
            description: "Kat sorumlularının stok talep işlemlerini yönetin.",
            steps: [
              '"Dolum Talepleri" sayfasına gidin',
              "Bekleyen talepleri görün",
              "Talep detaylarını inceleyin",
              "Onaylayın veya reddedin",
              "Onaylanan talepler zimmet olarak işlenir",
            ],
          },
        ],
      },
      {
        id: "ai-analitik",
        title: "AI & Analitik",
        icon: "fa-brain",
        color: "violet",
        items: [
          {
            title: "ML Analiz Sistemi Nedir?",
            description:
              "Yapay zeka destekli analiz ve tahmin sistemi. Minibar operasyonlarınızı optimize etmenize yardımcı olur.",
            steps: [
              "Sol menüden 'AI & Analitik' bölümünü açın",
              "'ML Analiz Sistemi' seçeneğine tıklayın",
              "Dashboard'da genel AI metriklerini görün",
              "Sistem otomatik olarak verilerinizi analiz eder",
              "Öneriler ve tahminler sunar",
            ],
          },
          {
            title: "Talep Tahmini",
            description:
              "Geçmiş verilere dayanarak gelecekteki ürün taleplerini tahmin edin.",
            steps: [
              "ML Dashboard'a gidin",
              "'Talep Tahmini' bölümünü seçin",
              "Otel ve tarih aralığı belirleyin",
              "Sistem geçmiş tüketim verilerini analiz eder",
              "Önümüzdeki dönem için tahminler sunar",
              "Stok planlamasında bu tahminleri kullanın",
            ],
          },
          {
            title: "Anomali Tespiti",
            description:
              "Olağandışı tüketim veya stok hareketlerini otomatik tespit edin.",
            steps: [
              "ML Dashboard'da 'Anomaliler' bölümünü görün",
              "Kırmızı ile işaretlenen anormal durumları inceleyin",
              "Örnek: Beklenenden çok yüksek tüketim",
              "Örnek: Ani stok düşüşleri",
              "Detaylara tıklayarak araştırın",
            ],
          },
          {
            title: "Performans Önerileri",
            description: "AI'ın operasyonel iyileştirme önerilerini görün.",
            steps: [
              "Dashboard'daki 'Öneriler' kartını inceleyin",
              "Stok optimizasyonu önerileri",
              "Personel verimliliği önerileri",
              "Setup iyileştirme önerileri",
              "Önerileri uygulayarak verimliliği artırın",
            ],
          },
        ],
      },
      {
        id: "raporlar",
        title: "Raporlar & Analiz",
        icon: "fa-chart-bar",
        color: "cyan",
        items: [
          {
            title: "Doluluk Raporları",
            description:
              "Otel doluluk oranlarını analiz edin. Hangi dönemlerde yoğunluk olduğunu görün.",
            steps: [
              '"Raporlar" menüsünden "Doluluk Raporları"nı seçin',
              "Otel ve tarih aralığı seçin",
              "Günlük/haftalık/aylık doluluk oranlarını görün",
              "Grafiklerde trend analizi yapın",
              "Excel'e aktararak detaylı analiz yapın",
            ],
          },
          {
            title: "Stok Raporları",
            description:
              "Depo ve zimmet stoklarını raporlayın. Kritik seviyeleri takip edin.",
            steps: [
              '"Stok Raporları" sayfasına gidin',
              "Rapor tipini seçin: Mevcut Stok veya Hareketler",
              "Otel bazlı filtreleyin",
              "Kritik stokları kırmızı renkte görün",
              "Stok devir hızını analiz edin",
              "Excel/PDF olarak indirin",
            ],
          },
          {
            title: "Zimmet Raporları",
            description: "Personel zimmetlerini ve kullanımlarını takip edin.",
            steps: [
              '"Zimmet Raporları" sayfasına gidin',
              "Personel veya ürün bazlı filtreleyin",
              "Tarih aralığı belirleyin",
              "Zimmet dağılımını görün",
              "İade ve kullanım oranlarını inceleyin",
            ],
          },
          {
            title: "Performans Raporları",
            description:
              "Personel ve otel performansını ölçün ve karşılaştırın.",
            steps: [
              '"Performans Raporları" sayfasına gidin',
              "Otel ve personel seçin",
              "Görev tamamlama oranlarını görün",
              "Ortalama tamamlama sürelerini inceleyin",
              "En iyi performans gösteren personeli belirleyin",
            ],
          },
          {
            title: "Otel Zimmet Stokları",
            description: "Her otelin zimmet stok durumunu görün.",
            steps: [
              '"Otel Zimmet Stokları" raporuna gidin',
              "Otel seçin",
              "Personel bazlı zimmet stoklarını görün",
              "Kritik seviyedeki ürünleri takip edin",
            ],
          },
          {
            title: "Kat Sorumlusu Kullanım",
            description:
              "Kat sorumlularının ürün kullanım detaylarını inceleyin.",
            steps: [
              '"Kat Sorumlusu Kullanım" raporuna gidin',
              "Personel ve tarih aralığı seçin",
              "Kullanılan ürün miktarlarını görün",
              "İade edilen ürünleri takip edin",
              "Verimlilik analizi yapın",
            ],
          },
          {
            title: "Oda Bazlı Tüketim",
            description: "Hangi odaların en çok tüketim yaptığını görün.",
            steps: [
              '"Oda Bazlı Tüketim" raporuna gidin',
              "Otel seçin (zorunlu)",
              "Tarih aralığı belirleyin",
              "En çok tüketen odaları listeleyin",
              "Ürün ve tutar bazlı sıralama yapın",
            ],
          },
          {
            title: "Günlük Görev Detay",
            description:
              "Günlük görev tamamlama durumlarını detaylı inceleyin.",
            steps: [
              '"Günlük Görev Detay" raporuna gidin',
              "Tarih aralığı ve otel seçin",
              "Tamamlanan/bekleyen görevleri görün",
              "DND (Rahatsız Etmeyin) durumlarını takip edin",
              "Personel bazlı performans analizi yapın",
            ],
          },
          {
            title: "Otel Karşılaştırma",
            description: "Birden fazla oteli yan yana karşılaştırın.",
            steps: [
              '"Otel Karşılaştırma" raporuna gidin',
              "Karşılaştırılacak otelleri seçin",
              "Doluluk, tüketim ve performans metriklerini görün",
              "En iyi performans gösteren oteli belirleyin",
            ],
          },
        ],
      },
      {
        id: "sistem",
        title: "Sistem & Güvenlik",
        icon: "fa-shield-alt",
        color: "red",
        items: [
          {
            title: "Sistem Ayarları",
            description: "Genel sistem ayarlarını yapılandırın.",
            steps: [
              '"Sistem Ayarları" sayfasına gidin',
              "Email ayarlarını yapın (SMTP)",
              "Bildirim tercihlerini belirleyin",
              "Otomatik görev ayarlarını düzenleyin",
            ],
          },
          {
            title: "Audit Trail",
            description: "Tüm işlemlerin geçmişini görün ve denetleyin.",
            steps: [
              '"Audit Trail" sayfasına gidin',
              "Kullanıcı veya işlem tipine göre filtreleyin",
              "Tarih aralığı belirleyin",
              "Detaylı log görüntüleyin",
              "Şüpheli aktiviteleri tespit edin",
            ],
          },
          {
            title: "Sistem Logları",
            description: "Teknik hata ve sistem loglarını inceleyin.",
            steps: [
              '"Sistem Logları" sayfasına gidin',
              "Log seviyesine göre filtreleyin (Error, Warning, Info)",
              "Hata detaylarını inceleyin",
              "Logları indirin",
            ],
          },
        ],
      },
    ],
  },

  // Depo Sorumlusu için özel rehber
  depo_sorumlusu: {
    sections: [
      {
        id: "gunluk-isler",
        title: "Günlük İşler",
        icon: "fa-calendar-day",
        color: "blue",
        items: [
          {
            title: "Gün Başlangıcı",
            description: "Her güne bu adımlarla başlayın.",
            steps: [
              "Dashboard'dan günlük özeti kontrol edin",
              "Bekleyen kat sorumlusu siparişlerini görün",
              "Kritik stok uyarılarını inceleyin",
              "Doluluk verilerini yükleyin (varsa)",
            ],
          },
          {
            title: "Doluluk Yükleme",
            description:
              "Opera'dan alınan Excel ile günlük doluluk bilgilerini yükleyin.",
            steps: [
              '"Doluluk Yönetimi" sayfasına gidin',
              "Otelinizi seçin",
              "Dosya tipini seçin:",
              "  • IN HOUSE: Kalmaya devam edenler",
              "  • ARRIVALS: Bugün giriş yapacaklar",
              "  • DEPARTURES: Bugün çıkış yapacaklar",
              "Excel dosyasını sürükleyip bırakın",
              "Önizleme ekranında verileri kontrol edin",
              "Onaylayın - Görevler otomatik oluşur",
            ],
          },
          {
            title: "Günlük Doluluk Görüntüleme",
            description: "Yüklenen doluluk verilerini kontrol edin.",
            steps: [
              '"Günlük Doluluk" sayfasına gidin',
              "Tarih seçin",
              "Oda durumlarını görün:",
              "  • Dolu odalar (yeşil)",
              "  • Boş odalar (gri)",
              "  • Giriş yapacaklar (mavi)",
              "  • Çıkış yapacaklar (turuncu)",
            ],
          },
        ],
      },
      {
        id: "stok-yonetimi",
        title: "Stok Yönetimi",
        icon: "fa-boxes",
        color: "emerald",
        items: [
          {
            title: "Stok Kontrolü",
            description: "Depo stoklarınızı görüntüleyin ve yönetin.",
            steps: [
              '"Stoklarım" sayfasına gidin',
              "Ürün adı veya barkod ile arayın",
              "Mevcut stok miktarlarını görün",
              "Kritik seviyedeki ürünler kırmızı gösterilir",
              "Excel'e aktarabilirsiniz",
            ],
          },
          {
            title: "Ana Depodan Tedarik",
            description: "Ana depodan ürün tedarik edin.",
            steps: [
              '"Ana Depo Tedarik" sayfasına gidin',
              "Tedarik edilecek ürünleri seçin",
              "Miktar belirleyin",
              "Tedarik talebini gönderin",
              "Onay sonrası stoklar güncellenir",
            ],
          },
          {
            title: "Stok Sayımı",
            description: "Fiziksel stok sayımı yapın ve sistemi güncelleyin.",
            steps: [
              '"Stoklarım" sayfasına gidin',
              "Sayım yapılacak ürünü bulun",
              "Gerçek miktarı girin",
              "Fark varsa düzeltme kaydı oluşur",
              "Sayım geçmişi tutulur",
            ],
          },
        ],
      },
      {
        id: "zimmet-islemleri",
        title: "Zimmet İşlemleri",
        icon: "fa-clipboard-check",
        color: "amber",
        items: [
          {
            title: "Kat Sorumlusuna Zimmet",
            description: "Kat sorumlularına ürün zimmetleyin.",
            steps: [
              '"Personel Zimmet" sayfasına gidin',
              "Kat sorumlusunu seçin",
              "Zimmetlenecek ürünleri seçin",
              "Her ürün için miktar girin",
              '"Zimmetle" butonuna tıklayın',
              "Zimmet fişi otomatik oluşur",
            ],
          },
          {
            title: "Sipariş Onaylama",
            description: "Kat sorumlularından gelen siparişleri yönetin.",
            steps: [
              '"Kat Sorumlusu Siparişleri" sayfasına gidin',
              "Bekleyen siparişleri görün",
              "Sipariş detaylarını inceleyin",
              "Stok durumunu kontrol edin",
              "Onaylayın veya reddedin",
              "Onaylanan siparişler zimmet olarak işlenir",
            ],
          },
          {
            title: "Zimmet Geçmişi",
            description: "Geçmiş zimmet işlemlerini görüntüleyin.",
            steps: [
              '"Personel Zimmet" sayfasında geçmişi görün',
              "Tarih aralığı filtreleyin",
              "Personel bazlı arayın",
              "Zimmet detaylarını inceleyin",
            ],
          },
        ],
      },
      {
        id: "raporlar",
        title: "Raporlar",
        icon: "fa-chart-bar",
        color: "cyan",
        items: [
          {
            title: "Depo Raporları",
            description: "Depo stok ve hareket raporlarını görüntüleyin.",
            steps: [
              '"Raporlar" sayfasına gidin',
              "Rapor tipini seçin",
              "Tarih aralığı belirleyin",
              "Filtreleri uygulayın",
              "Excel/PDF olarak indirin",
            ],
          },
          {
            title: "Kat Tüketim Raporu",
            description: "Kat bazlı tüketim analizi yapın.",
            steps: [
              '"Kat Tüketim Raporu" sayfasına gidin',
              "Otel ve kat seçin",
              "Tarih aralığı belirleyin",
              "Ürün bazlı tüketimleri görün",
              "Karşılaştırmalı analiz yapın",
            ],
          },
          {
            title: "Otel Zimmet Stokları",
            description: "Otel bazlı zimmet stok durumunu görün.",
            steps: [
              '"Otel Zimmet Stokları" raporuna gidin',
              "Otelinizi seçin",
              "Personel bazlı stokları görün",
              "Kritik ürünleri takip edin",
            ],
          },
          {
            title: "Kat Sorumlusu Kullanım",
            description: "Kat sorumlularının ürün kullanımını analiz edin.",
            steps: [
              '"Kat Sorumlusu Kullanım" raporuna gidin',
              "Personel seçin",
              "Tarih aralığı belirleyin",
              "Kullanım ve iade miktarlarını görün",
            ],
          },
          {
            title: "Oda Bazlı Tüketim",
            description: "Oda bazlı tüketim analizi yapın.",
            steps: [
              '"Oda Bazlı Tüketim" raporuna gidin',
              "Otel seçin (zorunlu)",
              "Tarih aralığı belirleyin",
              "En çok tüketen odaları görün",
              "Tutar bazlı sıralama yapın",
            ],
          },
          {
            title: "Günlük Görev Detay",
            description: "Kat sorumlusu görev performansını takip edin.",
            steps: [
              '"Günlük Görev Detay" raporuna gidin',
              "Tarih aralığı seçin",
              "Tamamlanma oranlarını görün",
              "DND ve incomplete durumları takip edin",
              "Personel bazlı performans analizi yapın",
            ],
          },
        ],
      },
      {
        id: "ipuclari",
        title: "İpuçları & Kısayollar",
        icon: "fa-lightbulb",
        color: "yellow",
        items: [
          {
            title: "Hızlı İşlemler",
            description: "Günlük işlerinizi hızlandıracak ipuçları.",
            steps: [
              "Dashboard'daki kartlara tıklayarak hızlı erişim sağlayın",
              "Barkod okuyucu ile ürün arayın",
              "Sık kullandığınız raporları favorilere ekleyin",
              "Excel şablonlarını indirip tekrar kullanın",
            ],
          },
          {
            title: "Kritik Stok Takibi",
            description: "Stok seviyelerini proaktif takip edin.",
            steps: [
              "Dashboard'da kritik stok uyarılarını kontrol edin",
              "Haftalık stok sayımı yapın",
              "Mevsimsel talep değişikliklerini öngörün",
              "Ana depodan zamanında tedarik edin",
            ],
          },
          {
            title: "Verimli Zimmet",
            description: "Zimmet işlemlerini optimize edin.",
            steps: [
              "Sabah erken saatte zimmet yapın",
              "Kat sorumlularının ihtiyaçlarını önceden belirleyin",
              "Toplu zimmet özelliğini kullanın",
              "Zimmet fişlerini saklayın",
            ],
          },
        ],
      },
    ],
  },
};

// Sistem yöneticisi için admin rehberini kullan
SYSTEM_GUIDE_BY_ROLE.sistem_yoneticisi = SYSTEM_GUIDE_BY_ROLE.admin;
// ============================================
// SAYFA BAZLI MİNİ KILAVUZ FONKSİYONLARI
// ============================================

class PageGuide {
  constructor() {
    this.isOpen = false;
    this.currentEndpoint = null;
    this.userRole = null;
    this.init();
  }

  init() {
    this.currentEndpoint =
      document.body.dataset.endpoint || window.CURRENT_ENDPOINT;
    this.userRole = document.body.dataset.userRole || window.USER_ROLE;

    // Kılavuz butonunu oluştur
    this.createFloatingButton();
    this.createGuidePanel();
    this.checkFirstVisit();
  }

  createFloatingButton() {
    const btn = document.createElement("button");
    btn.id = "page-guide-btn";
    btn.className =
      "fixed bottom-6 right-6 z-50 w-14 h-14 bg-gradient-to-br from-indigo-500 to-purple-600 text-white rounded-full shadow-lg hover:shadow-xl transform hover:scale-105 transition-all duration-300 flex items-center justify-center group";
    btn.innerHTML = `
      <i class="fas fa-question text-xl group-hover:hidden"></i>
      <i class="fas fa-lightbulb text-xl hidden group-hover:block"></i>
      <span class="absolute -top-1 -right-1 w-5 h-5 bg-amber-400 rounded-full flex items-center justify-center text-xs font-bold text-amber-900 animate-pulse" id="guide-badge">?</span>
    `;
    btn.onclick = () => this.toggle();
    document.body.appendChild(btn);
  }

  createGuidePanel() {
    const guide = this.getGuideForCurrentPage();
    if (!guide) return;

    const panel = document.createElement("div");
    panel.id = "page-guide-panel";
    panel.className =
      "fixed bottom-24 right-6 z-50 w-80 bg-white dark:bg-slate-800 rounded-2xl shadow-2xl border border-slate-200 dark:border-slate-700 transform translate-y-4 opacity-0 pointer-events-none transition-all duration-300";

    panel.innerHTML = `
      <div class="p-4 bg-gradient-to-r from-indigo-500 to-purple-600 rounded-t-2xl">
        <div class="flex items-center justify-between">
          <div class="flex items-center gap-3">
            <div class="w-10 h-10 bg-white/20 rounded-xl flex items-center justify-center">
              <i class="fas ${guide.icon} text-white"></i>
            </div>
            <div>
              <h3 class="text-white font-semibold">${guide.title}</h3>
              <p class="text-white/70 text-xs">Sayfa Kılavuzu</p>
            </div>
          </div>
          <button onclick="pageGuide.close()" class="w-8 h-8 bg-white/20 rounded-lg flex items-center justify-center text-white hover:bg-white/30 transition">
            <i class="fas fa-times"></i>
          </button>
        </div>
      </div>
      <div class="p-4 space-y-3 max-h-64 overflow-y-auto">
        ${guide.tips
          .map(
            (tip) => `
          <div class="flex items-start gap-3 p-3 bg-slate-50 dark:bg-slate-900/50 rounded-xl hover:bg-indigo-50 dark:hover:bg-indigo-900/20 transition group">
            <div class="w-8 h-8 bg-indigo-100 dark:bg-indigo-900/30 rounded-lg flex items-center justify-center flex-shrink-0 group-hover:bg-indigo-200 dark:group-hover:bg-indigo-800/50 transition">
              <i class="fas ${tip.icon} text-indigo-600 dark:text-indigo-400 text-sm"></i>
            </div>
            <p class="text-sm text-slate-700 dark:text-slate-300 leading-relaxed">${tip.text}</p>
          </div>
        `
          )
          .join("")}
      </div>
      <div class="p-3 border-t border-slate-200 dark:border-slate-700 flex items-center justify-between">
        <button onclick="pageGuide.dontShowAgain()" class="text-xs text-slate-500 hover:text-slate-700 dark:hover:text-slate-300">
          <i class="fas fa-eye-slash mr-1"></i>Bu sayfada gösterme
        </button>
        <button onclick="openSystemGuide()" class="text-xs text-indigo-600 dark:text-indigo-400 hover:text-indigo-700 font-medium">
          <i class="fas fa-book mr-1"></i>Tam Kılavuz
        </button>
      </div>
    `;

    document.body.appendChild(panel);
  }

  getGuideForCurrentPage() {
    const guide = PAGE_GUIDES[this.currentEndpoint];
    if (!guide) return null;

    // Rol kontrolü
    if (guide.roles && !guide.roles.includes(this.userRole)) {
      return null;
    }
    return guide;
  }

  toggle() {
    this.isOpen ? this.close() : this.open();
  }

  open() {
    const panel = document.getElementById("page-guide-panel");
    const badge = document.getElementById("guide-badge");
    if (panel) {
      panel.classList.remove(
        "translate-y-4",
        "opacity-0",
        "pointer-events-none"
      );
      panel.classList.add(
        "translate-y-0",
        "opacity-100",
        "pointer-events-auto"
      );
      this.isOpen = true;
      if (badge) badge.classList.add("hidden");
    }
  }

  close() {
    const panel = document.getElementById("page-guide-panel");
    if (panel) {
      panel.classList.add("translate-y-4", "opacity-0", "pointer-events-none");
      panel.classList.remove(
        "translate-y-0",
        "opacity-100",
        "pointer-events-auto"
      );
      this.isOpen = false;
    }
  }

  checkFirstVisit() {
    const key = `guide_shown_${this.currentEndpoint}`;
    const shown = localStorage.getItem(key);
    if (!shown && this.getGuideForCurrentPage()) {
      setTimeout(() => this.open(), 1500);
      localStorage.setItem(key, "true");
    }
  }

  dontShowAgain() {
    const key = `guide_disabled_${this.currentEndpoint}`;
    localStorage.setItem(key, "true");
    this.close();
    const btn = document.getElementById("page-guide-btn");
    if (btn) btn.style.display = "none";
  }
}
// ============================================
// GENEL SİSTEM REHBERİ MODAL - ROL BAZLI
// ============================================

function getCurrentUserRole() {
  return document.body.dataset.userRole || window.USER_ROLE || "depo_sorumlusu";
}

function getSystemGuideForRole() {
  const role = getCurrentUserRole();
  return SYSTEM_GUIDE_BY_ROLE[role] || SYSTEM_GUIDE_BY_ROLE.depo_sorumlusu;
}

function openSystemGuide() {
  const existing = document.getElementById("system-guide-modal");
  if (existing) existing.remove();

  const guide = getSystemGuideForRole();
  const role = getCurrentUserRole();
  const roleTitle =
    role === "depo_sorumlusu" ? "Depo Sorumlusu" : "Sistem Yöneticisi";

  const modal = document.createElement("div");
  modal.id = "system-guide-modal";
  modal.className =
    "fixed inset-0 z-[100] flex items-center justify-center p-4";
  modal.innerHTML = `
    <div class="absolute inset-0 bg-black/60 backdrop-blur-sm" onclick="closeSystemGuide()"></div>
    <div class="relative w-full max-w-5xl max-h-[90vh] bg-white dark:bg-slate-900 rounded-2xl shadow-2xl overflow-hidden flex flex-col animate-scale-in">
      <!-- Header -->
      <div class="p-6 bg-gradient-to-r from-indigo-600 via-purple-600 to-pink-600 flex-shrink-0">
        <div class="flex items-center justify-between">
          <div class="flex items-center gap-4">
            <div class="w-14 h-14 bg-white/20 rounded-2xl flex items-center justify-center">
              <i class="fas fa-book-open text-2xl text-white"></i>
            </div>
            <div>
              <h2 class="text-2xl font-bold text-white">Sistem Kullanım Kılavuzu</h2>
              <p class="text-white/70">${roleTitle} Paneli - Detaylı Rehber</p>
            </div>
          </div>
          <button onclick="closeSystemGuide()" class="w-10 h-10 bg-white/20 rounded-xl flex items-center justify-center text-white hover:bg-white/30 transition">
            <i class="fas fa-times text-xl"></i>
          </button>
        </div>
      </div>
      
      <!-- Content -->
      <div class="flex-1 overflow-hidden flex">
        <!-- Sidebar -->
        <div class="w-64 bg-slate-50 dark:bg-slate-800/50 border-r border-slate-200 dark:border-slate-700 overflow-y-auto flex-shrink-0">
          <div class="p-4 space-y-2">
            ${guide.sections
              .map(
                (section, i) => `
              <button onclick="showGuideSection('${section.id}')" 
                class="guide-section-btn w-full flex items-center gap-3 p-3 rounded-xl text-left transition hover:bg-white dark:hover:bg-slate-700 ${
                  i === 0 ? "bg-white dark:bg-slate-700 shadow-sm" : ""
                }"
                data-section="${section.id}">
                <div class="w-10 h-10 bg-${section.color}-100 dark:bg-${
                  section.color
                }-900/30 rounded-xl flex items-center justify-center">
                  <i class="fas ${section.icon} text-${
                  section.color
                }-600 dark:text-${section.color}-400"></i>
                </div>
                <span class="font-medium text-slate-700 dark:text-slate-200 text-sm">${
                  section.title
                }</span>
              </button>
            `
              )
              .join("")}
          </div>
        </div>
        
        <!-- Main Content -->
        <div class="flex-1 overflow-y-auto p-6" id="guide-content">
          ${renderGuideSection(guide.sections[0])}
        </div>
      </div>
      
      <!-- Footer -->
      <div class="p-4 border-t border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800/50 flex-shrink-0">
        <div class="flex items-center justify-between">
          <p class="text-sm text-slate-500 dark:text-slate-400">
            <i class="fas fa-info-circle mr-1"></i>
            Detaylı yardım için sistem yöneticinize başvurun
          </p>
          <button onclick="closeSystemGuide()" class="px-4 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 transition text-sm font-medium">
            <i class="fas fa-check mr-2"></i>Anladım
          </button>
        </div>
      </div>
    </div>
  `;

  document.body.appendChild(modal);
  document.body.style.overflow = "hidden";
}

function closeSystemGuide() {
  const modal = document.getElementById("system-guide-modal");
  if (modal) {
    modal.remove();
    document.body.style.overflow = "";
  }
}

function showGuideSection(sectionId) {
  const guide = getSystemGuideForRole();
  const section = guide.sections.find((s) => s.id === sectionId);
  if (!section) return;

  // Aktif butonu güncelle
  document.querySelectorAll(".guide-section-btn").forEach((btn) => {
    btn.classList.remove("bg-white", "dark:bg-slate-700", "shadow-sm");
  });
  document
    .querySelector(`[data-section="${sectionId}"]`)
    ?.classList.add("bg-white", "dark:bg-slate-700", "shadow-sm");

  // İçeriği güncelle
  document.getElementById("guide-content").innerHTML =
    renderGuideSection(section);
}

function renderGuideSection(section) {
  return `
    <div class="space-y-6">
      <div class="flex items-center gap-4 pb-4 border-b border-slate-200 dark:border-slate-700">
        <div class="w-14 h-14 bg-${section.color}-100 dark:bg-${
    section.color
  }-900/30 rounded-2xl flex items-center justify-center">
          <i class="fas ${section.icon} text-2xl text-${
    section.color
  }-600 dark:text-${section.color}-400"></i>
        </div>
        <div>
          <h3 class="text-xl font-bold text-slate-900 dark:text-white">${
            section.title
          }</h3>
          <p class="text-slate-500 dark:text-slate-400">${
            section.items.length
          } konu</p>
        </div>
      </div>
      
      <div class="grid gap-4">
        ${section.items
          .map(
            (item, i) => `
          <div class="bg-slate-50 dark:bg-slate-800/50 rounded-xl p-5 hover:shadow-md transition">
            <div class="flex items-start gap-4">
              <div class="w-10 h-10 bg-${section.color}-100 dark:bg-${
              section.color
            }-900/30 rounded-xl flex items-center justify-center flex-shrink-0">
                <span class="text-${section.color}-600 dark:text-${
              section.color
            }-400 font-bold">${i + 1}</span>
              </div>
              <div class="flex-1">
                <h4 class="font-semibold text-slate-900 dark:text-white mb-1">${
                  item.title
                }</h4>
                <p class="text-sm text-slate-600 dark:text-slate-400 mb-3">${
                  item.description
                }</p>
                <div class="space-y-2">
                  ${item.steps
                    .map(
                      (step, j) => `
                    <div class="flex items-start gap-2 text-sm">
                      <span class="w-5 h-5 bg-${section.color}-100 dark:bg-${
                        section.color
                      }-900/30 rounded-full flex items-center justify-center flex-shrink-0 text-xs font-medium text-${
                        section.color
                      }-600 dark:text-${section.color}-400">${j + 1}</span>
                      <span class="text-slate-700 dark:text-slate-300">${step}</span>
                    </div>
                  `
                    )
                    .join("")}
                </div>
              </div>
            </div>
          </div>
        `
          )
          .join("")}
      </div>
    </div>
  `;
}

// ============================================
// INIT
// ============================================

let pageGuide;

document.addEventListener("DOMContentLoaded", function () {
  const userRole = document.body.dataset.userRole || window.USER_ROLE;
  if (
    userRole === "sistem_yoneticisi" ||
    userRole === "depo_sorumlusu" ||
    userRole === "admin"
  ) {
    pageGuide = new PageGuide();
  }
});

// ESC tuşu ile modal kapat
document.addEventListener("keydown", function (e) {
  if (e.key === "Escape") {
    closeSystemGuide();
    if (pageGuide) pageGuide.close();
  }
});
