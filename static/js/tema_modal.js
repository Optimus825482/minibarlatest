/**
 * Tema Ayarları Modal Sistemi
 */

let secilenTemaRenk1 = "#2563EB";
let secilenTemaRenk2 = "#0284C7";

// Tema ayarları modalını aç
function temaAyarlariModalAc() {
  // Mevcut tema renklerini yükle
  fetch("/api/kullanici/tema-renkleri")
    .then((response) => response.json())
    .then((data) => {
      if (data.success) {
        secilenTemaRenk1 = data.tema_renk_1;
        secilenTemaRenk2 = data.tema_renk_2;
        // Önizlemeyi güncelle
        document.getElementById("tema-preview-badge").style.background =
          secilenTemaRenk1;
        document.getElementById("tema-preview-button").style.background =
          `linear-gradient(180deg, ${secilenTemaRenk2}, ${secilenTemaRenk2})`;
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

// Tema uygula (önizleme)
function temaUygula(renk1, renk2, temaAdi) {
  secilenTemaRenk1 = renk1;
  secilenTemaRenk2 = renk2;

  // Önizlemeyi güncelle
  document.getElementById("tema-preview-badge").style.background = renk1;
  document.getElementById("tema-preview-button").style.background =
    `linear-gradient(180deg, ${renk2}, ${renk2})`;

  // Bildirim göster
  showToast(`🎨 ${temaAdi} teması seçildi. Kaydet butonuna tıklayın.`, "info");
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
  toast.className = `fixed top-4 right-4 px-6 py-3 rounded-lg shadow-lg text-white z-50 ${
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
