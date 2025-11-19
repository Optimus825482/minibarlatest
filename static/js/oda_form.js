/**
 * Oda Formu - Dinamik Kat ve Oda Tipi Yükleme
 * Otel seçildiğinde otele ait katları ve oda tiplerini AJAX ile yükler
 */

// Oda tiplerini yükleyen yardımcı fonksiyon
// NOT: Oda tipleri otellere özel değil, genel tanımlardır
function yukleOdaTipleri(odaTipiSelectId, callback) {
  const odaTipiSelect = document.getElementById(odaTipiSelectId);

  if (!odaTipiSelect) {
    console.error("Oda tipi select elementi bulunamadı:", odaTipiSelectId);
    return;
  }

  // Choices.js instance'ını yok et
  if (window.choicesInstances && window.choicesInstances[odaTipiSelectId]) {
    try {
      window.choicesInstances[odaTipiSelectId].destroy();
      delete window.choicesInstances[odaTipiSelectId];
    } catch (e) {
      console.warn("Choices.js destroy hatası:", e);
    }
  }

  // Oda tipi dropdown'unu temizle
  odaTipiSelect.innerHTML = '<option value="">Yükleniyor...</option>';
  odaTipiSelect.disabled = true;

  // AJAX ile tüm aktif oda tiplerini yükle
  fetch("/api/oda-tipleri")
    .then((response) => {
      if (!response.ok) {
        throw new Error("Oda tipleri yüklenemedi");
      }
      return response.json();
    })
    .then((data) => {
      // Dropdown'u doldur
      odaTipiSelect.innerHTML =
        '<option value="">Oda Tipi Seçin (Opsiyonel)</option>';

      if (data.success && data.oda_tipleri && data.oda_tipleri.length > 0) {
        data.oda_tipleri.forEach((tip) => {
          const option = document.createElement("option");
          option.value = tip.id;
          option.textContent = tip.ad;
          odaTipiSelect.appendChild(option);
        });
        odaTipiSelect.disabled = false;
      } else {
        odaTipiSelect.innerHTML =
          '<option value="">Oda tipi tanımlı değil</option>';
        odaTipiSelect.disabled = false;
      }

      // Choices.js'i yeniden başlat
      setTimeout(function () {
        if (typeof Choices !== "undefined" && !odaTipiSelect.disabled) {
          try {
            const choices = new Choices(odaTipiSelect, {
              searchEnabled: true,
              searchPlaceholderValue: "Ara...",
              noResultsText: "Sonuç bulunamadı",
              itemSelectText: "Seçmek için tıklayın",
              placeholder: true,
              placeholderValue: "Oda Tipi Seçin (Opsiyonel)",
              shouldSort: false,
              allowHTML: false,
            });
            if (window.choicesInstances) {
              window.choicesInstances[odaTipiSelectId] = choices;
            }
          } catch (e) {
            console.error("Choices.js başlatma hatası:", e);
          }
        }
      }, 150);

      // Callback varsa çalıştır
      if (callback) callback(data.oda_tipleri);
    })
    .catch((error) => {
      console.error("Oda tipleri yükleme hatası:", error);
      odaTipiSelect.innerHTML =
        '<option value="">Hata oluştu, tekrar deneyin</option>';
      odaTipiSelect.disabled = false;
    });
}

// Katları yükleyen yardımcı fonksiyon
function yukleKatlar(otelId, katSelectId, callback) {
  const katSelect = document.getElementById(katSelectId);

  if (!katSelect) {
    console.error("Kat select elementi bulunamadı:", katSelectId);
    return;
  }

  // Choices.js instance'ını yok et
  if (window.choicesInstances && window.choicesInstances[katSelectId]) {
    try {
      window.choicesInstances[katSelectId].destroy();
      delete window.choicesInstances[katSelectId];
    } catch (e) {
      console.warn("Choices.js destroy hatası:", e);
    }
  }

  // Kat dropdown'unu temizle
  katSelect.innerHTML = '<option value="">Yükleniyor...</option>';
  katSelect.disabled = true;

  if (!otelId || otelId === "0" || otelId === "") {
    katSelect.innerHTML = '<option value="">Önce otel seçin...</option>';
    return;
  }

  // AJAX ile katları yükle
  fetch(`/api/oteller/${otelId}/katlar`)
    .then((response) => {
      if (!response.ok) {
        throw new Error("Katlar yüklenemedi");
      }
      return response.json();
    })
    .then((katlar) => {
      // Dropdown'u doldur
      katSelect.innerHTML = '<option value="">Kat Seçin...</option>';

      if (katlar.length === 0) {
        katSelect.innerHTML =
          '<option value="">Bu otelde kat bulunamadı</option>';
        katSelect.disabled = false;
      } else {
        katlar.forEach((kat) => {
          const option = document.createElement("option");
          option.value = kat.id;
          option.textContent = `${kat.kat_adi} (${kat.kat_no})`;
          katSelect.appendChild(option);
        });
        katSelect.disabled = false;
      }

      // Choices.js'i yeniden başlat
      setTimeout(function () {
        if (typeof Choices !== "undefined" && !katSelect.disabled) {
          try {
            const choices = new Choices(katSelect, {
              searchEnabled: true,
              searchPlaceholderValue: "Ara...",
              noResultsText: "Sonuç bulunamadı",
              itemSelectText: "Seçmek için tıklayın",
              placeholder: true,
              placeholderValue: "Kat Seçin...",
              shouldSort: false,
              allowHTML: false,
            });
            if (window.choicesInstances) {
              window.choicesInstances[katSelectId] = choices;
            }
          } catch (e) {
            console.error("Choices.js başlatma hatası:", e);
          }
        }
      }, 150);

      // Callback varsa çalıştır
      if (callback) callback(katlar);
    })
    .catch((error) => {
      console.error("Katlar yükleme hatası:", error);
      katSelect.innerHTML =
        '<option value="">Hata oluştu, tekrar deneyin</option>';
      katSelect.disabled = false;
    });
}

document.addEventListener("DOMContentLoaded", function () {
  console.log("Oda Form JS yüklendi");

  // Form sayfası için (otel_id ve kat_id)
  const otelSelect = document.getElementById("otel_id");
  const katSelect = document.getElementById("kat_id");
  const odaTipiSelect = document.getElementById("oda_tipi");

  if (otelSelect && katSelect) {
    otelSelect.addEventListener("change", function () {
      console.log("Otel seçildi (form):", this.value);
      yukleKatlar(this.value, "kat_id");
    });
  }

  // Oda tipi dropdown'larını sayfa yüklendiğinde doldur (otelden bağımsız)
  if (odaTipiSelect) {
    yukleOdaTipleri("oda_tipi");
  }

  // Yeni Oda Modal için
  const yeniOtelSelect = document.getElementById("yeniOtelId");
  if (yeniOtelSelect) {
    yeniOtelSelect.addEventListener("change", function () {
      console.log("Otel seçildi (yeni oda):", this.value);
      yukleKatlar(this.value, "yeniKatId");
    });

    // Oda tipi dropdown'unu doldur
    const yeniOdaTipiSelect = document.getElementById("yeniOdaTipi");
    if (yeniOdaTipiSelect) {
      yukleOdaTipleri("yeniOdaTipi");
    }
  }

  // Oda Düzenle Modal için
  const duzenleOtelSelect = document.getElementById("duzenleOtelId");
  if (duzenleOtelSelect) {
    duzenleOtelSelect.addEventListener("change", function () {
      console.log("Otel seçildi (düzenle):", this.value);
      yukleKatlar(this.value, "duzenleKatId");
    });

    // Oda tipi dropdown'unu doldur
    const duzenleOdaTipiSelect = document.getElementById("duzenleOdaTipi");
    if (duzenleOdaTipiSelect) {
      yukleOdaTipleri("duzenleOdaTipi");
    }
  }
});
