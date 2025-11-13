/**
 * Fiyatlandırma ve Karlılık Yönetim Sistemi - JavaScript Modülü
 * 
 * Bu modül fiyatlandırma, kampanya, karlılık hesaplama ve raporlama
 * işlemlerini yönetir. Chart.js ve DataTables entegrasyonu içerir.
 * 
 * @author Minibar Takip Sistemi
 * @version 1.0.0
 */

// ============================================================================
// CSRF Token Yönetimi
// ============================================================================

/**
 * CSRF token'ı meta tag'den alır
 * @returns {string} CSRF token
 */
function getCsrfToken() {
    return document.querySelector('meta[name="csrf-token"]')?.getAttribute('content') || '';
}

/**
 * Fetch istekleri için varsayılan header'lar
 * @returns {Object} Headers objesi
 */
function getDefaultHeaders() {
    return {
        'Content-Type': 'application/json',
        'X-CSRFToken': getCsrfToken()
    };
}

// ============================================================================
// Yardımcı Fonksiyonlar
// ============================================================================

/**
 * Para formatı (Türk Lirası)
 * @param {number} value - Formatlanacak değer
 * @returns {string} Formatlanmış para birimi
 */
function formatCurrency(value) {
    if (value === null || value === undefined) return '₺0,00';
    return new Intl.NumberFormat('tr-TR', {
        style: 'currency',
        currency: 'TRY',
        minimumFractionDigits: 2,
        maximumFractionDigits: 2
    }).format(value);
}

/**
 * Yüzde formatı
 * @param {number} value - Formatlanacak değer
 * @returns {string} Formatlanmış yüzde
 */
function formatPercent(value) {
    if (value === null || value === undefined) return '%0,00';
    return `%${value.toFixed(2).replace('.', ',')}`;
}

/**
 * Tarih formatı (Türkçe)
 * @param {string|Date} date - Formatlanacak tarih
 * @returns {string} Formatlanmış tarih
 */
function formatDate(date) {
    if (!date) return '';
    const d = new Date(date);
    return d.toLocaleDateString('tr-TR', {
        year: 'numeric',
        month: 'long',
        day: 'numeric'
    });
}

/**
 * Başarı mesajı göster (SweetAlert2)
 * @param {string} message - Mesaj metni
 */
function showSuccess(message) {
    Swal.fire({
        icon: 'success',
        title: 'Başarılı',
        text: message,
        confirmButtonText: 'Tamam',
        timer: 3000
    });
}

/**
 * Hata mesajı göster (SweetAlert2)
 * @param {string} message - Hata mesajı
 */
function showError(message) {
    Swal.fire({
        icon: 'error',
        title: 'Hata',
        text: message,
        confirmButtonText: 'Tamam'
    });
}

/**
 * Yükleniyor göstergesi
 * @param {string} message - Yükleme mesajı
 */
function showLoading(message = 'Yükleniyor...') {
    Swal.fire({
        title: message,
        allowOutsideClick: false,
        didOpen: () => {
            Swal.showLoading();
        }
    });
}

/**
 * Yükleniyor göstergesini kapat
 */
function hideLoading() {
    Swal.close();
}

// ============================================================================
// FiyatlandirmaManager Sınıfı
// ============================================================================

class FiyatlandirmaManager {
    constructor() {
        this.apiBase = '/api/v1/fiyat';
        this.init();
    }

    /**
     * Başlangıç işlemleri
     */
    init() {
        console.log('✅ FiyatlandirmaManager başlatıldı');
    }

    /**
     * Dinamik fiyat hesapla
     * @param {number} urunId - Ürün ID
     * @param {number} odaId - Oda ID
     * @param {number} miktar - Miktar
     * @returns {Promise<Object>} Fiyat bilgisi
     */
    async dinamikFiyatHesapla(urunId, odaId, miktar = 1) {
        try {
            showLoading('Fiyat hesaplanıyor...');
            
            const response = await fetch(`${this.apiBase}/dinamik-hesapla`, {
                method: 'POST',
                headers: getDefaultHeaders(),
                body: JSON.stringify({
                    urun_id: urunId,
                    oda_id: odaId,
                    miktar: miktar
                })
            });

            const data = await response.json();
            hideLoading();

            if (!response.ok) {
                throw new Error(data.message || 'Fiyat hesaplama hatası');
            }

            return data;
        } catch (error) {
            hideLoading();
            showError(error.message);
            throw error;
        }
    }

    /**
     * Ürün fiyat bilgilerini getir
     * @param {number} urunId - Ürün ID
     * @returns {Promise<Object>} Fiyat bilgileri
     */
    async getUrunFiyat(urunId) {
        try {
            const response = await fetch(`${this.apiBase}/urun/${urunId}`, {
                headers: getDefaultHeaders()
            });

            const data = await response.json();

            if (!response.ok) {
                throw new Error(data.message || 'Fiyat bilgisi alınamadı');
            }

            return data;
        } catch (error) {
            showError(error.message);
            throw error;
        }
    }

    /**
     * Ürün fiyatını güncelle
     * @param {number} urunId - Ürün ID
     * @param {Object} fiyatData - Fiyat verileri
     * @returns {Promise<Object>} Güncelleme sonucu
     */
    async updateUrunFiyat(urunId, fiyatData) {
        try {
            showLoading('Fiyat güncelleniyor...');

            const response = await fetch(`${this.apiBase}/urun/${urunId}/guncelle`, {
                method: 'POST',
                headers: getDefaultHeaders(),
                body: JSON.stringify(fiyatData)
            });

            const data = await response.json();
            hideLoading();

            if (!response.ok) {
                throw new Error(data.message || 'Fiyat güncellenemedi');
            }

            showSuccess('Fiyat başarıyla güncellendi');
            return data;
        } catch (error) {
            hideLoading();
            showError(error.message);
            throw error;
        }
    }

    /**
     * Kampanya oluştur
     * @param {Object} kampanyaData - Kampanya verileri
     * @returns {Promise<Object>} Oluşturma sonucu
     */
    async createKampanya(kampanyaData) {
        try {
            showLoading('Kampanya oluşturuluyor...');

            const response = await fetch(`${this.apiBase}/kampanya`, {
                method: 'POST',
                headers: getDefaultHeaders(),
                body: JSON.stringify(kampanyaData)
            });

            const data = await response.json();
            hideLoading();

            if (!response.ok) {
                throw new Error(data.message || 'Kampanya oluşturulamadı');
            }

            showSuccess('Kampanya başarıyla oluşturuldu');
            return data;
        } catch (error) {
            hideLoading();
            showError(error.message);
            throw error;
        }
    }

    /**
     * Kampanya güncelle
     * @param {number} kampanyaId - Kampanya ID
     * @param {Object} kampanyaData - Kampanya verileri
     * @returns {Promise<Object>} Güncelleme sonucu
     */
    async updateKampanya(kampanyaId, kampanyaData) {
        try {
            showLoading('Kampanya güncelleniyor...');

            const response = await fetch(`${this.apiBase}/kampanya/${kampanyaId}`, {
                method: 'PUT',
                headers: getDefaultHeaders(),
                body: JSON.stringify(kampanyaData)
            });

            const data = await response.json();
            hideLoading();

            if (!response.ok) {
                throw new Error(data.message || 'Kampanya güncellenemedi');
            }

            showSuccess('Kampanya başarıyla güncellendi');
            return data;
        } catch (error) {
            hideLoading();
            showError(error.message);
            throw error;
        }
    }

    /**
     * Kampanya sil
     * @param {number} kampanyaId - Kampanya ID
     * @returns {Promise<Object>} Silme sonucu
     */
    async deleteKampanya(kampanyaId) {
        try {
            const result = await Swal.fire({
                title: 'Emin misiniz?',
                text: 'Bu kampanya silinecek!',
                icon: 'warning',
                showCancelButton: true,
                confirmButtonText: 'Evet, sil',
                cancelButtonText: 'İptal'
            });

            if (!result.isConfirmed) return null;

            showLoading('Kampanya siliniyor...');

            const response = await fetch(`${this.apiBase}/kampanya/${kampanyaId}`, {
                method: 'DELETE',
                headers: getDefaultHeaders()
            });

            const data = await response.json();
            hideLoading();

            if (!response.ok) {
                throw new Error(data.message || 'Kampanya silinemedi');
            }

            showSuccess('Kampanya başarıyla silindi');
            return data;
        } catch (error) {
            hideLoading();
            showError(error.message);
            throw error;
        }
    }
}

// ============================================================================
// KarlilikManager Sınıfı
// ============================================================================

class KarlilikManager {
    constructor() {
        this.apiBase = '/api/v1/kar';
        this.charts = {};
        this.init();
    }

    /**
     * Başlangıç işlemleri
     */
    init() {
        console.log('✅ KarlilikManager başlatıldı');
    }

    /**
     * Ürün karlılık bilgisi getir
     * @param {number} urunId - Ürün ID
     * @returns {Promise<Object>} Karlılık bilgisi
     */
    async getUrunKarlilik(urunId) {
        try {
            const response = await fetch(`${this.apiBase}/urun/${urunId}`, {
                headers: getDefaultHeaders()
            });

            const data = await response.json();

            if (!response.ok) {
                throw new Error(data.message || 'Karlılık bilgisi alınamadı');
            }

            return data;
        } catch (error) {
            showError(error.message);
            throw error;
        }
    }

    /**
     * Oda karlılık bilgisi getir
     * @param {number} odaId - Oda ID
     * @returns {Promise<Object>} Karlılık bilgisi
     */
    async getOdaKarlilik(odaId) {
        try {
            const response = await fetch(`${this.apiBase}/oda/${odaId}`, {
                headers: getDefaultHeaders()
            });

            const data = await response.json();

            if (!response.ok) {
                throw new Error(data.message || 'Karlılık bilgisi alınamadı');
            }

            return data;
        } catch (error) {
            showError(error.message);
            throw error;
        }
    }

    /**
     * Dönemsel kar raporu getir
     * @param {Object} params - Filtre parametreleri
     * @returns {Promise<Object>} Kar raporu
     */
    async getDonemselKar(params = {}) {
        try {
            showLoading('Rapor hazırlanıyor...');

            const queryString = new URLSearchParams(params).toString();
            const response = await fetch(`${this.apiBase}/donemsel?${queryString}`, {
                headers: getDefaultHeaders()
            });

            const data = await response.json();
            hideLoading();

            if (!response.ok) {
                throw new Error(data.message || 'Rapor alınamadı');
            }

            return data;
        } catch (error) {
            hideLoading();
            showError(error.message);
            throw error;
        }
    }

    /**
     * ROI hesapla
     * @param {number} urunId - Ürün ID
     * @returns {Promise<Object>} ROI bilgisi
     */
    async calculateROI(urunId) {
        try {
            const response = await fetch(`${this.apiBase}/roi/${urunId}`, {
                headers: getDefaultHeaders()
            });

            const data = await response.json();

            if (!response.ok) {
                throw new Error(data.message || 'ROI hesaplanamadı');
            }

            return data;
        } catch (error) {
            showError(error.message);
            throw error;
        }
    }

    /**
     * Trend analizi getir
     * @param {Object} params - Filtre parametreleri
     * @returns {Promise<Object>} Trend verileri
     */
    async getTrendAnalizi(params = {}) {
        try {
            const queryString = new URLSearchParams(params).toString();
            const response = await fetch(`${this.apiBase}/trend?${queryString}`, {
                headers: getDefaultHeaders()
            });

            const data = await response.json();

            if (!response.ok) {
                throw new Error(data.message || 'Trend analizi alınamadı');
            }

            return data;
        } catch (error) {
            showError(error.message);
            throw error;
        }
    }

    /**
     * Kar trend grafiği oluştur (Chart.js)
     * @param {string} canvasId - Canvas element ID
     * @param {Array} data - Grafik verileri
     */
    createKarTrendChart(canvasId, data) {
        try {
            const ctx = document.getElementById(canvasId);
            if (!ctx) {
                console.error(`Canvas element bulunamadı: ${canvasId}`);
                return;
            }

            // Mevcut grafiği temizle
            if (this.charts[canvasId]) {
                this.charts[canvasId].destroy();
            }

            // Yeni grafik oluştur
            this.charts[canvasId] = new Chart(ctx, {
                type: 'line',
                data: {
                    labels: data.map(d => formatDate(d.tarih)),
                    datasets: [{
                        label: 'Kar (₺)',
                        data: data.map(d => d.kar),
                        borderColor: 'rgb(75, 192, 192)',
                        backgroundColor: 'rgba(75, 192, 192, 0.2)',
                        tension: 0.1,
                        fill: true
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        legend: {
                            display: true,
                            position: 'top'
                        },
                        tooltip: {
                            callbacks: {
                                label: function(context) {
                                    return formatCurrency(context.parsed.y);
                                }
                            }
                        }
                    },
                    scales: {
                        y: {
                            beginAtZero: true,
                            ticks: {
                                callback: function(value) {
                                    return formatCurrency(value);
                                }
                            }
                        }
                    }
                }
            });

            console.log(`✅ Kar trend grafiği oluşturuldu: ${canvasId}`);
        } catch (error) {
            console.error('Grafik oluşturma hatası:', error);
            showError('Grafik oluşturulamadı');
        }
    }

    /**
     * Kar marjı grafiği oluştur (Chart.js - Doughnut)
     * @param {string} canvasId - Canvas element ID
     * @param {Object} data - Grafik verileri
     */
    createKarMarjiChart(canvasId, data) {
        try {
            const ctx = document.getElementById(canvasId);
            if (!ctx) {
                console.error(`Canvas element bulunamadı: ${canvasId}`);
                return;
            }

            // Mevcut grafiği temizle
            if (this.charts[canvasId]) {
                this.charts[canvasId].destroy();
            }

            // Yeni grafik oluştur
            this.charts[canvasId] = new Chart(ctx, {
                type: 'doughnut',
                data: {
                    labels: ['Kar', 'Maliyet'],
                    datasets: [{
                        data: [data.kar, data.maliyet],
                        backgroundColor: [
                            'rgba(75, 192, 192, 0.8)',
                            'rgba(255, 99, 132, 0.8)'
                        ],
                        borderColor: [
                            'rgb(75, 192, 192)',
                            'rgb(255, 99, 132)'
                        ],
                        borderWidth: 1
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        legend: {
                            display: true,
                            position: 'bottom'
                        },
                        tooltip: {
                            callbacks: {
                                label: function(context) {
                                    const label = context.label || '';
                                    const value = formatCurrency(context.parsed);
                                    return `${label}: ${value}`;
                                }
                            }
                        }
                    }
                }
            });

            console.log(`✅ Kar marjı grafiği oluşturuldu: ${canvasId}`);
        } catch (error) {
            console.error('Grafik oluşturma hatası:', error);
            showError('Grafik oluşturulamadı');
        }
    }

    /**
     * En karlı ürünler tablosu oluştur (DataTables)
     * @param {string} tableId - Tablo element ID
     * @param {Array} data - Tablo verileri
     */
    createEnKarliUrunlerTable(tableId, data) {
        try {
            const table = $(`#${tableId}`);
            if (!table.length) {
                console.error(`Tablo element bulunamadı: ${tableId}`);
                return;
            }

            // Mevcut DataTable'ı temizle
            if ($.fn.DataTable.isDataTable(`#${tableId}`)) {
                table.DataTable().destroy();
            }

            // Tablo içeriğini temizle
            table.empty();

            // Thead oluştur
            const thead = $('<thead>').append(
                $('<tr>').append(
                    '<th>Ürün</th>',
                    '<th>Satış</th>',
                    '<th>Kar</th>',
                    '<th>Kar Marjı</th>',
                    '<th>ROI</th>'
                )
            );

            // Tbody oluştur
            const tbody = $('<tbody>');
            data.forEach(item => {
                tbody.append(
                    $('<tr>').append(
                        `<td>${item.urun_adi}</td>`,
                        `<td>${formatCurrency(item.satis)}</td>`,
                        `<td>${formatCurrency(item.kar)}</td>`,
                        `<td>${formatPercent(item.kar_marji)}</td>`,
                        `<td>${formatPercent(item.roi)}</td>`
                    )
                );
            });

            table.append(thead, tbody);

            // DataTable başlat
            table.DataTable({
                language: {
                    url: '//cdn.datatables.net/plug-ins/1.13.7/i18n/tr.json'
                },
                order: [[2, 'desc']], // Kar'a göre sırala
                pageLength: 10,
                responsive: true
            });

            console.log(`✅ En karlı ürünler tablosu oluşturuldu: ${tableId}`);
        } catch (error) {
            console.error('Tablo oluşturma hatası:', error);
            showError('Tablo oluşturulamadı');
        }
    }
}

// ============================================================================
// Global Instance'lar
// ============================================================================

let fiyatlandirmaManager;
let karlilikManager;

// Sayfa yüklendiğinde
document.addEventListener('DOMContentLoaded', function() {
    // Manager'ları başlat
    fiyatlandirmaManager = new FiyatlandirmaManager();
    karlilikManager = new KarlilikManager();

    console.log('✅ Fiyatlandırma ve Karlılık sistemi hazır');
});

// ============================================================================
// Export (Modül olarak kullanım için)
// ============================================================================

if (typeof module !== 'undefined' && module.exports) {
    module.exports = {
        FiyatlandirmaManager,
        KarlilikManager,
        formatCurrency,
        formatPercent,
        formatDate
    };
}