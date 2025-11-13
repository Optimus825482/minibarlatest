/**
 * Oda Tanımlama Sayfası JavaScript
 * Yeni oda ekleme, düzenleme ve QR kod işlemleri
 */

// Global değişkenler
var yeniEklenenOdaId = yeniEklenenOdaId || null;

/**
 * Yeni oda modal'ını aç
 */
function yeniOdaModal() {
    // Formu temizle
    document.getElementById('yeniOdaForm').reset();
    document.getElementById('yeniOdaAlert').style.display = 'none';
    document.getElementById('yeniOdaQrBolumu').style.display = 'none';
    document.getElementById('yeniOdaKaydetBtn').style.display = 'inline-flex';
    document.getElementById('yeniOdaTamamBtn').style.display = 'none';
    
    // Kat ve oda tipi dropdown'larını sıfırla
    const katSelect = document.getElementById('yeniKatId');
    const odaTipiSelect = document.getElementById('yeniOdaTipi');
    
    if (katSelect) {
        katSelect.innerHTML = '<option value="">Önce otel seçin...</option>';
        katSelect.disabled = true;
    }
    
    if (odaTipiSelect) {
        odaTipiSelect.innerHTML = '<option value="">Önce otel seçin...</option>';
        odaTipiSelect.disabled = true;
    }
    
    // Modal'ı aç
    $('#yeniOdaModal').modal('show');
}

/**
 * Yeni oda form submit
 */
document.addEventListener('DOMContentLoaded', function() {
    const yeniOdaForm = document.getElementById('yeniOdaForm');
    
    if (yeniOdaForm) {
        yeniOdaForm.addEventListener('submit', function(e) {
            e.preventDefault();
            
            const otelId = document.getElementById('yeniOtelId').value;
            const katId = document.getElementById('yeniKatId').value;
            const odaNo = document.getElementById('yeniOdaNo').value;
            const odaTipi = document.getElementById('yeniOdaTipi').value;
            
            // Validasyon
            if (!otelId || otelId === '0') {
                showAlert('yeniOdaAlert', 'Lütfen bir otel seçin!', 'danger');
                return;
            }
            
            if (!katId || katId === '0') {
                showAlert('yeniOdaAlert', 'Lütfen bir kat seçin!', 'danger');
                return;
            }
            
            if (!odaNo || odaNo.trim() === '') {
                showAlert('yeniOdaAlert', 'Lütfen oda numarası girin!', 'danger');
                return;
            }
            
            // Butonu devre dışı bırak
            const kaydetBtn = document.getElementById('yeniOdaKaydetBtn');
            kaydetBtn.disabled = true;
            kaydetBtn.innerHTML = '<span class="spinner-border spinner-border-sm mr-2"></span>Kaydediliyor...';
            
            // AJAX ile oda ekle
            fetch('/api/oda-ekle', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    otel_id: otelId,
                    kat_id: katId,
                    oda_no: odaNo,
                    oda_tipi: odaTipi || null
                })
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    yeniEklenenOdaId = data.oda.id;
                    
                    // QR kod oluştur
                    return fetch(`/admin/oda-qr-olustur/${data.oda.id}`, {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json',
                        }
                    });
                } else {
                    throw new Error(data.error || 'Oda eklenirken hata oluştu');
                }
            })
            .then(response => response.json())
            .then(qrData => {
                if (qrData.success) {
                    // Başarı mesajı göster
                    showAlert('yeniOdaAlert', 'Oda başarıyla eklendi ve QR kod oluşturuldu!', 'success');
                    
                    // QR kod bölümünü göster
                    document.getElementById('yeniOdaQrBolumu').style.display = 'block';
                    document.getElementById('yeniOdaQrImage').src = qrData.qr_kod;
                    document.getElementById('yeniOdaNoGoster').textContent = document.getElementById('yeniOdaNo').value;
                    
                    // Butonları değiştir
                    document.getElementById('yeniOdaKaydetBtn').style.display = 'none';
                    document.getElementById('yeniOdaTamamBtn').style.display = 'inline-flex';
                    
                    // Toastr bildirimi
                    if (typeof toastr !== 'undefined') {
                        toastr.success('Oda başarıyla eklendi!');
                    }
                } else {
                    throw new Error(qrData.error || 'QR kod oluşturulamadı');
                }
            })
            .catch(error => {
                console.error('Hata:', error);
                showAlert('yeniOdaAlert', error.message, 'danger');
                
                // Butonu tekrar aktif et
                kaydetBtn.disabled = false;
                kaydetBtn.innerHTML = '<svg class="h-4 w-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 7H5a2 2 0 00-2 2v9a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2h-3m-1 4l-3 3m0 0l-3-3m3 3V4"></path></svg>Kaydet ve QR Oluştur';
            });
        });
    }
});

/**
 * Yeni oda ekleme tamamlandı - modal'ı kapat ve sayfayı yenile
 */
function yeniOdaTamamla() {
    $('#yeniOdaModal').modal('hide');
    location.reload();
}

/**
 * Yeni eklenen odanın QR kodunu indir
 */
function qrIndirYeni() {
    if (yeniEklenenOdaId) {
        window.location.href = `/admin/oda-qr-indir/${yeniEklenenOdaId}`;
    }
}

/**
 * Yeni eklenen odanın misafir mesajını düzenle
 */
function misafirMesajiDuzenleYeni() {
    if (yeniEklenenOdaId) {
        $('#yeniOdaModal').modal('hide');
        misafirMesajiDuzenle(yeniEklenenOdaId);
    }
}

/**
 * Alert mesajı göster
 */
function showAlert(alertId, message, type) {
    const alertDiv = document.getElementById(alertId);
    const alertClass = type === 'success' ? 'alert-success' : 'alert-danger';
    
    alertDiv.className = `alert ${alertClass} alert-dismissible fade show`;
    alertDiv.innerHTML = `
        ${message}
        <button type="button" class="close" data-dismiss="alert">
            <span>&times;</span>
        </button>
    `;
    alertDiv.style.display = 'block';
    
    // 5 saniye sonra otomatik kapat
    setTimeout(() => {
        alertDiv.style.display = 'none';
    }, 5000);
}


/**
 * Oda düzenleme modal'ını aç
 */
function odaDuzenle(odaId, odaNo, katId, qrVarMi) {
    // Form alanlarını doldur
    document.getElementById('duzenleOdaId').value = odaId;
    document.getElementById('duzenleOdaNo').textContent = odaNo;
    document.getElementById('duzenleOdaNoInput').value = odaNo;
    
    // Alert'i temizle
    document.getElementById('odaDuzenleAlert').style.display = 'none';
    
    // Oda bilgilerini AJAX ile getir
    fetch(`/api/odalar/${odaId}`)
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                const oda = data.oda;
                
                // Otel seç
                document.getElementById('duzenleOtelId').value = oda.otel_id;
                
                // Katları yükle
                yukleKatlar(oda.otel_id, 'duzenleKatId', function() {
                    // Kat seç
                    document.getElementById('duzenleKatId').value = katId;
                });
                
                // Oda tiplerini yükle
                yukleOdaTipleri(oda.otel_id, 'duzenleOdaTipi', function() {
                    // Oda tipi seç
                    if (oda.oda_tipi) {
                        document.getElementById('duzenleOdaTipi').value = oda.oda_tipi;
                    }
                });
                
                // QR kod varsa göster
                if (qrVarMi) {
                    document.getElementById('qrKodBolumu').style.display = 'block';
                    document.getElementById('duzenleQrImage').src = `/admin/oda-qr-goruntule/${odaId}`;
                } else {
                    document.getElementById('qrKodBolumu').style.display = 'none';
                }
            }
        })
        .catch(error => {
            console.error('Hata:', error);
            showAlert('odaDuzenleAlert', 'Oda bilgileri yüklenirken hata oluştu!', 'danger');
        });
    
    // Modal'ı aç
    $('#odaDuzenleModal').modal('show');
}

/**
 * Oda düzenleme form submit
 */
document.addEventListener('DOMContentLoaded', function() {
    const odaDuzenleForm = document.getElementById('odaDuzenleForm');
    
    if (odaDuzenleForm) {
        odaDuzenleForm.addEventListener('submit', function(e) {
            e.preventDefault();
            
            const odaId = document.getElementById('duzenleOdaId').value;
            const otelId = document.getElementById('duzenleOtelId').value;
            const katId = document.getElementById('duzenleKatId').value;
            const odaNo = document.getElementById('duzenleOdaNoInput').value;
            const odaTipi = document.getElementById('duzenleOdaTipi').value;
            
            // Validasyon
            if (!otelId || otelId === '0') {
                showAlert('odaDuzenleAlert', 'Lütfen bir otel seçin!', 'danger');
                return;
            }
            
            if (!katId || katId === '0') {
                showAlert('odaDuzenleAlert', 'Lütfen bir kat seçin!', 'danger');
                return;
            }
            
            if (!odaNo || odaNo.trim() === '') {
                showAlert('odaDuzenleAlert', 'Lütfen oda numarası girin!', 'danger');
                return;
            }
            
            // AJAX ile oda güncelle
            fetch(`/api/oda-guncelle/${odaId}`, {
                method: 'PUT',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    otel_id: otelId,
                    kat_id: katId,
                    oda_no: odaNo,
                    oda_tipi: odaTipi || null
                })
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    showAlert('odaDuzenleAlert', 'Oda başarıyla güncellendi!', 'success');
                    
                    // Toastr bildirimi
                    if (typeof toastr !== 'undefined') {
                        toastr.success('Oda başarıyla güncellendi!');
                    }
                    
                    // 2 saniye sonra sayfayı yenile
                    setTimeout(() => {
                        location.reload();
                    }, 2000);
                } else {
                    throw new Error(data.error || 'Oda güncellenirken hata oluştu');
                }
            })
            .catch(error => {
                console.error('Hata:', error);
                showAlert('odaDuzenleAlert', error.message, 'danger');
            });
        });
    }
});
