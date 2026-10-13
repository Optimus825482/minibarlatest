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
    this.userRole = document.body?.dataset?.userRole || "";
    this.gosterilenMybarDialoglari = new Set();
    this.mybarDialogKuyrugu = [];
    this.aktifMybarDialog = false;

    this.init();
  }

  init() {
    // İlk yükleme
    this.bildirimleriYukle();

    // Kat sorumlusu ise henüz onaylanmamış Mybar taleplerini kontrol et ve confirm dialog göster
    if (this.userRole === "kat_sorumlusu") {
      this.gorulmemisMybarTalepleriniKontrolEt();
    }

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
      if (this.userRole === "kat_sorumlusu") {
        await this.gorulmemisMybarTalepleriniKontrolEt();
      }
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
          let yeniMybarGeldi = false;
          data.yeni_bildirimler.forEach((bildirim) => {
            this.toastGoster(bildirim);
            // Listeye ekle
            this.bildirimler.unshift(bildirim);
            if (bildirim.bildirim_tipi === "mybar_talebi") {
              yeniMybarGeldi = true;
            }
          });
          this.panelGuncelle();

          if (yeniMybarGeldi && this.userRole === "kat_sorumlusu") {
            await this.gorulmemisMybarTalepleriniKontrolEt();
          }

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

    liste.innerHTML = DOMPurify.sanitize(this.bildirimler
      .slice(0, 20)
      .map((b) => this.bildirimHTML(b))
      .join(""));
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
      mybar_talebi: {
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

  escapeHtml(str) {
    if (str == null) return "";
    return String(str)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#39;");
  }

  async gorulmemisMybarTalepleriniKontrolEt() {
    try {
      const response = await fetch("/api/dolum-talepleri-gorulmemis");
      if (!response.ok) return;
      const data = await response.json();
      if (data.success && Array.isArray(data.talepler)) {
        let yeniEklendi = false;
        data.talepler.forEach((talep) => {
          if (!this.gosterilenMybarDialoglari.has(talep.id)) {
            this.gosterilenMybarDialoglari.add(talep.id);
            this.mybarDialogKuyrugu.push(talep);
            yeniEklendi = true;
          }
        });
        if (yeniEklendi) {
          this.bildirimSesiCal();
          this.siradakiMybarDialoguGoster();
        }
      }
    } catch (err) {
      console.error("Görülmemiş Mybar talebi kontrol hatası:", err);
    }
  }

  siradakiMybarDialoguGoster() {
    if (this.aktifMybarDialog || this.mybarDialogKuyrugu.length === 0) {
      return;
    }
    this.aktifMybarDialog = true;
    const talep = this.mybarDialogKuyrugu.shift();

    // Varsa eski modalı temizle
    const mevcut = document.getElementById("mybar-onay-dialog-backdrop");
    if (mevcut) mevcut.remove();

    const talepZamani = talep.talep_tarihi
      ? new Date(talep.talep_tarihi).toLocaleString("tr-TR")
      : "";

    const urunChips =
      Array.isArray(talep.secili_urunler) && talep.secili_urunler.length > 0
        ? `<div class="mt-3 p-3 rounded-xl bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-800">
             <p class="text-xs font-semibold text-amber-800 dark:text-amber-300 uppercase tracking-wide mb-2">
               <i class="fas fa-box-open mr-1"></i> Seçili Ürünler
             </p>
             <div class="flex flex-wrap gap-1.5">
               ${talep.secili_urunler
                 .map(
                   (u) =>
                     `<span class="inline-flex items-center px-2.5 py-1 rounded-full text-xs font-semibold bg-amber-200/80 dark:bg-amber-800 text-amber-900 dark:text-amber-100">${this.escapeHtml(u)}</span>`,
                 )
                 .join("")}
             </div>
           </div>`
        : "";

    const notBlok = talep.notlar
      ? `<div class="mt-3 p-3 rounded-xl bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800">
           <p class="text-xs font-semibold text-blue-800 dark:text-blue-300 uppercase tracking-wide mb-1">
             <i class="fas fa-language mr-1"></i> Misafir Notu (Türkçe)
           </p>
           <p class="text-sm text-blue-900 dark:text-blue-100 font-medium break-words">${this.escapeHtml(talep.notlar)}</p>
         </div>`
      : "";

    const backdrop = document.createElement("div");
    backdrop.id = "mybar-onay-dialog-backdrop";
    backdrop.className =
      "fixed inset-0 z-[9999] flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm";

    backdrop.innerHTML = `
      <div class="bg-white dark:bg-slate-800 rounded-2xl shadow-2xl border-2 border-amber-400 dark:border-amber-500 max-w-md w-full overflow-hidden notification-modal">
        <div class="bg-gradient-to-r from-amber-500 to-yellow-600 px-6 py-4 flex items-center gap-3 text-white">
          <div class="w-11 h-11 rounded-full bg-white/20 flex items-center justify-center flex-shrink-0">
            <i class="fas fa-concierge-bell text-xl"></i>
          </div>
          <div>
            <h3 class="text-lg font-bold leading-tight">Yeni Mybar Kişiselleştirme Talebi</h3>
            <p class="text-xs text-amber-100 mt-0.5">Lütfen talebi gördüğünüzü onaylayın</p>
          </div>
        </div>

        <div class="p-6">
          <div class="flex items-center justify-between bg-slate-100 dark:bg-slate-700/60 rounded-xl p-3.5 border border-slate-200 dark:border-slate-600">
            <div>
              <span class="text-xs text-slate-500 dark:text-slate-400 block">Oda Numarası</span>
              <span class="text-xl font-extrabold text-slate-900 dark:text-white">Oda ${this.escapeHtml(talep.oda_no)}</span>
            </div>
            <div class="text-right">
              <span class="text-xs text-slate-500 dark:text-slate-400 block">${this.escapeHtml(talep.kat_adi)}</span>
              <span class="text-xs font-medium text-slate-600 dark:text-slate-300">${this.escapeHtml(talepZamani)}</span>
            </div>
          </div>

          ${urunChips}
          ${notBlok}

          <div class="mt-5 flex flex-col sm:flex-row gap-2.5">
            <button
              type="button"
              id="mybar-onay-btn"
              class="flex-1 inline-flex items-center justify-center px-5 py-3 rounded-xl text-sm font-bold text-white bg-emerald-600 hover:bg-emerald-700 shadow-lg shadow-emerald-600/25 transition-all cursor-pointer"
            >
              <i class="fas fa-check-circle mr-2"></i> Talebi Gördüm (Onayla)
            </button>
            <button
              type="button"
              id="mybar-git-onayla-btn"
              class="inline-flex items-center justify-center px-4 py-3 rounded-xl text-sm font-semibold text-amber-800 dark:text-amber-200 bg-amber-100 dark:bg-amber-900/40 hover:bg-amber-200 dark:hover:bg-amber-900/60 transition-all cursor-pointer"
            >
              <i class="fas fa-external-link-alt mr-1.5"></i> Taleplere Git
            </button>
          </div>
        </div>
      </div>
    `;

    document.body.appendChild(backdrop);

    const onayBtn = document.getElementById("mybar-onay-btn");
    const gitBtn = document.getElementById("mybar-git-onayla-btn");

    if (onayBtn) {
      onayBtn.addEventListener("click", async () => {
        onayBtn.disabled = true;
        onayBtn.innerHTML = '<i class="fas fa-spinner fa-spin mr-2"></i> Onaylanıyor...';
        await this.mybarTalebiOnayla(talep.id, false);
      });
    }

    if (gitBtn) {
      gitBtn.addEventListener("click", async () => {
        gitBtn.disabled = true;
        await this.mybarTalebiOnayla(talep.id, true);
      });
    }
  }

  async mybarTalebiOnayla(talepId, sayfaYonlendir = false) {
    try {
      const csrfToken =
        document
          .querySelector('meta[name="csrf-token"]')
          ?.getAttribute("content") || "";

      await fetch(`/api/dolum-talebi-goruldu/${talepId}`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-CSRFToken": csrfToken,
        },
      });

      // Bildirim sayacını ve listesini tazele
      await this.bildirimleriYukle();

      // Eğer dolum talepleri sayfasındaysak listeyi yenile
      if (typeof talepleriYukle === "function") {
        talepleriYukle();
      }
    } catch (err) {
      console.error("Mybar talep onaylama hatası:", err);
    } finally {
      const mevcut = document.getElementById("mybar-onay-dialog-backdrop");
      if (mevcut) mevcut.remove();
      this.aktifMybarDialog = false;

      if (sayfaYonlendir && window.location.pathname !== "/dolum-talepleri") {
        window.location.href = "/dolum-talepleri";
      } else {
        this.siradakiMybarDialoguGoster();
      }
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
