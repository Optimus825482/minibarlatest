/**
 * Minibar İşlemlerim
 * Kat sorumlusunun yaptığı minibar işlemlerini görüntüleme, düzenleme ve silme
 */

let silinecekIslemId = null;

// Sayfa yüklendiğinde
document.addEventListener("DOMContentLoaded", function () {
  console.log("✅ Minibar İşlemleri sayfası yüklendi");

  // Bugünün tarihini set et
  const bugun = new Date().toISOString().split("T")[0];
  document.getElementById("filtre_tarih").value = bugun;

  // İşlemleri yükle
  islemleriYukle();
});

// CSRF token al
function getCsrfToken() {
  const token = document.querySelector('meta[name="csrf-token"]');
  return token ? token.getAttribute("content") : "";
}

// İşlemleri yükle
async function islemleriYukle() {
  const loading = document.getElementById("loading");
  const container = document.getElementById("islemler_container");
  const bosDurum = document.getElementById("bos_durum");

  try {
    loading.classList.remove("hidden");
    container.classList.add("hidden");
    bosDurum.classList.add("hidden");

    const tarih = document.getElementById("filtre_tarih").value;
    const oda = document.getElementById("filtre_oda").value;
    const islemTipi = document.getElementById("filtre_islem_tipi").value;

    const params = new URLSearchParams();
    if (tarih) params.append("tarih", tarih);
    if (oda) params.append("oda", oda);
    if (islemTipi) params.append("islem_tipi", islemTipi);

    const response = await fetch(
      `/api/kat-sorumlusu/minibar-islemlerim?${params}`
    );
    const data = await response.json();

    if (!response.ok || !data.success) {
      throw new Error(data.error || "İşlemler yüklenemedi");
    }

    if (data.islemler.length === 0) {
      bosDurum.classList.remove("hidden");
    } else {
      renderIslemler(data.islemler);
      container.classList.remove("hidden");
    }

    document.getElementById("toplam_islem").textContent = data.islemler.length;
  } catch (error) {
    console.error("❌ İşlem yükleme hatası:", error);
    toastGoster(error.message, "error");
  } finally {
    loading.classList.add("hidden");
  }
}

// İşlemleri render et
function renderIslemler(islemler) {
  const tbody = document.getElementById("islemler_tbody");
  tbody.innerHTML = "";

  islemler.forEach((islem) => {
    const tr = document.createElement("tr");
    tr.className = "hover:bg-slate-50 transition-colors";

    const islemTipiText =
      {
        setup_kontrol: "Tüketim İkamesi",
        ekstra_ekleme: "Ekstra Ekleme",
        ekstra_tuketim: "Ekstra Tüketim",
      }[islem.islem_tipi] || islem.islem_tipi;

    const islemTipiClass =
      {
        setup_kontrol: "bg-blue-100 text-blue-800",
        ekstra_ekleme: "bg-orange-100 text-orange-800",
        ekstra_tuketim: "bg-red-100 text-red-800",
      }[islem.islem_tipi] || "bg-slate-100 text-slate-800";

    tr.innerHTML = `
      <td class="px-4 py-3 text-sm text-slate-900">
        ${formatTarih(islem.islem_tarihi)}
      </td>
      <td class="px-4 py-3 text-sm font-medium text-slate-900">
        ${islem.oda_no}
      </td>
      <td class="px-4 py-3">
        <span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${islemTipiClass}">
          ${islemTipiText}
        </span>
      </td>
      <td class="px-4 py-3 text-sm text-slate-600">
        ${islem.urun_sayisi} ürün
      </td>
      <td class="px-4 py-3 text-center space-x-2">
        <button
          onclick='detayGoster(${JSON.stringify(islem).replace(/'/g, "&#39;")})'
          class="inline-flex items-center px-3 py-1.5 bg-slate-600 text-white text-xs font-medium rounded-lg hover:bg-slate-700 transition-colors"
        >
          Detay
        </button>
        ${
          islem.ayni_gun
            ? `
          <button
            onclick='islemSilModalAc(${islem.id})'
            class="inline-flex items-center px-3 py-1.5 bg-red-600 text-white text-xs font-medium rounded-lg hover:bg-red-700 transition-colors"
          >
            Sil
          </button>
        `
            : `
          <span class="text-xs text-slate-400">Silinemez</span>
        `
        }
      </td>
    `;

    tbody.appendChild(tr);
  });
}

// Tarih formatla
function formatTarih(tarihStr) {
  const tarih = new Date(tarihStr);
  const gun = tarih.getDate().toString().padStart(2, "0");
  const ay = (tarih.getMonth() + 1).toString().padStart(2, "0");
  const yil = tarih.getFullYear();
  const saat = tarih.getHours().toString().padStart(2, "0");
  const dakika = tarih.getMinutes().toString().padStart(2, "0");

  return `${gun}.${ay}.${yil} ${saat}:${dakika}`;
}

// Detay göster
function detayGoster(islem) {
  const detayIcerik = document.getElementById("detay_icerik");

  let html = `
    <div class="space-y-4">
      <div class="grid grid-cols-2 gap-4">
        <div>
          <label class="block text-sm font-medium text-slate-700">Oda</label>
          <p class="mt-1 text-base text-slate-900">${islem.oda_no}</p>
        </div>
        <div>
          <label class="block text-sm font-medium text-slate-700">Tarih/Saat</label>
          <p class="mt-1 text-base text-slate-900">${formatTarih(
            islem.islem_tarihi
          )}</p>
        </div>
      </div>

      <div>
        <label class="block text-sm font-medium text-slate-700 mb-2">Ürünler</label>
        <div class="overflow-x-auto">
          <table class="min-w-full divide-y divide-slate-200">
            <thead class="bg-slate-50">
              <tr>
                <th class="px-3 py-2 text-left text-xs font-medium text-slate-500">Ürün</th>
                <th class="px-3 py-2 text-center text-xs font-medium text-slate-500">Setup Miktar</th>
                <th class="px-3 py-2 text-center text-xs font-medium text-slate-500">Eklenen</th>
                <th class="px-3 py-2 text-center text-xs font-medium text-slate-500">Tüketim</th>
                <th class="px-3 py-2 text-center text-xs font-medium text-slate-500">Bitiş</th>
              </tr>
            </thead>
            <tbody class="bg-white divide-y divide-slate-200">
  `;

  // Setup Miktar: Minibar her zaman dolu kabul edilir (setup'taki miktar)
  // Eklenen: Setup'tan eksik olanları tamamlama (ikame işlemi)
  // Tüketim: Setup miktarından tüketilen
  // Bitiş: Setup miktar + ekstra eklenenler
  islem.detaylar.forEach((detay) => {
    html += `
      <tr>
        <td class="px-3 py-2 text-sm text-slate-900">${detay.urun_adi}</td>
        <td class="px-3 py-2 text-sm text-center text-slate-600">${
          detay.setup_miktari || 0
        }</td>
        <td class="px-3 py-2 text-sm text-center text-green-600 font-semibold">${
          detay.eklenen_miktar
        }</td>
        <td class="px-3 py-2 text-sm text-center text-red-600 font-semibold">${
          detay.tuketim
        }</td>
        <td class="px-3 py-2 text-sm text-center text-slate-900 font-semibold">${
          detay.bitis_stok
        }</td>
      </tr>
    `;
  });

  html += `
            </tbody>
          </table>
        </div>
      </div>

      ${
        islem.aciklama
          ? `
        <div>
          <label class="block text-sm font-medium text-slate-700">Açıklama</label>
          <p class="mt-1 text-sm text-slate-600">${islem.aciklama}</p>
        </div>
      `
          : ""
      }
    </div>
  `;

  detayIcerik.innerHTML = html;
  document.getElementById("detayModal").classList.remove("hidden");
}

// Detay modal kapat
function detayModalKapat() {
  document.getElementById("detayModal").classList.add("hidden");
}

// Silme modal aç
function islemSilModalAc(islemId) {
  silinecekIslemId = islemId;
  document.getElementById("silModal").classList.remove("hidden");
}

// Silme modal kapat
function silModalKapat() {
  silinecekIslemId = null;
  document.getElementById("silModal").classList.add("hidden");
}

// İşlem sil
async function islemSil() {
  if (!silinecekIslemId) return;

  try {
    const response = await fetch(
      `/api/kat-sorumlusu/minibar-islem-sil/${silinecekIslemId}`,
      {
        method: "DELETE",
        headers: {
          "Content-Type": "application/json",
          "X-CSRFToken": getCsrfToken(),
        },
      }
    );

    const data = await response.json();

    if (!response.ok || !data.success) {
      throw new Error(data.error || "İşlem silinemedi");
    }

    toastGoster(data.message, "success");
    silModalKapat();
    islemleriYukle();
  } catch (error) {
    console.error("❌ İşlem silme hatası:", error);
    toastGoster(error.message, "error");
  }
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
