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

    renderSetupListesi(data.setuplar);

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
function renderSetupListesi(setuplar) {
  const container = document.getElementById("setup_listesi");
  container.innerHTML = "";

  setuplar.forEach((setup, index) => {
    // Setup başlığı
    const setupDiv = document.createElement("div");
    setupDiv.className =
      "bg-slate-800/80 dark:bg-slate-800/80 rounded-xl shadow-sm border border-slate-700/50 dark:border-slate-700/50 overflow-hidden mb-4 backdrop-blur-sm";

    const headerClass = setup.dolap_ici
      ? "bg-gradient-to-r from-slate-700 to-slate-800"
      : "bg-gradient-to-r from-slate-600 to-slate-700";

    const dolapBilgisi = setup.dolap_ici
      ? `Dolap ${setup.dolap_no}`
      : "Dolap Dışı";

    setupDiv.innerHTML = `
      <div class="${headerClass} text-white px-4 py-3 border-b border-slate-700/50">
        <div class="flex items-center justify-between">
          <div>
            <h3 class="text-base font-semibold text-slate-100">${setup.setup_adi}</h3>
            <p class="text-xs text-slate-300">${dolapBilgisi} • ${setup.urunler.length} ürün</p>
          </div>
        </div>
      </div>
      <div class="p-3 bg-slate-900/30">
        <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3" id="setup-grid-${index}"></div>
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
}

// Ürün kartı oluştur - Kompakt ve Pratik + Bugünkü Ekleme Badge
function createUrunCard(urun) {
  const card = document.createElement("div");
  card.className =
    "bg-slate-800/70 dark:bg-slate-800/70 rounded-lg p-2.5 border border-slate-700 dark:border-slate-700 relative backdrop-blur-sm hover:border-slate-600 transition-all shadow-md hover:shadow-lg";

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
    butonlar.push(`
      <button style="background-color:#2b00fa ;" onclick="hizliUrunEkle(${urun.urun_id}, '${urun.urun_adi.replace(
        /'/g,
        "\\'",
      )}', ${urun.setup_miktari}, ${urun.ekstra_miktar || 0}, ${
        urun.setup_id
      }, ${i})"
        class="py-1 text-sm font-semibold rounded-md transition-all shadow-sm ${
          aktif
            ? "bg-gradient-to-b from-cyan-500 to-blue-600 text-white hover:from-cyan-600 hover:to-blue-700 active:scale-95"
            : "bg-gradient-to-b from-slate-700 to-slate-800 text-slate-500 cursor-not-allowed"
        }"
        ${!aktif ? "disabled" : ""}>
        +${i}
      </button>
    `);
  }

  // Bugünkü ekleme badge'i (sağ tarafta, yanıp sönme yok)
  const bugunBadge =
    bugunEklenen > 0
      ? `<span class="w-7 h-7 rounded-full bg-gradient-to-b from-blue-500 to-blue-600 text-white text-xs font-bold flex items-center justify-center shadow-md">+${bugunEklenen}</span>`
      : `<span class="w-7 h-7"></span>`;

  card.innerHTML = `
    <!-- Üst Satır: Setup Miktarı | Ürün Adı | Bugün Eklenen -->
    <div class="flex items-center justify-between mb-2">
      <span class="w-7 h-7 rounded-full bg-gradient-to-b from-indigo-500 to-indigo-600 text-white text-xs font-bold flex items-center justify-center shadow-md">${
        urun.setup_miktari
      }</span>
      <span class="text-lg font-medium text-slate-100 dark:text-slate-100 truncate flex-1 text-center mx-2" style="font-family: 'Roboto', system-ui, -apple-system, 'Segoe UI', 'Helvetica Neue', Arial, sans-serif;" title="${
        urun.urun_adi
      }">${urun.urun_adi}</span>
      ${bugunBadge}
    </div>
    
    <!-- Stok ve Ekstra Bilgisi -->
    <div class="flex justify-between text-xs mb-2">
      <span class="text-slate-300 dark:text-slate-300">Stok: <strong class="text-base ${
        stokVar ? "text-emerald-400" : "text-red-400"
      }">${zimmetStok?.miktar || 0}</strong></span>
      ${
        urun.ekstra_miktar > 0
          ? `<span class="text-amber-400 font-bold text-sm">+${urun.ekstra_miktar} ekstra</span>`
          : ""
      }
    </div>
    
    <!-- Hızlı Ekleme Butonları -->
    <div class="grid grid-cols-${butonSayisi} gap-1.5 mb-2">
      ${butonlar.join("")}
    </div>
    
    <!-- Ekstra ve Sıfırla Butonları -->
    ${
      urun.ekstra_miktar > 0
        ? `
    <div class="grid grid-cols-2 gap-1.5">
      <button onclick="ekstraDialogAc(${urun.urun_id}, '${urun.urun_adi.replace(
        /'/g,
        "\\'",
      )}', ${urun.setup_miktari}, ${urun.ekstra_miktar || 0}, ${urun.setup_id})"
        class="py-1.5 text-xs font-semibold rounded-md bg-gradient-to-b from-amber-500 to-amber-600 text-white hover:from-amber-600 hover:to-amber-700 active:scale-95 transition-all shadow-sm">
        + Ekstra
      </button>
      <button onclick="ekstraSifirlaModalAc(${
        urun.urun_id
      }, '${urun.urun_adi.replace(/'/g, "\\'")}', ${urun.ekstra_miktar}, ${
        urun.setup_id
      })"
        class="py-1.5 text-xs font-semibold rounded-md bg-gradient-to-b from-red-500 to-red-600 text-white hover:from-red-600 hover:to-red-700 active:scale-95 transition-all shadow-sm">
        Sıfırla
      </button>
    </div>
    `
        : `
    <button onclick="ekstraDialogAc(${urun.urun_id}, '${urun.urun_adi.replace(
      /'/g,
      "\\'",
    )}', ${urun.setup_miktari}, ${urun.ekstra_miktar || 0}, ${urun.setup_id})"
      class="w-full py-1.5 text-xs font-semibold rounded-md bg-gradient-to-b from-amber-500 to-amber-600 text-white hover:from-amber-600 hover:to-amber-700 active:scale-95 transition-all shadow-sm">
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

  dialog.innerHTML = `
    <div class="bg-slate-800 dark:bg-slate-800 rounded-xl shadow-2xl w-full max-w-sm animate-slideUp overflow-hidden">
      <!-- Header -->
      <div class="bg-gradient-to-r from-amber-500 to-amber-600 px-4 py-3 text-center">
        <p class="text-base font-semibold text-white" style="font-family: 'Roboto', system-ui, -apple-system, 'Segoe UI', 'Helvetica Neue', Arial, sans-serif;">${urunAdi}</p>
        <p class="text-xs text-amber-100 mt-0.5">Ekstra Ekle</p>
      </div>
      
      <!-- Content -->
      <div class="p-5">
        <!-- Miktar Girişi -->
        <div class="flex gap-3 mb-4">
          <input type="number" id="ekstraDialogInput" min="1" value="1" inputmode="numeric"
            class="flex-1 px-4 py-3 text-center text-3xl font-bold border-2 border-slate-600 rounded-lg bg-slate-900 text-white focus:border-amber-500 focus:ring-2 focus:ring-amber-500/50">
          <button onclick="hizliEkstraEkle(parseInt(document.getElementById('ekstraDialogInput').value))"
            class="px-6 py-3 bg-gradient-to-b from-amber-500 to-amber-600 text-white font-bold rounded-lg hover:from-amber-600 hover:to-amber-700 active:scale-95 transition-all shadow-md">
            Ekle
          </button>
        </div>
        
        <!-- Stok Bilgisi -->
        <div class="text-center text-sm text-slate-400 mb-4 py-2.5 bg-slate-900/50 rounded-lg">
          Stok: <strong class="${
            zimmetStok?.miktar > 0 ? "text-emerald-400" : "text-red-400"
          }">${zimmetStok?.miktar || 0}</strong>
        </div>
        
        <!-- İptal Butonu -->
        <button onclick="ekstraDialogKapat()" class="w-full py-2.5 text-sm font-semibold rounded-lg bg-slate-700 hover:bg-slate-600 text-slate-300 transition-all">
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

    // Success dialog göster
    successDialogGoster(modalData.urun_adi, miktar, "ekstra");
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

    // Success dialog göster
    successDialogGoster(urunAdi, miktar, "tuketim");
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
function successDialogGoster(urunAdi, miktar, tip = "tuketim") {
  // Mevcut dialog varsa kaldır
  const existingDialog = document.getElementById("successDialog");
  if (existingDialog) existingDialog.remove();

  const renk = tip === "ekstra" ? "orange" : "green";
  const ikon = tip === "ekstra" ? "plus-circle" : "check-circle";
  const baslik = tip === "ekstra" ? "Ekstra Eklendi" : "Tüketim Kaydedildi";

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
    </div>
  `;

  document.body.appendChild(dialog);

  // 1.5 saniye sonra otomatik kapat
  setTimeout(() => {
    dialog.classList.add("animate-fadeOut");
    setTimeout(() => dialog.remove(), 300);
  }, 1500);
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
