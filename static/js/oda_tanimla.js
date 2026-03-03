/**
 * Oda Tanımlama Sayfası JavaScript
 * Yeni oda ekleme, düzenleme ve QR kod işlemleri
 */

// Global değişkenler (window objesine ekle - çakışmayı önle)
window.yeniEklenenOdaId = window.yeniEklenenOdaId || null;

/**
 * Yeni oda modal'ını aç
 */
function yeniOdaModal() {
  console.log("Yeni oda modal açılıyor...");

  // Formu temizle
  document.getElementById("yeniOdaForm").reset();
  document.getElementById("yeniOdaAlert").style.display = "none";
  document.getElementById("yeniOdaQrBolumu").style.display = "none";
  document.getElementById("yeniOdaKaydetBtn").style.display = "inline-flex";
  document.getElementById("yeniOdaTamamBtn").style.display = "none";

  // Kat ve oda tipi dropdown'larını sıfırla
  const katSelect = document.getElementById("yeniKatId");
  const odaTipiSelect = document.getElementById("yeniOdaTipi");

  if (katSelect) {
    katSelect.innerHTML = '<option value="">Önce otel seçin...</option>';
    katSelect.disabled = true;
  }

  if (odaTipiSelect) {
    odaTipiSelect.innerHTML = '<option value="">Önce otel seçin...</option>';
    odaTipiSelect.disabled = true;
  }

  // Modal'ı aç
  $("#yeniOdaModal").modal("show");
}

/**
 * Anlık oda numarası kontrol (input sırasında)
 */
let odaNoKontrolTimeout = null;

function odaNoAnlikKontrol(odaNoInput) {
  const odaNo = odaNoInput.value.trim();
  const feedbackDiv = document.getElementById("yeniOdaNoFeedback");
  const kaydetBtn = document.getElementById("yeniOdaKaydetBtn");

  // Feedback div yoksa oluştur
  if (!feedbackDiv) {
    const newFeedback = document.createElement("div");
    newFeedback.id = "yeniOdaNoFeedback";
    newFeedback.className = "mt-1 text-sm";
    odaNoInput.parentNode.appendChild(newFeedback);
  }

  const feedback = document.getElementById("yeniOdaNoFeedback");

  // Boşsa temizle ve butonu devre dışı bırak
  if (!odaNo) {
    feedback.innerHTML = "";
    odaNoInput.classList.remove("is-valid", "is-invalid");
    if (kaydetBtn) {
      kaydetBtn.disabled = true;
    }
    return;
  }

  // Loading göster ve butonu devre dışı bırak
  feedback.innerHTML =
    '<span class="text-muted"><i class="fas fa-spinner fa-spin"></i> Kontrol ediliyor...</span>';
  odaNoInput.classList.remove("is-valid", "is-invalid");
  if (kaydetBtn) {
    kaydetBtn.disabled = true;
  }

  // Debounce - 500ms bekle
  clearTimeout(odaNoKontrolTimeout);
  odaNoKontrolTimeout = setTimeout(() => {
    fetch(`/api/oda-no-kontrol?oda_no=${encodeURIComponent(odaNo)}`)
      .then((response) => response.json())
      .then((data) => {
        if (data.success) {
          if (data.mevcut) {
            // Oda numarası kullanılıyor - BUTONU DEVRE DIŞI BIRAK
            feedback.innerHTML =
              '<span class="text-danger"><i class="fas fa-times-circle"></i> Bu oda numarası zaten kullanılıyor!</span>';
            odaNoInput.classList.remove("is-valid");
            odaNoInput.classList.add("is-invalid");
            if (kaydetBtn) {
              kaydetBtn.disabled = true;
            }
          } else {
            // Oda numarası müsait - BUTONU AKTİF ET
            feedback.innerHTML =
              '<span class="text-success"><i class="fas fa-check-circle"></i> Oda numarası müsait</span>';
            odaNoInput.classList.remove("is-invalid");
            odaNoInput.classList.add("is-valid");
            if (kaydetBtn) {
              kaydetBtn.disabled = false;
            }
          }
        } else {
          feedback.innerHTML = "";
          odaNoInput.classList.remove("is-valid", "is-invalid");
          if (kaydetBtn) {
            kaydetBtn.disabled = true;
          }
        }
      })
      .catch((error) => {
        console.error("Kontrol hatası:", error);
        feedback.innerHTML = "";
        odaNoInput.classList.remove("is-valid", "is-invalid");
        if (kaydetBtn) {
          kaydetBtn.disabled = true;
        }
      });
  }, 500);
}

/**
 * Yeni oda form submit
 */
document.addEventListener("DOMContentLoaded", function () {
  const yeniOdaForm = document.getElementById("yeniOdaForm");

  if (yeniOdaForm) {
    // Kaydet butonunu başlangıçta devre dışı bırak
    const kaydetBtn = document.getElementById("yeniOdaKaydetBtn");
    if (kaydetBtn) {
      kaydetBtn.disabled = true;
    }

    // Oda numarası input'una anlık kontrol ekle
    const odaNoInput = document.getElementById("yeniOdaNo");
    if (odaNoInput) {
      odaNoInput.addEventListener("input", function () {
        odaNoAnlikKontrol(this);
      });
    }

    yeniOdaForm.addEventListener("submit", function (e) {
      e.preventDefault();

      const otelId = document.getElementById("yeniOtelId").value;
      const katId = document.getElementById("yeniKatId").value;
      const odaNo = document.getElementById("yeniOdaNo").value;
      const odaTipi = document.getElementById("yeniOdaTipi").value;

      // Validasyon
      if (!otelId || otelId === "0") {
        showAlert("yeniOdaAlert", "Lütfen bir otel seçin!", "danger");
        return;
      }

      if (!katId || katId === "0") {
        showAlert("yeniOdaAlert", "Lütfen bir kat seçin!", "danger");
        return;
      }

      if (!odaNo || odaNo.trim() === "") {
        showAlert("yeniOdaAlert", "Lütfen oda numarası girin!", "danger");
        return;
      }

      // QR bölümünü gizle (önceki denemeden kalabilir)
      document.getElementById("yeniOdaQrBolumu").style.display = "none";
      document.getElementById("yeniOdaAlert").style.display = "none";

      // Butonu devre dışı bırak
      const kaydetBtn = document.getElementById("yeniOdaKaydetBtn");
      kaydetBtn.disabled = true;
      kaydetBtn.innerHTML =
        '<span class="spinner-border spinner-border-sm mr-2"></span>Kontrol ediliyor...';

      // Önce oda numarası duplikasyon kontrolü yap
      fetch(`/api/oda-no-kontrol?oda_no=${encodeURIComponent(odaNo)}`)
        .then((response) => response.json())
        .then((kontrolData) => {
          if (!kontrolData.success) {
            throw new Error(kontrolData.error || "Kontrol hatası");
          }

          // Oda numarası kullanılıyorsa uyarı ver
          if (kontrolData.mevcut) {
            throw new Error(
              `Oda numarası "${odaNo}" zaten kullanılıyor! Lütfen farklı bir oda numarası girin.`,
            );
          }

          // Duplikasyon yoksa devam et
          kaydetBtn.innerHTML =
            '<span class="spinner-border spinner-border-sm mr-2"></span>Kaydediliyor...';

          // AJAX ile oda ekle
          return fetch("/api/oda-ekle", {
            method: "POST",
            headers: {
              "Content-Type": "application/json",
            },
            body: JSON.stringify({
              otel_id: otelId,
              kat_id: katId,
              oda_no: odaNo,
              oda_tipi: odaTipi || null,
            }),
          });
        })
        .then((response) => response.json())
        .then((data) => {
          if (!data.success) {
            throw new Error(data.error || "Oda eklenirken hata oluştu");
          }

          window.yeniEklenenOdaId = data.oda.id;

          // CSRF token'ı al
          const csrfToken =
            document
              .querySelector('meta[name="csrf-token"]')
              ?.getAttribute("content") ||
            document.querySelector('input[name="csrf_token"]')?.value;

          // QR kod oluştur
          return fetch(`/admin/oda-qr-olustur/${data.oda.id}`, {
            method: "POST",
            headers: {
              "Content-Type": "application/json",
              "X-CSRFToken": csrfToken,
            },
          });
        })
        .then((response) => {
          if (!response) return null;
          return response.json();
        })
        .then((qrData) => {
          if (!qrData) return;

          if (!qrData.success) {
            throw new Error(qrData.error || "QR kod oluşturulamadı");
          }

          if (qrData.success) {
            // Başarı mesajı göster
            showAlert(
              "yeniOdaAlert",
              "Oda başarıyla eklendi ve QR kod oluşturuldu!",
              "success",
            );

            // QR kod bölümünü göster
            document.getElementById("yeniOdaQrBolumu").style.display = "block";
            // SVG'yi img elementi yerine koy
            const qrImgElement = document.getElementById("yeniOdaQrImage");
            qrImgElement.outerHTML = qrData.data.qr_image;
            document.getElementById("yeniOdaNoGoster").textContent =
              document.getElementById("yeniOdaNo").value;

            // Butonları değiştir
            document.getElementById("yeniOdaKaydetBtn").style.display = "none";
            document.getElementById("yeniOdaTamamBtn").style.display =
              "inline-flex";

            // Toastr bildirimi
            if (typeof toastr !== "undefined") {
              toastr.success("Oda başarıyla eklendi!");
            }
          } else {
            throw new Error(qrData.error || "QR kod oluşturulamadı");
          }
        })
        .catch((error) => {
          console.error("Hata:", error);
          showAlert("yeniOdaAlert", error.message, "danger");

          // Butonu tekrar aktif et
          kaydetBtn.disabled = false;
          kaydetBtn.innerHTML =
            '<svg class="h-4 w-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 7H5a2 2 0 00-2 2v9a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2h-3m-1 4l-3 3m0 0l-3-3m3 3V4"></path></svg>Kaydet ve QR Oluştur';
        });
    });
  }
});

/**
 * Yeni oda ekleme tamamlandı - modal'ı kapat ve sayfayı yenile
 */
function yeniOdaTamamla() {
  $("#yeniOdaModal").modal("hide");
  location.reload();
}

/**
 * Yeni eklenen odanın QR kodunu indir
 */
function qrIndirYeni() {
  if (window.yeniEklenenOdaId) {
    window.location.href = `/admin/oda-qr-indir/${window.yeniEklenenOdaId}`;
  }
}

/**
 * Yeni eklenen odanın misafir mesajını düzenle
 */
function misafirMesajiDuzenleYeni() {
  if (window.yeniEklenenOdaId) {
    $("#yeniOdaModal").modal("hide");
    misafirMesajiDuzenle(window.yeniEklenenOdaId);
  }
}

/**
 * Alert mesajı göster
 */
function showAlert(alertId, message, type) {
  const alertDiv = document.getElementById(alertId);
  const alertClass = type === "success" ? "alert-success" : "alert-danger";

  alertDiv.className = `alert ${alertClass} alert-dismissible fade show`;
  alertDiv.innerHTML = `
        ${message}
        <button type="button" class="close" data-dismiss="alert">
            <span>&times;</span>
        </button>
    `;
  alertDiv.style.display = "block";

  // 5 saniye sonra otomatik kapat
  setTimeout(() => {
    alertDiv.style.display = "none";
  }, 5000);
}

/**
 * Oda düzenleme modal'ını aç
 */
function odaDuzenle(odaId, odaNo, katId, qrVarMi, odaTipi) {
  // Form alanlarını doldur
  document.getElementById("duzenleOdaId").value = odaId;
  document.getElementById("duzenleOdaNo").textContent = odaNo;
  document.getElementById("duzenleOdaNoInput").value = odaNo;

  // Alert'i temizle
  document.getElementById("odaDuzenleAlert").style.display = "none";

  // Oda bilgilerini AJAX ile getir
  fetch(`/api/odalar/${odaId}`)
    .then((response) => response.json())
    .then((data) => {
      if (data.success) {
        const oda = data.oda;

        // Otel seç
        document.getElementById("duzenleOtelId").value = oda.otel_id;

        // Katları yükle
        yukleKatlar(oda.otel_id, "duzenleKatId", function () {
          // Kat seç
          document.getElementById("duzenleKatId").value = katId;
        });

        // Oda tiplerini yükle (otelden bağımsız)
        yukleOdaTipleri("duzenleOdaTipi", function () {
          // Oda tipi seç
          if (oda.oda_tipi_id) {
            document.getElementById("duzenleOdaTipi").value = oda.oda_tipi_id;
          }
        });

        // QR kod varsa göster
        if (qrVarMi) {
          document.getElementById("qrKodBolumu").style.display = "block";

          // QR görselini AJAX ile yükle
          fetch(`/admin/oda-qr-goruntule/${odaId}`)
            .then((response) => response.json())
            .then((qrData) => {
              console.log("QR Data:", qrData); // Debug
              if (qrData.success && qrData.data && qrData.data.qr_image) {
                // SVG'yi direkt HTML olarak yerleştir
                const qrContainer = document.getElementById("duzenleQrImage");
                if (qrContainer) {
                  // SVG'yi wrapper div içine yerleştir (boyut kontrolü için)
                  qrContainer.innerHTML =
                    '<div style="width: 256px; height: 256px; background: white; display: flex; align-items: center; justify-content: center;">' +
                    qrData.data.qr_image +
                    "</div>";
                } else {
                  console.error("duzenleQrImage elementi bulunamadı");
                }
              } else {
                console.error("QR görsel verisi yok:", qrData);
              }
            })
            .catch((error) => {
              console.error("QR yükleme hatası:", error);
            });
        } else {
          document.getElementById("qrKodBolumu").style.display = "none";
        }
      }
    })
    .catch((error) => {
      console.error("Hata:", error);
      showAlert(
        "odaDuzenleAlert",
        "Oda bilgileri yüklenirken hata oluştu!",
        "danger",
      );
    });

  // Modal'ı aç
  $("#odaDuzenleModal").modal("show");
}

/**
 * Oda düzenleme form submit
 */
document.addEventListener("DOMContentLoaded", function () {
  const odaDuzenleForm = document.getElementById("odaDuzenleForm");

  if (odaDuzenleForm) {
    odaDuzenleForm.addEventListener("submit", function (e) {
      e.preventDefault();

      const odaId = document.getElementById("duzenleOdaId").value;
      const otelId = document.getElementById("duzenleOtelId").value;
      const katId = document.getElementById("duzenleKatId").value;
      const odaNo = document.getElementById("duzenleOdaNoInput").value;
      const odaTipi = document.getElementById("duzenleOdaTipi").value;

      // Validasyon
      if (!otelId || otelId === "0") {
        showAlert("odaDuzenleAlert", "Lütfen bir otel seçin!", "danger");
        return;
      }

      if (!katId || katId === "0") {
        showAlert("odaDuzenleAlert", "Lütfen bir kat seçin!", "danger");
        return;
      }

      if (!odaNo || odaNo.trim() === "") {
        showAlert("odaDuzenleAlert", "Lütfen oda numarası girin!", "danger");
        return;
      }

      // AJAX ile oda güncelle
      const csrfToken =
        document
          .querySelector('meta[name="csrf-token"]')
          ?.getAttribute("content") ||
        document.querySelector('input[name="csrf_token"]')?.value ||
        "";
      fetch(`/api/oda-guncelle/${odaId}`, {
        method: "PUT",
        headers: {
          "Content-Type": "application/json",
          "X-CSRFToken": csrfToken,
        },
        body: JSON.stringify({
          otel_id: otelId,
          kat_id: katId,
          oda_no: odaNo,
          oda_tipi: odaTipi || null,
        }),
      })
        .then((response) => response.json())
        .then((data) => {
          if (data.success) {
            showAlert(
              "odaDuzenleAlert",
              "Oda başarıyla güncellendi!",
              "success",
            );

            // Toastr bildirimi
            if (typeof toastr !== "undefined") {
              toastr.success("Oda başarıyla güncellendi!");
            }

            // 2 saniye sonra sayfayı yenile
            setTimeout(() => {
              location.reload();
            }, 2000);
          } else {
            throw new Error(data.error || "Oda güncellenirken hata oluştu");
          }
        })
        .catch((error) => {
          console.error("Hata:", error);
          showAlert("odaDuzenleAlert", error.message, "danger");
        });
    });
  }
});

/**
 * Tüm QR kodları temizle (jQuery UI Dialog ile)
 */
function tumQrTemizle() {
  // jQuery UI Dialog ile onay al
  $("<div>")
    .html(
      '<div class="text-center p-4">' +
        '<svg class="mx-auto h-16 w-16 text-red-600 mb-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">' +
        '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"></path>' +
        "</svg>" +
        '<p class="text-xl font-bold text-slate-900 mb-3">Tüm QR Kodları Temizle</p>' +
        '<p class="text-base text-slate-700 mb-2">Tüm odalara ait QR kodları silinecek.</p>' +
        '<p class="text-base text-red-600 font-semibold">Bu işlem geri alınamaz!</p>' +
        '<p class="text-sm text-slate-600 mt-3">Devam etmek istediğinize emin misiniz?</p>' +
        "</div>",
    )
    .dialog({
      title: "⚠️ Onay Gerekli",
      modal: true,
      width: 500,
      buttons: {
        "Evet, Tümünü Temizle": {
          text: "Evet, Tümünü Temizle",
          class: "btn btn-danger",
          click: function () {
            $(this).dialog("close");
            tumQrTemizleOnay();
          },
        },
        İptal: {
          text: "İptal",
          class: "btn btn-secondary",
          click: function () {
            $(this).dialog("close");
          },
        },
      },
      close: function () {
        $(this).remove();
      },
    });
}

/**
 * Tüm QR kodları temizle - onaylandı
 */
function tumQrTemizleOnay() {
  // CSRF token'ı al
  const csrfToken =
    document
      .querySelector('meta[name="csrf-token"]')
      ?.getAttribute("content") ||
    document.querySelector('input[name="csrf_token"]')?.value;

  // Loading göster
  if (typeof toastr !== "undefined") {
    toastr.info("QR kodları temizleniyor...", "İşlem Başladı");
  }

  // AJAX ile tüm QR kodları temizle
  fetch("/admin/tum-qr-temizle", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "X-CSRFToken": csrfToken,
    },
  })
    .then((response) => response.json())
    .then((data) => {
      if (data.success) {
        // Başarı mesajı
        if (typeof toastr !== "undefined") {
          toastr.success(
            `${data.temizlenen_adet} odanın QR kodu temizlendi!`,
            "Başarılı",
          );
        }

        // Sayfayı yenile
        setTimeout(() => {
          location.reload();
        }, 1500);
      } else {
        throw new Error(data.message || "QR kodları temizlenirken hata oluştu");
      }
    })
    .catch((error) => {
      console.error("Hata:", error);
      if (typeof toastr !== "undefined") {
        toastr.error(error.message, "Hata");
      } else {
        alert("Hata: " + error.message);
      }
    });
}

/**
 * Toplu QR kod oluştur (jQuery UI Dialog ile onay)
 */
function topluQrOlustur(tip) {
  // Mesajı belirle
  let baslik, mesaj, ikon;

  if (tip === "tumu") {
    baslik = "Tüm Odalar İçin QR Oluştur";
    mesaj =
      "Tüm odalara QR kod oluşturulacak. Mevcut QR kodlar değiştirilmeyecek.";
    ikon =
      '<svg class="mx-auto h-16 w-16 text-indigo-600 mb-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v16m8-8H4"></path></svg>';
  } else {
    baslik = "QR'sız Odalar İçin QR Oluştur";
    mesaj = "Sadece QR kodu olmayan odalara QR kod oluşturulacak.";
    ikon =
      '<svg class="mx-auto h-16 w-16 text-green-600 mb-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 6v6m0 0v6m0-6h6m-6 0H6"></path></svg>';
  }

  // jQuery UI Dialog ile onay al
  $("<div>")
    .html(
      '<div class="text-center p-4">' +
        ikon +
        '<p class="text-xl font-bold text-slate-900 dark:text-slate-100 mb-3">' +
        baslik +
        "</p>" +
        '<p class="text-base text-slate-700 dark:text-slate-300 mb-2">' +
        mesaj +
        "</p>" +
        '<p class="text-sm text-slate-600 dark:text-slate-400 mt-3">Devam etmek istiyor musunuz?</p>' +
        "</div>",
    )
    .dialog({
      title: "📱 QR Kod Oluştur",
      modal: true,
      width: 500,
      buttons: {
        "Evet, Oluştur": {
          text: "Evet, Oluştur",
          class: "btn btn-primary",
          click: function () {
            $(this).dialog("close");
            topluQrOlusturOnay(tip);
          },
        },
        İptal: {
          text: "İptal",
          class: "btn btn-secondary",
          click: function () {
            $(this).dialog("close");
          },
        },
      },
      close: function () {
        $(this).remove();
      },
    });
}

/**
 * Toplu QR kod oluştur - onaylandı
 */
function topluQrOlusturOnay(tip) {
  // CSRF token'ı al
  const csrfToken =
    document
      .querySelector('meta[name="csrf-token"]')
      ?.getAttribute("content") ||
    document.querySelector('input[name="csrf_token"]')?.value;

  // Loading göster
  if (typeof toastr !== "undefined") {
    toastr.info("QR kodları oluşturuluyor...", "İşlem Başladı");
  }

  // AJAX ile toplu QR oluştur
  fetch("/admin/toplu-qr-olustur", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "X-CSRFToken": csrfToken,
    },
    body: JSON.stringify({
      tip: tip,
    }),
  })
    .then((response) => response.json())
    .then((data) => {
      if (data.success) {
        // Başarı mesajı
        if (typeof toastr !== "undefined") {
          toastr.success(
            `${data.olusturulan_adet} odaya QR kodu oluşturuldu!`,
            "Başarılı",
          );
        }

        // Sayfayı yenile
        setTimeout(() => {
          location.reload();
        }, 1500);
      } else {
        throw new Error(
          data.message || "QR kodları oluşturulurken hata oluştu",
        );
      }
    })
    .catch((error) => {
      console.error("Hata:", error);
      if (typeof toastr !== "undefined") {
        toastr.error(error.message, "Hata");
      } else {
        alert("Hata: " + error.message);
      }
    });
}

/**
 * Toplu QR indir
 */
function topluQrIndir() {
  window.location.href = "/admin/toplu-qr-indir";
}
