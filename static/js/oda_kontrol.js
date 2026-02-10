/**
 * Oda Kontrol - Setup Bazlı Sistem
 * YENİ MANTIK: Minibar her zaman dolu kabul edilir
 * - EKLE = Tüketim ikamesi (tüketim kaydedilir)
 * - EKSTRA = Setup üstü ekleme (tüketim kaydedilmez)
 */

// Global değişkenler
let mevcutOdaId = null;
let mevcutSetuplar = [];
let zimmetStoklar = {};
let modalData = {};
let acikAkordiyonlar = new Set(); // Açık akordiyonları takip et
let mevcutGorevDetayId = null; // Görev detay ID (görev listesinden gelirse)
let katDetayGeriDonUrl = null; // Kat detaylarından gelindiyse geri dönüş URL'i

// Sayfa yüklendiğinde
document.addEventListener("DOMContentLoaded", async function () {
  console.log("✅ Oda Kontrol sistemi yüklendi");

  const katSelect = document.getElementById("kat_id");
  const odaSelect = document.getElementById("oda_id");

  if (katSelect) {
    katSelect.addEventListener("change", katSecildi);
  }

  if (odaSelect) {
    odaSelect.addEventListener("change", odaSecildi);
  }

  // URL parametrelerinden QR kod ile gelen kat ve oda bilgilerini al
  const urlParams = new URLSearchParams(window.location.search);
  const qrKatId = urlParams.get("kat_id");
  const qrOdaId = urlParams.get("oda_id");
  const gorevOdaId = urlParams.get("gorev_oda_id");
  const gorevDetayId = urlParams.get("gorev_detay_id");
  const fromKatDetay = urlParams.get("from_kat_detay");

  // Kat detaylarından gelindiyse geri dön URL'ini kaydet
  if (fromKatDetay === "1" && qrKatId) {
    katDetayGeriDonUrl = "/kat-doluluk/" + qrKatId;
    const katGeriButonu = document.getElementById("kat_gorunumu_geri_butonu");
    const katGeriLink = document.getElementById("kat_gorunumu_link");
    if (katGeriButonu && katGeriLink) {
      katGeriLink.href = katDetayGeriDonUrl;
      katGeriButonu.classList.remove("hidden");
    }
  }

  if (qrKatId && qrOdaId) {
    console.log(`🔍 QR parametreleri bulundu: Kat=${qrKatId}, Oda=${qrOdaId}`);
    qrParametreleriIsle(qrKatId, qrOdaId);
  }

  // Görev listesinden gelen oda kontrolü
  if (gorevOdaId && gorevDetayId) {
    console.log(
      `📋 Görev parametreleri bulundu: Oda=${gorevOdaId}, Detay=${gorevDetayId}`,
    );
    mevcutGorevDetayId = gorevDetayId;
    gorevOdaKontrolBaslat(gorevOdaId);
  }

  // Ekstra güvenlik: 1 saniye sonra tüm panelleri kontrol et
  setTimeout(panelKontrolEt, 1000);
});

// Panel kontrol fonksiyonu - DND butonunun görünür olduğundan emin ol
function panelKontrolEt() {
  if (!mevcutOdaId) return; // Oda seçilmemişse kontrol etme

  const panel = document.getElementById("gorev_islemleri");
  if (panel && panel.classList.contains("hidden")) {
    console.warn(
      "🔧 [Panel Kontrol] DND butonu gizli bulundu, gösteriliyor...",
    );
    panel.classList.remove("hidden");
    panel.style.display = "";
  }
}

// Kat seçildiğinde
async function katSecildi() {
  const katId = document.getElementById("kat_id").value;
  const odaSelect = document.getElementById("oda_id");

  if (!katId) {
    odaSelect.disabled = true;
    odaSelect.innerHTML = '<option value="">Önce kat seçiniz...</option>';
    setupListesiniTemizle();
    return;
  }

  try {
    odaSelect.innerHTML = '<option value="">Yükleniyor...</option>';
    odaSelect.disabled = true;

    const response = await fetch(`/kat-odalari?kat_id=${katId}`);
    const data = await response.json();

    if (data.success && data.odalar) {
      odaSelect.innerHTML = '<option value="">Oda seçiniz...</option>';

      data.odalar.forEach((oda) => {
        const option = document.createElement("option");
        option.value = oda.id;
        option.textContent = oda.oda_no;
        odaSelect.appendChild(option);
      });

      odaSelect.disabled = false;
    } else {
      throw new Error(data.error || "Odalar yüklenemedi");
    }
  } catch (error) {
    console.error("❌ Oda yükleme hatası:", error);
    odaSelect.innerHTML = '<option value="">Hata oluştu</option>';
    toastGoster(error.message, "error");
  }

  setupListesiniTemizle();
}

// Oda seçildiğinde
async function odaSecildi() {
  const odaId = document.getElementById("oda_id").value;

  if (!odaId) {
    setupListesiniTemizle();
    return;
  }

  mevcutOdaId = odaId;

  // Oda seçim formunu gizle, geri butonunu göster
  const odaSecimFormu = document.getElementById("oda_secim_formu");
  const geriButonu = document.getElementById("geri_butonu");
  if (odaSecimFormu) odaSecimFormu.classList.add("hidden");
  if (geriButonu) geriButonu.classList.remove("hidden");

  // Kontrol başlat (varış kaydı oluştur)
  await kontrolBaslat(odaId);

  await setupListesiYukle(odaId);

  // Görev işlemleri panelini göster (oda seçildiğinde her zaman)
  gorevIslemleriGoster();

  // Fallback: 200ms sonra tekrar kontrol et (timing sorunu için)
  setTimeout(() => {
    const panel = document.getElementById("gorev_islemleri");
    if (panel && panel.classList.contains("hidden")) {
      console.warn("⚠️ Panel hala gizli, tekrar gösteriliyor...");
      panel.classList.remove("hidden");
      panel.style.display = "";
    }
  }, 200);
}

// Oda seçimine geri dön
function odaSecimineGeriDon() {
  // Kat detaylarından gelindiyse oraya geri dön
  if (katDetayGeriDonUrl) {
    window.location.href = katDetayGeriDonUrl;
    return;
  }

  // Yedek: Seçili kat ID'sinden kat detaylarına git
  const katId = document.getElementById("kat_id")?.value;
  if (katId) {
    window.location.href = "/kat-doluluk/" + katId;
    return;
  }

  // Normal akış - formu göster, geri butonunu gizle
  const odaSecimFormu = document.getElementById("oda_secim_formu");
  const geriButonu = document.getElementById("geri_butonu");
  if (odaSecimFormu) odaSecimFormu.classList.remove("hidden");
  if (geriButonu) geriButonu.classList.add("hidden");

  // Setup listesini temizle
  setupListesiniTemizle();

  // Görev işlemleri panelini gizle
  const panel = document.getElementById("gorev_islemleri");
  if (panel) panel.classList.add("hidden");
}

// Kontrol başlat - Varış kaydı oluşturur
async function kontrolBaslat(odaId) {
  try {
    const response = await fetch("/api/kat-sorumlusu/kontrol-baslat", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-CSRFToken": getCsrfToken(),
      },
      body: JSON.stringify({ oda_id: odaId }),
    });

    const data = await response.json();
    if (data.success) {
      console.log("✅ Kontrol başlatıldı:", data.baslangic_zamani);
    }
  } catch (error) {
    console.error("❌ Kontrol başlatma hatası:", error);
  }
}

// Kontrol tamamla - Bitiş zamanını kaydeder
async function kontrolTamamla(kontrolTipi = "sarfiyat_yok") {
  if (!mevcutOdaId) return;

  try {
    const response = await fetch("/api/kat-sorumlusu/kontrol-tamamla", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-CSRFToken": getCsrfToken(),
      },
      body: JSON.stringify({
        oda_id: mevcutOdaId,
        kontrol_tipi: kontrolTipi,
      }),
    });

    const data = await response.json();
    if (data.success) {
      console.log("✅ Kontrol tamamlandı:", data.bitis_zamani);
    }
  } catch (error) {
    console.error("❌ Kontrol tamamlama hatası:", error);
  }
}

// Setup listesini yükle
async function setupListesiYukle(odaId) {
  const loadingDiv = document.getElementById("loading");
  const setupListesiDiv = document.getElementById("setup_listesi");
  const odaBilgileriDiv = document.getElementById("oda_bilgileri");

  try {
    loadingDiv.classList.remove("hidden");
    setupListesiDiv.classList.add("hidden");
    odaBilgileriDiv.classList.add("hidden");

    // Bugünkü eklemeleri yükle
    await bugunEklemeleriYukle(odaId);

    const response = await fetch(`/api/kat-sorumlusu/oda-setup/${odaId}`);
    const data = await response.json();

    if (!response.ok || !data.success) {
      throw new Error(data.error || "Setup listesi yüklenemedi");
    }

    mevcutSetuplar = data.setuplar;
    zimmetStoklar = data.kat_sorumlusu_stok;

    document.getElementById("oda_no_text").textContent = data.oda.oda_no;
    document.getElementById("oda_tipi_text").textContent = data.oda.oda_tipi;
    document.getElementById("toplam_setup").textContent = data.setuplar.length;
    odaBilgileriDiv.classList.remove("hidden");

    // Kontrol durumu badge'ini göster
    kontrolDurumuBadgeGoster(data.kontrol_durumu);

    renderSetupListesi(data.setuplar, data.gunluk_islemler || []);

    setupListesiDiv.classList.remove("hidden");
    console.log(`✅ ${data.setuplar.length} setup yüklendi`);
  } catch (error) {
    console.error("❌ Setup yükleme hatası:", error);
    toastGoster(error.message, "error");

    // HATA OLSA BİLE DND butonunu göster
    console.log("⚠️ Hata oldu ama DND butonu yine de gösteriliyor");
    gorevIslemleriGoster();
  } finally {
    loadingDiv.classList.add("hidden");
  }
}

// Setup listesini render et - Setup bazlı gruplu görünüm
function renderSetupListesi(setuplar, gunlukIslemler) {
  const container = document.getElementById("setup_listesi");
  container.innerHTML = "";

  // Setup Dışı Ürün Ekle butonu — EN ÜSTTE
  const setupDisiDiv = document.createElement("div");
  setupDisiDiv.className = "mb-4";
  setupDisiDiv.innerHTML = `
    <button onclick="setupDisiDialogAc()"
      class="w-full h-14 text-lg font-bold rounded-2xl bg-gradient-to-r from-violet-600 to-purple-700 text-white border border-violet-500/40 hover:from-violet-700 hover:to-purple-800 active:scale-[0.98] transition-all shadow-lg shadow-violet-600/20 touch-manipulation flex items-center justify-center gap-3">
      <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 6v6m0 0v6m0-6h6m-6 0H6"></path>
      </svg>
      Setup Dışı Ürün Ekle
    </button>
  `;
  container.appendChild(setupDisiDiv);

  // Setup'lar — Accordion yapısı (varsayılan kapalı)
  setuplar.forEach((setup, index) => {
    const setupDiv = document.createElement("div");
    setupDiv.className =
      "rounded-2xl shadow-md border border-slate-700/60 overflow-hidden mb-3";

    // Dolap içi/dışı için farklı renk şeması — TAM CLASS KULLANIMI (Tailwind JIT uyumlu)
    const isDolap = setup.dolap_ici;
    const headerBg = isDolap
      ? "bg-gradient-to-r from-sky-900/80 via-slate-800 to-slate-800"
      : "bg-gradient-to-r from-amber-900/60 via-slate-800 to-slate-800";

    const iconBoxClass = isDolap
      ? "bg-sky-500/20 border-sky-500/30"
      : "bg-amber-500/20 border-amber-500/30";

    const iconTextClass = isDolap ? "text-sky-400" : "text-amber-400";

    const badgeBgClass = isDolap
      ? "bg-sky-500/20 text-sky-300 border-sky-500/20"
      : "bg-amber-500/20 text-amber-300 border-amber-500/20";

    const dolapIcon = isDolap
      ? `<svg class="w-5 h-5 ${iconTextClass}" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M5 3h14a1 1 0 011 1v16a1 1 0 01-1 1H5a1 1 0 01-1-1V4a1 1 0 011-1zm7 0v18M9 10h.01M15 10h.01"></path></svg>`
      : `<svg class="w-5 h-5 ${iconTextClass}" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M20 7l-8-4-8 4m16 0l-8 4m8-4v10l-8 4m0-10L4 7m8 4v10M4 7v10l8 4"></path></svg>`;

    const dolapBilgisi = isDolap ? `Dolap ${setup.dolap_no}` : "Dolap Dışı";

    const isOpen = acikAkordiyonlar.has(index);

    setupDiv.innerHTML = `
      <button onclick="setupAccordionToggle(${index})" class="w-full ${headerBg} text-white px-4 py-4 flex items-center justify-between touch-manipulation active:opacity-90 transition-all">
        <div class="flex items-center gap-3">
          <div class="w-10 h-10 rounded-xl ${iconBoxClass} border flex items-center justify-center flex-shrink-0">
            ${dolapIcon}
          </div>
          <div class="text-left">
            <h3 class="text-base font-bold text-white leading-tight">${setup.setup_adi}</h3>
            <p class="text-xs text-slate-400 mt-0.5">${dolapBilgisi} • ${setup.urunler.length} ürün</p>
          </div>
        </div>
        <div class="flex items-center gap-2.5 flex-shrink-0">
          <span class="min-w-[28px] h-7 px-2 rounded-lg ${badgeBgClass} text-xs font-bold flex items-center justify-center border">${setup.urunler.length}</span>
          <svg id="accordion-icon-${index}" class="w-5 h-5 text-slate-400 transition-transform duration-300 ${isOpen ? "rotate-180" : ""}" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2.5" d="M19 9l-7 7-7-7"></path>
          </svg>
        </div>
      </button>
      <div id="accordion-body-${index}" class="bg-slate-900/40 ${isOpen ? "" : "hidden"}">
        <div class="p-3">
          <div class="grid grid-cols-2 sm:grid-cols-2 md:grid-cols-2 lg:grid-cols-3 gap-4" id="setup-grid-${index}"></div>
        </div>
      </div>
    `;

    container.appendChild(setupDiv);

    // Ürün kartlarını ekle
    const gridContainer = document.getElementById(`setup-grid-${index}`);
    setup.urunler.forEach((urun) => {
      const card = createUrunCard({
        ...urun,
        setup_id: setup.setup_id,
        setup_adi: setup.setup_adi,
      });
      gridContainer.appendChild(card);
    });
  });

  // Setup Dışı Eklenen Ürünler — Bugünkü
  const setupDisiIslemler = (gunlukIslemler || []).filter(
    (i) => i.islem_tipi === "setup_disi_ekleme",
  );

  if (setupDisiIslemler.length > 0) {
    const sdDiv = document.createElement("div");
    sdDiv.className =
      "mt-4 rounded-2xl overflow-hidden border border-fuchsia-500/30";

    // Tüm detayları topla
    let sdUrunlerHtml = "";
    let toplamAdet = 0;
    setupDisiIslemler.forEach((islem) => {
      (islem.detaylar || []).forEach((d) => {
        const miktar = d.eklenen_miktar || d.ekstra_miktar || 0;
        if (miktar <= 0) return;
        toplamAdet += miktar;
        sdUrunlerHtml += `
          <div class="flex items-center justify-between px-4 py-2.5 border-b border-slate-700/40 last:border-b-0">
            <div class="flex items-center gap-2 min-w-0 flex-1">
              <span class="w-2 h-2 rounded-full flex-shrink-0" style="background:#d946ef;"></span>
              <span class="text-sm text-white truncate" style="font-family:'Roboto',system-ui,sans-serif;">${d.urun_adi}</span>
            </div>
            <div class="flex items-center gap-3 flex-shrink-0">
              <span class="text-sm font-bold" style="color:#d946ef;">x${miktar}</span>
              <span class="text-[10px] text-slate-500">${islem.islem_tarihi || ""}</span>
            </div>
          </div>`;
      });
    });

    sdDiv.innerHTML = `
      <div class="px-4 py-3 flex items-center justify-between" style="background:linear-gradient(to right,#701a75,#1e293b);">
        <div class="flex items-center gap-2.5">
          <div class="w-8 h-8 rounded-lg flex items-center justify-center" style="background:rgba(217,70,239,0.25);border:1px solid rgba(217,70,239,0.4);">
            <svg class="w-4 h-4" style="color:#e879f9;" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 6v6m0 0v6m0-6h6m-6 0H6"></path></svg>
          </div>
          <div>
            <p class="text-sm font-bold text-white">Setup Dışı Eklenenler</p>
            <p class="text-[11px]" style="color:#c084fc;">Bugün eklenen ürünler</p>
          </div>
        </div>
        <span class="min-w-[28px] h-7 px-2 rounded-lg text-xs font-bold flex items-center justify-center" style="background:rgba(217,70,239,0.2);color:#e879f9;border:1px solid rgba(217,70,239,0.3);">${toplamAdet}</span>
      </div>
      <div style="background:#0f172a;">
        ${sdUrunlerHtml}
      </div>
    `;

    container.appendChild(sdDiv);
  }
}

// Accordion toggle
function setupAccordionToggle(index) {
  const body = document.getElementById(`accordion-body-${index}`);
  const icon = document.getElementById(`accordion-icon-${index}`);
  if (!body) return;

  if (body.classList.contains("hidden")) {
    body.classList.remove("hidden");
    icon?.classList.add("rotate-180");
    acikAkordiyonlar.add(index);
  } else {
    body.classList.add("hidden");
    icon?.classList.remove("rotate-180");
    acikAkordiyonlar.delete(index);
  }
}

// Ürün kartı oluştur - Kompakt ve Pratik + Bugünkü Ekleme Badge
function createUrunCard(urun) {
  const card = document.createElement("div");
  card.className =
    "bg-slate-800/70 dark:bg-slate-800/70 rounded-2xl p-5 border border-slate-700 dark:border-slate-700 relative backdrop-blur-sm hover:border-slate-600 transition-all shadow-md hover:shadow-lg";

  // Zimmet stok kontrolü
  const zimmetStok = zimmetStoklar[urun.urun_id];
  const stokVar = zimmetStok && zimmetStok.miktar > 0;
  const maxMiktar = Math.min(urun.setup_miktari, zimmetStok?.miktar || 0);

  // Bugünkü ekleme miktarı
  const bugunEklenen = bugunEklemeler[urun.urun_id] || 0;

  // Dinamik buton sayısı (setup miktarına göre, max 4)
  const butonSayisi = Math.min(urun.setup_miktari, 4);
  const butonlar = [];

  for (let i = 1; i <= butonSayisi; i++) {
    const aktif = stokVar && zimmetStok.miktar >= i;
    // Tek buton varsa full genişlik (col-span-2), değilse normal
    const spanClass =
      butonSayisi === 1
        ? "col-span-2"
        : butonSayisi === 3 && i === 3
          ? "col-span-2"
          : "";
    butonlar.push(`
      <button onclick="hizliUrunEkle(${urun.urun_id}, '${urun.urun_adi.replace(
        /'/g,
        "\\'",
      )}', ${urun.setup_miktari}, ${urun.ekstra_miktar || 0}, ${
        urun.setup_id
      }, ${i})"
        class="${spanClass} h-14 text-lg font-bold rounded-xl transition-all shadow-md touch-manipulation ${
          aktif
            ? "bg-gradient-to-b from-blue-500 to-blue-700 text-white hover:from-blue-600 hover:to-blue-800 active:scale-95 border border-blue-400/30"
            : "bg-gradient-to-b from-slate-700 to-slate-800 text-slate-500 cursor-not-allowed border border-slate-600/30"
        }"
        ${!aktif ? "disabled" : ""}>
        +${i}
      </button>
    `);
  }

  // Bugünkü ekleme badge'i (sağ tarafta)
  const bugunBadge =
    bugunEklenen > 0
      ? `<span class="w-9 h-9 rounded-full bg-gradient-to-b from-green-500 to-green-600 text-white text-sm font-bold flex items-center justify-center shadow-md flex-shrink-0">+${bugunEklenen}</span>`
      : `<span class="w-9 h-9 flex-shrink-0"></span>`;

  card.innerHTML = `
    <!-- Üst Satır: Setup Miktarı | Ürün Adı | Bugün Eklenen -->
    <div class="flex items-center justify-between mb-4">
      <span class="w-9 h-9 rounded-full bg-gradient-to-b from-indigo-500 to-indigo-600 text-white text-sm font-bold flex items-center justify-center shadow-md flex-shrink-0">${
        urun.setup_miktari
      }</span>
      <span class="text-base font-semibold text-slate-100 flex-1 text-center mx-2 leading-snug break-words line-clamp-2" style="font-family: 'Roboto', system-ui, -apple-system, 'Segoe UI', 'Helvetica Neue', Arial, sans-serif;" title="${
        urun.urun_adi
      }">${urun.urun_adi}</span>
      ${bugunBadge}
    </div>
    
    ${
      urun.ekstra_miktar > 0
        ? `<div class="text-center mb-3"><span class="text-amber-400 font-bold text-base">+${urun.ekstra_miktar} ekstra</span></div>`
        : ""
    }
    
    <!-- Hızlı Ekleme Butonları — Sabit 2 sütun grid -->
    <div class="grid grid-cols-2 gap-2.5 mb-3">
      ${butonlar.join("")}
    </div>
    
    <!-- Ekstra ve Sıfırla Butonları -->
    ${
      urun.ekstra_miktar > 0
        ? `
    <div class="grid grid-cols-2 gap-2.5">
      <button onclick="ekstraDialogAc(${urun.urun_id}, '${urun.urun_adi.replace(
        /'/g,
        "\\'",
      )}', ${urun.setup_miktari}, ${urun.ekstra_miktar || 0}, ${urun.setup_id})"
        class="h-12 text-base font-bold rounded-xl bg-gradient-to-b from-orange-500 to-orange-600 text-white border border-orange-400/50 hover:from-orange-600 hover:to-orange-700 active:scale-95 transition-all shadow-md shadow-orange-500/20 touch-manipulation">
        + Ekstra
      </button>
      <button onclick="ekstraSifirlaModalAc(${
        urun.urun_id
      }, '${urun.urun_adi.replace(/'/g, "\\'")}', ${urun.ekstra_miktar}, ${
        urun.setup_id
      })"
        class="h-12 text-base font-bold rounded-xl bg-gradient-to-b from-red-500 to-red-600 text-white border border-red-400/50 hover:from-red-600 hover:to-red-700 active:scale-95 transition-all shadow-md shadow-red-500/20 touch-manipulation">
        Sıfırla
      </button>
    </div>
    `
        : `
    <button onclick="ekstraDialogAc(${urun.urun_id}, '${urun.urun_adi.replace(
      /'/g,
      "\\'",
    )}', ${urun.setup_miktari}, ${urun.ekstra_miktar || 0}, ${urun.setup_id})"
      class="w-full h-12 text-base font-bold rounded-xl bg-gradient-to-b from-orange-500 to-orange-600 text-white border border-orange-400/50 hover:from-orange-600 hover:to-orange-700 active:scale-95 transition-all shadow-md shadow-orange-500/20 touch-manipulation">
      + Ekstra
    </button>
    `
    }
  `;

  return card;
}

// Ekstra Dialog - Mini popup (Sadece input ve Ekle butonu)
function ekstraDialogAc(urunId, urunAdi, setupMiktari, ekstraMiktar, setupId) {
  modalData = {
    oda_id: mevcutOdaId,
    urun_id: urunId,
    setup_id: setupId,
    urun_adi: urunAdi,
    setup_miktari: setupMiktari,
  };

  const zimmetStok = zimmetStoklar[urunId];
  if (zimmetStok) {
    modalData.zimmet_detay_id = zimmetStok.zimmet_detay_id;
  }

  // Mini dialog oluştur
  const existingDialog = document.getElementById("ekstraDialog");
  if (existingDialog) existingDialog.remove();

  const dialog = document.createElement("div");
  dialog.id = "ekstraDialog";
  dialog.className =
    "fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4";
  dialog.onclick = (e) => {
    if (e.target === dialog) ekstraDialogKapat();
  };

  const stokMiktar = zimmetStok?.miktar || 0;
  const stokRenk = stokMiktar > 0 ? "text-emerald-400" : "text-red-400";

  dialog.innerHTML = `
    <div class="bg-slate-800 rounded-2xl shadow-2xl w-full max-w-sm animate-slideUp overflow-hidden">
      <!-- Header -->
      <div class="bg-gradient-to-r from-orange-500 to-amber-500 px-5 py-4 text-center">
        <p class="text-lg font-bold text-white" style="font-family: 'Roboto', system-ui, -apple-system, 'Segoe UI', 'Helvetica Neue', Arial, sans-serif;">${urunAdi}</p>
        <p class="text-sm text-orange-100 mt-0.5 font-medium">Ekstra Ekle</p>
      </div>
      
      <!-- Content -->
      <div class="p-5 space-y-4">
        <!-- Stepper: [-] Miktar [+] -->
        <div class="flex items-center justify-center gap-3">
          <button onclick="ekstraStepperAzalt()"
            class="w-14 h-14 rounded-xl bg-slate-700 hover:bg-slate-600 active:scale-90 transition-all flex items-center justify-center touch-manipulation border border-slate-600">
            <svg class="w-7 h-7 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="3" d="M20 12H4"></path>
            </svg>
          </button>
          <input type="number" id="ekstraDialogInput" min="1" value="1" inputmode="numeric"
            class="w-24 h-14 text-center text-3xl font-bold border-2 border-slate-600 rounded-xl bg-slate-900 text-white focus:border-orange-500 focus:ring-2 focus:ring-orange-500/50 touch-manipulation">
          <button onclick="ekstraStepperArtir(${stokMiktar})"
            class="w-14 h-14 rounded-xl bg-slate-700 hover:bg-slate-600 active:scale-90 transition-all flex items-center justify-center touch-manipulation border border-slate-600">
            <svg class="w-7 h-7 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="3" d="M12 4v16m8-8H4"></path>
            </svg>
          </button>
        </div>

        <!-- Hızlı Ekleme Butonları -->
        <div class="grid grid-cols-4 gap-2">
          ${[1, 2, 3, 5]
            .map(
              (n) => `
            <button onclick="document.getElementById('ekstraDialogInput').value=${n}"
              class="py-3 text-base font-bold rounded-xl transition-all touch-manipulation active:scale-90
              ${
                stokMiktar >= n
                  ? "bg-gradient-to-b from-slate-600 to-slate-700 text-white hover:from-orange-500 hover:to-orange-600 border border-slate-500 hover:border-orange-400"
                  : "bg-slate-800 text-slate-600 cursor-not-allowed border border-slate-700"
              }"
              ${stokMiktar < n ? "disabled" : ""}>
              +${n}
            </button>
          `,
            )
            .join("")}
        </div>
        
        <!-- Stok Bilgisi -->
        <div class="text-center text-sm text-slate-400 py-2 bg-slate-900/50 rounded-lg">
          Zimmet Stok: <strong class="${stokRenk} text-base">${stokMiktar}</strong>
        </div>
        
        <!-- Ekle Butonu -->
        <button onclick="hizliEkstraEkle(parseInt(document.getElementById('ekstraDialogInput').value))"
          class="w-full py-4 text-lg font-bold rounded-xl bg-gradient-to-r from-orange-500 to-amber-500 text-white hover:from-orange-600 hover:to-amber-600 active:scale-95 transition-all shadow-lg shadow-orange-500/30 touch-manipulation">
          ✓ Ekstra Ekle
        </button>

        <!-- İptal Butonu -->
        <button onclick="ekstraDialogKapat()" class="w-full py-3 text-sm font-semibold rounded-xl bg-slate-700 hover:bg-slate-600 text-slate-300 transition-all touch-manipulation active:scale-95">
          İptal
        </button>
      </div>
    </div>
  `;

  document.body.appendChild(dialog);
}

function ekstraDialogKapat() {
  const dialog = document.getElementById("ekstraDialog");
  if (dialog) dialog.remove();
}

// Stepper fonksiyonları
function ekstraStepperAzalt() {
  const input = document.getElementById("ekstraDialogInput");
  const val = parseInt(input.value) || 1;
  if (val > 1) input.value = val - 1;
}

function ekstraStepperArtir(maxStok) {
  const input = document.getElementById("ekstraDialogInput");
  const val = parseInt(input.value) || 0;
  if (val < maxStok) input.value = val + 1;
}

// Hızlı ekstra ekleme
async function hizliEkstraEkle(miktar) {
  if (!miktar || miktar <= 0) {
    toastGoster("Geçerli miktar girin", "warning");
    return;
  }

  const zimmetStok = zimmetStoklar[modalData.urun_id];
  if (!zimmetStok || zimmetStok.miktar < miktar) {
    toastGoster("Yetersiz zimmet stoğu!", "warning");
    return;
  }

  try {
    const response = await fetch("/api/kat-sorumlusu/ekstra-ekle", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-CSRFToken": getCsrfToken(),
      },
      body: JSON.stringify({
        oda_id: modalData.oda_id,
        urun_id: modalData.urun_id,
        setup_id: modalData.setup_id,
        ekstra_miktar: miktar,
        zimmet_detay_id: modalData.zimmet_detay_id,
      }),
    });

    const data = await response.json();

    if (!response.ok || !data.success) {
      throw new Error(data.error || "Ekstra eklenemedi");
    }

    // Kalan stoğu hesapla (setupListesiYukle stokları yenileyecek, önceden kaydet)
    const kalanStokEkstra =
      (zimmetStoklar[modalData.urun_id]?.miktar || 0) - miktar;

    // Success dialog göster (kalan stok bilgisiyle)
    successDialogGoster(
      modalData.urun_adi,
      miktar,
      "ekstra",
      kalanStokEkstra >= 0 ? kalanStokEkstra : 0,
    );
    ekstraDialogKapat();
    await setupListesiYukle(mevcutOdaId);
  } catch (error) {
    console.error("❌ Ekstra ekleme hatası:", error);
    toastGoster(error.message, "error");
  }
}

// Hızlı ürün ekleme (tek tıkla)
async function hizliUrunEkle(
  urunId,
  urunAdi,
  setupMiktari,
  ekstraMiktar,
  setupId,
  miktar,
) {
  // Bugün eklenen miktarı kontrol et
  const bugunEklenen = bugunEklemeler[urunId] || 0;
  const kalanEklenebilir = setupMiktari - bugunEklenen;

  // Setup miktarını aşma kontrolü
  if (bugunEklenen + miktar > setupMiktari) {
    setupAsimiUyariGoster(
      urunAdi,
      setupMiktari,
      bugunEklenen,
      kalanEklenebilir,
    );
    return;
  }

  const zimmetStok = zimmetStoklar[urunId];

  if (!zimmetStok || zimmetStok.miktar < miktar) {
    toastGoster("Yetersiz zimmet stoğu!", "warning");
    return;
  }

  try {
    const response = await fetch("/api/kat-sorumlusu/urun-ekle", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-CSRFToken": getCsrfToken(),
      },
      body: JSON.stringify({
        oda_id: mevcutOdaId,
        urun_id: urunId,
        setup_id: setupId,
        eklenen_miktar: miktar,
        zimmet_detay_id: zimmetStok.zimmet_detay_id,
      }),
    });

    const data = await response.json();

    if (!response.ok || !data.success) {
      throw new Error(data.error || "Ürün eklenemedi");
    }

    // Kontrol tamamla
    await kontrolTamamla("urun_eklendi");

    // Local state güncelle (sayfa yenilenmeden)
    bugunEklemeler[urunId] = (bugunEklemeler[urunId] || 0) + miktar;
    zimmetStoklar[urunId].miktar -= miktar;

    // Kartı güncelle (DOM manipülasyonu)
    kartGuncelle(urunId, setupMiktari, ekstraMiktar, setupId, urunAdi);

    // Success dialog göster (kalan stok bilgisiyle)
    const kalanStok = zimmetStoklar[urunId]?.miktar || 0;
    successDialogGoster(urunAdi, miktar, "tuketim", kalanStok);
  } catch (error) {
    console.error("❌ Hızlı ekleme hatası:", error);
    toastGoster(error.message, "error");
  }
}

// Setup listesini temizle
function setupListesiniTemizle() {
  document.getElementById("setup_listesi").innerHTML = "";
  document.getElementById("setup_listesi").classList.add("hidden");
  document.getElementById("oda_bilgileri").classList.add("hidden");
  mevcutOdaId = null;
  mevcutSetuplar = [];
  zimmetStoklar = {};
  acikAkordiyonlar.clear(); // Açık akordiyonları temizle
}

// Modal fonksiyonları
function urunEkleModalAc(urunId, urunAdi, setupMiktari, ekstraMiktar, setupId) {
  modalData = {
    oda_id: mevcutOdaId,
    urun_id: urunId,
    setup_id: setupId,
    urun_adi: urunAdi,
    setup_miktari: setupMiktari,
  };

  // Güvenli element güncellemesi
  const setTextIfExists = (id, text) => {
    const el = document.getElementById(id);
    if (el) el.textContent = text;
  };

  setTextIfExists("modal_urun_adi", urunAdi);
  setTextIfExists("modal_setup_miktari", setupMiktari);
  setTextIfExists("modal_mevcut_miktar", setupMiktari + (ekstraMiktar || 0));
  setTextIfExists("modal_eksik_miktar", "0");
  setTextIfExists("modal_max_miktar", setupMiktari);

  const inputEklenen = document.getElementById("modal_eklenen_miktar");
  if (inputEklenen) {
    inputEklenen.value = 1;
    inputEklenen.max = setupMiktari;
  }

  const zimmetStok = zimmetStoklar[urunId];
  if (zimmetStok) {
    setTextIfExists("modal_zimmet_stok", zimmetStok.miktar);
    modalData.zimmet_detay_id = zimmetStok.zimmet_detay_id;
  } else {
    setTextIfExists("modal_zimmet_stok", "0");
  }

  document.getElementById("urunEkleModal").classList.remove("hidden");
}

function urunEkleModalKapat() {
  document.getElementById("urunEkleModal").classList.add("hidden");
  modalData = {};
}

function ekstraEkleModalAc(
  urunId,
  urunAdi,
  setupMiktari,
  ekstraMiktar,
  setupId,
) {
  modalData = {
    oda_id: mevcutOdaId,
    urun_id: urunId,
    setup_id: setupId,
    urun_adi: urunAdi,
    setup_miktari: setupMiktari,
  };

  // Güvenli element güncellemesi
  const setTextIfExists = (id, text) => {
    const el = document.getElementById(id);
    if (el) el.textContent = text;
  };

  setTextIfExists("ekstra_modal_urun_adi", urunAdi);
  setTextIfExists("ekstra_modal_setup_miktari", setupMiktari);
  setTextIfExists(
    "ekstra_modal_mevcut_miktar",
    setupMiktari + (ekstraMiktar || 0),
  );

  const inputMiktar = document.getElementById("ekstra_modal_miktar");
  if (inputMiktar) inputMiktar.value = 1;

  const zimmetStok = zimmetStoklar[urunId];
  if (zimmetStok) {
    setTextIfExists("ekstra_modal_zimmet_stok", zimmetStok.miktar);
    modalData.zimmet_detay_id = zimmetStok.zimmet_detay_id;
  } else {
    setTextIfExists("ekstra_modal_zimmet_stok", "0");
  }

  document.getElementById("ekstraEkleModal").classList.remove("hidden");
}

function ekstraEkleModalKapat() {
  document.getElementById("ekstraEkleModal").classList.add("hidden");
  modalData = {};
}

function ekstraSifirlaModalAc(urunId, urunAdi, ekstraMiktar, setupId) {
  modalData = {
    oda_id: mevcutOdaId,
    urun_id: urunId,
    setup_id: setupId,
    urun_adi: urunAdi,
    ekstra_miktar: ekstraMiktar,
  };

  document.getElementById("sifirla_modal_urun_adi").textContent = urunAdi;
  document.getElementById("sifirla_modal_ekstra_miktar").textContent =
    ekstraMiktar;

  document.getElementById("ekstraSifirlaModal").classList.remove("hidden");
}

function ekstraSifirlaModalKapat() {
  document.getElementById("ekstraSifirlaModal").classList.add("hidden");
  modalData = {};
}

// CSRF token al
function getCsrfToken() {
  const token = document.querySelector('meta[name="csrf-token"]');
  return token ? token.getAttribute("content") : "";
}

// API çağrıları
async function urunEkle() {
  const eklenenMiktar = parseInt(
    document.getElementById("modal_eklenen_miktar").value,
  );

  if (!eklenenMiktar || eklenenMiktar <= 0) {
    toastGoster("Lütfen geçerli bir miktar giriniz", "warning");
    return;
  }

  try {
    const response = await fetch("/api/kat-sorumlusu/urun-ekle", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-CSRFToken": getCsrfToken(),
      },
      body: JSON.stringify({
        oda_id: modalData.oda_id,
        urun_id: modalData.urun_id,
        setup_id: modalData.setup_id,
        eklenen_miktar: eklenenMiktar,
        zimmet_detay_id: modalData.zimmet_detay_id,
      }),
    });

    const data = await response.json();

    if (!response.ok || !data.success) {
      throw new Error(data.error || "Ürün eklenemedi");
    }

    // Kontrol tamamla (ürün eklendi)
    await kontrolTamamla("urun_eklendi");

    toastGoster(data.message, "success");
    urunEkleModalKapat();
    await setupListesiYukle(mevcutOdaId);
  } catch (error) {
    console.error("❌ Ürün ekleme hatası:", error);
    toastGoster(error.message, "error");
  }
}

async function ekstraEkle() {
  const ekstraMiktar = parseInt(
    document.getElementById("ekstra_modal_miktar").value,
  );

  if (!ekstraMiktar || ekstraMiktar <= 0) {
    toastGoster("Lütfen geçerli bir miktar giriniz", "warning");
    return;
  }

  try {
    const response = await fetch("/api/kat-sorumlusu/ekstra-ekle", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-CSRFToken": getCsrfToken(),
      },
      body: JSON.stringify({
        oda_id: modalData.oda_id,
        urun_id: modalData.urun_id,
        setup_id: modalData.setup_id,
        ekstra_miktar: ekstraMiktar,
        zimmet_detay_id: modalData.zimmet_detay_id,
      }),
    });

    const data = await response.json();

    if (!response.ok || !data.success) {
      throw new Error(data.error || "Ekstra ürün eklenemedi");
    }

    toastGoster(data.message, "success");
    // Kalan stok bilgisiyle success dialog da göster
    const kalanStokModal =
      (zimmetStoklar[modalData.urun_id]?.miktar || 0) - ekstraMiktar;
    successDialogGoster(
      modalData.urun_adi,
      ekstraMiktar,
      "ekstra",
      kalanStokModal >= 0 ? kalanStokModal : 0,
    );
    ekstraEkleModalKapat();
    await setupListesiYukle(mevcutOdaId);
  } catch (error) {
    console.error("❌ Ekstra ekleme hatası:", error);
    toastGoster(error.message, "error");
  }
}

async function ekstraSifirla() {
  try {
    const response = await fetch("/api/kat-sorumlusu/ekstra-sifirla", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-CSRFToken": getCsrfToken(),
      },
      body: JSON.stringify({
        oda_id: modalData.oda_id,
        urun_id: modalData.urun_id,
        setup_id: modalData.setup_id,
      }),
    });

    const data = await response.json();

    if (!response.ok || !data.success) {
      throw new Error(data.error || "Ekstra sıfırlanamadı");
    }

    toastGoster(data.message, "success");
    ekstraSifirlaModalKapat();
    await setupListesiYukle(mevcutOdaId);
  } catch (error) {
    console.error("❌ Ekstra sıfırlama hatası:", error);
    toastGoster(error.message, "error");
  }
}

// QR ile başlat
function qrIleBaslat() {
  window.location.href = "/kat-sorumlusu/qr-okuyucu?redirect=oda-kontrol";
}

// QR parametrelerini işle ve oda seçimini otomatik yap
async function qrParametreleriIsle(katId, odaId) {
  try {
    const katSelect = document.getElementById("kat_id");
    const odaSelect = document.getElementById("oda_id");

    // Kat seçimini yap
    if (katSelect) {
      katSelect.value = katId;
      console.log(`✅ Kat seçildi: ${katId}`);

      // Odaları yükle
      await katSecildi();

      // Oda seçimini yap
      if (odaSelect) {
        // Odalar yüklenene kadar bekle
        await new Promise((resolve) => setTimeout(resolve, 500));

        odaSelect.value = odaId;
        console.log(`✅ Oda seçildi: ${odaId}`);

        // Setup listesini yükle
        await odaSetupDurumuYukle(odaId);

        toastGoster("✅ QR kod başarıyla okundu!", "success");

        // URL'den parametreleri temizle (temiz görünüm için)
        const cleanUrl = window.location.pathname;
        window.history.replaceState({}, document.title, cleanUrl);
      }
    }
  } catch (error) {
    console.error("❌ QR parametreleri işlenirken hata:", error);
    toastGoster("QR kod işlenirken hata: " + error.message, "error");
  }
}

// Oda setup durumunu yükle (QR için özel fonksiyon)
async function odaSetupDurumuYukle(odaId) {
  mevcutOdaId = odaId;

  // Oda seçim formunu gizle, geri butonunu göster
  const odaSecimFormu = document.getElementById("oda_secim_formu");
  const geriButonu = document.getElementById("geri_butonu");
  if (odaSecimFormu) odaSecimFormu.classList.add("hidden");
  if (geriButonu) geriButonu.classList.remove("hidden");

  await setupListesiYukle(odaId);
  // Görev işlemleri panelini göster
  gorevIslemleriGoster();

  // Fallback: 200ms sonra tekrar kontrol et
  setTimeout(() => {
    const panel = document.getElementById("gorev_islemleri");
    if (panel && panel.classList.contains("hidden")) {
      console.warn("⚠️ [QR] Panel hala gizli, tekrar gösteriliyor...");
      panel.classList.remove("hidden");
      panel.style.display = "";
    }
  }, 200);
}

// Toast mesajı göster
function toastGoster(mesaj, tip = "info") {
  const toast = document.createElement("div");
  toast.className = `fixed top-4 right-4 z-50 px-6 py-4 rounded-lg shadow-lg text-white transform transition-all duration-300 ${
    tip === "success"
      ? "bg-green-500"
      : tip === "error"
        ? "bg-red-500"
        : tip === "warning"
          ? "bg-orange-500"
          : "bg-blue-500"
  }`;
  toast.textContent = mesaj;

  document.body.appendChild(toast);

  setTimeout(() => {
    toast.style.opacity = "0";
    setTimeout(() => document.body.removeChild(toast), 300);
  }, 3000);
}

// Görev listesinden gelen oda kontrolünü başlat
async function gorevOdaKontrolBaslat(odaId) {
  try {
    // Önce oda bilgilerini al
    const response = await fetch(`/api/kat-sorumlusu/oda-setup/${odaId}`);
    const data = await response.json();

    if (!response.ok || !data.success) {
      throw new Error(data.error || "Oda bilgileri yüklenemedi");
    }

    // Kat ve oda seçimlerini ayarla
    const katSelect = document.getElementById("kat_id");
    const odaSelect = document.getElementById("oda_id");

    if (data.oda && data.oda.kat_id) {
      katSelect.value = data.oda.kat_id;
      await katSecildi();

      // Odalar yüklenene kadar bekle
      await new Promise((resolve) => setTimeout(resolve, 300));

      odaSelect.value = odaId;
      mevcutOdaId = odaId;
    }

    // Setup listesini yükle
    await setupListesiYukle(odaId);

    // Görev işlemleri panelini göster
    gorevIslemleriGoster();

    // Fallback: 200ms sonra tekrar kontrol et
    setTimeout(() => {
      const panel = document.getElementById("gorev_islemleri");
      if (panel && panel.classList.contains("hidden")) {
        console.warn("⚠️ [Görev] Panel hala gizli, tekrar gösteriliyor...");
        panel.classList.remove("hidden");
        panel.style.display = "";
      }
    }, 200);

    // URL'yi temizle
    const cleanUrl = window.location.pathname;
    window.history.replaceState({}, document.title, cleanUrl);

    toastGoster("✅ Oda kontrolü başlatıldı", "success");
  } catch (error) {
    console.error("❌ Görev oda kontrolü hatası:", error);
    toastGoster(error.message, "error");
  }
}

// Görev işlemleri panelini göster
function gorevIslemleriGoster() {
  console.log("🔍 gorevIslemleriGoster çağrıldı - Oda ID:", mevcutOdaId);

  const panel = document.getElementById("gorev_islemleri");

  if (!panel) {
    console.error("❌ gorev_islemleri elementi bulunamadı!");
    return;
  }

  if (!mevcutOdaId) {
    console.warn("⚠️ Oda seçilmemiş, panel gösterilemiyor");
    return;
  }

  // Tüm hidden class'larını kaldır ve inline style'ı temizle
  panel.classList.remove("hidden");
  panel.style.display = ""; // Inline style override'ı temizle

  console.log("✅ DND butonu gösterildi - Oda:", mevcutOdaId);

  const bilgiText = document.getElementById("gorev_bilgi_text");
  const odaNo = document.getElementById("oda_no_text")?.textContent || "";

  if (bilgiText) {
    if (mevcutGorevDetayId) {
      bilgiText.textContent = `Oda ${odaNo} için minibar kontrol görevi`;
    } else {
      bilgiText.textContent = `Oda ${odaNo} için hızlı kontrol`;
    }
  }
}

// Sarfiyat yok onaylama - Modal ile
function sarfiyatYokOnayla() {
  if (!mevcutOdaId) {
    toastGoster("Lütfen önce bir oda seçin", "warning");
    return;
  }

  const odaNo =
    document.getElementById("oda_no_text")?.textContent || mevcutOdaId;
  const bugun = new Date().toLocaleDateString("tr-TR");

  // Modal içeriğini güncelle
  document.getElementById("sarfiyat_modal_oda_no").textContent = odaNo;
  document.getElementById("sarfiyat_modal_tarih").textContent = bugun;

  // Modal'ı göster
  document.getElementById("sarfiyatYokModal").classList.remove("hidden");
}

// Sarfiyat yok modal kapat
function sarfiyatYokModalKapat() {
  document.getElementById("sarfiyatYokModal").classList.add("hidden");
}

// Sarfiyat yok kaydı
async function sarfiyatYokKaydet() {
  try {
    // Önce kontrol tamamla (bitiş zamanı kaydet)
    await kontrolTamamla("sarfiyat_yok");

    const response = await fetch("/api/kat-sorumlusu/sarfiyat-yok", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-CSRFToken": getCsrfToken(),
      },
      body: JSON.stringify({
        oda_id: mevcutOdaId,
        gorev_detay_id: mevcutGorevDetayId,
      }),
    });

    const data = await response.json();

    if (!response.ok || !data.success) {
      throw new Error(data.error || "Kayıt yapılamadı");
    }

    toastGoster("✅ " + data.message, "success");

    // Görev panelini gizle
    const panel = document.getElementById("gorev_islemleri");
    if (panel) panel.classList.add("hidden");

    // Görev detay ID'yi temizle
    mevcutGorevDetayId = null;

    // 2 saniye sonra görev listesine yönlendir
    setTimeout(() => {
      window.location.href = "/gorevler/yonetim";
    }, 2000);
  } catch (error) {
    console.error("❌ Sarfiyat yok kayıt hatası:", error);
    toastGoster(error.message, "error");
  }
}

// DND onaylama - Modal ile
async function dndOnayla() {
  if (!mevcutOdaId) {
    toastGoster("Lütfen önce bir oda seçin", "warning");
    return;
  }

  const odaNo =
    document.getElementById("oda_no_text")?.textContent || mevcutOdaId;

  // Modal içeriğini güncelle
  document.getElementById("dnd_modal_oda_no").textContent = odaNo;

  // Mevcut DND durumunu kontrol et
  try {
    const response = await fetch(`/api/kat-sorumlusu/dnd-durum/${mevcutOdaId}`);
    const data = await response.json();

    const bilgiDiv = document.getElementById("dnd_sayisi_bilgi");
    if (bilgiDiv) {
      if (data.success && data.dnd_durumu) {
        const dndSayisi = data.dnd_durumu.dnd_sayisi;
        const sonKontrol = data.dnd_durumu.son_dnd_zamani
          ? new Date(data.dnd_durumu.son_dnd_zamani).toLocaleTimeString(
              "tr-TR",
              { hour: "2-digit", minute: "2-digit" },
            )
          : "-";

        bilgiDiv.innerHTML = `
          <div class="flex items-start space-x-3">
            <i class="fas fa-info-circle text-orange-600 dark:text-orange-400 mt-0.5"></i>
            <div>
              <p class="text-sm font-medium text-orange-900 dark:text-orange-100">
                Bu oda bugün <strong>${dndSayisi}</strong> kez DND olarak işaretlenmiş.
              </p>
              <p class="text-xs text-orange-700 dark:text-orange-300 mt-1">
                Son kontrol: ${sonKontrol} • ${
                  dndSayisi >= 2
                    ? "✅ Minimum kontrol tamamlandı"
                    : `${2 - dndSayisi} kontrol daha gerekli`
                }
              </p>
            </div>
          </div>
        `;
      } else {
        bilgiDiv.innerHTML = `
          <div class="flex items-start space-x-3">
            <i class="fas fa-info-circle text-orange-600 dark:text-orange-400 mt-0.5"></i>
            <div>
              <p class="text-sm font-medium text-orange-900 dark:text-orange-100">
                Bu oda DND olarak işaretlenecek.
              </p>
              <p class="text-xs text-orange-700 dark:text-orange-300 mt-1">
                Gün içinde en az 2 kez DND kontrolü yapılmalıdır.
              </p>
            </div>
          </div>
        `;
      }
    }
  } catch (error) {
    console.error("DND durum kontrolü hatası:", error);
  }

  // Modal'ı göster
  document.getElementById("dndModal").classList.remove("hidden");
}

// DND modal kapat
function dndModalKapat() {
  document.getElementById("dndModal").classList.add("hidden");
}

// DND kaydı - Bağımsız DND sistemi
async function dndKaydet() {
  // Önce onay modal'ını kapat
  dndModalKapat();

  try {
    const response = await fetch("/api/kat-sorumlusu/dnd-kaydet", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-CSRFToken": getCsrfToken(),
      },
      body: JSON.stringify({
        oda_id: mevcutOdaId,
        gorev_detay_id: mevcutGorevDetayId, // Opsiyonel - varsa bağlanır
      }),
    });

    const data = await response.json();

    if (!response.ok || !data.success) {
      throw new Error(data.error || "DND kaydı yapılamadı");
    }

    // Başarı mesajı göster
    const dndSayisi = data.dnd_sayisi;
    const tamamlandi = data.min_kontrol_tamamlandi || data.otomatik_tamamlandi;

    if (tamamlandi) {
      // 2+ kontrol tamamlandı - özel başarı dialog'u
      dndTamamlandiDialogGoster(dndSayisi);
    } else if (dndSayisi === 1) {
      // İlk DND kaydı - bilgilendirme modal'ı göster
      dndIlkKayitModalGoster();
    } else {
      // Normal DND kaydı
      toastGoster(`✅ ${data.message}`, "success");
    }

    // DND sayısını UI'da güncelle (görev panelinde)
    dndBilgiGuncelle(dndSayisi, tamamlandi);

    // Görev bağlıysa ve tamamlandıysa yönlendir
    if (tamamlandi && mevcutGorevDetayId) {
      setTimeout(() => {
        window.location.href = "/gorevler/yonetim";
      }, 2500);
    }
  } catch (error) {
    console.error("❌ DND kayıt hatası:", error);
    toastGoster(error.message, "error");
  }
}

// İlk DND kaydı bilgilendirme modal'ı
function dndIlkKayitModalGoster() {
  const existingModal = document.getElementById("dndIlkKayitModal");
  if (existingModal) existingModal.remove();

  const odaNo =
    document.getElementById("oda_no_text")?.textContent || mevcutOdaId;

  const modal = document.createElement("div");
  modal.id = "dndIlkKayitModal";
  modal.className =
    "fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50 backdrop-blur-sm";
  modal.innerHTML = `
    <div class="bg-white dark:bg-slate-800 rounded-2xl shadow-2xl max-w-md w-full transform animate-modalSlideIn overflow-hidden">
      <!-- Header -->
      <div class="bg-gradient-to-r from-amber-500 to-orange-500 px-6 py-4">
        <div class="flex items-center space-x-3">
          <div class="w-12 h-12 rounded-full bg-white/20 flex items-center justify-center">
            <i class="fas fa-door-closed text-2xl text-white"></i>
          </div>
          <div>
            <h3 class="text-lg font-bold text-white">DND Kaydı Oluşturuldu</h3>
            <p class="text-sm text-amber-100">Oda ${odaNo}</p>
          </div>
        </div>
      </div>
      
      <!-- Body -->
      <div class="px-6 py-5">
        <div class="flex items-start space-x-4">
          <div class="flex-shrink-0 w-10 h-10 rounded-full bg-amber-100 dark:bg-amber-900/30 flex items-center justify-center">
            <i class="fas fa-info-circle text-amber-600 dark:text-amber-400"></i>
          </div>
          <div class="flex-1">
            <p class="text-slate-700 dark:text-slate-200 font-medium mb-2">
              Bu oda için görevin tamamlanması için:
            </p>
            <div class="bg-slate-50 dark:bg-slate-700/50 rounded-xl p-4 border border-slate-200 dark:border-slate-600">
              <div class="flex items-center space-x-3 mb-3">
                <div class="w-8 h-8 rounded-full bg-amber-500 text-white flex items-center justify-center font-bold text-sm">1</div>
                <span class="text-slate-600 dark:text-slate-300 line-through">İlk DND kontrolü</span>
                <i class="fas fa-check-circle text-green-500"></i>
              </div>
              <div class="flex items-center space-x-3">
                <div class="w-8 h-8 rounded-full bg-slate-300 dark:bg-slate-600 text-slate-600 dark:text-slate-300 flex items-center justify-center font-bold text-sm">2</div>
                <span class="text-slate-700 dark:text-slate-200 font-medium">Gün içinde 1 kontrol daha gerekli</span>
              </div>
            </div>
            <p class="text-sm text-slate-500 dark:text-slate-400 mt-3 flex items-center">
              <i class="fas fa-clock mr-2 text-amber-500"></i>
              Lütfen gün içinde tekrar kontrol ediniz
            </p>
          </div>
        </div>
      </div>
      
      <!-- Footer -->
      <div class="px-6 py-4 bg-slate-50 dark:bg-slate-700/30 border-t border-slate-200 dark:border-slate-600">
        <button onclick="dndIlkKayitModalKapat()" 
                class="w-full py-3 px-4 bg-gradient-to-r from-amber-500 to-orange-500 hover:from-amber-600 hover:to-orange-600 text-white font-semibold rounded-xl transition-all duration-200 flex items-center justify-center space-x-2 shadow-lg shadow-amber-500/25">
          <i class="fas fa-check"></i>
          <span>Anladım</span>
        </button>
      </div>
    </div>
  `;

  document.body.appendChild(modal);

  // ESC tuşu ile kapatma
  const escHandler = (e) => {
    if (e.key === "Escape") {
      dndIlkKayitModalKapat();
      document.removeEventListener("keydown", escHandler);
    }
  };
  document.addEventListener("keydown", escHandler);

  // Backdrop tıklama ile kapatma
  modal.addEventListener("click", (e) => {
    if (e.target === modal) {
      dndIlkKayitModalKapat();
    }
  });
}

// İlk DND kaydı modal'ını kapat
function dndIlkKayitModalKapat() {
  const modal = document.getElementById("dndIlkKayitModal");
  if (modal) {
    modal.classList.add("animate-fadeOut");
    setTimeout(() => modal.remove(), 200);
  }
}

// DND tamamlandı dialog'u
function dndTamamlandiDialogGoster(dndSayisi) {
  const existingDialog = document.getElementById("dndTamamlandiDialog");
  if (existingDialog) existingDialog.remove();

  const dialog = document.createElement("div");
  dialog.id = "dndTamamlandiDialog";
  dialog.className =
    "fixed inset-0 z-50 flex items-center justify-center p-4 pointer-events-none";

  dialog.innerHTML = `
    <div class="bg-white dark:bg-slate-800 rounded-2xl shadow-2xl p-6 max-w-xs w-full text-center transform animate-successPop pointer-events-auto">
      <div class="w-16 h-16 mx-auto mb-4 rounded-full bg-green-100 dark:bg-green-900/30 flex items-center justify-center">
        <i class="fas fa-check-double text-3xl text-green-500"></i>
      </div>
      <h3 class="text-lg font-bold text-slate-900 dark:text-white mb-1">DND Kontrolü Tamamlandı!</h3>
      <p class="text-sm text-slate-600 dark:text-slate-400 mb-2">Bu oda için ${dndSayisi} kontrol yapıldı</p>
      <p class="text-2xl font-bold text-green-600 dark:text-green-400">✓ Minimum kontrol sağlandı</p>
    </div>
  `;

  document.body.appendChild(dialog);

  setTimeout(() => {
    dialog.classList.add("animate-fadeOut");
    setTimeout(() => dialog.remove(), 300);
  }, 2500);
}

// DND bilgisini UI'da güncelle
function dndBilgiGuncelle(dndSayisi, tamamlandi) {
  const bilgiText = document.getElementById("gorev_bilgi_text");
  if (bilgiText) {
    if (tamamlandi) {
      bilgiText.innerHTML = `<span class="text-green-600 dark:text-green-400">✅ DND kontrolü tamamlandı (${dndSayisi}/2)</span>`;
    } else {
      bilgiText.innerHTML = `<span class="text-orange-600 dark:text-orange-400">🚪 DND: ${dndSayisi}/2 kontrol yapıldı</span>`;
    }
  }
}

// Success Dialog - Ortada gösterilir
function successDialogGoster(
  urunAdi,
  miktar,
  tip = "tuketim",
  kalanStok = null,
) {
  // Mevcut dialog varsa kaldır
  const existingDialog = document.getElementById("successDialog");
  if (existingDialog) existingDialog.remove();

  const renk = tip === "ekstra" ? "orange" : "green";
  const ikon = tip === "ekstra" ? "plus-circle" : "check-circle";
  const baslik = tip === "ekstra" ? "Ekstra Eklendi" : "Tüketim Kaydedildi";

  // Kalan stok bilgisi
  const kalanStokHtml =
    kalanStok !== null
      ? `
      <div class="mt-3 pt-3 border-t border-slate-200 dark:border-slate-700">
        <p class="text-sm text-slate-500 dark:text-slate-400">Kalan Stoğunuz</p>
        <p class="text-2xl font-bold ${kalanStok > 0 ? "text-emerald-500" : "text-red-500"}">${kalanStok}</p>
      </div>`
      : "";

  const dialog = document.createElement("div");
  dialog.id = "successDialog";
  dialog.className =
    "fixed inset-0 z-50 flex items-center justify-center p-4 pointer-events-none";

  dialog.innerHTML = `
    <div class="bg-white dark:bg-slate-800 rounded-2xl shadow-2xl p-6 max-w-xs w-full text-center transform animate-successPop pointer-events-auto">
      <div class="w-16 h-16 mx-auto mb-4 rounded-full bg-${renk}-100 dark:bg-${renk}-900/30 flex items-center justify-center">
        <i class="fas fa-${ikon} text-3xl text-${renk}-500"></i>
      </div>
      <h3 class="text-lg font-bold text-slate-900 dark:text-white mb-1">${baslik}</h3>
      <p class="text-base font-medium text-slate-900 dark:text-white mb-2" style="font-family: 'Roboto', system-ui, -apple-system, 'Segoe UI', 'Helvetica Neue', Arial, sans-serif;">${urunAdi}</p>
      <p class="text-3xl font-bold text-${renk}-600 dark:text-${renk}-400">+${miktar}</p>
      ${kalanStokHtml}
    </div>
  `;

  document.body.appendChild(dialog);

  // 2 saniye sonra otomatik kapat (kalan stok varsa biraz daha uzun)
  setTimeout(
    () => {
      dialog.classList.add("animate-fadeOut");
      setTimeout(() => dialog.remove(), 300);
    },
    kalanStok !== null ? 2000 : 1500,
  );
}

// Bugünkü eklemeleri takip eden global obje
let bugunEklemeler = {};

// Bugünkü eklemeleri yükle
async function bugunEklemeleriYukle(odaId) {
  try {
    const response = await fetch(`/api/kat-sorumlusu/bugun-eklemeler/${odaId}`);
    const data = await response.json();
    if (data.success) {
      bugunEklemeler = data.eklemeler || {};
    }
  } catch (error) {
    console.error("❌ Bugünkü eklemeler yüklenemedi:", error);
    bugunEklemeler = {};
  }
}

// Kart güncelle - Sayfa yenilenmeden DOM manipülasyonu
function kartGuncelle(urunId, setupMiktari, ekstraMiktar, setupId, urunAdi) {
  // Tüm setup grid'lerini tara ve ilgili kartı bul
  const allGrids = document.querySelectorAll('[id^="setup-grid-"]');

  allGrids.forEach((grid) => {
    const cards = grid.children;
    for (let card of cards) {
      // Kart içindeki ürün adını kontrol et
      const urunAdiSpan = card.querySelector("span[title]");
      if (urunAdiSpan && urunAdiSpan.title === urunAdi) {
        // Bu kartı yeniden oluştur
        const urun = {
          urun_id: urunId,
          urun_adi: urunAdi,
          setup_miktari: setupMiktari,
          ekstra_miktar: ekstraMiktar || 0,
          setup_id: setupId,
        };

        const yeniKart = createUrunCard(urun);
        card.replaceWith(yeniKart);
        return;
      }
    }
  });
}

// Setup aşımı uyarı dialog'u - Sayfanın ortasında
function setupAsimiUyariGoster(
  urunAdi,
  setupMiktari,
  bugunEklenen,
  kalanEklenebilir,
) {
  // Mevcut dialog varsa kaldır
  const existingDialog = document.getElementById("setupAsimiDialog");
  if (existingDialog) existingDialog.remove();

  const dialog = document.createElement("div");
  dialog.id = "setupAsimiDialog";
  dialog.className =
    "fixed inset-0 bg-black/60 backdrop-blur-sm z-50 flex items-center justify-center p-4";
  dialog.onclick = (e) => {
    if (e.target === dialog) dialog.remove();
  };

  dialog.innerHTML = `
    <div class="bg-white dark:bg-slate-800 rounded-2xl shadow-2xl p-6 max-w-sm w-full text-center transform animate-successPop">
      <div class="w-16 h-16 mx-auto mb-4 rounded-full bg-red-100 dark:bg-red-900/30 flex items-center justify-center">
        <i class="fas fa-exclamation-triangle text-3xl text-red-500"></i>
      </div>
      <h3 class="text-lg font-bold text-slate-900 dark:text-white mb-2">Setup Miktarı Aşılamaz!</h3>
      <p class="text-base font-medium text-slate-900 dark:text-white mb-4" style="font-family: 'Roboto', system-ui, -apple-system, 'Segoe UI', 'Helvetica Neue', Arial, sans-serif;">${urunAdi}</p>
      
      <div class="bg-slate-100 dark:bg-slate-700 rounded-xl p-4 mb-4 space-y-2">
        <div class="flex justify-between text-sm">
          <span class="text-slate-500 dark:text-slate-400">Setup Miktarı:</span>
          <span class="font-bold text-indigo-600 dark:text-indigo-400">${setupMiktari}</span>
        </div>
        <div class="flex justify-between text-sm">
          <span class="text-slate-500 dark:text-slate-400">Bugün Eklenen:</span>
          <span class="font-bold text-green-600 dark:text-green-400">${bugunEklenen}</span>
        </div>
        <div class="flex justify-between text-sm border-t border-slate-200 dark:border-slate-600 pt-2">
          <span class="text-slate-500 dark:text-slate-400">Kalan Eklenebilir:</span>
          <span class="font-bold text-orange-600 dark:text-orange-400">${kalanEklenebilir}</span>
        </div>
      </div>
      
      <button onclick="document.getElementById('setupAsimiDialog').remove()" 
        class="w-full py-3 bg-slate-200 dark:bg-slate-700 text-slate-700 dark:text-slate-300 font-bold rounded-xl active:scale-95 transition-all">
        Tamam
      </button>
    </div>
  `;

  document.body.appendChild(dialog);
}

// Kontrol durumu badge'ini göster
function kontrolDurumuBadgeGoster(kontrolDurumu) {
  const badgeContainer = document.getElementById("kontrol_durumu_badge");
  const badgeContent = document.getElementById("kontrol_badge_content");

  if (!badgeContainer || !badgeContent) return;

  if (!kontrolDurumu) {
    badgeContainer.classList.add("hidden");
    return;
  }

  let badgeClass = "";
  let icon = "";
  let text = "";

  switch (kontrolDurumu.durum) {
    case "completed":
      badgeClass = "bg-green-500 text-white";
      icon = '<i class="fas fa-check-circle mr-2"></i>';
      text = `✅ ${kontrolDurumu.tip}`;
      break;
    case "dnd":
      badgeClass = "bg-orange-500 text-white";
      icon = '<i class="fas fa-door-closed mr-2"></i>';
      text = `🚫 ${kontrolDurumu.tip}`;
      break;
    case "sarfiyat_yok":
      badgeClass = "bg-blue-500 text-white";
      icon = '<i class="fas fa-check mr-2"></i>';
      text = `✔️ ${kontrolDurumu.tip}`;
      break;
    default:
      badgeContainer.classList.add("hidden");
      return;
  }

  // Saat bilgisi varsa ekle
  if (kontrolDurumu.saat) {
    text += ` - ${kontrolDurumu.saat}`;
  }

  badgeContent.className = `inline-flex items-center px-4 py-2 rounded-full text-sm font-bold ${badgeClass}`;
  badgeContent.innerHTML = `${icon}${text}`;
  badgeContainer.classList.remove("hidden");
}

// ============================================================================
// SETUP DIŞI ÜRÜN EKLEME
// ============================================================================

let setupDisiUrunler = null; // Cache

// Setup Dışı Ürün Ekle dialog'unu aç
async function setupDisiDialogAc() {
  if (!mevcutOdaId) {
    toastGoster("Önce bir oda seçin", "warning");
    return;
  }

  // Mevcut dialog varsa kaldır
  const existing = document.getElementById("setupDisiDialog");
  if (existing) existing.remove();

  // Dialog oluştur
  const dialog = document.createElement("div");
  dialog.id = "setupDisiDialog";
  dialog.className =
    "fixed inset-0 bg-slate-950/95 z-50 flex items-end sm:items-center justify-center";
  dialog.onclick = (e) => {
    if (e.target === dialog) setupDisiDialogKapat();
  };

  dialog.innerHTML = `
    <div class="bg-slate-900 w-full max-w-lg rounded-t-3xl sm:rounded-2xl shadow-2xl max-h-[90vh] flex flex-col animate-slideUp overflow-hidden border border-slate-700/60">
      <!-- Header -->
      <div class="bg-gradient-to-r from-violet-600 via-purple-600 to-fuchsia-600 px-5 py-5 flex-shrink-0">
        <div class="flex items-center justify-between">
          <div class="flex items-center gap-3 min-w-0">
            <div class="w-11 h-11 rounded-xl bg-white/20 flex items-center justify-center flex-shrink-0">
              <svg class="w-6 h-6 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M20 7l-8-4-8 4m16 0l-8 4m8-4v10l-8 4m0-10L4 7m8 4v10M4 7v10l8 4"></path>
              </svg>
            </div>
            <div class="min-w-0">
              <h3 class="text-lg font-bold text-white">Setup Dışı Ürün Ekle</h3>
              <p class="text-sm text-white/70 mt-0.5">Stoğunuzdaki ürünleri ekleyin</p>
            </div>
          </div>
          <button onclick="setupDisiDialogKapat()" class="w-10 h-10 rounded-xl bg-white/20 flex items-center justify-center text-white hover:bg-white/30 transition-all touch-manipulation active:scale-90 flex-shrink-0">
            <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2.5" d="M6 18L18 6M6 6l12 12"></path></svg>
          </button>
        </div>
      </div>

      <!-- Arama -->
      <div class="px-4 py-3 border-b border-slate-700/60 flex-shrink-0 bg-slate-900">
        <div class="relative">
          <svg class="absolute left-3.5 top-1/2 -translate-y-1/2 w-5 h-5 text-violet-400" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"></path></svg>
          <input type="text" id="setupDisiArama" placeholder="Ürün ara..." oninput="setupDisiFiltrele(this.value)"
            class="w-full pl-11 pr-4 py-3 bg-slate-800 border border-slate-600 rounded-xl text-white placeholder-slate-500 focus:border-violet-500 focus:ring-2 focus:ring-violet-500/30 text-base touch-manipulation transition-all">
        </div>
      </div>

      <!-- Ürün Listesi -->
      <div id="setupDisiUrunListesi" class="flex-1 overflow-y-auto px-4 py-3" style="min-height: 200px; max-height: 55vh;">
        <div class="flex flex-col items-center justify-center py-12 gap-3">
          <div class="w-12 h-12 rounded-full bg-violet-500/20 flex items-center justify-center">
            <div class="animate-spin w-6 h-6 border-2 border-violet-400 border-t-transparent rounded-full"></div>
          </div>
          <span class="text-sm text-slate-400">Ürünler yükleniyor...</span>
        </div>
      </div>
    </div>
  `;

  document.body.appendChild(dialog);

  // Ürünleri yükle
  await setupDisiUrunleriYukle();
}

// Dialog kapat
function setupDisiDialogKapat() {
  const dialog = document.getElementById("setupDisiDialog");
  if (dialog) dialog.remove();
}

// Ürünleri API'den yükle
async function setupDisiUrunleriYukle() {
  try {
    const response = await fetch(
      `/api/kat-sorumlusu/zimmet-urunler?oda_id=${mevcutOdaId}`,
    );
    const data = await response.json();

    if (!response.ok || !data.success) {
      throw new Error(data.error || "Ürünler yüklenemedi");
    }

    setupDisiUrunler = data.gruplar;
    setupDisiListeRender(setupDisiUrunler);
  } catch (error) {
    console.error("❌ Setup dışı ürün yükleme hatası:", error);
    const container = document.getElementById("setupDisiUrunListesi");
    if (container) {
      container.innerHTML = `
        <div class="text-center py-8 text-red-400">
          <svg class="w-10 h-10 mx-auto mb-2 opacity-50" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.964-.833-2.732 0L4.082 16.5c-.77.833.192 2.5 1.732 2.5z"></path></svg>
          <p>${error.message}</p>
        </div>`;
    }
  }
}

// Ürün listesini render et
function setupDisiListeRender(gruplar, filtre = "") {
  const container = document.getElementById("setupDisiUrunListesi");
  if (!container) return;

  const filtreLC = filtre.toLowerCase().trim();
  let html = "";
  let toplamGosterilen = 0;

  // Kategori renkleri — statik class'lar (Tailwind JIT uyumlu)
  const kategoriStilleri = [
    {
      dot: "bg-violet-400",
      text: "text-violet-400",
      badge: "bg-violet-500/20 text-violet-300",
    },
    {
      dot: "bg-cyan-400",
      text: "text-cyan-400",
      badge: "bg-cyan-500/20 text-cyan-300",
    },
    {
      dot: "bg-rose-400",
      text: "text-rose-400",
      badge: "bg-rose-500/20 text-rose-300",
    },
    {
      dot: "bg-amber-400",
      text: "text-amber-400",
      badge: "bg-amber-500/20 text-amber-300",
    },
    {
      dot: "bg-emerald-400",
      text: "text-emerald-400",
      badge: "bg-emerald-500/20 text-emerald-300",
    },
    {
      dot: "bg-sky-400",
      text: "text-sky-400",
      badge: "bg-sky-500/20 text-sky-300",
    },
    {
      dot: "bg-fuchsia-400",
      text: "text-fuchsia-400",
      badge: "bg-fuchsia-500/20 text-fuchsia-300",
    },
    {
      dot: "bg-lime-400",
      text: "text-lime-400",
      badge: "bg-lime-500/20 text-lime-300",
    },
  ];

  const grupAdlari = Object.keys(gruplar).sort();

  grupAdlari.forEach((grupAdi, grupIndex) => {
    const urunler = gruplar[grupAdi].filter((u) => {
      if (!filtreLC) return true;
      return u.urun_adi.toLowerCase().includes(filtreLC);
    });

    if (urunler.length === 0) return;
    toplamGosterilen += urunler.length;

    const stil = kategoriStilleri[grupIndex % kategoriStilleri.length];

    // Kategori başlığı
    html += `<div class="mb-3 mt-1">
      <div class="flex items-center gap-2 mb-2 px-1">
        <span class="w-2.5 h-2.5 rounded-full ${stil.dot} flex-shrink-0"></span>
        <p class="text-xs font-bold ${stil.text} uppercase tracking-widest flex-1">${grupAdi}</p>
        <span class="text-[10px] font-bold ${stil.badge} px-2 py-0.5 rounded-full">${urunler.length}</span>
      </div>`;

    for (const urun of urunler) {
      const setupBadge = urun.setup_urunu
        ? `<span class="text-[10px] font-semibold bg-indigo-500/20 text-indigo-300 px-1.5 py-0.5 rounded">Setup</span>`
        : "";

      // Stok renk — basit ve net
      let stokClass;
      if (urun.stok > 10) {
        stokClass = "text-emerald-400";
      } else if (urun.stok > 0) {
        stokClass = "text-amber-400";
      } else {
        stokClass = "text-red-400";
      }

      html += `
      <button onclick="setupDisiUrunSec(${urun.urun_id}, '${urun.urun_adi.replace(/'/g, "\\'")}', ${urun.stok})"
        class="w-full flex items-center px-3 py-3 bg-slate-800 hover:bg-slate-700 rounded-xl mb-1.5 transition-all touch-manipulation active:scale-[0.98] border border-slate-700/50 hover:border-violet-500/40 text-left group"
        ${urun.stok <= 0 ? 'disabled style="opacity:0.35;pointer-events:none;"' : ""}>
        <div class="flex-1 min-w-0 mr-2 overflow-hidden">
          <p class="text-sm font-semibold text-white truncate" style="font-family: 'Roboto', system-ui, sans-serif;">${urun.urun_adi}</p>
          <div class="flex items-center gap-1.5 mt-0.5">
            <span class="text-[11px] text-slate-500">${urun.birim}</span>
            ${setupBadge}
          </div>
        </div>
        <div class="flex items-center gap-2 flex-shrink-0">
          <div class="text-right">
            <p class="text-base font-bold ${stokClass} tabular-nums leading-none">${urun.stok}</p>
            <p class="text-[9px] text-slate-500 mt-0.5 uppercase font-semibold">stok</p>
          </div>
          <svg class="w-4 h-4 text-slate-600 group-hover:text-violet-400 transition-colors" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7"></path></svg>
        </div>
      </button>`;
    }

    html += `</div>`;
  });

  if (toplamGosterilen === 0) {
    html = `
      <div class="text-center py-12">
        <div class="w-14 h-14 mx-auto mb-3 rounded-2xl bg-slate-800 flex items-center justify-center">
          <svg class="w-7 h-7 text-slate-500" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M20 13V6a2 2 0 00-2-2H6a2 2 0 00-2 2v7m16 0v5a2 2 0 01-2 2H6a2 2 0 01-2-2v-5m16 0h-2.586a1 1 0 00-.707.293l-2.414 2.414a1 1 0 01-.707.293h-2.172a1 1 0 01-.707-.293l-2.414-2.414A1 1 0 006.586 13H4"></path></svg>
        </div>
        <p class="text-sm font-medium text-slate-400">${filtreLC ? "Aramanızla eşleşen ürün bulunamadı" : "Stoğunuzda ürün bulunmuyor"}</p>
      </div>`;
  }

  container.innerHTML = html;
}

// Arama filtresi
function setupDisiFiltrele(deger) {
  if (setupDisiUrunler) {
    setupDisiListeRender(setupDisiUrunler, deger);
  }
}

// Ürün seçildiğinde — miktar giriş dialog'u
function setupDisiUrunSec(urunId, urunAdi, stok) {
  // Ürün listesi dialog'unu kapat
  setupDisiDialogKapat();

  // Miktar dialog'u oluştur
  const dialog = document.createElement("div");
  dialog.id = "setupDisiMiktarDialog";
  dialog.className =
    "fixed inset-0 bg-slate-950/95 z-50 flex items-center justify-center p-4";
  dialog.onclick = (e) => {
    if (e.target === dialog) setupDisiMiktarKapat();
  };

  dialog.innerHTML = `
    <div class="bg-slate-900 rounded-2xl shadow-2xl w-full max-w-sm animate-slideUp overflow-hidden border border-slate-700/60">
      <!-- Header -->
      <div class="bg-gradient-to-r from-violet-600 via-purple-600 to-fuchsia-600 px-5 py-4 text-center">
        <p class="text-lg font-bold text-white truncate" style="font-family: 'Roboto', system-ui, sans-serif;">${urunAdi}</p>
        <p class="text-sm text-white/70 mt-0.5">Setup Dışı Ürün Ekleme</p>
      </div>

      <!-- Content -->
      <div class="p-5 space-y-4">
        <!-- Stepper -->
        <div class="flex items-center justify-center gap-3">
          <button onclick="sdMiktarAzalt()"
            class="w-14 h-14 rounded-xl active:scale-90 transition-all flex items-center justify-center touch-manipulation"
            style="background:#dc2626;box-shadow:0 4px 12px rgba(220,38,38,0.4);">
            <svg class="w-7 h-7 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="3" d="M20 12H4"></path></svg>
          </button>
          <input type="number" id="sdMiktarInput" min="1" max="${stok}" value="1" inputmode="numeric"
            class="w-24 h-14 text-center text-3xl font-bold rounded-xl text-white touch-manipulation"
            style="background:#1e293b;border:2px solid #7c3aed;">
          <button onclick="sdMiktarArtir(${stok})"
            class="w-14 h-14 rounded-xl active:scale-90 transition-all flex items-center justify-center touch-manipulation"
            style="background:#059669;box-shadow:0 4px 12px rgba(5,150,105,0.4);">
            <svg class="w-7 h-7 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="3" d="M12 4v16m8-8H4"></path></svg>
          </button>
        </div>

        <!-- Hızlı Butonlar -->
        <div class="grid grid-cols-4 gap-2">
          ${[1, 2, 3, 5]
            .map(
              (n) => `
            <button onclick="document.getElementById('sdMiktarInput').value=${n}"
              class="py-3 text-base font-bold rounded-xl transition-all touch-manipulation active:scale-90 text-white"
              style="${
                stok >= n
                  ? "background:#7c3aed;box-shadow:0 4px 10px rgba(124,58,237,0.35);"
                  : "background:#1e293b;color:#475569;cursor:not-allowed;border:1px solid #334155;"
              }"
              ${stok < n ? "disabled" : ""}>+${n}</button>
          `,
            )
            .join("")}
        </div>

        <!-- Stok Bilgisi -->
        <div class="text-center text-sm py-2.5 rounded-xl" style="background:#1e293b;border:1px solid #334155;color:#cbd5e1;">
          Zimmet Stok: <strong style="color:${stok > 0 ? "#34d399" : "#f87171"};font-size:1.125rem;">${stok}</strong>
        </div>

        <!-- Ekle Butonu -->
        <button onclick="setupDisiUrunKaydet(${urunId}, '${urunAdi.replace(/'/g, "\\'")}')"
          class="w-full py-4 text-lg font-bold rounded-xl text-white active:scale-95 transition-all touch-manipulation"
          style="background:linear-gradient(to right,#059669,#16a34a);box-shadow:0 6px 20px rgba(5,150,105,0.4);">
          ✓ Ekle
        </button>

        <!-- Geri / İptal -->
        <div class="grid grid-cols-2 gap-2">
          <button onclick="setupDisiMiktarKapat(); setupDisiDialogAc();"
            class="py-3 text-sm font-semibold rounded-xl text-white transition-all touch-manipulation active:scale-95"
            style="background:#475569;box-shadow:0 2px 8px rgba(0,0,0,0.3);">
            ← Geri
          </button>
          <button onclick="setupDisiMiktarKapat()"
            class="py-3 text-sm font-semibold rounded-xl text-white transition-all touch-manipulation active:scale-95"
            style="background:#475569;box-shadow:0 2px 8px rgba(0,0,0,0.3);">
            İptal
          </button>
        </div>
      </div>
    </div>
  `;

  document.body.appendChild(dialog);
}

// Miktar dialog kapat
function setupDisiMiktarKapat() {
  const dialog = document.getElementById("setupDisiMiktarDialog");
  if (dialog) dialog.remove();
}

// Stepper fonksiyonları
function sdMiktarAzalt() {
  const input = document.getElementById("sdMiktarInput");
  const val = parseInt(input.value) || 1;
  if (val > 1) input.value = val - 1;
}

function sdMiktarArtir(maxStok) {
  const input = document.getElementById("sdMiktarInput");
  const val = parseInt(input.value) || 0;
  if (val < maxStok) input.value = val + 1;
}

// API'ye kaydet
async function setupDisiUrunKaydet(urunId, urunAdi) {
  const miktar = parseInt(document.getElementById("sdMiktarInput").value);

  if (!miktar || miktar <= 0) {
    toastGoster("Geçerli bir miktar girin", "warning");
    return;
  }

  // Butonu disable et
  const btn = document.querySelector(
    '#setupDisiMiktarDialog button[onclick*="setupDisiUrunKaydet"]',
  );
  if (btn) {
    btn.disabled = true;
    btn.innerHTML =
      '<span class="animate-spin inline-block w-5 h-5 border-2 border-white border-t-transparent rounded-full mr-2"></span> Kaydediliyor...';
  }

  try {
    const response = await fetch("/api/kat-sorumlusu/setup-disi-urun-ekle", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-CSRFToken": getCsrfToken(),
      },
      body: JSON.stringify({
        oda_id: mevcutOdaId,
        urun_id: urunId,
        miktar: miktar,
      }),
    });

    const data = await response.json();

    if (!response.ok || !data.success) {
      throw new Error(data.error || "Ürün eklenemedi");
    }

    // Dialog kapat
    setupDisiMiktarKapat();

    // Kalan stok
    const kalanStok = data.zimmet_kalan;

    // Success dialog göster
    successDialogGoster(urunAdi, miktar, "ekstra", kalanStok);

    // Cache temizle (bir sonraki açılışta yeniden yüklensin)
    setupDisiUrunler = null;

    // Setup listesini yenile
    await setupListesiYukle(mevcutOdaId);
  } catch (error) {
    console.error("❌ Setup dışı ürün ekleme hatası:", error);
    toastGoster(error.message, "error");

    // Butonu tekrar aktif et
    if (btn) {
      btn.disabled = false;
      btn.innerHTML = "✓ Ekle";
    }
  }
}
