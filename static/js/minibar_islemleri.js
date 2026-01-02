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

    // DND kaydı için özel görünüm
    if (islem.kayit_tipi === "dnd" || islem.islem_tipi === "dnd") {
      const dndDurum =
        islem.dnd_durum === "tamamlandi"
          ? "Tamamlandı"
          : islem.dnd_durum === "iptal"
          ? "İptal"
          : "Aktif";
      const dndClass =
        islem.dnd_durum === "tamamlandi"
          ? "bg-green-100 text-green-800"
          : islem.dnd_durum === "iptal"
          ? "bg-red-100 text-red-800"
          : "bg-yellow-100 text-yellow-800";

      tr.innerHTML = `
        <td class="px-4 py-3 text-sm text-slate-900">
          ${formatTarih(islem.islem_tarihi)}
        </td>
        <td class="px-4 py-3 text-sm font-medium text-slate-900">
          ${islem.oda_no}
        </td>
        <td class="px-4 py-3">
          <span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-purple-100 text-purple-800">
            🚫 DND (${islem.dnd_sayisi || 0}/3)
          </span>
        </td>
        <td class="px-4 py-3">
          <span class="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium ${dndClass}">
            ${dndDurum}
          </span>
        </td>
        <td class="px-4 py-3 text-center">
          <button
            onclick='detayGoster(${JSON.stringify(islem).replace(
              /'/g,
              "&#39;"
            )})'
            class="inline-flex items-center px-3 py-1.5 bg-slate-600 text-white text-xs font-medium rounded-lg hover:bg-slate-700 transition-colors"
          >
            Detay
          </button>
        </td>
      `;
      tbody.appendChild(tr);
      return;
    }

    const islemTipiText =
      {
        setup_kontrol: "Tüketim İkamesi",
        ekstra_ekleme: "Ekstra Ekleme",
        ekstra_tuketim: "Ekstra Tüketim",
        sarfiyat_yok: "Sarfiyat Yok",
      }[islem.islem_tipi] || islem.islem_tipi;

    const islemTipiClass =
      {
        setup_kontrol: "bg-blue-100 text-blue-800",
        ekstra_ekleme: "bg-orange-100 text-orange-800",
        ekstra_tuketim: "bg-red-100 text-red-800",
        sarfiyat_yok: "bg-emerald-100 text-emerald-800",
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

  // DND kaydı için özel görünüm
  if (islem.kayit_tipi === "dnd" || islem.islem_tipi === "dnd") {
    const dndDurum =
      islem.dnd_durum === "tamamlandi"
        ? "Tamamlandı"
        : islem.dnd_durum === "iptal"
        ? "İptal"
        : "Aktif";
    const dndClass =
      islem.dnd_durum === "tamamlandi"
        ? "bg-green-50 border-green-200"
        : islem.dnd_durum === "iptal"
        ? "bg-red-50 border-red-200"
        : "bg-yellow-50 border-yellow-200";
    const dndIconClass =
      islem.dnd_durum === "tamamlandi"
        ? "text-green-600"
        : islem.dnd_durum === "iptal"
        ? "text-red-600"
        : "text-yellow-600";

    let html = `
      <div class="space-y-4">
        <div class="grid grid-cols-2 gap-4">
          <div>
            <label class="block text-sm font-medium text-slate-700">Oda</label>
            <p class="mt-1 text-base text-slate-900">${islem.oda_no}</p>
          </div>
          <div>
            <label class="block text-sm font-medium text-slate-700">Tarih</label>
            <p class="mt-1 text-base text-slate-900">${formatTarih(
              islem.islem_tarihi
            )}</p>
          </div>
        </div>

        <div class="${dndClass} border rounded-lg p-4">
          <div class="flex items-center">
            <svg class="w-8 h-8 ${dndIconClass} mr-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M18.364 18.364A9 9 0 005.636 5.636m12.728 12.728A9 9 0 015.636 5.636m12.728 12.728L5.636 5.636"></path>
            </svg>
            <div>
              <p class="text-lg font-semibold text-slate-800">DND - Rahatsız Etmeyin</p>
              <p class="text-sm text-slate-600">${
                islem.dnd_sayisi || 0
              }/3 kontrol yapıldı - ${dndDurum}</p>
            </div>
          </div>
        </div>
    `;

    // Kontrol detayları
    if (islem.kontroller && islem.kontroller.length > 0) {
      html += `
        <div>
          <label class="block text-sm font-medium text-slate-700 mb-2">Kontrol Geçmişi</label>
          <div class="space-y-2">
      `;

      islem.kontroller.forEach((k) => {
        html += `
          <div class="flex items-center justify-between bg-slate-50 rounded-lg p-3">
            <div class="flex items-center">
              <span class="inline-flex items-center justify-center w-8 h-8 rounded-full bg-purple-100 text-purple-800 text-sm font-medium mr-3">
                ${k.kontrol_no}
              </span>
              <span class="text-sm text-slate-700">${
                k.kontrol_no
              }. Kontrol</span>
            </div>
            <span class="text-sm text-slate-500">${
              k.kontrol_zamani ? formatTarih(k.kontrol_zamani) : "-"
            }</span>
          </div>
        `;
      });

      html += `
          </div>
        </div>
      `;
    }

    html += `</div>`;
    detayIcerik.innerHTML = html;
    document.getElementById("detayModal").classList.remove("hidden");
    return;
  }

  // Sarfiyat Yok işlemi için özel görünüm
  if (islem.islem_tipi === "sarfiyat_yok") {
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

        <div class="bg-emerald-50 border border-emerald-200 rounded-lg p-4">
          <div class="flex items-center">
            <svg class="w-6 h-6 text-emerald-600 mr-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"></path>
            </svg>
            <div>
              <p class="text-sm font-medium text-emerald-800">Sarfiyat Yok</p>
              <p class="text-sm text-emerald-600">Oda kontrol edildi, tüketim tespit edilmedi.</p>
            </div>
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
    return;
  }

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
        <div class="overflow-x-auto rounded-lg border border-slate-200">
          <table class="min-w-full divide-y divide-slate-200">
            <thead class="bg-slate-50">
              <tr>
                <th class="px-4 py-3 text-left text-xs font-medium text-slate-500 uppercase tracking-wider">Ürün</th>
                <th class="px-4 py-3 text-center text-xs font-medium text-slate-500 uppercase tracking-wider">Setup</th>
                <th class="px-4 py-3 text-center text-xs font-medium text-slate-500 uppercase tracking-wider">Eklenen</th>
                <th class="px-4 py-3 text-center text-xs font-medium text-slate-500 uppercase tracking-wider">Tüketim</th>
                <th class="px-4 py-3 text-center text-xs font-medium text-slate-500 uppercase tracking-wider">Bitiş</th>
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
      <tr class="hover:bg-slate-50 transition-colors">
        <td class="px-4 py-3 text-sm font-medium text-slate-900">${
          detay.urun_adi
        }</td>
        <td class="px-4 py-3 text-sm text-center">
          <span class="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-slate-100 text-slate-700">
            ${detay.setup_miktari || 0}
          </span>
        </td>
        <td class="px-4 py-3 text-sm text-center">
          <span class="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-green-100 text-green-700">
            +${detay.eklenen_miktar}
          </span>
        </td>
        <td class="px-4 py-3 text-sm text-center">
          <span class="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-red-100 text-red-700">
            -${detay.tuketim}
          </span>
        </td>
        <td class="px-4 py-3 text-sm text-center">
          <span class="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-blue-100 text-blue-700">
            ${detay.bitis_stok}
          </span>
        </td>
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
