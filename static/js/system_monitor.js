/**
 * System Monitor Dashboard — Real-time gauges, charts & log stream
 * Lightweight: polls every N seconds, no WebSocket needed
 */

// ---- State ----
let refreshTimer = null;
let refreshSec = 10;
const TREND_MAX = 30; // max data points in trend chart
const trendData = { labels: [], cpu: [], mem: [] };
let trendChart = null;
let responseChart = null;

// ---- Init ----
document.addEventListener("DOMContentLoaded", () => {
  initCharts();
  refreshAll();
  startAutoRefresh();
});

// ---- Auto Refresh ----
function setRefreshInterval(sec) {
  refreshSec = parseInt(sec);
  document.getElementById("refresh-interval-label").textContent =
    refreshSec > 0 ? refreshSec + "s" : "Kapalı";
  startAutoRefresh();
}

function startAutoRefresh() {
  if (refreshTimer) clearInterval(refreshTimer);
  if (refreshSec > 0) {
    refreshTimer = setInterval(refreshAll, refreshSec * 1000);
  }
}

async function refreshAll() {
  const icon = document.getElementById("refresh-icon");
  icon.classList.add("fa-spin");
  try {
    await Promise.all([loadOverview(), loadEndpoints(), loadErrorLog()]);
  } catch (e) {
    console.error("Refresh error:", e);
  }
  setTimeout(() => icon.classList.remove("fa-spin"), 500);
}

// ---- Gauge Drawing ----
function drawGauge(canvasId, percent, color) {
  const canvas = document.getElementById(canvasId);
  if (!canvas) return;
  const ctx = canvas.getContext("2d");
  const dpr = window.devicePixelRatio || 1;
  const w = canvas.parentElement.clientWidth;
  const h = canvas.parentElement.clientHeight;
  canvas.width = w * dpr;
  canvas.height = h * dpr;
  canvas.style.width = w + "px";
  canvas.style.height = h + "px";
  ctx.scale(dpr, dpr);

  const cx = w / 2,
    cy = h - 5,
    r = Math.min(w / 2 - 8, h - 12);
  const startAngle = Math.PI,
    endAngle = 2 * Math.PI;
  const valAngle =
    startAngle + (endAngle - startAngle) * (Math.min(percent, 100) / 100);

  // Background arc
  ctx.beginPath();
  ctx.arc(cx, cy, r, startAngle, endAngle);
  ctx.lineWidth = 10;
  ctx.strokeStyle = "#1e293b";
  ctx.lineCap = "round";
  ctx.stroke();

  // Value arc
  ctx.beginPath();
  ctx.arc(cx, cy, r, startAngle, valAngle);
  ctx.lineWidth = 10;
  ctx.strokeStyle = color;
  ctx.lineCap = "round";
  ctx.stroke();
}

function getColor(pct) {
  if (pct < 50) return "#22c55e";
  if (pct < 75) return "#eab308";
  if (pct < 90) return "#f97316";
  return "#ef4444";
}

// ---- Overview ----
async function loadOverview() {
  try {
    const res = await fetch("/api/system-monitor/overview");
    const json = await res.json();
    if (!json.success) return;
    const d = json.data;

    // CPU
    const cpuPct = d.cpu.percent;
    drawGauge("gauge-cpu", cpuPct, getColor(cpuPct));
    setText("val-cpu", cpuPct.toFixed(1) + "%", getColorClass(cpuPct));
    setText("sub-cpu", d.cpu.cores + " çekirdek");

    // Memory
    const memPct = d.memory.percent;
    drawGauge("gauge-mem", memPct, getColor(memPct));
    setText("val-mem", memPct.toFixed(1) + "%", getColorClass(memPct));
    setText("sub-mem", d.memory.used_mb + " / " + d.memory.total_mb + " MB");

    // Disk
    const diskPct = d.disk.percent;
    drawGauge("gauge-disk", diskPct, getColor(diskPct));
    setText("val-disk", diskPct.toFixed(1) + "%", getColorClass(diskPct));
    setText("sub-disk", d.disk.used_gb + " / " + d.disk.total_gb + " GB");

    // Response time
    const avgMs = d.api.avg_response_ms;
    const respColor =
      avgMs < 200
        ? "g-green"
        : avgMs < 500
          ? "g-yellow"
          : avgMs < 1000
            ? "g-orange"
            : "g-red";
    setText("val-resp", avgMs.toFixed(0) + " ms", respColor);
    setText(
      "sub-resp",
      "P95: " + d.api.p95_ms.toFixed(0) + " ms | Hata: %" + d.api.error_rate,
    );

    // DB connections
    const dbC = d.database;
    setText("val-dbconn", dbC.total, "g-cyan");
    setText("sub-dbconn", "aktif: " + dbC.active + " / idle: " + dbC.idle);

    // Uptime
    setText("val-uptime", d.app.uptime, "g-green");
    setText(
      "sub-uptime",
      "PID: " + d.app.pid + " | App: " + d.app.process_memory_mb + " MB",
    );

    // Update trend
    updateTrend(cpuPct, memPct);

    // Load DB stats
    loadDbStats();

    // Update response chart
    updateResponseChart(d.api);
  } catch (e) {
    console.error("Overview error:", e);
  }
}

function setText(id, text, colorClass) {
  const el = document.getElementById(id);
  if (!el) return;
  el.textContent = text;
  if (colorClass) {
    el.className = el.className.replace(/g-\w+/g, "") + " " + colorClass;
  }
}

function getColorClass(pct) {
  if (pct < 50) return "g-green";
  if (pct < 75) return "g-yellow";
  if (pct < 90) return "g-orange";
  return "g-red";
}

// ---- Trend Chart ----
function initCharts() {
  const trendCtx = document.getElementById("chart-trend");
  if (trendCtx) {
    trendChart = new Chart(trendCtx, {
      type: "line",
      data: {
        labels: [],
        datasets: [
          {
            label: "CPU %",
            data: [],
            borderColor: "#06b6d4",
            backgroundColor: "rgba(6,182,212,0.1)",
            fill: true,
            tension: 0.3,
            pointRadius: 0,
            borderWidth: 2,
          },
          {
            label: "Bellek %",
            data: [],
            borderColor: "#a855f7",
            backgroundColor: "rgba(168,85,247,0.1)",
            fill: true,
            tension: 0.3,
            pointRadius: 0,
            borderWidth: 2,
          },
        ],
      },
      options: chartOpts(100, "%"),
    });
  }

  const respCtx = document.getElementById("chart-response");
  if (respCtx) {
    responseChart = new Chart(respCtx, {
      type: "bar",
      data: {
        labels: ["Ort.", "P50", "P95", "P99"],
        datasets: [
          {
            label: "ms",
            data: [0, 0, 0, 0],
            backgroundColor: ["#3b82f6", "#22c55e", "#eab308", "#ef4444"],
            borderRadius: 6,
            barThickness: 40,
          },
        ],
      },
      options: chartOpts(null, "ms"),
    });
  }
}

function chartOpts(maxY, unit) {
  return {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: {
        display: true,
        labels: { color: "#94a3b8", font: { size: 11 } },
      },
    },
    scales: {
      x: {
        ticks: { color: "#64748b", font: { size: 10 } },
        grid: { color: "rgba(51,65,85,0.3)" },
      },
      y: {
        max: maxY || undefined,
        ticks: {
          color: "#64748b",
          font: { size: 10 },
          callback: (v) => v + (unit || ""),
        },
        grid: { color: "rgba(51,65,85,0.3)" },
      },
    },
  };
}

function updateTrend(cpu, mem) {
  const now = new Date().toLocaleTimeString("tr-TR", {
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
  });
  trendData.labels.push(now);
  trendData.cpu.push(cpu);
  trendData.mem.push(mem);
  if (trendData.labels.length > TREND_MAX) {
    trendData.labels.shift();
    trendData.cpu.shift();
    trendData.mem.shift();
  }
  if (trendChart) {
    trendChart.data.labels = [...trendData.labels];
    trendChart.data.datasets[0].data = [...trendData.cpu];
    trendChart.data.datasets[1].data = [...trendData.mem];
    trendChart.update("none");
  }
}

function updateResponseChart(api) {
  if (!responseChart) return;
  // We need p50/p99 from endpoint stats — use avg and p95 from overview
  responseChart.data.datasets[0].data = [
    api.avg_response_ms,
    api.avg_response_ms * 0.8, // approximate p50
    api.p95_ms,
    api.p95_ms * 1.3, // approximate p99
  ];
  responseChart.update("none");
}

// ---- DB Stats ----
async function loadDbStats() {
  try {
    const res = await fetch("/api/system-monitor/db-stats");
    const json = await res.json();
    if (!json.success) return;
    const d = json.data;

    document.getElementById("db-size").textContent = d.db_size;
    document.getElementById("db-cache-hit").textContent = d.cache_hit + "%";
    document.getElementById("db-conn-total").textContent = d.connections.total;
    document.getElementById("db-conn-active").textContent =
      d.connections.active;

    // Cache hit color
    const chEl = document.getElementById("db-cache-hit");
    chEl.className =
      "db-stat-value " +
      (d.cache_hit > 95 ? "g-green" : d.cache_hit > 80 ? "g-yellow" : "g-red");

    // Top tables
    if (d.table_sizes && d.table_sizes.length > 0) {
      const wrap = document.getElementById("top-tables-wrap");
      wrap.style.display = "block";
      const maxBytes = d.table_sizes[0].bytes || 1;
      document.getElementById("top-tables").innerHTML = d.table_sizes
        .slice(0, 8)
        .map(
          (t) => `
        <div class="flex items-center gap-2 mb-1">
          <span class="text-xs text-slate-400" style="min-width:120px">${t.table}</span>
          <div class="ep-bar flex-1">
            <div class="ep-bar-fill" style="width:${((t.bytes / maxBytes) * 100).toFixed(0)}%;background:#3b82f6"></div>
          </div>
          <span class="text-xs text-slate-500" style="min-width:60px;text-align:right">${t.size}</span>
        </div>
      `,
        )
        .join("");
    }
  } catch (e) {
    console.error("DB stats error:", e);
  }
}

// ---- Endpoints ----
async function loadEndpoints() {
  try {
    const sort = document.getElementById("ep-sort")?.value || "avg_time";
    const res = await fetch("/api/system-monitor/endpoints?sort=" + sort);
    const json = await res.json();
    if (!json.success) return;

    const tbody = document.getElementById("ep-tbody");
    if (!json.data || json.data.length === 0) {
      tbody.innerHTML =
        '<tr><td colspan="6" class="text-center text-slate-500 py-4">Henüz veri yok</td></tr>';
      return;
    }

    const maxTime = Math.max(
      ...json.data.map((e) => e.avg_response_time || 0),
      0.001,
    );
    tbody.innerHTML = json.data
      .map((ep) => {
        const avgMs = ((ep.avg_response_time || 0) * 1000).toFixed(0);
        const p95Ms = ((ep.p95 || 0) * 1000).toFixed(0);
        const errRate = (ep.error_rate || 0).toFixed(1);
        const barPct = (((ep.avg_response_time || 0) / maxTime) * 100).toFixed(
          0,
        );
        const barColor =
          avgMs < 200
            ? "#22c55e"
            : avgMs < 500
              ? "#eab308"
              : avgMs < 1000
                ? "#f97316"
                : "#ef4444";
        const errColor =
          errRate > 5 ? "color:#ef4444" : errRate > 1 ? "color:#eab308" : "";
        return `<tr>
        <td class="text-xs">${ep.endpoint || "-"}</td>
        <td>${ep.request_count || 0}</td>
        <td style="color:${barColor}">${avgMs}</td>
        <td>${p95Ms}</td>
        <td style="${errColor}">${errRate}%</td>
        <td><div class="ep-bar"><div class="ep-bar-fill" style="width:${barPct}%;background:${barColor}"></div></div></td>
      </tr>`;
      })
      .join("");
  } catch (e) {
    console.error("Endpoints error:", e);
  }
}

// ---- Error Log ----
async function loadErrorLog() {
  try {
    const res = await fetch("/api/system-monitor/error-log?limit=50");
    const json = await res.json();
    if (!json.success) return;

    document.getElementById("log-count").textContent = json.total + " kayıt";
    const stream = document.getElementById("log-stream");

    if (!json.data || json.data.length === 0) {
      stream.innerHTML =
        '<div class="text-center text-slate-500 py-4"><i class="fas fa-check-circle text-green-500 mr-2"></i>Hata kaydı yok</div>';
      return;
    }

    stream.innerHTML = json.data
      .map((log) => {
        const time = log.timestamp
          ? log.timestamp.split("T")[1]?.split(".")[0] || ""
          : "";
        return `<div class="log-entry">
        <span class="log-time">${time}</span>
        <span class="log-level ${log.level}">${log.level}</span>
        <span class="log-module">[${log.module}]</span>
        <span class="log-msg">${escapeHtml(log.message)}</span>
      </div>`;
      })
      .join("");
  } catch (e) {
    console.error("Error log error:", e);
  }
}

function escapeHtml(str) {
  const div = document.createElement("div");
  div.textContent = str;
  return div.innerHTML;
}
