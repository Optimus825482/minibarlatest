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
document.addEventListener("DOMContentLoaded", function () {
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
    katDetayGeriDonUrl = "/doluluk/kat-doluluk/" + qrKatId;
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
      `📋 Görev parametreleri bulundu: Oda=${gorevOdaId}, Detay=${gorevDetayId}`
    );
    mevcutGorevDetayId = gorevDetayId;
    gorevOdaKontrolBaslat(gorevOdaId);
  }
});

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
}

// Oda seçimine geri dön
function odaSecimineGeriDon() {
  // Kat detaylarından gelindiyse oraya geri dön
  if (katDetayGeriDonUrl) {
    window.location.href = katDetayGeriDonUrl;
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

    renderSetupListesi(data.setuplar);

    setupListesiDiv.classList.remove("hidden");
    console.log(`✅ ${data.setuplar.length} setup yüklendi`);
  } catch (error) {
    console.error("❌ Setup yükleme hatası:", error);
    toastGoster(error.message, "error");
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
      "bg-white dark:bg-slate-800 rounded-xl shadow-sm border border-slate-200 dark:border-slate-700 overflow-hidden mb-4";

    const headerClass = setup.dolap_ici
      ? "bg-gradient-to-r from-indigo-500 to-purple-600"
      : "bg-gradient-to-r from-pink-500 to-rose-600";

    const dolapBilgisi = setup.dolap_ici
      ? `Dolap ${setup.dolap_no}`
      : "Dolap Dışı";

    setupDiv.innerHTML = `
      <div class="${headerClass} text-white px-4 py-3">
        <div class="flex items-center justify-between">
          <div>
            <h3 class="text-base font-bold">${setup.setup_adi}</h3>
            <p class="text-xs opacity-80">${dolapBilgisi} • ${setup.urunler.length} ürün</p>
          </div>
        </div>
      </div>
      <div class="p-3">
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
    "bg-slate-50 dark:bg-slate-900 rounded-lg p-3 border border-slate-200 dark:border-slate-700 relative";

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
      <button onclick="hizliUrunEkle(${urun.urun_id}, '${urun.urun_adi.replace(
      /'/g,
      "\\'"
    )}', ${urun.setup_miktari}, ${urun.ekstra_miktar || 0}, ${
      urun.setup_id
    }, ${i})"
        class="py-1.5 text-s font-bold rounded transition-all ${
          aktif
            ? "bg-indigo-600 text-white active:bg-indigo-700"
            : "bg-slate-300 dark:bg-slate-600 text-slate-400 cursor-not-allowed"
        }"
        ${!aktif ? "disabled" : ""}>
        +${i}
      </button>
    `);
  }

  // Bugünkü ekleme badge'i (sağ tarafta, yanıp sönme yok)
  const bugunBadge =
    bugunEklenen > 0
      ? `<span class="w-8 h-8 rounded-full bg-green-500 text-white text-sm font-bold flex items-center justify-center shadow-md">+${bugunEklenen}</span>`
      : `<span class="w-8 h-8"></span>`;

  card.innerHTML = `
    <!-- Üst Satır: Setup Miktarı | Ürün Adı | Bugün Eklenen -->
    <div class="flex items-center justify-between mb-2">
      <span class="w-8 h-8 rounded-full bg-indigo-500 text-white text-sm font-bold flex items-center justify-center">${
        urun.setup_miktari
      }</span>
      <span class="text-base font-bold text-slate-800 dark:text-white truncate flex-1 text-center mx-2" title="${
        urun.urun_adi
      }">${urun.urun_adi}</span>
      ${bugunBadge}
    </div>
    
    <!-- Stok ve Ekstra Bilgisi -->
    <div class="flex justify-between text-xs mb-2">
      <span class="text-slate-500 dark:text-slate-400">Stok: <strong class="${
        stokVar ? "text-green-600" : "text-red-500"
      }">${zimmetStok?.miktar || 0}</strong></span>
      ${
        urun.ekstra_miktar > 0
          ? `<span class="text-orange-500 font-bold">+${urun.ekstra_miktar} ekstra</span>`
          : ""
      }
    </div>
    
    <!-- Hızlı Ekleme Butonları -->
    <div class="grid grid-cols-${butonSayisi} gap-1 mb-2">
      ${butonlar.join("")}
    </div>
    
    <!-- Ekstra Butonu -->
    <button onclick="ekstraDialogAc(${urun.urun_id}, '${urun.urun_adi.replace(
    /'/g,
    "\\'"
  )}', ${urun.setup_miktari}, ${urun.ekstra_miktar || 0}, ${urun.setup_id})"
      class="w-full py-1.5 text-s font-medium rounded bg-orange-100 dark:bg-orange-900/30 text-orange-600 dark:text-orange-400 active:bg-orange-200">
      + Ekstra
    </button>
    
    ${
      urun.ekstra_miktar > 0
        ? `
      <button onclick="ekstraSifirlaModalAc(${
        urun.urun_id
      }, '${urun.urun_adi.replace(/'/g, "\\'")}', ${urun.ekstra_miktar}, ${
            urun.setup_id
          })"
        class="w-full mt-1 py-1.5 text-xs font-medium rounded bg-red-100 dark:bg-red-900/30 text-red-600 dark:text-red-400 active:bg-red-200">
        Sıfırla
      </button>
    `
        : ""
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
    <div class="bg-white dark:bg-slate-800 rounded-xl shadow-2xl w-full max-w-xs p-4 animate-slideUp">
      <div class="text-center mb-3">
        <p class="text-sm font-bold text-slate-900 dark:text-white">${urunAdi}</p>
        <p class="text-xs text-slate-500">Ekstra Ekle</p>
      </div>
      
      <!-- Miktar Girişi -->
      <div class="flex gap-2 mb-3">
        <input type="number" id="ekstraDialogInput" min="1" value="1" inputmode="numeric"
          class="flex-1 px-3 py-3 text-center text-xl font-bold border-2 border-slate-300 dark:border-slate-600 rounded-lg dark:bg-slate-900 dark:text-white focus:border-orange-500 focus:ring-2 focus:ring-orange-200">
        <button onclick="hizliEkstraEkle(parseInt(document.getElementById('ekstraDialogInput').value))"
          class="px-5 py-3 bg-orange-600 text-white font-bold rounded-lg active:bg-orange-700 active:scale-95 transition-all">
          Ekle
        </button>
      </div>
      
      <div class="text-center text-xs text-slate-500 mb-3">
        Stok: <strong class="${
          zimmetStok?.miktar > 0 ? "text-green-600" : "text-red-500"
        }">${zimmetStok?.miktar || 0}</strong>
      </div>
      
      <button onclick="ekstraDialogKapat()" class="w-full py-2 text-sm font-medium rounded-lg bg-slate-200 dark:bg-slate-700 text-slate-700 dark:text-slate-300">
        İptal
      </button>
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
  miktar
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
      kalanEklenebilir
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
  setupId
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
    setupMiktari + (ekstraMiktar || 0)
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
    document.getElementById("modal_eklenen_miktar").value
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
    document.getElementById("ekstra_modal_miktar").value
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
  const panel = document.getElementById("gorev_islemleri");
  if (panel && mevcutOdaId) {
    panel.classList.remove("hidden");
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
function dndOnayla() {
  if (!mevcutOdaId) {
    toastGoster("Lütfen önce bir oda seçin", "warning");
    return;
  }

  const odaNo =
    document.getElementById("oda_no_text")?.textContent || mevcutOdaId;

  // Modal içeriğini güncelle
  document.getElementById("dnd_modal_oda_no").textContent = odaNo;

  // Modal'ı göster
  document.getElementById("dndModal").classList.remove("hidden");
}

// DND modal kapat
function dndModalKapat() {
  document.getElementById("dndModal").classList.add("hidden");
}

// DND kaydı
async function dndKaydet() {
  try {
    const response = await fetch("/api/kat-sorumlusu/dnd-kaydet", {
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
      throw new Error(data.error || "DND kaydı yapılamadı");
    }

    toastGoster(`✅ ${data.message}`, "success");

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
    console.error("❌ DND kayıt hatası:", error);
    toastGoster(error.message, "error");
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
      <p class="text-sm text-slate-600 dark:text-slate-400 mb-2">${urunAdi}</p>
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
  kalanEklenebilir
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
      <p class="text-sm font-medium text-slate-700 dark:text-slate-300 mb-4">${urunAdi}</p>
      
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
