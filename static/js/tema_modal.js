/**
 * Tema Ayarları Modal Sistemi
 * Badge ve Buton renklerini ayrı ayrı seçebilme
 * Sticky tab sistemi ile kolay renk seçimi
 */

let secilenTemaRenk1 = "#2563EB"; // Badge rengi
let secilenTemaRenk2 = "#0284C7"; // Buton rengi
let aktifRenkTipi = "badge"; // 'badge' veya 'button'

// Tema ayarları modalını aç
function temaAyarlariModalAc() {
  // Mevcut tema renklerini yükle
  fetch("/api/kullanici/tema-renkleri")
    .then((response) => response.json())
    .then((data) => {
      if (data.success) {
        secilenTemaRenk1 = data.tema_renk_1;
        secilenTemaRenk2 = data.tema_renk_2;

        // Aktif renk picker'ı güncelle
        renkSecimTipiDegistir("badge");
      }
    })
    .catch((error) => console.error("Tema renkleri yüklenemedi:", error));

  // Modal'ı göster
  document.getElementById("temaAyarlariModal").classList.remove("hidden");
  document.body.style.overflow = "hidden";
}

// Tema ayarları modalını kapat
function temaAyarlariModalKapat() {
  document.getElementById("temaAyarlariModal").classList.add("hidden");
  document.body.style.overflow = "";
}

// Renk seçim tipini değiştir (badge veya button)
function renkSecimTipiDegistir(tip) {
  aktifRenkTipi = tip;

  const badgeTab = document.getElementById("badge-tab");
  const buttonTab = document.getElementById("button-tab");
  const aktifPicker = document.getElementById("aktif-color-picker");
  const aktifHex = document.getElementById("aktif-hex-display");
  const baslik = document.getElementById("renk-secim-baslik");
  const renkSecimAlani = document.getElementById("renk-secim-alani");

  if (tip === "badge") {
    // Badge tab aktif
    badgeTab.className =
      "flex-1 px-4 py-2 rounded-lg font-medium text-sm transition-all border-2 border-blue-500 bg-blue-50 dark:bg-blue-900/30 text-blue-700 dark:text-blue-300";
    buttonTab.className =
      "flex-1 px-4 py-2 rounded-lg font-medium text-sm transition-all border-2 border-slate-200 dark:border-slate-700 text-slate-600 dark:text-slate-400 hover:border-slate-300 dark:hover:border-slate-600";

    // Renk seçim alanı mavi
    renkSecimAlani.className =
      "mb-4 p-4 bg-gradient-to-r from-blue-50 to-cyan-50 dark:from-blue-900/20 dark:to-cyan-900/20 rounded-lg border-2 border-blue-200 dark:border-blue-700";

    aktifPicker.value = secilenTemaRenk1;
    aktifHex.textContent = secilenTemaRenk1.toUpperCase();
    baslik.textContent = "Badge Rengi Seçin";
  } else {
    // Button tab aktif
    badgeTab.className =
      "flex-1 px-4 py-2 rounded-lg font-medium text-sm transition-all border-2 border-slate-200 dark:border-slate-700 text-slate-600 dark:text-slate-400 hover:border-slate-300 dark:hover:border-slate-600";
    buttonTab.className =
      "flex-1 px-4 py-2 rounded-lg font-medium text-sm transition-all border-2 border-cyan-500 bg-cyan-50 dark:bg-cyan-900/30 text-cyan-700 dark:text-cyan-300";

    // Renk seçim alanı turkuaz
    renkSecimAlani.className =
      "mb-4 p-4 bg-gradient-to-r from-cyan-50 to-teal-50 dark:from-cyan-900/20 dark:to-teal-900/20 rounded-lg border-2 border-cyan-200 dark:border-cyan-700";

    aktifPicker.value = secilenTemaRenk2;
    aktifHex.textContent = secilenTemaRenk2.toUpperCase();
    baslik.textContent = "Buton Rengi Seçin";
  }

  // Önizlemeyi güncelle
  onizlemeGuncelle();
}

// Aktif renk picker'dan renk seçildiğinde
function aktifRenkSecildi(renk) {
  if (aktifRenkTipi === "badge") {
    secilenTemaRenk1 = renk;
  } else {
    secilenTemaRenk2 = renk;
  }

  // Hex display'i güncelle
  document.getElementById("aktif-hex-display").textContent = renk.toUpperCase();

  // Önizlemeyi güncelle
  onizlemeGuncelle();
}

// Hazır tema uygula
function temaUygula(renk1, renk2, temaAdi) {
  secilenTemaRenk1 = renk1;
  secilenTemaRenk2 = renk2;

  // Aktif picker'ı güncelle (mevcut tab'a göre)
  const aktifPicker = document.getElementById("aktif-color-picker");
  const aktifHex = document.getElementById("aktif-hex-display");

  if (aktifPicker && aktifHex) {
    if (aktifRenkTipi === "badge") {
      aktifPicker.value = renk1;
      aktifHex.textContent = renk1.toUpperCase();
    } else {
      aktifPicker.value = renk2;
      aktifHex.textContent = renk2.toUpperCase();
    }
  }

  // Önizlemeyi güncelle
  onizlemeGuncelle();

  // Bildirim göster
  showToast(`🎨 ${temaAdi} teması seçildi`, "info");
}

// Önizlemeyi güncelle
function onizlemeGuncelle() {
  document.getElementById("tema-preview-badge").style.background =
    secilenTemaRenk1;
  document.getElementById("tema-preview-button").style.background =
    `linear-gradient(180deg, ${secilenTemaRenk2}, ${secilenTemaRenk2})`;
}

// Tema kaydet
async function temaKaydet() {
  try {
    const response = await fetch("/api/kullanici/tema-kaydet", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-CSRFToken": document.querySelector('meta[name="csrf-token"]')
          .content,
      },
      body: JSON.stringify({
        tema_renk_1: secilenTemaRenk1,
        tema_renk_2: secilenTemaRenk2,
      }),
    });

    const data = await response.json();

    if (data.success) {
      showToast(data.message, "success");
      // Modal'ı kapat
      temaAyarlariModalKapat();
      // 1 saniye sonra sayfayı yenile
      setTimeout(() => {
        window.location.reload();
      }, 1000);
    } else {
      showToast(data.message, "error");
    }
  } catch (error) {
    console.error("Tema kaydetme hatası:", error);
    showToast("❌ Tema kaydedilemedi!", "error");
  }
}

// Toast bildirimi
function showToast(message, type = "info") {
  const toast = document.createElement("div");
  toast.className = `fixed top-4 right-4 px-6 py-3 rounded-lg shadow-lg text-white z-[60] ${
    type === "success"
      ? "bg-green-500"
      : type === "error"
        ? "bg-red-500"
        : "bg-blue-500"
  }`;
  toast.textContent = message;
  document.body.appendChild(toast);

  setTimeout(() => {
    toast.remove();
  }, 3000);
}

// ESC tuşu ile modal'ı kapat
document.addEventListener("keydown", function (e) {
  if (e.key === "Escape") {
    const modal = document.getElementById("temaAyarlariModal");
    if (modal && !modal.classList.contains("hidden")) {
      temaAyarlariModalKapat();
    }
  }
});
