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

  if (qrKatId && qrOdaId) {
    console.log(`🔍 QR parametreleri bulundu: Kat=${qrKatId}, Oda=${qrOdaId}`);
    qrParametreleriIsle(qrKatId, qrOdaId);
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
  await setupListesiYukle(odaId);
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

// Setup listesini render et
function renderSetupListesi(setuplar) {
  const container = document.getElementById("setup_listesi");
  container.innerHTML = "";

  setuplar.forEach((setup, index) => {
    const accordionItem = createAccordionItem(setup, index);
    container.appendChild(accordionItem);

    // Eğer bu akordion daha önce açıktıysa, tekrar aç
    if (acikAkordiyonlar.has(index)) {
      setTimeout(() => {
        const content = document.getElementById(`content-${index}`);
        const icon = document.getElementById(`icon-${index}`);
        if (content && icon) {
          content.classList.remove("hidden");
          icon.classList.add("rotate-180");
        }
      }, 100);
    }
  });
}

// Accordion item oluştur
function createAccordionItem(setup, index) {
  const item = document.createElement("div");
  item.className =
    "bg-white rounded-lg shadow-sm border border-slate-200 overflow-hidden";

  const headerClass = setup.dolap_ici
    ? "bg-gradient-to-r from-indigo-500 to-purple-600"
    : "bg-gradient-to-r from-pink-500 to-rose-600";

  // Dolap bilgisi
  let dolapBilgisi = "";
  if (setup.dolap_ici) {
    dolapBilgisi = `Dolap İçi - Dolap ${setup.dolap_no}`;
  } else {
    dolapBilgisi = "Dolap Dışı";
  }

  item.innerHTML = `
    <div class="${headerClass} text-white p-4 cursor-pointer hover:opacity-90 transition-opacity" onclick="accordionToggle(${index})">
      <div class="flex items-center justify-between">
        <div>
          <h3 class="text-lg font-semibold">${setup.setup_adi}</h3>
          <p class="text-sm opacity-90 mt-1">
            ${dolapBilgisi} • ${setup.urunler.length} ürün
          </p>
        </div>
        <svg id="icon-${index}" class="w-6 h-6 transform transition-transform" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7"></path>
        </svg>
      </div>
    </div>
    <div id="content-${index}" class="hidden">
      <div class="p-4">
        ${createUrunTablosu(setup)}
      </div>
    </div>
  `;

  return item;
}

// Ürün tablosu oluştur
function createUrunTablosu(setup) {
  let html = `
    <div class="overflow-x-auto">
      <table class="min-w-full divide-y divide-slate-200">
        <thead class="bg-slate-50">
          <tr>
            <th class="px-4 py-3 text-left text-xs font-medium text-slate-500 uppercase">Ürün</th>
            <th class="px-4 py-3 text-center text-xs font-medium text-slate-500 uppercase">Setup Miktarı</th>
            <th class="px-4 py-3 text-center text-xs font-medium text-slate-500 uppercase">Ekstra</th>
            <th class="px-4 py-3 text-center text-xs font-medium text-slate-500 uppercase">İşlem</th>
          </tr>
        </thead>
        <tbody class="bg-white divide-y divide-slate-200">
  `;

  setup.urunler.forEach((urun) => {
    const islemButonlari = getIslemButonlari(urun, setup);

    html += `
      <tr class="hover:bg-slate-50 transition-colors">
        <td class="px-4 py-3 text-sm font-medium text-slate-900">${
          urun.urun_adi
        }</td>
        <td class="px-4 py-3 text-sm text-center font-semibold text-slate-900">${
          urun.setup_miktari
        }</td>
        <td class="px-4 py-3 text-sm text-center ${
          urun.ekstra_miktar > 0
            ? "text-orange-600 font-bold"
            : "text-slate-400"
        }">${urun.ekstra_miktar || "-"}</td>
        <td class="px-4 py-3 text-center">${islemButonlari}</td>
      </tr>
    `;
  });

  html += `
        </tbody>
      </table>
    </div>
  `;

  return html;
}

// İşlem butonlarını oluştur
function getIslemButonlari(urun, setup) {
  let butonlar = "";

  // HER ZAMAN "Ekle" butonu göster (tüketim ikamesi için)
  butonlar += `
    <button onclick="urunEkleModalAc(${urun.urun_id}, '${urun.urun_adi.replace(
    /'/g,
    "\\'"
  )}', ${urun.setup_miktari}, ${urun.ekstra_miktar || 0}, ${setup.setup_id})" 
            class="inline-flex items-center px-3 py-1.5 bg-blue-600 text-white text-xs font-medium rounded-lg hover:bg-blue-700 transition-colors">
      Ekle
    </button>
  `;

  // HER ZAMAN "Ekstra" butonu göster (setup üstü ekleme için)
  butonlar += `
    <button onclick="ekstraEkleModalAc(${
      urun.urun_id
    }, '${urun.urun_adi.replace(/'/g, "\\'")}', ${urun.setup_miktari}, ${
    urun.ekstra_miktar || 0
  }, ${setup.setup_id})" 
            class="inline-flex items-center px-3 py-1.5 bg-orange-500 text-white text-xs font-medium rounded-lg hover:bg-orange-600 transition-colors ml-2">
      Ekstra
    </button>
  `;

  // Eğer ekstra varsa "Sıfırla" butonu göster
  if (urun.ekstra_miktar > 0) {
    butonlar += `
      <button onclick="ekstraSifirlaModalAc(${
        urun.urun_id
      }, '${urun.urun_adi.replace(/'/g, "\\'")}', ${urun.ekstra_miktar}, ${
      setup.setup_id
    })" 
              class="inline-flex items-center px-3 py-1.5 bg-red-600 text-white text-xs font-medium rounded-lg hover:bg-red-700 transition-colors ml-2">
        Sıfırla
      </button>
    `;
  }

  return butonlar;
}

// Accordion toggle
function accordionToggle(index) {
  const content = document.getElementById(`content-${index}`);
  const icon = document.getElementById(`icon-${index}`);

  const isOpen = !content.classList.contains("hidden");

  content.classList.toggle("hidden");
  icon.classList.toggle("rotate-180");

  // Açık/kapalı durumu kaydet
  if (isOpen) {
    acikAkordiyonlar.delete(index);
  } else {
    acikAkordiyonlar.add(index);
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
  await setupListesiYukle(odaId);
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
