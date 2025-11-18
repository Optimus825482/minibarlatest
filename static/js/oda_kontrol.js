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

  item.innerHTML = `
    <div class="${headerClass} text-white p-4 cursor-pointer hover:opacity-90 transition-opacity" onclick="accordionToggle(${index})">
      <div class="flex items-center justify-between">
        <div>
          <h3 class="text-lg font-semibold">${setup.setup_adi}</h3>
          <p class="text-sm opacity-90 mt-1">
            ${
              setup.dolap_ici
                ? `Dolap İçi (${setup.dolap_sayisi} dolap)`
                : "Dolap Dışı"
            } • ${setup.urunler.length} ürün
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
    <button onclick='urunEkleModalAc(${JSON.stringify(urun)}, ${
    setup.setup_id
  })' 
            class="inline-flex items-center px-3 py-1.5 bg-blue-600 text-white text-xs font-medium rounded-lg hover:bg-blue-700 transition-colors">
      Ekle
    </button>
  `;

  // HER ZAMAN "Ekstra" butonu göster (setup üstü ekleme için)
  butonlar += `
    <button onclick='ekstraEkleModalAc(${JSON.stringify(urun)}, ${
    setup.setup_id
  })' 
            class="inline-flex items-center px-3 py-1.5 bg-orange-500 text-white text-xs font-medium rounded-lg hover:bg-orange-600 transition-colors ml-2">
      Ekstra
    </button>
  `;

  // Eğer ekstra varsa "Sıfırla" butonu göster
  if (urun.ekstra_miktar > 0) {
    butonlar += `
      <button onclick='ekstraSifirlaModalAc(${JSON.stringify(urun)}, ${
      setup.setup_id
    })' 
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

  content.classList.toggle("hidden");
  icon.classList.toggle("rotate-180");
}

// Setup listesini temizle
function setupListesiniTemizle() {
  document.getElementById("setup_listesi").innerHTML = "";
  document.getElementById("setup_listesi").classList.add("hidden");
  document.getElementById("oda_bilgileri").classList.add("hidden");
  mevcutOdaId = null;
  mevcutSetuplar = [];
  zimmetStoklar = {};
}

// Modal fonksiyonları
function urunEkleModalAc(urun, setupId) {
  modalData = {
    oda_id: mevcutOdaId,
    urun_id: urun.urun_id,
    setup_id: setupId,
    urun_adi: urun.urun_adi,
    setup_miktari: urun.setup_miktari,
  };

  document.getElementById("modal_urun_adi").textContent = urun.urun_adi;
  document.getElementById("modal_setup_miktari").textContent =
    urun.setup_miktari;
  document.getElementById("modal_max_miktar").textContent = urun.setup_miktari;

  const inputEklenen = document.getElementById("modal_eklenen_miktar");
  inputEklenen.value = 1; // Varsayılan 1
  inputEklenen.max = urun.setup_miktari; // Maksimum setup miktarı

  const zimmetStok = zimmetStoklar[urun.urun_id];
  if (zimmetStok) {
    document.getElementById("modal_zimmet_stok").textContent =
      zimmetStok.miktar;
    modalData.zimmet_detay_id = zimmetStok.zimmet_detay_id;
  } else {
    document.getElementById("modal_zimmet_stok").textContent = "0 (Yetersiz!)";
  }

  document.getElementById("urunEkleModal").classList.remove("hidden");
}

function urunEkleModalKapat() {
  document.getElementById("urunEkleModal").classList.add("hidden");
  modalData = {};
}

function ekstraEkleModalAc(urun, setupId) {
  modalData = {
    oda_id: mevcutOdaId,
    urun_id: urun.urun_id,
    setup_id: setupId,
    urun_adi: urun.urun_adi,
    setup_miktari: urun.setup_miktari,
  };

  document.getElementById("ekstra_modal_urun_adi").textContent = urun.urun_adi;
  document.getElementById("ekstra_modal_setup_miktari").textContent =
    urun.setup_miktari;
  document.getElementById("ekstra_modal_miktar").value = 1;

  const zimmetStok = zimmetStoklar[urun.urun_id];
  if (zimmetStok) {
    document.getElementById("ekstra_modal_zimmet_stok").textContent =
      zimmetStok.miktar;
    modalData.zimmet_detay_id = zimmetStok.zimmet_detay_id;
  } else {
    document.getElementById("ekstra_modal_zimmet_stok").textContent =
      "0 (Yetersiz!)";
  }

  document.getElementById("ekstraEkleModal").classList.remove("hidden");
}

function ekstraEkleModalKapat() {
  document.getElementById("ekstraEkleModal").classList.add("hidden");
  modalData = {};
}

function ekstraSifirlaModalAc(urun, setupId) {
  modalData = {
    oda_id: mevcutOdaId,
    urun_id: urun.urun_id,
    setup_id: setupId,
    urun_adi: urun.urun_adi,
    ekstra_miktar: urun.ekstra_miktar,
  };

  document.getElementById("sifirla_modal_urun_adi").textContent = urun.urun_adi;
  document.getElementById("sifirla_modal_ekstra_miktar").textContent =
    urun.ekstra_miktar;

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
  toastGoster("QR okuyucu özelliği yakında eklenecek", "info");
  // window.location.href = "/qr-okuyucu?redirect=oda-kontrol";
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
