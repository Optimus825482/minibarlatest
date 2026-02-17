/**
 * Bildirim Manager - Real-time bildirim yönetimi
 *
 * Özellikler:
 * - Polling ile yeni bildirimleri kontrol et
 * - Toast bildirimleri göster
 * - Bildirim sayacını güncelle
 * - Bildirim dropdown/panel yönetimi
 */

class BildirimManager {
  constructor(options = {}) {
    this.pollInterval = options.pollInterval || 10000; // 10 saniye
    this.maxToasts = options.maxToasts || 3;
    this.toastDuration = options.toastDuration || 5000;

    this.sonKontrol = null;
    this.pollTimer = null;
    this.bildirimler = [];
    this.okunmamisSayisi = 0;

    this.init();
  }

  init() {
    // İlk yükleme
    this.bildirimleriYukle();

    // Polling başlat
    this.pollBaslat();

    // Event listener'ları ekle
    this.eventListenerEkle();

    console.log("🔔 Bildirim Manager başlatıldı");
  }

  eventListenerEkle() {
    // Bildirim ikonu tıklama
    const bildirimBtn = document.getElementById("bildirim-btn");
    if (bildirimBtn) {
      bildirimBtn.addEventListener("click", () => this.panelToggle());
    }

    // Tümünü okundu işaretle butonu
    const tumunuOkuBtn = document.getElementById("tumunu-oku-btn");
    if (tumunuOkuBtn) {
      tumunuOkuBtn.addEventListener("click", () => this.tumunuOkunduIsaretle());
    }

    // Panel dışına tıklama
    document.addEventListener("click", (e) => {
      const panel = document.getElementById("bildirim-panel");
      const btn = document.getElementById("bildirim-btn");
      if (panel && !panel.contains(e.target) && !btn?.contains(e.target)) {
        panel.classList.add("hidden");
      }
    });
  }

  async bildirimleriYukle() {
    try {
      const response = await fetch("/api/bildirimler?limit=20");
      const data = await response.json();

      if (data.success) {
        this.bildirimler = data.bildirimler;
        this.okunmamisSayisi = data.okunmamis_sayisi;
        this.sayacGuncelle();
        this.panelGuncelle();
      }
    } catch (error) {
      console.error("Bildirim yükleme hatası:", error);
    }
  }

  pollBaslat() {
    this.sonKontrol = new Date().toISOString();

    this.pollTimer = setInterval(async () => {
      await this.yeniBildirimleriKontrolEt();
    }, this.pollInterval);
  }

  pollDurdur() {
    if (this.pollTimer) {
      clearInterval(this.pollTimer);
      this.pollTimer = null;
    }
  }

  async yeniBildirimleriKontrolEt() {
    try {
      const url = `/api/bildirimler/poll?son_kontrol=${encodeURIComponent(
        this.sonKontrol,
      )}`;
      const response = await fetch(url);
      const data = await response.json();

      if (data.success) {
        this.sonKontrol = data.kontrol_zamani;
        this.okunmamisSayisi = data.okunmamis_sayisi;
        this.sayacGuncelle();

        // Yeni bildirimler varsa toast göster
        if (data.yeni_bildirimler && data.yeni_bildirimler.length > 0) {
          data.yeni_bildirimler.forEach((bildirim) => {
            this.toastGoster(bildirim);
            // Listeye ekle
            this.bildirimler.unshift(bildirim);
          });
          this.panelGuncelle();

          // Görev özeti güncelle (depo sorumlusu için)
          if (typeof gorevOzetiGuncelle === "function") {
            gorevOzetiGuncelle();
          }
        }
      }
    } catch (error) {
      console.error("Bildirim poll hatası:", error);
    }
  }

  sayacGuncelle() {
    const badge = document.getElementById("bildirim-sayac");
    if (badge) {
      if (this.okunmamisSayisi > 0) {
        badge.textContent =
          this.okunmamisSayisi > 99 ? "99+" : this.okunmamisSayisi;
        badge.classList.remove("hidden");
      } else {
        badge.classList.add("hidden");
      }
    }
  }

  panelToggle() {
    const panel = document.getElementById("bildirim-panel");
    if (panel) {
      panel.classList.toggle("hidden");
    }
  }

  panelGuncelle() {
    const liste = document.getElementById("bildirim-liste");
    if (!liste) return;

    if (this.bildirimler.length === 0) {
      liste.innerHTML = `
        <div class="p-4 text-center text-slate-500 dark:text-slate-400">
          <i class="fas fa-bell-slash text-2xl mb-2"></i>
          <p class="text-sm">Bildirim bulunmuyor</p>
        </div>
      `;
      return;
    }

    liste.innerHTML = this.bildirimler
      .slice(0, 20)
      .map((b) => this.bildirimHTML(b))
      .join("");
  }

  bildirimHTML(bildirim) {
    const icon = this.bildirimIcon(bildirim.bildirim_tipi);
    const zaman = this.zamanFormat(bildirim.olusturma_tarihi);
    const okunduClass = bildirim.okundu
      ? "opacity-60"
      : "bg-indigo-50 dark:bg-indigo-900/20";

    return `
      <div class="p-3 border-b border-slate-200 dark:border-slate-700 ${okunduClass} hover:bg-slate-50 dark:hover:bg-slate-700/50 cursor-pointer transition-colors"
           onclick="bildirimManager.bildirimTiklandi(${bildirim.id})">
        <div class="flex items-start gap-3">
          <div class="flex-shrink-0 w-8 h-8 rounded-full ${
            icon.bg
          } flex items-center justify-center">
            <i class="${icon.icon} ${icon.color}"></i>
          </div>
          <div class="flex-1 min-w-0">
            <p class="text-sm font-medium text-slate-900 dark:text-white truncate">${
              bildirim.baslik
            }</p>
            ${
              bildirim.mesaj
                ? `<p class="text-xs text-slate-500 dark:text-slate-400 mt-0.5 truncate">${bildirim.mesaj}</p>`
                : ""
            }
            <p class="text-xs text-slate-400 dark:text-slate-500 mt-1">${zaman}</p>
          </div>
          ${
            !bildirim.okundu
              ? '<div class="w-2 h-2 rounded-full bg-indigo-500 flex-shrink-0"></div>'
              : ""
          }
        </div>
      </div>
    `;
  }

  bildirimIcon(tip) {
    const icons = {
      gorev_olusturuldu: {
        icon: "fas fa-tasks",
        color: "text-indigo-600",
        bg: "bg-indigo-100 dark:bg-indigo-900/30",
      },
      gorev_tamamlandi: {
        icon: "fas fa-check-circle",
        color: "text-green-600",
        bg: "bg-green-100 dark:bg-green-900/30",
      },
      dnd_kaydi: {
        icon: "fas fa-door-closed",
        color: "text-orange-600",
        bg: "bg-orange-100 dark:bg-orange-900/30",
      },
      sarfiyat_yok: {
        icon: "fas fa-check",
        color: "text-blue-600",
        bg: "bg-blue-100 dark:bg-blue-900/30",
      },
      doluluk_yuklendi: {
        icon: "fas fa-chart-bar",
        color: "text-purple-600",
        bg: "bg-purple-100 dark:bg-purple-900/30",
      },
      royalbar_talebi: {
        icon: "fas fa-concierge-bell",
        color: "text-amber-600",
        bg: "bg-amber-100 dark:bg-amber-900/30",
      },
    };
    return (
      icons[tip] || {
        icon: "fas fa-bell",
        color: "text-slate-600",
        bg: "bg-slate-100 dark:bg-slate-700",
      }
    );
  }

  zamanFormat(isoString) {
    if (!isoString) return "";

    const tarih = new Date(isoString);
    const simdi = new Date();
    const fark = Math.floor((simdi - tarih) / 1000);

    if (fark < 60) return "Az önce";
    if (fark < 3600) return `${Math.floor(fark / 60)} dk önce`;
    if (fark < 86400) return `${Math.floor(fark / 3600)} saat önce`;

    return tarih.toLocaleDateString("tr-TR", {
      day: "numeric",
      month: "short",
      hour: "2-digit",
      minute: "2-digit",
    });
  }

  async bildirimTiklandi(id) {
    // Okundu işaretle
    try {
      // CSRF token al
      const csrfToken =
        document
          .querySelector('meta[name="csrf-token"]')
          ?.getAttribute("content") || "";

      await fetch(`/api/bildirimler/${id}/okundu`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-CSRFToken": csrfToken,
        },
      });

      // Local state güncelle
      const bildirim = this.bildirimler.find((b) => b.id === id);
      if (bildirim && !bildirim.okundu) {
        bildirim.okundu = true;
        this.okunmamisSayisi = Math.max(0, this.okunmamisSayisi - 1);
        this.sayacGuncelle();
        this.panelGuncelle();
      }
    } catch (error) {
      console.error("Okundu işaretleme hatası:", error);
    }
  }

  async tumunuOkunduIsaretle() {
    try {
      // CSRF token al
      const csrfToken =
        document
          .querySelector('meta[name="csrf-token"]')
          ?.getAttribute("content") || "";

      await fetch("/api/bildirimler/tumunu-oku", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-CSRFToken": csrfToken,
        },
      });

      // Local state güncelle
      this.bildirimler.forEach((b) => (b.okundu = true));
      this.okunmamisSayisi = 0;
      this.sayacGuncelle();
      this.panelGuncelle();
    } catch (error) {
      console.error("Tümünü okundu işaretleme hatası:", error);
    }
  }

  toastGoster(bildirim) {
    const container =
      document.getElementById("toast-container") ||
      this.toastContainerOlustur();

    const icon = this.bildirimIcon(bildirim.bildirim_tipi);

    const toast = document.createElement("div");
    toast.className = `
      flex items-start gap-3 p-4 mb-3 bg-white dark:bg-slate-800 rounded-lg shadow-lg border border-slate-200 dark:border-slate-700
      transform translate-x-full transition-transform duration-300 ease-out max-w-sm
    `;

    toast.innerHTML = `
      <div class="flex-shrink-0 w-10 h-10 rounded-full ${
        icon.bg
      } flex items-center justify-center">
        <i class="${icon.icon} ${icon.color}"></i>
      </div>
      <div class="flex-1 min-w-0">
        <p class="text-sm font-semibold text-slate-900 dark:text-white">${
          bildirim.baslik
        }</p>
        ${
          bildirim.mesaj
            ? `<p class="text-xs text-slate-500 dark:text-slate-400 mt-1">${bildirim.mesaj}</p>`
            : ""
        }
      </div>
      <button onclick="this.parentElement.remove()" class="text-slate-400 hover:text-slate-600 dark:hover:text-slate-300">
        <i class="fas fa-times"></i>
      </button>
    `;

    container.appendChild(toast);

    // Animasyon
    requestAnimationFrame(() => {
      toast.classList.remove("translate-x-full");
    });

    // Otomatik kaldır
    setTimeout(() => {
      toast.classList.add("translate-x-full");
      setTimeout(() => toast.remove(), 300);
    }, this.toastDuration);

    // Ses çal (opsiyonel)
    this.bildirimSesiCal();
  }

  toastContainerOlustur() {
    const container = document.createElement("div");
    container.id = "toast-container";
    container.className = "fixed top-4 right-4 z-50";
    document.body.appendChild(container);
    return container;
  }

  bildirimSesiCal() {
    // Basit bir beep sesi (opsiyonel)
    try {
      const audioContext = new (
        window.AudioContext || window.webkitAudioContext
      )();
      const oscillator = audioContext.createOscillator();
      const gainNode = audioContext.createGain();

      oscillator.connect(gainNode);
      gainNode.connect(audioContext.destination);

      oscillator.frequency.value = 800;
      oscillator.type = "sine";
      gainNode.gain.value = 0.1;

      oscillator.start();
      setTimeout(() => oscillator.stop(), 100);
    } catch (e) {
      // Ses çalınamazsa sessizce devam et
    }
  }
}

// Global instance
let bildirimManager = null;

// Sayfa yüklendiğinde başlat
document.addEventListener("DOMContentLoaded", function () {
  // Sadece giriş yapmış kullanıcılar için
  if (document.getElementById("bildirim-btn")) {
    bildirimManager = new BildirimManager();
  }
});
