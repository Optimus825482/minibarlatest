/**
 * Dark Mode / Theme Switcher System
 * Tema değiştirme ve yönetim sistemi
 *
 * NOT: GEÇİCİ OLARAK SADECE DARK MODE AKTİF
 * Light mode geçici olarak devre dışı bırakıldı
 */

class ThemeManager {
  constructor() {
    // GEÇİCİ: Her zaman dark mode
    this.currentTheme = "dark";
    this.init();
  }

  init() {
    // GEÇİCİ: Dark mode zorunlu
    document.documentElement.classList.add("dark");
    localStorage.setItem("minibar-theme", "dark");

    // Tema toggle butonu devre dışı - artık bağlamıyoruz
    // this.bindNavbarToggle();

    // Sistem tema değişikliğini dinleme - devre dışı
    // this.watchSystemTheme();
  }

  /**
   * Navbar'daki tema toggle butonunu bağla
   */
  bindNavbarToggle() {
    const themeToggle = document.getElementById("theme-toggle");
    const darkIcon = document.getElementById("theme-toggle-dark-icon");
    const lightIcon = document.getElementById("theme-toggle-light-icon");

    if (!themeToggle) return;

    // İlk durumu ayarla
    this.updateNavbarIcons(darkIcon, lightIcon);

    // Click eventi ekle
    themeToggle.addEventListener("click", () => {
      this.toggleTheme();
      this.updateNavbarIcons(darkIcon, lightIcon);
    });

    // Referansları sakla
    this.themeToggle = themeToggle;
    this.darkIcon = darkIcon;
    this.lightIcon = lightIcon;
  }

  /**
   * Navbar icon'larını güncelle
   */
  updateNavbarIcons(darkIcon, lightIcon) {
    if (!darkIcon || !lightIcon) return;

    if (this.currentTheme === "dark") {
      // Dark modda: Light icon göster (tıklayınca light'a geçecek)
      darkIcon.classList.add("hidden");
      lightIcon.classList.remove("hidden");
    } else {
      // Light modda: Dark icon göster (tıklayınca dark'a geçecek)
      darkIcon.classList.remove("hidden");
      lightIcon.classList.add("hidden");
    }
  }

  /**
   * Kaydedilen temayı al
   */
  getStoredTheme() {
    return localStorage.getItem("minibar-theme");
  }

  /**
   * Temayı kaydet
   */
  storeTheme(theme) {
    localStorage.setItem("minibar-theme", theme);
  }

  /**
   * Sistem temasını kontrol et
   */
  getSystemTheme() {
    return window.matchMedia("(prefers-color-scheme: dark)").matches
      ? "dark"
      : "light";
  }

  /**
   * Temayı uygula
   */
  applyTheme(theme, saveToStorage = true) {
    this.currentTheme = theme;

    if (theme === "dark") {
      document.documentElement.classList.add("dark");
    } else {
      document.documentElement.classList.remove("dark");
    }

    // Sadece kullanıcı manuel değiştirdiğinde kaydet
    if (saveToStorage) {
      this.storeTheme(theme);
    }

    // Navbar icon'larını güncelle
    if (this.darkIcon && this.lightIcon) {
      this.updateNavbarIcons(this.darkIcon, this.lightIcon);
    }

    // Custom event dispatch et
    window.dispatchEvent(
      new CustomEvent("themeChanged", { detail: { theme } })
    );
  }

  /**
   * Tema değiştir - GEÇİCİ OLARAK DEVRE DIŞI
   */
  toggleTheme() {
    // GEÇİCİ: Dark mode zorunlu, tema değiştirme devre dışı
    // const newTheme = this.currentTheme === "light" ? "dark" : "light";
    // this.applyTheme(newTheme);

    // Toast bildirim
    if (window.Toast) {
      window.Toast.info(
        `Tema: ${newTheme === "dark" ? "🌙 Karanlık Mod" : "☀️ Aydınlık Mod"}`
      );
    }
  }

  /**
   * Sistem tema değişikliğini izle
   */
  watchSystemTheme() {
    window
      .matchMedia("(prefers-color-scheme: dark)")
      .addEventListener("change", (e) => {
        // Eğer kullanıcı manuel tema seçmediyse, sistem temasını uygula
        if (!this.getStoredTheme()) {
          this.applyTheme(e.matches ? "dark" : "light");
        }
      });
  }

  /**
   * Tema tercihini sıfırla (sistem temasını kullan)
   */
  resetToSystemTheme() {
    localStorage.removeItem("minibar-theme");
    this.applyTheme(this.getSystemTheme());

    if (window.Toast) {
      window.Toast.info("Sistem teması uygulandı");
    }
  }
}

// Global instance
window.ThemeManager = new ThemeManager();

// Kısayol fonksiyonlar
window.toggleTheme = () => window.ThemeManager.toggleTheme();
window.setTheme = (theme) => window.ThemeManager.applyTheme(theme);

// CSS için dark mode helper classes
// Tailwind dark: prefix kullanımı için documentElement'e dark class ekle/çıkar
