/**
 * Güncelleme Modal - Sadece 1 Kez Gösterilir
 * LocalStorage ile kontrol edilir
 */

// Güncelleme versiyonu - Her yeni güncelleme için bu değeri değiştirin
const GUNCELLEME_VERSIYONU = "v2.5.0_2026_01_30";

document.addEventListener("DOMContentLoaded", function () {
  // LocalStorage'dan kontrol et
  const gosterildi = localStorage.getItem(
    `guncelleme_modal_${GUNCELLEME_VERSIYONU}`,
  );

  // Eğer daha önce gösterilmediyse modal'ı göster
  if (!gosterildi) {
    setTimeout(() => {
      guncellemeModalGoster();
    }, 1000); // 1 saniye gecikme ile göster (sayfa yüklendikten sonra)
  }
});

// Modal'ı göster
function guncellemeModalGoster() {
  const modal = document.getElementById("guncellemeModal");
  if (modal) {
    modal.classList.remove("hidden");
    modal.classList.add("flex");

    // Animasyon için
    setTimeout(() => {
      const content = modal.querySelector(".modal-content");
      if (content) {
        content.classList.add("animate-slideInUp");
      }
    }, 50);
  }
}

// Modal'ı kapat ve LocalStorage'a kaydet
function guncellemeModalKapat() {
  const modal = document.getElementById("guncellemeModal");
  if (modal) {
    const content = modal.querySelector(".modal-content");
    if (content) {
      content.classList.remove("animate-slideInUp");
      content.classList.add("animate-slideOutDown");
    }

    setTimeout(() => {
      modal.classList.add("hidden");
      modal.classList.remove("flex");
    }, 300);

    // LocalStorage'a kaydet (bir daha gösterme)
    localStorage.setItem(`guncelleme_modal_${GUNCELLEME_VERSIYONU}`, "true");
  }
}

// ESC tuşu ile kapatma
document.addEventListener("keydown", function (e) {
  if (e.key === "Escape") {
    const modal = document.getElementById("guncellemeModal");
    if (modal && !modal.classList.contains("hidden")) {
      guncellemeModalKapat();
    }
  }
});
