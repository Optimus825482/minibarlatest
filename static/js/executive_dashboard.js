/**
 * Executive Dashboard - Global Period Management & Charts
 */

// Chart instances
let consumptionChart = null;
let roomControlChart = null;
let topProductsChart = null;
let hourlyChart = null;

// Current period
let currentPeriod = "today";

// Feed polling
let feedInterval = null;

// Period labels
const periodLabels = {
  today: "Bugün",
  yesterday: "Dün",
  this_week: "Bu Hafta",
  last_week: "Geçen Hafta",
  this_month: "Bu Ay",
  last_month: "Geçen Ay",
  all: "Tüm Zamanlar",
};

// Chart.js defaults
Chart.defaults.color = "#94a3b8";
Chart.defaults.borderColor = "rgba(71, 85, 105, 0.2)";
Chart.defaults.font.family = "'Roboto', sans-serif";

// ---- INITIALIZATION ----
document.addEventListener("DOMContentLoaded", function () {
  // Detect initial period from active button
  const activeBtn = document.querySelector(".exec-time-btn.active");
  if (activeBtn) currentPeriod = activeBtn.dataset.period;

  updateClock();
  setInterval(updateClock, 1000);
  updatePeriodLabel();

  // Bind time selector buttons
  document.querySelectorAll(".exec-time-btn").forEach((btn) => {
    btn.addEventListener("click", function () {
      changePeriod(this.dataset.period);
    });
  });

  // Load all data
  loadAllCharts();
  loadActivityFeed();

  // Auto-refresh feed every 15 seconds
  feedInterval = setInterval(loadActivityFeed, 15000);
});

function updateClock() {
  const now = new Date();
  const opts = {
    timeZone: "Europe/Nicosia",
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
    hour12: false,
  };
  const el = document.getElementById("exec-clock");
  if (el) el.textContent = now.toLocaleString("tr-TR", opts);
}

function updatePeriodLabel() {
  const el = document.getElementById("period-text");
  if (el) el.textContent = periodLabels[currentPeriod] || currentPeriod;
}

// ---- PERIOD MANAGEMENT ----
function changePeriod(period) {
  currentPeriod = period;

  // Update button states
  document.querySelectorAll(".exec-time-btn").forEach((btn) => {
    btn.classList.toggle("active", btn.dataset.period === period);
  });

  updatePeriodLabel();
  loadAllCharts();
  loadKPI();
}

// ---- API HELPER ----
async function fetchAPI(url) {
  try {
    const resp = await fetch(url);
    if (!resp.ok) throw new Error("HTTP " + resp.status);
    const data = await resp.json();
    if (!data.success) throw new Error(data.error || "API error");
    return data.data;
  } catch (e) {
    console.error("API Error:", url, e);
    return null;
  }
}

// ---- KPI LOADER ----
async function loadKPI() {
  const data = await fetchAPI("/api/executive/kpi?period=" + currentPeriod);
  if (!data) return;

  animateValue("kpi-kontrol", data.bugun_kontrol);
  animateValue("kpi-tuketim", data.bugun_tuketim);
  animateValue("kpi-islem", data.bugun_islem);
  animateValue("kpi-kullanici", data.aktif_kullanici);

  const gorevEl = document.getElementById("kpi-gorev");
  if (gorevEl) gorevEl.textContent = "%" + data.gorev_oran;

  const gorevSub = document.getElementById("kpi-gorev-sub");
  if (gorevSub)
    gorevSub.textContent = data.tamamlanan_gorev + "/" + data.toplam_gorev;
}

function animateValue(id, target) {
  const el = document.getElementById(id);
  if (!el) return;
  const current = parseInt(el.textContent.replace(/[^0-9]/g, "")) || 0;
  if (current === target) {
    el.textContent = target;
    return;
  }

  const duration = 400;
  const start = performance.now();

  function step(timestamp) {
    const progress = Math.min((timestamp - start) / duration, 1);
    const value = Math.round(current + (target - current) * progress);
    el.textContent = value;
    if (progress < 1) requestAnimationFrame(step);
  }
  requestAnimationFrame(step);
}

// ---- CHART LOADERS ----
function loadAllCharts() {
  loadConsumptionTrends();
  loadRoomControls();
  loadTopProducts();
  loadHourlyActivity();
  loadHotelComparison();
  loadTaskCompletion();
}

async function loadConsumptionTrends() {
  const data = await fetchAPI(
    "/api/executive/consumption-trends?period=" + currentPeriod,
  );
  if (!data) return;

  const ctx = document.getElementById("consumptionChart")?.getContext("2d");
  if (!ctx) return;
  if (consumptionChart) consumptionChart.destroy();

  consumptionChart = new Chart(ctx, {
    type: "line",
    data: {
      labels: data.labels,
      datasets: [
        {
          label: "Tüketim",
          data: data.values,
          borderColor: "#10b981",
          backgroundColor: "rgba(16, 185, 129, 0.1)",
          borderWidth: 2,
          fill: true,
          tension: 0.4,
          pointRadius: data.values.length > 30 ? 0 : 3,
          pointBackgroundColor: "#10b981",
        },
      ],
    },
    options: chartOptions("Adet"),
  });
}

async function loadRoomControls() {
  const data = await fetchAPI(
    "/api/executive/room-controls?period=" + currentPeriod,
  );
  if (!data) return;

  const ctx = document.getElementById("roomControlChart")?.getContext("2d");
  if (!ctx) return;
  if (roomControlChart) roomControlChart.destroy();

  roomControlChart = new Chart(ctx, {
    type: "bar",
    data: {
      labels: data.labels,
      datasets: [
        {
          label: "Kontrol Edilen Oda",
          data: data.values,
          backgroundColor: "rgba(59, 130, 246, 0.6)",
          borderColor: "#3b82f6",
          borderWidth: 1,
          borderRadius: 4,
        },
      ],
    },
    options: chartOptions("Oda"),
  });
}

async function loadTopProducts() {
  const data = await fetchAPI(
    "/api/executive/top-products?period=" + currentPeriod,
  );
  if (!data || !data.labels.length) {
    const ctx = document.getElementById("topProductsChart")?.getContext("2d");
    if (topProductsChart) topProductsChart.destroy();
    if (ctx) {
      ctx.font = "14px Roboto";
      ctx.fillStyle = "#64748b";
      ctx.textAlign = "center";
      ctx.fillText(
        "Bu dönemde veri yok",
        ctx.canvas.width / 2,
        ctx.canvas.height / 2,
      );
    }
    return;
  }

  const ctx = document.getElementById("topProductsChart")?.getContext("2d");
  if (!ctx) return;
  if (topProductsChart) topProductsChart.destroy();

  const colors = [
    "#f59e0b",
    "#10b981",
    "#3b82f6",
    "#8b5cf6",
    "#ef4444",
    "#06b6d4",
    "#ec4899",
    "#f97316",
    "#14b8a6",
    "#6366f1",
  ];

  topProductsChart = new Chart(ctx, {
    type: "doughnut",
    data: {
      labels: data.labels,
      datasets: [
        {
          data: data.values,
          backgroundColor: colors.slice(0, data.labels.length),
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
      },
    },
  });
}

async function loadHourlyActivity() {
  const data = await fetchAPI(
    "/api/executive/hourly-activity?period=" + currentPeriod,
  );
  if (!data) return;

  const ctx = document.getElementById("hourlyChart")?.getContext("2d");
  if (!ctx) return;
  if (hourlyChart) hourlyChart.destroy();

  hourlyChart = new Chart(ctx, {
    type: "bar",
    data: {
      labels: data.labels,
      datasets: [
        {
          label: "İşlem Sayısı",
          data: data.values,
          backgroundColor: "rgba(168, 85, 247, 0.5)",
          borderColor: "#a855f7",
          borderWidth: 1,
          borderRadius: 3,
        },
      ],
    },
    options: chartOptions("İşlem"),
  });
}

function chartOptions(yLabel) {
  return {
    responsive: true,
    maintainAspectRatio: false,
    plugins: { legend: { display: false } },
    scales: {
      y: {
        beginAtZero: true,
        grid: { color: "rgba(71, 85, 105, 0.15)" },
        title: { display: false },
      },
      x: {
        grid: { display: false },
        ticks: {
          font: { size: 9 },
          maxRotation: 45,
          autoSkip: true,
          maxTicksLimit: 15,
        },
      },
    },
  };
}

// ---- DYNAMIC TABLE LOADERS ----
async function loadHotelComparison() {
  const data = await fetchAPI(
    "/api/executive/hotel-comparison?period=" + currentPeriod,
  );
  if (!data) return;

  const container = document.getElementById("hotel-comparison-container");
  if (!container) return;

  let html = '<table class="exec-table"><thead><tr>';
  html += '<th>Otel</th><th class="text-center">Oda</th>';
  html +=
    '<th class="text-center">Kontrol</th><th class="text-center">Tüketim</th>';
  html += '<th class="text-center">Görev %</th></tr></thead><tbody>';

  data.forEach((h) => {
    const barColor =
      h.gorev_oran >= 80
        ? "bg-green-500"
        : h.gorev_oran >= 50
          ? "bg-amber-500"
          : "bg-red-500";
    html += "<tr>";
    html += '<td class="font-medium text-white">' + h.ad + "</td>";
    html += '<td class="text-center">' + h.oda_sayisi + "</td>";
    html +=
      '<td class="text-center"><span class="text-blue-400">' +
      h.kontrol +
      "</span></td>";
    html +=
      '<td class="text-center"><span class="text-emerald-400">' +
      h.tuketim +
      "</span></td>";
    html +=
      '<td class="text-center"><div class="flex items-center justify-center gap-2">';
    html += '<div class="w-16 bg-slate-700 rounded-full h-1.5">';
    html +=
      '<div class="h-1.5 rounded-full ' +
      barColor +
      '" style="width:' +
      h.gorev_oran +
      '%"></div></div>';
    html += '<span class="text-xs">%' + h.gorev_oran + "</span></div></td>";
    html += "</tr>";
  });

  html += "</tbody></table>";
  container.innerHTML = html;
}

async function loadTaskCompletion() {
  const data = await fetchAPI(
    "/api/executive/task-completion?period=" + currentPeriod,
  );
  if (!data) return;

  const container = document.getElementById("task-completion-container");
  if (!container) return;

  if (data.length === 0) {
    container.innerHTML =
      '<div class="text-center text-slate-500 py-4"><p class="text-sm">Bu dönemde görev verisi yok</p></div>';
    return;
  }

  let html = "";
  data.forEach((t) => {
    let gradientClass = "bg-gradient-to-r from-red-500 to-rose-400";
    if (t.oran >= 80)
      gradientClass = "bg-gradient-to-r from-green-500 to-emerald-400";
    else if (t.oran >= 50)
      gradientClass = "bg-gradient-to-r from-amber-500 to-yellow-400";

    html += "<div>";
    html += '<div class="flex items-center justify-between mb-1">';
    html += '<span class="text-sm text-slate-300">' + t.otel + "</span>";
    html +=
      '<span class="text-sm font-medium text-white">' +
      t.tamamlanan +
      "/" +
      t.toplam;
    html +=
      ' <span class="text-xs text-slate-500">(%' +
      t.oran +
      ")</span></span></div>";
    html += '<div class="w-full bg-slate-700 rounded-full h-2.5">';
    html +=
      '<div class="h-2.5 rounded-full transition-all duration-500 ' +
      gradientClass +
      '" style="width:' +
      t.oran +
      '%"></div>';
    html += "</div></div>";
  });

  container.innerHTML = html;
}

// ---- ACTIVITY FEED ----
async function loadActivityFeed() {
  const data = await fetchAPI("/api/executive/activity-feed?limit=30");
  if (!data) return;

  const container = document.getElementById("activity-feed");
  if (!container) return;

  if (data.length === 0) {
    container.innerHTML =
      '<div class="text-center text-slate-500 py-8"><i class="fas fa-inbox text-2xl mb-2"></i><p class="text-sm">Henüz aktivite yok</p></div>';
    return;
  }

  container.innerHTML = data
    .map(
      (a) =>
        '<div class="exec-feed-item">' +
        '<div class="exec-feed-time">' +
        a.zaman +
        "</div>" +
        '<div class="exec-feed-content">' +
        '<div class="exec-feed-user">' +
        a.kullanici +
        "</div>" +
        '<div class="exec-feed-action">' +
        a.islem +
        (a.detay ? " — " + a.detay.substring(0, 80) : "") +
        "</div>" +
        "</div></div>",
    )
    .join("");

  const timeEl = document.getElementById("feed-update-time");
  if (timeEl) {
    const now = new Date();
    timeEl.textContent =
      "Son: " +
      now.toLocaleTimeString("tr-TR", {
        timeZone: "Europe/Nicosia",
        hour: "2-digit",
        minute: "2-digit",
      });
  }
}

// ---- REFRESH ALL ----
async function refreshAllData() {
  const icon = document.getElementById("refresh-icon");
  if (icon) icon.classList.add("fa-spin");

  await Promise.all([
    loadKPI(),
    loadConsumptionTrends(),
    loadRoomControls(),
    loadTopProducts(),
    loadHourlyActivity(),
    loadHotelComparison(),
    loadTaskCompletion(),
    loadActivityFeed(),
  ]);

  if (icon) setTimeout(() => icon.classList.remove("fa-spin"), 500);
}
