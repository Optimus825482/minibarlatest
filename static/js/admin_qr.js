/**
 * Admin QR Kod Yönetimi JavaScript
 */

// QR Kod Oluştur (Tek Oda)
function qrOlustur(odaId) {
  if (!confirm("Bu oda için QR kod oluşturulsun mu?")) {
    return;
  }

  $.ajax({
    url: `/admin/oda-qr-olustur/${odaId}`,
    method: "POST",
    headers: {
      "X-CSRFToken": $('meta[name="csrf-token"]').attr("content"),
    },
    success: function (response) {
      if (response.success) {
        toastr.success(response.message);
        setTimeout(() => location.reload(), 1500);
      } else {
        toastr.error(response.message);
      }
    },
    error: function (xhr) {
      if (xhr.status === 429) {
        toastr.error("Çok fazla deneme. Lütfen 1 dakika bekleyin.");
      } else {
        toastr.error("QR kod oluşturulamadı");
      }
    },
  });
}

// QR Kod Görüntüle
function qrGoruntule(odaId) {
  $.ajax({
    url: `/admin/oda-qr-goruntule/${odaId}`,
    method: "GET",
    success: function (response) {
      if (response.success) {
        const data = response.data;

        // Oda bilgilerini span'lere yaz
        $("#qrOdaNo").text(data.oda_no || "");
        $("#qrKat").text(data.kat_adi || "");
        $("#qrOdaNoDetay").text(data.oda_no || "");

        // SVG'yi direkt innerHTML ile ekle (jQuery selector hatası önlemek için)
        const qrContainer = document.getElementById("qrImage");

        // Eski data URI prefix'ini temizle (veritabanında eski format varsa)
        let svgContent = data.qr_image;
        if (svgContent.startsWith("data:image/svg+xml")) {
          // "data:image/svg+xml;utf8," veya benzeri prefix'i kaldır
          svgContent = svgContent.replace(/^data:image\/svg\+xml[^,]*,/, "");
        }

        qrContainer.innerHTML = svgContent;

        // SVG'yi sabit boyutta tut (256x256)
        const svgElement = qrContainer.querySelector("svg");
        if (svgElement) {
          svgElement.setAttribute("width", "256");
          svgElement.setAttribute("height", "256");
          svgElement.style.display = "block";
          svgElement.style.margin = "0 auto";
        }

        // Modal'ı aç
        $("#qrModal").data("oda-id", odaId);
        $("#qrModal").data("oda-no", data.oda_no);
        $("#qrModal").data("kat-adi", data.kat_adi);
        $("#qrModal").modal("show");
      } else {
        toastr.error(response.message);
      }
    },
    error: function () {
      toastr.error("QR kod yüklenemedi");
    },
  });
}

// QR Kod İndir (Tek Oda)
function qrIndir(odaId) {
  if (!odaId) {
    odaId = $("#qrModal").data("oda-id");
  }
  window.location.href = `/admin/oda-qr-indir/${odaId}`;
  toastr.success("QR kod indiriliyor...");
}

// QR Kod Yazdır
function qrYazdir() {
  const qrSvg = $("#qrImage").html();

  // Önce span'lerden al (DOM'da görünür olan)
  let odaNo = $("#qrOdaNo").text().trim();
  let katAdi = $("#qrKat").text().trim();

  // Eğer boşsa modal data'dan al
  if (!odaNo) {
    odaNo = $("#qrModal").data("oda-no") || "";
  }
  if (!katAdi) {
    katAdi = $("#qrModal").data("kat-adi") || "";
  }

  console.log("Yazdırma - Oda No:", odaNo, "Kat:", katAdi);

  if (!odaNo) {
    toastr.error("Oda numarası bulunamadı!");
    return;
  }

  const printWindow = window.open("", "_blank");
  printWindow.document.write(`
        <html>
        <head>
            <title>QR Kod - Oda ${odaNo}</title>
            <style>
                @page { size: A4; margin: 20mm; }
                body { 
                    text-align: center; 
                    font-family: Arial, sans-serif; 
                    padding: 40px 20px;
                    margin: 0;
                }
                .qr-container {
                    display: inline-block;
                    background: white;
                    padding: 30px;
                    border: 2px solid #e2e8f0;
                    border-radius: 12px;
                    box-shadow: 0 4px 6px rgba(0,0,0,0.1);
                }
                svg { 
                    width: 300px !important; 
                    height: 300px !important; 
                    display: block;
                    margin: 0 auto;
                }
                h1 { 
                    margin: 0 0 10px 0;
                    font-size: 32px;
                    font-weight: bold;
                    color: #1e293b;
                }
                .kat-info {
                    margin: 10px 0 20px 0;
                    font-size: 18px;
                    color: #64748b;
                }
                @media print {
                    body { padding: 20px; }
                    .qr-container { box-shadow: none; }
                }
            </style>
        </head>
        <body>
            <div class="qr-container">
                <h1>Oda ${odaNo}</h1>
                <div class="kat-info">${katAdi}</div>
                ${qrSvg}
            </div>
        </body>
        </html>
    `);
  printWindow.document.close();
  printWindow.print();
}

// Toplu QR Oluştur
function topluQrOlustur(mod) {
  const mesaj =
    mod === "tumu"
      ? "Tüm odalar için QR kod oluşturulsun mu?"
      : "QR kodu olmayan odalar için QR kod oluşturulsun mu?";

  if (!confirm(mesaj)) {
    return;
  }

  toastr.info("QR kodları oluşturuluyor, lütfen bekleyin...");

  $.ajax({
    url: "/admin/toplu-qr-olustur",
    method: "POST",
    contentType: "application/json",
    headers: {
      "X-CSRFToken": $('meta[name="csrf-token"]').attr("content"),
    },
    data: JSON.stringify({ mod: mod }),
    success: function (response) {
      if (response.success) {
        const data = response.data;
        toastr.success(`${data.basarili} oda için QR kod oluşturuldu!`);
        if (data.basarisiz > 0) {
          toastr.warning(`${data.basarisiz} oda için hata oluştu`);
        }
        setTimeout(() => location.reload(), 2000);
      } else {
        toastr.error(response.message);
      }
    },
    error: function (xhr) {
      if (xhr.status === 429) {
        toastr.error("Çok fazla deneme. Lütfen 1 dakika bekleyin.");
      } else {
        toastr.error("Toplu QR oluşturma başarısız");
      }
    },
  });
}

// Toplu QR İndir
function topluQrIndir() {
  window.location.href = "/admin/toplu-qr-indir";
  toastr.success("QR kodları ZIP olarak indiriliyor...");
}

// Misafir Mesajı Düzenle
function misafirMesajiDuzenle(odaId, geriDonusModal) {
  $.ajax({
    url: `/admin/oda-misafir-mesaji/${odaId}`,
    method: "GET",
    success: function (response) {
      if (response.success) {
        const data = response.data;

        // Alert'i temizle
        $("#misafirMesajiAlert").hide();

        $("#misafirMesajiOdaNo").text(data.oda_no);
        $("#misafirMesajiInput").val(data.mesaj);

        // Karakter sayacını güncelle
        const len = data.mesaj ? data.mesaj.length : 0;
        $("#karakterSayaci").text(`${len}/500`);

        $("#misafirMesajiModal").data("oda-id", odaId);
        $("#misafirMesajiModal").data(
          "geri-donus-modal",
          geriDonusModal || null
        );
        $("#misafirMesajiModal").modal("show");
      } else {
        toastr.error(response.message);
      }
    },
    error: function () {
      toastr.error("Mesaj yüklenemedi");
    },
  });
}

// Misafir Mesajı Kaydet
function misafirMesajiKaydet() {
  const odaId = $("#misafirMesajiModal").data("oda-id");
  const mesaj = $("#misafirMesajiInput").val().trim();
  const geriDonusModal = $("#misafirMesajiModal").data("geri-donus-modal");

  if (mesaj.length > 500) {
    showModalAlert(
      "misafirMesajiAlert",
      "error",
      "Mesaj maksimum 500 karakter olabilir"
    );
    return;
  }

  $.ajax({
    url: `/admin/oda-misafir-mesaji/${odaId}`,
    method: "POST",
    contentType: "application/json",
    headers: {
      "X-CSRFToken": $('meta[name="csrf-token"]').attr("content"),
    },
    data: JSON.stringify({ mesaj: mesaj }),
    success: function (response) {
      if (response.success) {
        showModalAlert("misafirMesajiAlert", "success", response.message);
        toastr.success(response.message);
        setTimeout(() => {
          $("#misafirMesajiModal").modal("hide");

          // Eğer bir modal'dan geldiyse geri dön
          if (geriDonusModal === "odaDuzenle") {
            setTimeout(() => {
              const odaNo = $("#duzenleOdaNoInput").val();
              const katId = $("#duzenleKatId").val();
              odaDuzenle(odaId, odaNo, katId, true);
            }, 300);
          } else if (geriDonusModal === "yeniOda") {
            setTimeout(() => {
              $("#yeniOdaModal").modal("show");
            }, 300);
          }
        }, 1500);
      } else {
        showModalAlert("misafirMesajiAlert", "error", response.message);
      }
    },
    error: function () {
      showModalAlert("misafirMesajiAlert", "error", "Mesaj kaydedilemedi");
    },
  });
}

// Karakter sayacı
$(document).ready(function () {
  $("#misafirMesajiInput").on("input", function () {
    const len = $(this).val().length;
    $("#karakterSayaci").text(`${len}/500`);

    if (len > 500) {
      $("#karakterSayaci")
        .addClass("text-red-600 dark:text-red-400")
        .removeClass("text-slate-500 dark:text-slate-400");
    } else {
      $("#karakterSayaci")
        .removeClass("text-red-600 dark:text-red-400")
        .addClass("text-slate-500 dark:text-slate-400");
    }
  });
});

// Oda Düzenle Modal
function odaDuzenle(odaId, odaNo, katId, qrVar) {
  // Alert'i temizle
  $("#odaDuzenleAlert").hide();

  $("#duzenleOdaId").val(odaId);
  $("#duzenleOdaNo").text(odaNo);
  $("#duzenleOdaNoInput").val(odaNo);
  $("#duzenleKatId").val(katId);

  // Choices.js'i başlat
  setTimeout(function () {
    if (typeof initializeChoices === "function") {
      initializeChoices();
    }
  }, 100);

  // Kat bilgisinden otel ID'sini al ve otel dropdown'unu set et
  $.ajax({
    url: `/api/kat-bilgi/${katId}`,
    method: "GET",
    success: function (response) {
      if (response.success && response.otel_id) {
        const otelSelect = document.getElementById("duzenleOtelId");
        if (otelSelect) {
          otelSelect.value = response.otel_id;
          // Choices.js instance'ını güncelle
          if (
            window.choicesInstances &&
            window.choicesInstances["duzenleOtelId"]
          ) {
            window.choicesInstances["duzenleOtelId"].setChoiceByValue(
              response.otel_id.toString()
            );
          }
        }
        // Otele göre katları yükle
        yukleKatlar(response.otel_id, "duzenleKatId", function () {
          // Katlar yüklendikten sonra mevcut katı seç
          const katSelect = document.getElementById("duzenleKatId");
          if (katSelect) {
            katSelect.value = katId;
            // Choices.js instance'ını güncelle
            if (
              window.choicesInstances &&
              window.choicesInstances["duzenleKatId"]
            ) {
              window.choicesInstances["duzenleKatId"].setChoiceByValue(
                katId.toString()
              );
            }
          }
        });
      }
    },
    error: function () {
      console.error("Kat bilgisi alınamadı");
    },
  });

  // QR kod varsa göster
  if (qrVar) {
    // QR kodunu yükle
    $.ajax({
      url: `/admin/oda-qr-goruntule/${odaId}`,
      method: "GET",
      success: function (response) {
        if (response.success) {
          // SVG'yi düzenle modal'ına ekle
          const qrContainer = document.getElementById("duzenleQrImage");
          let svgContent = response.data.qr_image;
          if (svgContent.startsWith("data:image/svg+xml")) {
            svgContent = svgContent.replace(/^data:image\/svg\+xml[^,]*,/, "");
          }
          qrContainer.innerHTML = svgContent;

          const svgElement = qrContainer.querySelector("svg");
          if (svgElement) {
            svgElement.setAttribute("width", "100%");
            svgElement.setAttribute("height", "100%");
          }

          $("#qrKodBolumu").show();
          $("#qrYokMesaji").hide();
        } else {
          $("#qrKodBolumu").hide();
          $("#qrYokMesaji").show();
        }
      },
      error: function () {
        $("#qrKodBolumu").hide();
        $("#qrYokMesaji").show();
      },
    });
  } else {
    $("#qrKodBolumu").hide();
    $("#qrYokMesaji").show();
  }

  $("#odaDuzenleModal").modal("show");
}

// Oda Düzenle Form Submit - Document Ready içinde
$(document).ready(function () {
  $("#odaDuzenleForm").on("submit", function (e) {
    e.preventDefault();

    const odaId = $("#duzenleOdaId").val();
    const otelId = $("#duzenleOtelId").val();
    const katId = $("#duzenleKatId").val();
    const odaNo = $("#duzenleOdaNoInput").val().trim();

    if (!otelId || !katId || !odaNo) {
      showModalAlert(
        "odaDuzenleAlert",
        "error",
        "Lütfen tüm alanları doldurun"
      );
      return;
    }

    $.ajax({
      url: `/oda-duzenle/${odaId}`,
      method: "POST",
      data: {
        csrf_token: $('meta[name="csrf-token"]').attr("content"),
        otel_id: otelId,
        kat_id: katId,
        oda_no: odaNo,
      },
      success: function (response) {
        showModalAlert(
          "odaDuzenleAlert",
          "success",
          "Oda başarıyla güncellendi"
        );
        toastr.success("Oda başarıyla güncellendi");
        setTimeout(() => {
          $("#odaDuzenleModal").modal("hide");
          location.reload();
        }, 1500);
      },
      error: function (xhr) {
        const message =
          xhr.responseJSON?.message || "Oda güncellenirken hata oluştu";
        showModalAlert("odaDuzenleAlert", "error", message);
      },
    });
  });
});

// QR Yenile (Modal içinden)
function qrYenile() {
  if (
    !confirm(
      "⚠️ UYARI!\n\nQR kod yenilenirse:\n- Eski QR kod geçersiz olacak\n- Yeni QR kod yazdırılmalı\n- Odadaki QR değiştirilmeli\n\nDevam etmek istiyor musunuz?"
    )
  ) {
    return;
  }

  const odaId = $("#duzenleOdaId").val();

  $.ajax({
    url: `/admin/oda-qr-olustur/${odaId}`,
    method: "POST",
    headers: {
      "X-CSRFToken": $('meta[name="csrf-token"]').attr("content"),
    },
    success: function (response) {
      if (response.success) {
        showModalAlert(
          "odaDuzenleAlert",
          "success",
          "QR kod başarıyla yenilendi!"
        );
        toastr.success("QR kod yenilendi!");

        // SVG'yi düzenle modal'ına ekle
        const qrContainer = document.getElementById("duzenleQrImage");
        let svgContent = response.data.qr_image;
        if (svgContent.startsWith("data:image/svg+xml")) {
          svgContent = svgContent.replace(/^data:image\/svg\+xml[^,]*,/, "");
        }
        qrContainer.innerHTML = svgContent;

        const svgElement = qrContainer.querySelector("svg");
        if (svgElement) {
          svgElement.setAttribute("width", "100%");
          svgElement.setAttribute("height", "100%");
        }

        $("#qrKodBolumu").show();
        $("#qrYokMesaji").hide();
      } else {
        showModalAlert("odaDuzenleAlert", "error", response.message);
      }
    },
    error: function (xhr) {
      if (xhr.status === 429) {
        showModalAlert(
          "odaDuzenleAlert",
          "error",
          "Çok fazla deneme. Lütfen 1 dakika bekleyin."
        );
      } else {
        showModalAlert("odaDuzenleAlert", "error", "QR kod yenilenemedi");
      }
    },
  });
}

// QR Oluştur (Modal içinden - QR yoksa)
function qrOlusturDuzenle() {
  const odaId = $("#duzenleOdaId").val();
  qrOlustur(odaId);

  // Modal'ı güncelle
  setTimeout(() => {
    odaDuzenle(
      odaId,
      $("#duzenleOdaNoInput").val(),
      $("#duzenleKatId").val(),
      true
    );
  }, 2000);
}

// QR Yazdır (Modal içinden)
function qrYazdirDuzenle() {
  const qrSvg = $("#duzenleQrImage").html();
  const odaNo = $("#duzenleOdaNoInput").val();
  const katAdi = $("#duzenleKatId option:selected").text();

  const printWindow = window.open("", "_blank");
  printWindow.document.write(`
        <html>
        <head>
            <title>QR Kod - Oda ${odaNo}</title>
            <style>
                @page { size: A4; margin: 20mm; }
                body { 
                    text-align: center; 
                    font-family: Arial, sans-serif; 
                    padding: 40px 20px;
                    margin: 0;
                }
                .qr-container {
                    display: inline-block;
                    background: white;
                    padding: 30px;
                    border: 2px solid #e2e8f0;
                    border-radius: 12px;
                    box-shadow: 0 4px 6px rgba(0,0,0,0.1);
                }
                svg { 
                    width: 300px !important; 
                    height: 300px !important; 
                    display: block;
                    margin: 0 auto;
                }
                h1 { 
                    margin: 0 0 10px 0;
                    font-size: 32px;
                    font-weight: bold;
                    color: #1e293b;
                }
                .kat-info {
                    margin: 10px 0 20px 0;
                    font-size: 18px;
                    color: #64748b;
                }
                @media print {
                    body { padding: 20px; }
                    .qr-container { box-shadow: none; }
                }
            </style>
        </head>
        <body>
            <div class="qr-container">
                <h1>Oda ${odaNo}</h1>
                <div class="kat-info">${katAdi}</div>
                ${qrSvg}
            </div>
        </body>
        </html>
    `);
  printWindow.document.close();
  printWindow.print();
}

// QR İndir (Modal içinden)
function qrIndirDuzenle() {
  const odaId = $("#duzenleOdaId").val();
  qrIndir(odaId);
}

// Yeni Oda Modal Aç
function yeniOdaModal() {
  // Formu sıfırla
  $("#yeniOdaForm")[0].reset();
  $("#yeniOdaAlert").hide();
  $("#yeniOdaQrBolumu").hide();
  $("#yeniOdaKaydetBtn")
    .show()
    .prop("disabled", false)
    .html(
      '<svg class="h-4 w-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 7H5a2 2 0 00-2 2v9a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2h-3m-1 4l-3 3m0 0l-3-3m3 3V4"></path></svg> Kaydet ve QR Oluştur'
    );
  $("#yeniOdaTamamBtn").hide();
  $("#yeniOdaKapatBtn").text("Kapat");
  yeniEklenenOdaId = null;

  $("#yeniOdaModal").modal("show");
}

// Yeni Oda Form Submit
let yeniEklenenOdaId = null;

$(document).ready(function () {
  $("#yeniOdaForm").on("submit", function (e) {
    e.preventDefault();

    const otelId = $("#yeniOtelId").val();
    const katId = $("#yeniKatId").val();
    const odaNo = $("#yeniOdaNo").val().trim();

    if (!otelId || !katId || !odaNo) {
      showModalAlert("yeniOdaAlert", "error", "Lütfen tüm alanları doldurun");
      return;
    }

    // Butonu disable et
    $("#yeniOdaKaydetBtn")
      .prop("disabled", true)
      .html(
        '<svg class="animate-spin h-4 w-4 mr-2 inline-block" fill="none" stroke="currentColor" viewBox="0 0 24 24"><circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle><path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path></svg> Kaydediliyor...'
      );

    // Oda ekle
    $.ajax({
      url: "/oda-tanimla",
      method: "POST",
      data: {
        csrf_token: $('meta[name="csrf-token"]').attr("content"),
        otel_id: otelId,
        kat_id: katId,
        oda_no: odaNo,
      },
      success: function (response) {
        // Oda eklendi, şimdi QR oluştur
        showModalAlert(
          "yeniOdaAlert",
          "info",
          "Oda eklendi, QR kod oluşturuluyor..."
        );

        // Response'dan oda ID'sini al (sayfa yenilenmeden önce)
        // Yeni eklenen odayı bulmak için AJAX ile oda listesini çek
        $.ajax({
          url: "/api/odalar",
          method: "GET",
          success: function (odalar) {
            // En son eklenen odayı bul (oda_no ile)
            const yeniOda = odalar.find((o) => o.oda_no === odaNo);

            if (yeniOda) {
              yeniEklenenOdaId = yeniOda.id;

              // QR kod oluştur
              $.ajax({
                url: `/admin/oda-qr-olustur/${yeniOda.id}`,
                method: "POST",
                headers: {
                  "X-CSRFToken": $('meta[name="csrf-token"]').attr("content"),
                },
                success: function (qrResponse) {
                  if (qrResponse.success) {
                    // Alert'i temizle
                    $("#yeniOdaAlert").hide();

                    // QR kodu göster
                    $("#yeniOdaNoGoster").text(odaNo);
                    $("#yeniOdaQrImage").attr("src", qrResponse.data.qr_image);
                    $("#yeniOdaQrBolumu").show();

                    // Butonları değiştir
                    $("#yeniOdaKaydetBtn").hide();
                    $("#yeniOdaTamamBtn").show();
                    $("#yeniOdaKapatBtn").text("Kapat ve Sayfayı Yenile");

                    toastr.success("QR kod oluşturuldu!");
                  } else {
                    showModalAlert(
                      "yeniOdaAlert",
                      "error",
                      "QR kod oluşturulamadı: " + qrResponse.message
                    );
                    $("#yeniOdaKaydetBtn")
                      .prop("disabled", false)
                      .html(
                        '<svg class="h-4 w-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 7H5a2 2 0 00-2 2v9a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2h-3m-1 4l-3 3m0 0l-3-3m3 3V4"></path></svg> Kaydet ve QR Oluştur'
                      );
                  }
                },
                error: function () {
                  showModalAlert(
                    "yeniOdaAlert",
                    "error",
                    "QR kod oluşturulurken hata oluştu"
                  );
                  $("#yeniOdaKaydetBtn")
                    .prop("disabled", false)
                    .html(
                      '<svg class="h-4 w-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 7H5a2 2 0 00-2 2v9a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2h-3m-1 4l-3 3m0 0l-3-3m3 3V4"></path></svg> Kaydet ve QR Oluştur'
                    );
                },
              });
            } else {
              showModalAlert("yeniOdaAlert", "error", "Oda bulunamadı");
              $("#yeniOdaKaydetBtn")
                .prop("disabled", false)
                .html(
                  '<svg class="h-4 w-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 7H5a2 2 0 00-2 2v9a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2h-3m-1 4l-3 3m0 0l-3-3m3 3V4"></path></svg> Kaydet ve QR Oluştur'
                );
            }
          },
          error: function () {
            showModalAlert("yeniOdaAlert", "error", "Oda listesi alınamadı");
            $("#yeniOdaKaydetBtn")
              .prop("disabled", false)
              .html(
                '<svg class="h-4 w-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 7H5a2 2 0 00-2 2v9a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2h-3m-1 4l-3 3m0 0l-3-3m3 3V4"></path></svg> Kaydet ve QR Oluştur'
              );
          },
        });
      },
      error: function (xhr) {
        const message =
          xhr.responseJSON?.message || "Oda eklenirken hata oluştu";
        showModalAlert("yeniOdaAlert", "error", message);
        $("#yeniOdaKaydetBtn")
          .prop("disabled", false)
          .html(
            '<svg class="h-4 w-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 7H5a2 2 0 00-2 2v9a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2h-3m-1 4l-3 3m0 0l-3-3m3 3V4"></path></svg> Kaydet ve QR Oluştur'
          );
      },
    });
  });

  // Modal kapatıldığında sayfayı yenile (eğer oda eklendiyse)
  $("#yeniOdaModal").on("hidden.bs.modal", function () {
    if (yeniEklenenOdaId) {
      location.reload();
    }
  });
});

// Yeni Oda Tamamla
function yeniOdaTamamla() {
  $("#yeniOdaModal").modal("hide");
  setTimeout(() => location.reload(), 500);
}

// QR Yazdır (Yeni Oda)
function qrYazdirYeni() {
  const qrSvg = $("#yeniOdaQrImage").html();
  const odaNo = $("#yeniOdaNoGoster").text();
  const katAdi = $("#yeniKatId option:selected").text();

  const printWindow = window.open("", "_blank");
  printWindow.document.write(`
        <html>
        <head>
            <title>QR Kod - Oda ${odaNo}</title>
            <style>
                @page { size: A4; margin: 20mm; }
                body { 
                    text-align: center; 
                    font-family: Arial, sans-serif; 
                    padding: 40px 20px;
                    margin: 0;
                }
                .qr-container {
                    display: inline-block;
                    background: white;
                    padding: 30px;
                    border: 2px solid #e2e8f0;
                    border-radius: 12px;
                    box-shadow: 0 4px 6px rgba(0,0,0,0.1);
                }
                svg { 
                    width: 300px !important; 
                    height: 300px !important; 
                    display: block;
                    margin: 0 auto;
                }
                h1 { 
                    margin: 0 0 10px 0;
                    font-size: 32px;
                    font-weight: bold;
                    color: #1e293b;
                }
                .kat-info {
                    margin: 10px 0 20px 0;
                    font-size: 18px;
                    color: #64748b;
                }
                @media print {
                    body { padding: 20px; }
                    .qr-container { box-shadow: none; }
                }
            </style>
        </head>
        <body>
            <div class="qr-container">
                <h1>Oda ${odaNo}</h1>
                <div class="kat-info">${katAdi}</div>
                ${qrSvg}
            </div>
        </body>
        </html>
    `);
  printWindow.document.close();
  printWindow.print();
}

// QR İndir (Yeni Oda)
function qrIndirYeni() {
  if (yeniEklenenOdaId) {
    qrIndir(yeniEklenenOdaId);
  }
}

// Misafir Mesajı Düzenle (Yeni Oda)
function misafirMesajiDuzenleYeni() {
  if (yeniEklenenOdaId) {
    // Önce Yeni Oda Modal'ını kapat
    $("#yeniOdaModal").modal("hide");

    // Kısa bir gecikme ile Misafir Mesajı Modal'ını aç
    setTimeout(() => {
      misafirMesajiDuzenle(yeniEklenenOdaId, "yeniOda");
    }, 300);
  }
}

// Misafir Mesajı Düzenle (Düzenle Modal'ından)
function misafirMesajiDuzenleDuzenle() {
  const odaId = $("#duzenleOdaId").val();
  if (odaId) {
    // Önce Oda Düzenle Modal'ını kapat
    $("#odaDuzenleModal").modal("hide");

    // Kısa bir gecikme ile Misafir Mesajı Modal'ını aç
    setTimeout(() => {
      misafirMesajiDuzenle(odaId, "odaDuzenle");
    }, 300);
  }
}

// Modal içinde alert göster
function showModalAlert(containerId, type, message) {
  const container = $(`#${containerId}`);

  let bgColor, borderColor, textColor, icon;

  switch (type) {
    case "success":
      bgColor = "bg-green-50 dark:bg-green-900/20";
      borderColor = "border-green-200 dark:border-green-800";
      textColor = "text-green-800 dark:text-green-200";
      icon =
        '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"></path>';
      break;
    case "error":
      bgColor = "bg-red-50 dark:bg-red-900/20";
      borderColor = "border-red-200 dark:border-red-800";
      textColor = "text-red-800 dark:text-red-200";
      icon =
        '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 14l2-2m0 0l2-2m-2 2l-2-2m2 2l2 2m7-2a9 9 0 11-18 0 9 9 0 0118 0z"></path>';
      break;
    case "warning":
      bgColor = "bg-yellow-50 dark:bg-yellow-900/20";
      borderColor = "border-yellow-200 dark:border-yellow-800";
      textColor = "text-yellow-800 dark:text-yellow-200";
      icon =
        '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"></path>';
      break;
    case "info":
      bgColor = "bg-blue-50 dark:bg-blue-900/20";
      borderColor = "border-blue-200 dark:border-blue-800";
      textColor = "text-blue-800 dark:text-blue-200";
      icon =
        '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"></path>';
      break;
  }

  const alertHtml = `
        <div class="${bgColor} border ${borderColor} rounded-lg p-4 mb-4">
            <div class="flex items-center">
                <svg class="h-5 w-5 ${textColor} mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    ${icon}
                </svg>
                <p class="${textColor} text-sm font-medium">${message}</p>
            </div>
        </div>
    `;

  container.html(alertHtml).show();

  // 5 saniye sonra gizle
  setTimeout(() => {
    container.fadeOut();
  }, 5000);
}

// Misafir mesajı kaydet - alert ekle
function misafirMesajiKaydet() {
  const odaId = $("#misafirMesajiModal").data("oda-id");
  const mesaj = $("#misafirMesajiInput").val().trim();

  if (mesaj.length > 500) {
    showModalAlert(
      "misafirMesajiAlert",
      "error",
      "Mesaj maksimum 500 karakter olabilir"
    );
    return;
  }

  $.ajax({
    url: `/admin/oda-misafir-mesaji/${odaId}`,
    method: "POST",
    contentType: "application/json",
    headers: {
      "X-CSRFToken": $('meta[name="csrf-token"]').attr("content"),
    },
    data: JSON.stringify({ mesaj: mesaj }),
    success: function (response) {
      if (response.success) {
        showModalAlert("misafirMesajiAlert", "success", response.message);
        toastr.success(response.message);
        setTimeout(() => {
          $("#misafirMesajiModal").modal("hide");
        }, 1500);
      } else {
        showModalAlert("misafirMesajiAlert", "error", response.message);
      }
    },
    error: function () {
      showModalAlert("misafirMesajiAlert", "error", "Mesaj kaydedilemedi");
    },
  });
}

/**
 * Yeni Oda Modal Aç
 */
function yeniOdaModal() {
  const modal = document.getElementById("yeniOdaModal");
  if (modal) {
    // Bootstrap modal ise
    if (typeof bootstrap !== "undefined") {
      const bsModal = new bootstrap.Modal(modal);
      bsModal.show();
    }
    // jQuery modal ise
    else if (typeof $ !== "undefined" && $.fn.modal) {
      $(modal).modal("show");
    }
    // Basit göster
    else {
      modal.style.display = "block";
      modal.classList.add("show");
    }
  }
}
