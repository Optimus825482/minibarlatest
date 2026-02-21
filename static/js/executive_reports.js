/**
 * Executive Reports - Raporlama Merkezi
 * Merit Royal Hotel Group - 5 Tab Version
 */

// State
let currentTab = "product";
let currentGroupBy = "urun";
let reportChart1 = null;
let reportChart2 = null;
let currentReportData = null;

// Chart.js defaults
Chart.defaults.color = "#94a3b8";
Chart.defaults.borderColor = "rgba(71, 85, 105, 0.2)";
Chart.defaults.font.family = "'Roboto', sans-serif";

const COLORS = [
  "#8b5cf6",
  "#10b981",
  "#3b82f6",
  "#f59e0b",
  "#ef4444",
  "#06b6d4",
  "#ec4899",
  "#f97316",
  "#14b8a6",
  "#6366f1",
  "#84cc16",
  "#e879f9",
  "#22d3ee",
  "#fb923c",
  "#a78bfa",
];

// ==========================================
// INITIALIZATION
// ==========================================
document.addEventListener("DOMContentLoaded", function () {
  // Sidebar'dan gelen tab bilgisi ile başla
  if (typeof INITIAL_TAB !== "undefined" && INITIAL_TAB) {
    switchTab(INITIAL_TAB);
  }
  applyQuickDate();
  loadPersonnelList();
  initComparativeDates();
});

// ==========================================
// TAB SWITCHING (sidebar-driven, no tab buttons)
// ==========================================
function switchTab(tab) {
  currentTab = tab;

  // Filter visibility
  document
    .querySelectorAll(".product-filter")
    .forEach((el) => (el.style.display = tab === "product" ? "" : "none"));
  document
    .querySelectorAll(".personnel-filter")
    .forEach((el) => (el.style.display = tab === "personnel" ? "" : "none"));
  document
    .querySelectorAll(".task-filter")
    .forEach((el) => (el.style.display = tab === "task" ? "" : "none"));
  document.querySelectorAll(".cascading-filter").forEach((el) => {
    if (tab === "comparative" || tab === "task") el.style.display = "none";
  });

  document.getElementById("group-by-section").style.display =
    tab === "product" ? "flex" : "none";
  document.getElementById("comparative-filters").style.display =
    tab === "comparative" ? "" : "none";
  document.getElementById("main-filters").style.display =
    tab === "comparative" ? "none" : "";

  hideResults();
}

// ==========================================
// DATE HELPERS
// ==========================================
function applyQuickDate() {
  const sel = document.getElementById("filter-quick-date").value;
  const today = new Date();
  let start = new Date();
  switch (sel) {
    case "today":
      start = new Date(today);
      break;
    case "week":
      start = new Date(today);
      start.setDate(today.getDate() - today.getDay() + 1);
      break;
    case "month":
      start = new Date(today.getFullYear(), today.getMonth(), 1);
      break;
    case "last30":
      start.setDate(today.getDate() - 30);
      break;
    case "last90":
      start.setDate(today.getDate() - 90);
      break;
    default:
      return;
  }
  document.getElementById("filter-start-date").value = formatDate(start);
  document.getElementById("filter-end-date").value = formatDate(today);
}

function formatDate(d) {
  return d.toISOString().split("T")[0];
}
function onFilterChange() {
  document.getElementById("filter-quick-date").value = "";
}

function initComparativeDates() {
  setCompPreset("month");
}

function setCompPreset(preset) {
  const today = new Date();
  let p1s, p1e, p2s, p2e;
  if (preset === "month") {
    p1s = new Date(today.getFullYear(), today.getMonth(), 1);
    p1e = today;
    p2s = new Date(today.getFullYear(), today.getMonth() - 1, 1);
    p2e = new Date(today.getFullYear(), today.getMonth(), 0);
  } else if (preset === "week") {
    const dow = today.getDay() || 7;
    p1s = new Date(today);
    p1s.setDate(today.getDate() - dow + 1);
    p1e = today;
    p2s = new Date(p1s);
    p2s.setDate(p1s.getDate() - 7);
    p2e = new Date(p1s);
    p2e.setDate(p1s.getDate() - 1);
  } else {
    const q = Math.floor(today.getMonth() / 3);
    p1s = new Date(today.getFullYear(), q * 3, 1);
    p1e = today;
    p2s = new Date(today.getFullYear(), (q - 1) * 3, 1);
    p2e = new Date(today.getFullYear(), q * 3, 0);
  }
  document.getElementById("comp-p1-start").value = formatDate(p1s);
  document.getElementById("comp-p1-end").value = formatDate(p1e);
  document.getElementById("comp-p2-start").value = formatDate(p2s);
  document.getElementById("comp-p2-end").value = formatDate(p2e);
}

// ==========================================
// CASCADING FILTERS
// ==========================================
async function onOtelChange() {
  const otelId = document.getElementById("filter-otel").value;
  const katGroup = document.getElementById("filter-kat-group");
  const odaGroup = document.getElementById("filter-oda-group");
  const katSelect = document.getElementById("filter-kat");
  const odaSelect = document.getElementById("filter-oda");
  katSelect.innerHTML = '<option value="">Tüm Katlar</option>';
  odaSelect.innerHTML = '<option value="">Tüm Odalar</option>';
  odaGroup.style.display = "none";
  if (!otelId) {
    katGroup.style.display = "none";
    return;
  }
  katGroup.style.display = "";
  try {
    const resp = await fetch(
      `/api/executive/reports/filters/floors?otel_id=${otelId}`,
    );
    const data = await resp.json();
    data.forEach((k) => {
      katSelect.innerHTML += `<option value="${k.id}">${k.ad}</option>`;
    });
  } catch (e) {
    console.error("Kat yükleme hatası:", e);
  }
  loadPersonnelList();
  onFilterChange();
}

async function onKatChange() {
  const katId = document.getElementById("filter-kat").value;
  const odaGroup = document.getElementById("filter-oda-group");
  const odaSelect = document.getElementById("filter-oda");
  odaSelect.innerHTML = '<option value="">Tüm Odalar</option>';
  if (!katId) {
    odaGroup.style.display = "none";
    return;
  }
  odaGroup.style.display = "";
  try {
    const resp = await fetch(
      `/api/executive/reports/filters/rooms?kat_id=${katId}`,
    );
    const data = await resp.json();
    data.forEach((o) => {
      odaSelect.innerHTML += `<option value="${o.id}">${o.no}</option>`;
    });
  } catch (e) {
    console.error("Oda yükleme hatası:", e);
  }
  onFilterChange();
}

function onGrupChange() {
  const grupId = document.getElementById("filter-grup").value;
  const urunSelect = document.getElementById("filter-urun");
  urunSelect.innerHTML = '<option value="">Tüm Ürünler</option>';
  const filtered = grupId
    ? ALL_URUNLER.filter((u) => u.grup_id == grupId)
    : ALL_URUNLER;
  filtered.forEach((u) => {
    urunSelect.innerHTML += `<option value="${u.id}" data-grup="${u.grup_id}">${u.ad}</option>`;
  });
  onFilterChange();
}

async function loadPersonnelList() {
  const otelId = document.getElementById("filter-otel").value;
  const select = document.getElementById("filter-personel");
  select.innerHTML = '<option value="">Tüm Personel</option>';
  try {
    let url = "/api/executive/reports/filters/personnel";
    if (otelId) url += `?otel_id=${otelId}`;
    const resp = await fetch(url);
    const data = await resp.json();
    data.forEach((p) => {
      select.innerHTML += `<option value="${p.id}">${p.ad_soyad} (${p.rol})</option>`;
    });
  } catch (e) {
    console.error("Personel yükleme hatası:", e);
  }
}

// ==========================================
// GROUP BY
// ==========================================
function setGroupBy(group) {
  currentGroupBy = group;
  document
    .querySelectorAll(".group-by-btn")
    .forEach((b) => b.classList.remove("active"));
  document.querySelector(`[data-group="${group}"]`).classList.add("active");
  if (currentReportData) loadReport();
}

// ==========================================
// REPORT LOADING (ROUTER)
// ==========================================
async function loadReport() {
  showLoading();
  hideResults();
  const params = getFilterParams();
  try {
    switch (currentTab) {
      case "product":
        await loadProductReport(params);
        break;
      case "personnel":
        await loadPersonnelReport(params);
        break;
      case "hotel":
        await loadHotelReport(params);
        break;
      case "task":
        await loadTaskPerformanceReport(params);
        break;
      case "comparative":
        await loadComparativeReport();
        break;
    }
  } catch (e) {
    console.error("Rapor yükleme hatası:", e);
    showEmpty("Rapor yüklenirken hata oluştu");
  }
  hideLoading();
}

function getFilterParams() {
  return {
    start_date: document.getElementById("filter-start-date").value,
    end_date: document.getElementById("filter-end-date").value,
    otel_id: document.getElementById("filter-otel").value,
    kat_id: document.getElementById("filter-kat").value,
    oda_id: document.getElementById("filter-oda").value,
    urun_id: document.getElementById("filter-urun").value,
    grup_id: document.getElementById("filter-grup").value,
    personel_id: document.getElementById("filter-personel").value,
    gorev_tipi: document.getElementById("filter-gorev-tipi").value,
  };
}

function buildQuery(base, params) {
  const q = new URLSearchParams();
  Object.entries(params).forEach(([k, v]) => {
    if (v) q.append(k, v);
  });
  const qs = q.toString();
  return qs ? `${base}?${qs}` : base;
}

// ==========================================
// PRODUCT CONSUMPTION REPORT
// ==========================================
async function loadProductReport(params) {
  params.group_by = currentGroupBy;
  const url = buildQuery("/api/executive/reports/product-consumption", params);
  const resp = await fetch(url);
  const result = await resp.json();
  if (!result.success || !result.data.length) {
    showEmpty("Bu filtrelere uygun tüketim verisi bulunamadı");
    return;
  }
  currentReportData = result;
  renderProductSummary(result.summary);
  renderProductChart(result.data);
  renderProductTable(result.data);
  const trendUrl = buildQuery("/api/executive/reports/daily-trend", params);
  const trendResp = await fetch(trendUrl);
  const trendResult = await trendResp.json();
  if (trendResult.success && trendResult.data.length)
    renderTrendChart(trendResult.data);
}

function renderProductSummary(s) {
  const section = document.getElementById("summary-section");
  section.style.display = "";
  section.innerHTML = `
    <div class="summary-card"><div class="summary-value text-purple-400">${fmtNum(s.toplam_tuketim)}</div><div class="summary-label">Toplam Tüketim</div></div>
    <div class="summary-card"><div class="summary-value text-blue-400">${fmtNum(s.toplam_islem)}</div><div class="summary-label">İşlem Sayısı</div></div>
    <div class="summary-card"><div class="summary-value text-cyan-400">${fmtNum(s.urun_cesidi)}</div><div class="summary-label">Ürün Çeşidi</div></div>`;
}

function renderProductChart(data) {
  const card = document.getElementById("chart1-card");
  card.style.display = "";
  document.getElementById("chart1-title").innerHTML =
    '<i class="fas fa-chart-bar text-purple-400"></i> Tüketim Dağılımı';
  if (reportChart1) reportChart1.destroy();
  const ctx = document.getElementById("reportChart1").getContext("2d");
  const top = data.slice(0, 15);
  let labels, values;
  if (currentGroupBy === "gun") {
    labels = top.map((d) =>
      d.tarih
        ? new Date(d.tarih).toLocaleDateString("tr-TR", {
            day: "2-digit",
            month: "short",
          })
        : "",
    );
    values = top.map((d) => d.toplam_tuketim);
  } else if (currentGroupBy === "otel") {
    labels = top.map((d) => `${d.otel_adi} - ${d.urun_adi}`);
    values = top.map((d) => d.toplam_tuketim);
  } else if (currentGroupBy === "kat") {
    labels = top.map((d) => `${d.otel_adi} ${d.kat_adi} - ${d.urun_adi}`);
    values = top.map((d) => d.toplam_tuketim);
  } else if (currentGroupBy === "oda") {
    labels = top.map((d) => `${d.oda_no} - ${d.urun_adi}`);
    values = top.map((d) => d.toplam_tuketim);
  } else {
    labels = top.map((d) => d.urun_adi);
    values = top.map((d) => d.toplam_tuketim);
  }
  const isLine = currentGroupBy === "gun";
  if (isLine) {
    reportChart1 = new Chart(ctx, {
      type: "line",
      data: {
        labels,
        datasets: [
          {
            label: "Tüketim",
            data: values,
            backgroundColor: "rgba(139,92,246,0.1)",
            borderColor: "#8b5cf6",
            borderWidth: 2,
            fill: true,
            tension: 0.4,
            pointRadius: 3,
            pointBackgroundColor: "#8b5cf6",
          },
        ],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: { legend: { display: false } },
        scales: {
          y: { beginAtZero: true, grid: { color: "rgba(71,85,105,0.15)" } },
          x: {
            grid: { display: false },
            ticks: { maxRotation: 45, font: { size: 10 } },
          },
        },
      },
    });
  } else {
    // Horizontal bar — tek renk gradient, değer etiketli
    const maxVal = Math.max(...values, 1);
    const barBg = values.map((v) => {
      const ratio = v / maxVal;
      const alpha = 0.4 + ratio * 0.55;
      return `rgba(139, 92, 246, ${alpha.toFixed(2)})`;
    });
    const barBorder = values.map((v) => {
      const ratio = v / maxVal;
      const alpha = 0.6 + ratio * 0.4;
      return `rgba(139, 92, 246, ${alpha.toFixed(2)})`;
    });
    reportChart1 = new Chart(ctx, {
      type: "bar",
      data: {
        labels,
        datasets: [
          {
            label: "Tüketim",
            data: values,
            backgroundColor: barBg,
            borderColor: barBorder,
            borderWidth: 1,
            borderRadius: 6,
            borderSkipped: false,
            barPercentage: 0.7,
            categoryPercentage: 0.85,
          },
        ],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        indexAxis: "y",
        layout: { padding: { right: 40 } },
        plugins: {
          legend: { display: false },
          datalabels: {
            anchor: "end",
            align: "right",
            offset: 6,
            color: "#c4b5fd",
            font: { size: 12, weight: "bold" },
            formatter: (v) => v,
          },
        },
        scales: {
          x: {
            beginAtZero: true,
            grid: { color: "rgba(71,85,105,0.12)" },
            ticks: { color: "#94a3b8", font: { size: 10 }, stepSize: 1 },
          },
          y: {
            grid: { display: false },
            ticks: { color: "#e2e8f0", font: { size: 11 }, mirror: false },
          },
        },
      },
      plugins: [
        {
          id: "customBarLabels",
          afterDatasetsDraw(chart) {
            const { ctx: c, scales } = chart;
            const meta = chart.getDatasetMeta(0);
            c.save();
            c.font = "bold 12px sans-serif";
            c.fillStyle = "#c4b5fd";
            c.textBaseline = "middle";
            meta.data.forEach((bar, i) => {
              const val = chart.data.datasets[0].data[i];
              if (val > 0) {
                c.fillText(val, bar.x + 8, bar.y);
              }
            });
            c.restore();
          },
        },
      ],
    });
  }
}

function renderTrendChart(data) {
  const card = document.getElementById("chart2-card");
  card.style.display = "";
  document.getElementById("chart2-title").innerHTML =
    '<i class="fas fa-chart-line text-emerald-400"></i> Günlük Tüketim Trendi';
  if (reportChart2) reportChart2.destroy();
  const ctx = document.getElementById("reportChart2").getContext("2d");
  reportChart2 = new Chart(ctx, {
    type: "line",
    data: {
      labels: data.map((d) => d.tarih_label),
      datasets: [
        {
          label: "Tüketim",
          data: data.map((d) => d.toplam_tuketim),
          borderColor: "#10b981",
          backgroundColor: "rgba(16,185,129,0.1)",
          borderWidth: 2,
          fill: true,
          tension: 0.4,
          pointRadius: 3,
          pointBackgroundColor: "#10b981",
        },
      ],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      interaction: { mode: "index", intersect: false },
      plugins: {
        legend: { labels: { boxWidth: 12, padding: 10, font: { size: 11 } } },
      },
      scales: {
        y: {
          beginAtZero: true,
          grid: { color: "rgba(71,85,105,0.15)" },
          title: { display: true, text: "Adet", font: { size: 10 } },
        },
        x: { grid: { display: false } },
      },
    },
  });
}

// ==========================================
// PRODUCT TABLE
// ==========================================
function renderProductTable(data) {
  const card = document.getElementById("table-card");
  card.style.display = "";
  document.getElementById("table-title").innerHTML =
    '<i class="fas fa-table text-cyan-400"></i> Ürün Tüketim Detayı';
  document.getElementById("table-count").textContent = `${data.length} kayıt`;

  let cols = [];
  if (currentGroupBy === "urun") {
    cols = [
      { key: "urun_adi", label: "Ürün", cls: "font-medium" },
      {
        key: "toplam_tuketim",
        label: "Tüketim",
        cls: "text-right",
        fmt: "num",
      },
      { key: "islem_sayisi", label: "İşlem", cls: "text-right", fmt: "num" },
      {
        key: "ort_tuketim",
        label: "Ort. Tüketim/İşlem",
        cls: "text-right",
        fmt: "decimal",
      },
    ];
  } else if (currentGroupBy === "otel") {
    cols = [
      { key: "otel_adi", label: "Otel", cls: "font-medium" },
      { key: "urun_adi", label: "Ürün", cls: "" },
      {
        key: "toplam_tuketim",
        label: "Tüketim",
        cls: "text-right",
        fmt: "num",
      },
      { key: "islem_sayisi", label: "İşlem", cls: "text-right", fmt: "num" },
      {
        key: "ort_tuketim",
        label: "Ort. Tüketim/İşlem",
        cls: "text-right",
        fmt: "decimal",
      },
    ];
  } else if (currentGroupBy === "kat") {
    cols = [
      { key: "otel_adi", label: "Otel", cls: "" },
      { key: "kat_adi", label: "Kat", cls: "font-medium" },
      { key: "urun_adi", label: "Ürün", cls: "" },
      {
        key: "toplam_tuketim",
        label: "Tüketim",
        cls: "text-right",
        fmt: "num",
      },
      {
        key: "ort_tuketim",
        label: "Ort. Tüketim/İşlem",
        cls: "text-right",
        fmt: "decimal",
      },
    ];
  } else if (currentGroupBy === "oda") {
    cols = [
      { key: "oda_no", label: "Oda", cls: "font-medium" },
      { key: "urun_adi", label: "Ürün", cls: "" },
      {
        key: "toplam_tuketim",
        label: "Tüketim",
        cls: "text-right",
        fmt: "num",
      },
      {
        key: "ort_tuketim",
        label: "Ort. Tüketim/İşlem",
        cls: "text-right",
        fmt: "decimal",
      },
    ];
  } else {
    // gun
    cols = [
      { key: "tarih", label: "Tarih", cls: "font-medium" },
      {
        key: "toplam_tuketim",
        label: "Tüketim",
        cls: "text-right",
        fmt: "num",
      },
      { key: "islem_sayisi", label: "İşlem", cls: "text-right", fmt: "num" },
      {
        key: "ort_tuketim",
        label: "Ort. Tüketim/İşlem",
        cls: "text-right",
        fmt: "decimal",
      },
    ];
  }

  // İşlem başına ortalama tüketim hesapla
  data.forEach((row) => {
    const tuketim = Number(row.toplam_tuketim) || 0;
    const islem = Number(row.islem_sayisi) || 0;
    row.ort_tuketim = islem > 0 ? tuketim / islem : 0;
  });

  const thead = document.getElementById("report-thead");
  thead.innerHTML =
    "<tr>" +
    cols.map((c) => `<th class="${c.cls || ""}">${c.label}</th>`).join("") +
    "</tr>";

  const tbody = document.getElementById("report-tbody");
  tbody.innerHTML = data
    .map(
      (row) =>
        "<tr>" +
        cols
          .map((c) => {
            let val = row[c.key] ?? "";
            if (c.fmt === "money") val = fmtMoney(val);
            else if (c.fmt === "num") val = fmtNum(val);
            else if (c.fmt === "decimal")
              val = Number(val).toLocaleString("tr-TR", {
                minimumFractionDigits: 2,
                maximumFractionDigits: 2,
              });
            return `<td class="${c.cls || ""}">${val}</td>`;
          })
          .join("") +
        "</tr>",
    )
    .join("");
}

// ==========================================
// PERSONNEL REPORT
// ==========================================
async function loadPersonnelReport(params) {
  const url = buildQuery("/api/executive/reports/personnel", params);
  const resp = await fetch(url);
  const result = await resp.json();
  if (!result.success || !result.data.length) {
    showEmpty("Bu filtrelere uygun personel verisi bulunamadı");
    return;
  }
  currentReportData = result;
  renderPersonnelSummary(result.summary);
  renderPersonnelChart(result.data);
  renderPersonnelTable(result.data);
}

function renderPersonnelSummary(s) {
  const section = document.getElementById("summary-section");
  section.style.display = "";
  section.innerHTML = `
    <div class="summary-card"><div class="summary-value text-purple-400">${fmtNum(s.toplam_personel)}</div><div class="summary-label">Personel</div></div>
    <div class="summary-card"><div class="summary-value text-emerald-400">${fmtNum(s.toplam_kontrol)}</div><div class="summary-label">Toplam Kontrol</div></div>
    <div class="summary-card"><div class="summary-value text-blue-400">${fmtNum(s.toplam_oda)}</div><div class="summary-label">Kontrol Edilen Oda</div></div>
    <div class="summary-card"><div class="summary-value text-amber-400">${s.ort_kontrol_suresi} dk</div><div class="summary-label">Ort. Kontrol Süresi</div></div>`;
}

function renderPersonnelChart(data) {
  const card = document.getElementById("chart1-card");
  card.style.display = "";
  document.getElementById("chart1-title").innerHTML =
    '<i class="fas fa-chart-bar text-purple-400"></i> Personel Kontrol Sayıları';
  if (reportChart1) reportChart1.destroy();
  const ctx = document.getElementById("reportChart1").getContext("2d");
  const top = data.slice(0, 15);
  reportChart1 = new Chart(ctx, {
    type: "bar",
    data: {
      labels: top.map((d) => d.ad_soyad),
      datasets: [
        {
          label: "Kontrol",
          data: top.map((d) => d.toplam_kontrol),
          backgroundColor: "rgba(139,92,246,0.6)",
          borderColor: "#8b5cf6",
          borderWidth: 1,
          borderRadius: 4,
        },
        {
          label: "Tespit Tüketim",
          data: top.map((d) => d.tespit_tuketim),
          backgroundColor: "rgba(16,185,129,0.6)",
          borderColor: "#10b981",
          borderWidth: 1,
          borderRadius: 4,
        },
      ],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: { labels: { boxWidth: 12, padding: 10, font: { size: 11 } } },
      },
      scales: {
        y: { beginAtZero: true, grid: { color: "rgba(71,85,105,0.15)" } },
        x: {
          grid: { display: false },
          ticks: { maxRotation: 45, font: { size: 10 } },
        },
      },
    },
  });

  // Chart 2: Ort kontrol süresi
  const card2 = document.getElementById("chart2-card");
  card2.style.display = "";
  document.getElementById("chart2-title").innerHTML =
    '<i class="fas fa-clock text-amber-400"></i> Ort. Kontrol Süresi (dk)';
  if (reportChart2) reportChart2.destroy();
  const ctx2 = document.getElementById("reportChart2").getContext("2d");
  reportChart2 = new Chart(ctx2, {
    type: "bar",
    data: {
      labels: top.map((d) => d.ad_soyad),
      datasets: [
        {
          label: "Ort. Süre (dk)",
          data: top.map((d) => d.ort_kontrol_suresi_dk),
          backgroundColor: "rgba(245,158,11,0.6)",
          borderColor: "#f59e0b",
          borderWidth: 1,
          borderRadius: 4,
        },
      ],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      indexAxis: "y",
      plugins: { legend: { display: false } },
      scales: {
        x: { beginAtZero: true, grid: { color: "rgba(71,85,105,0.15)" } },
        y: { grid: { display: false }, ticks: { font: { size: 10 } } },
      },
    },
  });
}

function renderPersonnelTable(data) {
  const card = document.getElementById("table-card");
  card.style.display = "";
  document.getElementById("table-title").innerHTML =
    '<i class="fas fa-table text-cyan-400"></i> Personel Detayı';
  document.getElementById("table-count").textContent = `${data.length} kayıt`;

  const thead = document.getElementById("report-thead");
  thead.innerHTML = `<tr>
    <th>Personel</th><th>Rol</th><th>Otel</th>
    <th class="text-right">Kontrol</th><th class="text-right">Oda</th>
    <th class="text-right">Ort. Süre</th><th class="text-right">Eklenen</th>
    <th class="text-right">Tüketim</th>
  </tr>`;

  const tbody = document.getElementById("report-tbody");
  tbody.innerHTML = data
    .map(
      (r) => `<tr>
      <td class="font-medium">${r.ad_soyad}</td>
      <td>${r.rol}</td><td>${r.otel_adi}</td>
      <td class="text-right">${fmtNum(r.toplam_kontrol)}</td>
      <td class="text-right">${fmtNum(r.kontrol_edilen_oda)}</td>
      <td class="text-right">${r.ort_kontrol_suresi_dk} dk</td>
      <td class="text-right">${fmtNum(r.toplam_eklenen)}</td>
      <td class="text-right">${fmtNum(r.tespit_tuketim)}</td>
    </tr>`,
    )
    .join("");
}

// ==========================================
// HOTEL REPORT
// ==========================================
async function loadHotelReport(params) {
  const url = buildQuery("/api/executive/reports/hotel", params);
  const resp = await fetch(url);
  const result = await resp.json();
  if (!result.success || !result.data.length) {
    showEmpty("Bu filtrelere uygun otel verisi bulunamadı");
    return;
  }
  currentReportData = result;
  renderHotelSummary(result.summary);
  renderHotelChart(result.data);
  renderHotelTable(result.data);
}

function renderHotelSummary(s) {
  const section = document.getElementById("summary-section");
  section.style.display = "";
  section.innerHTML = `
    <div class="summary-card"><div class="summary-value text-purple-400">${fmtNum(s.toplam_otel)}</div><div class="summary-label">Otel</div></div>
    <div class="summary-card"><div class="summary-value text-emerald-400">${fmtNum(s.toplam_tuketim)}</div><div class="summary-label">Toplam Tüketim</div></div>
    <div class="summary-card"><div class="summary-value text-blue-400">${fmtNum(s.toplam_kontrol)}</div><div class="summary-label">Toplam Kontrol</div></div>`;
}

function renderHotelChart(data) {
  const card = document.getElementById("chart1-card");
  card.style.display = "";
  document.getElementById("chart1-title").innerHTML =
    '<i class="fas fa-hotel text-purple-400"></i> Otel Karşılaştırması';
  if (reportChart1) reportChart1.destroy();
  const ctx = document.getElementById("reportChart1").getContext("2d");
  reportChart1 = new Chart(ctx, {
    type: "bar",
    data: {
      labels: data.map((d) => d.otel_adi),
      datasets: [
        {
          label: "Tüketim",
          data: data.map((d) => d.toplam_tuketim),
          backgroundColor: "rgba(139,92,246,0.6)",
          borderColor: "#8b5cf6",
          borderWidth: 1,
          borderRadius: 4,
        },
        {
          label: "Kontrol",
          data: data.map((d) => d.toplam_kontrol),
          backgroundColor: "rgba(16,185,129,0.6)",
          borderColor: "#10b981",
          borderWidth: 1,
          borderRadius: 4,
        },
        {
          label: "Görev",
          data: data.map((d) => d.toplam_gorev),
          backgroundColor: "rgba(59,130,246,0.6)",
          borderColor: "#3b82f6",
          borderWidth: 1,
          borderRadius: 4,
        },
      ],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: { labels: { boxWidth: 12, padding: 10, font: { size: 11 } } },
      },
      scales: {
        y: { beginAtZero: true, grid: { color: "rgba(71,85,105,0.15)" } },
        x: { grid: { display: false } },
      },
    },
  });

  // Chart 2: Görev tamamlanma oranı
  const card2 = document.getElementById("chart2-card");
  card2.style.display = "";
  document.getElementById("chart2-title").innerHTML =
    '<i class="fas fa-check-circle text-emerald-400"></i> Görev Tamamlanma Oranı (%)';
  if (reportChart2) reportChart2.destroy();
  const ctx2 = document.getElementById("reportChart2").getContext("2d");
  reportChart2 = new Chart(ctx2, {
    type: "doughnut",
    data: {
      labels: data.map((d) => d.otel_adi),
      datasets: [
        {
          data: data.map((d) => d.gorev_oran),
          backgroundColor: COLORS.slice(0, data.length),
          borderColor: "#1e293b",
          borderWidth: 2,
        },
      ],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: {
          position: "right",
          labels: { boxWidth: 12, padding: 8, font: { size: 11 } },
        },
        tooltip: {
          callbacks: { label: (ctx) => `${ctx.label}: %${ctx.parsed}` },
        },
      },
    },
  });
}

function renderHotelTable(data) {
  const card = document.getElementById("table-card");
  card.style.display = "";
  document.getElementById("table-title").innerHTML =
    '<i class="fas fa-table text-cyan-400"></i> Otel Detayı';
  document.getElementById("table-count").textContent = `${data.length} kayıt`;

  const thead = document.getElementById("report-thead");
  thead.innerHTML = `<tr>
    <th>Otel</th><th class="text-right">Oda</th><th class="text-right">Tüketim</th>
    <th class="text-right">Kontrol</th>
    <th class="text-right">Personel</th><th class="text-right">Görev</th>
    <th class="text-right">Tamamlanma</th><th>Top Ürünler</th>
  </tr>`;

  const tbody = document.getElementById("report-tbody");
  tbody.innerHTML = data
    .map(
      (r) => `<tr>
      <td class="font-medium">${r.otel_adi}</td>
      <td class="text-right">${fmtNum(r.oda_sayisi)}</td>
      <td class="text-right">${fmtNum(r.toplam_tuketim)}</td>
      <td class="text-right">${fmtNum(r.toplam_kontrol)}</td>
      <td class="text-right">${fmtNum(r.aktif_personel)}</td>
      <td class="text-right">${fmtNum(r.toplam_gorev)}</td>
      <td class="text-right">%${r.gorev_oran}</td>
      <td>${r.top_urunler.map((u) => `${u.urun} (${u.miktar})`).join(", ")}</td>
    </tr>`,
    )
    .join("");
}

// ==========================================
// TASK PERFORMANCE REPORT
// ==========================================
async function loadTaskPerformanceReport(params) {
  const url = buildQuery("/api/executive/reports/task-performance", params);
  const resp = await fetch(url);
  const result = await resp.json();
  if (!result.success || !result.tip_data.length) {
    showEmpty("Bu filtrelere uygun görev verisi bulunamadı");
    return;
  }
  currentReportData = result;
  renderTaskSummary(result.summary);
  renderTaskCharts(result.tip_data, result.trend_data);
  renderTaskTable(result.personel_data);
}

function renderTaskSummary(s) {
  const section = document.getElementById("summary-section");
  section.style.display = "";
  section.innerHTML = `
    <div class="summary-card"><div class="summary-value text-purple-400">${fmtNum(s.toplam_oda_gorev)}</div><div class="summary-label">Toplam Oda Görevi</div></div>
    <div class="summary-card"><div class="summary-value text-emerald-400">${fmtNum(s.toplam_tamamlanan)}</div><div class="summary-label">Tamamlanan</div></div>
    <div class="summary-card"><div class="summary-value text-amber-400">%${s.genel_oran}</div><div class="summary-label">Tamamlanma Oranı</div></div>
    <div class="summary-card"><div class="summary-value text-red-400">${fmtNum(s.toplam_dnd)}</div><div class="summary-label">Toplam DND</div></div>
    <div class="summary-card"><div class="summary-value text-blue-400">${fmtNum(s.aktif_personel)}</div><div class="summary-label">Aktif Personel</div></div>`;
}

function renderTaskCharts(tipData, trendData) {
  // Chart 1: Görev tipi bazlı tamamlanma oranı
  const card = document.getElementById("chart1-card");
  card.style.display = "";
  document.getElementById("chart1-title").innerHTML =
    '<i class="fas fa-tasks text-purple-400"></i> Görev Tipi Tamamlanma Oranları';
  if (reportChart1) reportChart1.destroy();
  const ctx = document.getElementById("reportChart1").getContext("2d");
  reportChart1 = new Chart(ctx, {
    type: "bar",
    data: {
      labels: tipData.map((d) => d.gorev_tipi_label),
      datasets: [
        {
          label: "Tamamlanma %",
          data: tipData.map((d) => d.tamamlanma_orani),
          backgroundColor: "rgba(16,185,129,0.6)",
          borderColor: "#10b981",
          borderWidth: 1,
          borderRadius: 4,
        },
        {
          label: "DND %",
          data: tipData.map((d) => d.dnd_orani),
          backgroundColor: "rgba(239,68,68,0.6)",
          borderColor: "#ef4444",
          borderWidth: 1,
          borderRadius: 4,
        },
      ],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: { labels: { boxWidth: 12, padding: 10, font: { size: 11 } } },
        tooltip: {
          callbacks: {
            label: (ctx) => `${ctx.dataset.label}: %${ctx.parsed.y}`,
          },
        },
      },
      scales: {
        y: {
          beginAtZero: true,
          max: 100,
          grid: { color: "rgba(71,85,105,0.15)" },
          ticks: { callback: (v) => v + "%" },
        },
        x: {
          grid: { display: false },
          ticks: { maxRotation: 45, font: { size: 10 } },
        },
      },
    },
  });

  // Chart 2: Günlük trend
  if (trendData && trendData.length) {
    const card2 = document.getElementById("chart2-card");
    card2.style.display = "";
    document.getElementById("chart2-title").innerHTML =
      '<i class="fas fa-chart-line text-emerald-400"></i> Günlük Görev Trendi';
    if (reportChart2) reportChart2.destroy();
    const ctx2 = document.getElementById("reportChart2").getContext("2d");
    reportChart2 = new Chart(ctx2, {
      type: "line",
      data: {
        labels: trendData.map((d) => d.tarih_label),
        datasets: [
          {
            label: "Tamamlanma %",
            data: trendData.map((d) => d.oran),
            borderColor: "#10b981",
            backgroundColor: "rgba(16,185,129,0.1)",
            borderWidth: 2,
            fill: true,
            tension: 0.4,
            pointRadius: 3,
            pointBackgroundColor: "#10b981",
            yAxisID: "y",
          },
          {
            label: "DND",
            data: trendData.map((d) => d.dnd),
            borderColor: "#ef4444",
            backgroundColor: "rgba(239,68,68,0.05)",
            borderWidth: 2,
            fill: false,
            tension: 0.4,
            pointRadius: 2,
            borderDash: [5, 5],
            yAxisID: "y1",
          },
        ],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        interaction: { mode: "index", intersect: false },
        plugins: {
          legend: { labels: { boxWidth: 12, padding: 10, font: { size: 11 } } },
        },
        scales: {
          y: {
            beginAtZero: true,
            position: "left",
            grid: { color: "rgba(71,85,105,0.15)" },
            title: { display: true, text: "%", font: { size: 10 } },
          },
          y1: {
            beginAtZero: true,
            position: "right",
            grid: { drawOnChartArea: false },
            title: { display: true, text: "DND", font: { size: 10 } },
          },
          x: { grid: { display: false } },
        },
      },
    });
  }
}

function renderTaskTable(personelData) {
  const card = document.getElementById("table-card");
  card.style.display = "";
  document.getElementById("table-title").innerHTML =
    '<i class="fas fa-table text-cyan-400"></i> Personel Görev Performansı';
  document.getElementById("table-count").textContent =
    `${personelData.length} kayıt`;

  const thead = document.getElementById("report-thead");
  thead.innerHTML = `<tr>
    <th>Personel</th><th class="text-right">Görev</th>
    <th class="text-right">Oda</th><th class="text-right">Tamamlanan</th>
    <th class="text-right">Oran</th><th class="text-right">DND</th>
  </tr>`;

  const tbody = document.getElementById("report-tbody");
  tbody.innerHTML = personelData
    .map(
      (r) => `<tr>
      <td class="font-medium">${r.ad_soyad}</td>
      <td class="text-right">${fmtNum(r.gorev_sayisi)}</td>
      <td class="text-right">${fmtNum(r.toplam_oda)}</td>
      <td class="text-right">${fmtNum(r.tamamlanan)}</td>
      <td class="text-right">%${r.tamamlanma_orani}</td>
      <td class="text-right">${fmtNum(r.toplam_dnd)}</td>
    </tr>`,
    )
    .join("");
}

// ==========================================
// COMPARATIVE REPORT
// ==========================================
async function loadComparativeReport() {
  const params = {
    p1_start: document.getElementById("comp-p1-start").value,
    p1_end: document.getElementById("comp-p1-end").value,
    p2_start: document.getElementById("comp-p2-start").value,
    p2_end: document.getElementById("comp-p2-end").value,
    otel_id: document.getElementById("filter-otel").value,
  };
  const url = buildQuery("/api/executive/reports/comparative", params);
  const resp = await fetch(url);
  const result = await resp.json();
  if (!result.success) {
    showEmpty("Karşılaştırma verisi yüklenemedi");
    return;
  }
  currentReportData = result;
  renderComparativeCards(result.comparison, result.periods);
  if (result.otel_data && result.otel_data.length) {
    renderComparativeChart(result.otel_data);
  }
}

function renderComparativeCards(comp, periods) {
  const container = document.getElementById("comparative-cards");
  container.style.display = "";

  const p1Label = `${formatTR(periods.period1.start)} - ${formatTR(periods.period1.end)}`;
  const p2Label = `${formatTR(periods.period2.start)} - ${formatTR(periods.period2.end)}`;

  const metrics = [
    {
      key: "tuketim",
      label: "Toplam Tüketim",
      fmt: "num",
      icon: "wine-bottle",
      color: "purple",
    },
    {
      key: "tuketim_oda",
      label: "Tüketim Yapan Oda",
      fmt: "num",
      icon: "door-open",
      color: "blue",
    },
    {
      key: "kontrol",
      label: "Toplam Kontrol",
      fmt: "num",
      icon: "clipboard-check",
      color: "cyan",
    },
    {
      key: "kontrol_oda",
      label: "Kontrol Edilen Oda",
      fmt: "num",
      icon: "bed",
      color: "amber",
    },
    {
      key: "ort_kontrol_sure_dk",
      label: "Ort. Kontrol Süresi (dk)",
      fmt: "dec",
      icon: "clock",
      color: "orange",
    },
    {
      key: "gorev_toplam",
      label: "Toplam Görev",
      fmt: "num",
      icon: "tasks",
      color: "indigo",
    },
    {
      key: "gorev_oran",
      label: "Görev Tamamlanma %",
      fmt: "pct",
      icon: "check-circle",
      color: "green",
    },
    {
      key: "toplam_dnd",
      label: "Toplam DND",
      fmt: "num",
      icon: "do-not-disturb",
      color: "red",
    },
  ];

  let html = `<div class="comp-grid">`;
  for (const m of metrics) {
    const c = comp[m.key];
    if (!c) continue;
    const v1 =
      m.fmt === "money"
        ? fmtMoney(c.period1)
        : m.fmt === "pct"
          ? `%${c.period1}`
          : m.fmt === "dec"
            ? c.period1
            : fmtNum(c.period1);
    const v2 =
      m.fmt === "money"
        ? fmtMoney(c.period2)
        : m.fmt === "pct"
          ? `%${c.period2}`
          : m.fmt === "dec"
            ? c.period2
            : fmtNum(c.period2);
    const deg = c.degisim;
    const cls = deg > 0 ? "positive" : deg < 0 ? "negative" : "neutral";
    const arrow = deg > 0 ? "↑" : deg < 0 ? "↓" : "→";
    html += `
      <div class="comp-metric-card">
        <div class="comp-metric-label"><i class="fas fa-${m.icon} text-${m.color}-400"></i> ${m.label}</div>
        <div class="comp-metric-values">
          <div class="comp-val"><div class="comp-val-num">${v1}</div><div class="comp-val-label">Dönem 1</div></div>
          <div class="comp-change"><div class="comp-change-val ${cls}"><span class="comp-arrow">${arrow}</span> %${Math.abs(deg)}</div></div>
          <div class="comp-val"><div class="comp-val-num">${v2}</div><div class="comp-val-label">Dönem 2</div></div>
        </div>
      </div>`;
  }
  html += `</div>`;
  container.innerHTML = html;
}

function formatTR(dateStr) {
  if (!dateStr) return "";
  const d = new Date(dateStr);
  return d.toLocaleDateString("tr-TR", {
    day: "2-digit",
    month: "short",
    year: "numeric",
  });
}

function renderComparativeChart(otelData) {
  const card = document.getElementById("chart1-card");
  card.style.display = "";
  document.getElementById("chart1-title").innerHTML =
    '<i class="fas fa-balance-scale text-purple-400"></i> Otel Bazlı Dönem Karşılaştırması';
  if (reportChart1) reportChart1.destroy();
  const ctx = document.getElementById("reportChart1").getContext("2d");
  reportChart1 = new Chart(ctx, {
    type: "bar",
    data: {
      labels: otelData.map((d) => d.otel_adi),
      datasets: [
        {
          label: "Dönem 1",
          data: otelData.map((d) => d.period1_tuketim),
          backgroundColor: "rgba(139,92,246,0.6)",
          borderColor: "#8b5cf6",
          borderWidth: 1,
          borderRadius: 4,
        },
        {
          label: "Dönem 2",
          data: otelData.map((d) => d.period2_tuketim),
          backgroundColor: "rgba(100,116,139,0.4)",
          borderColor: "#64748b",
          borderWidth: 1,
          borderRadius: 4,
        },
      ],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: { labels: { boxWidth: 12, padding: 10, font: { size: 11 } } },
      },
      scales: {
        y: { beginAtZero: true, grid: { color: "rgba(71,85,105,0.15)" } },
        x: { grid: { display: false } },
      },
    },
  });

  // Chart 2 hide for comparative
  document.getElementById("chart2-card").style.display = "none";
}

// ==========================================
// EXPORT & PRINT
// ==========================================
function exportExcel() {
  if (!currentReportData) {
    alert("Önce rapor oluşturun");
    return;
  }
  let rows = [];
  let filename = "rapor";

  switch (currentTab) {
    case "product":
      filename = "urun_tuketim";
      rows = currentReportData.data.map((r) => ({
        Ürün: r.urun_adi || "",
        Otel: r.otel_adi || "",
        Kat: r.kat_adi || "",
        Oda: r.oda_no || "",
        Tüketim: r.toplam_tuketim,
        İşlem: r.islem_sayisi || "",
      }));
      break;
    case "personnel":
      filename = "personel";
      rows = currentReportData.data.map((r) => ({
        Personel: r.ad_soyad,
        Rol: r.rol,
        Otel: r.otel_adi,
        Kontrol: r.toplam_kontrol,
        Oda: r.kontrol_edilen_oda,
        "Ort. Süre (dk)": r.ort_kontrol_suresi_dk,
        Eklenen: r.toplam_eklenen,
        Tüketim: r.tespit_tuketim,
      }));
      break;
    case "hotel":
      filename = "otel";
      rows = currentReportData.data.map((r) => ({
        Otel: r.otel_adi,
        Oda: r.oda_sayisi,
        Tüketim: r.toplam_tuketim,
        Kontrol: r.toplam_kontrol,
        Personel: r.aktif_personel,
        Görev: r.toplam_gorev,
        "Tamamlanma %": r.gorev_oran,
      }));
      break;
    case "task":
      filename = "gorev_performans";
      rows = currentReportData.personel_data.map((r) => ({
        Personel: r.ad_soyad,
        Görev: r.gorev_sayisi,
        Oda: r.toplam_oda,
        Tamamlanan: r.tamamlanan,
        "Oran %": r.tamamlanma_orani,
        DND: r.toplam_dnd,
      }));
      break;
    case "comparative":
      filename = "karsilastirma";
      if (currentReportData.comparison) {
        rows = Object.entries(currentReportData.comparison).map(
          ([key, val]) => ({
            Metrik: key,
            "Dönem 1": val.period1,
            "Dönem 2": val.period2,
            "Değişim %": val.degisim,
          }),
        );
      }
      break;
  }

  if (!rows.length) {
    alert("Dışa aktarılacak veri yok");
    return;
  }

  const headers = Object.keys(rows[0]);
  const csv = [
    headers.join(";"),
    ...rows.map((r) => headers.map((h) => `"${r[h] ?? ""}"`).join(";")),
  ].join("\n");

  const BOM = "\uFEFF";
  const blob = new Blob([BOM + csv], { type: "text/csv;charset=utf-8;" });
  const link = document.createElement("a");
  link.href = URL.createObjectURL(blob);
  link.download = `${filename}_${formatDate(new Date())}.csv`;
  link.click();
  URL.revokeObjectURL(link.href);
}

function printReport() {
  const startEl = document.getElementById("filter-start-date");
  const endEl = document.getElementById("filter-end-date");
  const printDate = document.getElementById("print-date-range");
  const printTitle = document.getElementById("print-report-title");
  const printFooterTitle = document.getElementById("print-footer-title");
  const genDate = document.getElementById("print-generated-date");

  // Dinamik başlık
  const pageTitle = document.getElementById("er-page-title");
  if (pageTitle && printTitle) printTitle.textContent = pageTitle.textContent;
  if (pageTitle && printFooterTitle)
    printFooterTitle.textContent = pageTitle.textContent;
  if (genDate) genDate.textContent = new Date().toLocaleString("tr-TR");

  if (currentTab === "comparative") {
    const p1s = document.getElementById("comp-p1-start").value;
    const p1e = document.getElementById("comp-p1-end").value;
    const p2s = document.getElementById("comp-p2-start").value;
    const p2e = document.getElementById("comp-p2-end").value;
    printDate.textContent = `Dönem 1: ${p1s} — ${p1e} | Dönem 2: ${p2s} — ${p2e}`;
  } else {
    printDate.textContent = `${startEl.value} — ${endEl.value}`;
  }
  window.print();
}

// ==========================================
// PDF EXPORT
// ==========================================
function exportPDF() {
  if (!currentReportData) {
    alert("Önce rapor oluşturun");
    return;
  }

  const pdfOverlay = document.getElementById("pdf-loading");
  pdfOverlay.style.display = "flex";

  // Başlık bilgisi
  const pageTitle = document.getElementById("er-page-title");
  const title = pageTitle ? pageTitle.textContent.trim() : "Rapor";

  // Tarih aralığı
  let dateRange = "";
  if (currentTab === "comparative") {
    const p1s = document.getElementById("comp-p1-start").value;
    const p1e = document.getElementById("comp-p1-end").value;
    const p2s = document.getElementById("comp-p2-start").value;
    const p2e = document.getElementById("comp-p2-end").value;
    dateRange = `Dönem 1: ${p1s} — ${p1e} | Dönem 2: ${p2s} — ${p2e}`;
  } else {
    const startEl = document.getElementById("filter-start-date");
    const endEl = document.getElementById("filter-end-date");
    dateRange = `${startEl.value} — ${endEl.value}`;
  }

  // Özet kartları
  const summary = [];
  const summarySection = document.getElementById("summary-section");
  if (summarySection && summarySection.style.display !== "none") {
    summarySection.querySelectorAll(".summary-card").forEach((card) => {
      const valEl = card.querySelector(".summary-value");
      const lblEl = card.querySelector(".summary-label");
      if (valEl && lblEl) {
        summary.push({
          value: valEl.textContent.trim(),
          label: lblEl.textContent.trim(),
        });
      }
    });
  }

  // Tablo verileri
  const tableHeaders = [];
  const tableRows = [];
  const thead = document.getElementById("report-thead");
  const tbody = document.getElementById("report-tbody");

  if (thead) {
    thead.querySelectorAll("th").forEach((th) => {
      tableHeaders.push(th.textContent.trim());
    });
  }
  if (tbody) {
    tbody.querySelectorAll("tr").forEach((tr) => {
      const row = [];
      tr.querySelectorAll("td").forEach((td) => {
        row.push(td.textContent.trim());
      });
      if (row.length > 0) tableRows.push(row);
    });
  }

  const payload = {
    report_type: currentTab,
    title: title,
    date_range: dateRange,
    summary: summary,
    table_headers: tableHeaders,
    table_rows: tableRows,
  };

  const csrfToken = document
    .querySelector('meta[name="csrf-token"]')
    .getAttribute("content");

  fetch("/api/executive/reports/pdf", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "X-CSRFToken": csrfToken,
    },
    body: JSON.stringify(payload),
  })
    .then((resp) => {
      if (!resp.ok) throw new Error("PDF oluşturulamadı");
      return resp.blob();
    })
    .then((blob) => {
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `${title.replace(/\s+/g, "_")}_${formatDate(new Date())}.pdf`;
      a.click();
      URL.revokeObjectURL(url);
    })
    .catch((err) => {
      console.error("PDF hatası:", err);
      alert("PDF oluşturulurken hata oluştu: " + err.message);
    })
    .finally(() => {
      pdfOverlay.style.display = "none";
    });
}

// ==========================================
// UI HELPERS
// ==========================================
function showLoading() {
  document.getElementById("report-loading").style.display = "";
  document.getElementById("empty-state").style.display = "none";
}

function hideLoading() {
  document.getElementById("report-loading").style.display = "none";
}

function hideResults() {
  document.getElementById("summary-section").style.display = "none";
  document.getElementById("chart1-card").style.display = "none";
  document.getElementById("chart2-card").style.display = "none";
  document.getElementById("table-card").style.display = "none";
  document.getElementById("comparative-cards").style.display = "none";
  document.getElementById("empty-state").style.display = "none";
  if (reportChart1) {
    reportChart1.destroy();
    reportChart1 = null;
  }
  if (reportChart2) {
    reportChart2.destroy();
    reportChart2 = null;
  }
}

function showEmpty(msg) {
  const el = document.getElementById("empty-state");
  el.style.display = "";
  el.querySelector("p").textContent = msg || "Veri bulunamadı";
}

// ==========================================
// FORMATTERS
// ==========================================
function fmtNum(n) {
  if (n == null || isNaN(n)) return "0";
  return Number(n).toLocaleString("tr-TR");
}

function fmtMoney(n) {
  if (n == null || isNaN(n)) return "₺0";
  return (
    "₺" +
    Number(n).toLocaleString("tr-TR", {
      minimumFractionDigits: 2,
      maximumFractionDigits: 2,
    })
  );
}
