/**
 * Renk Tema Seçenekleri
 * Kullanıcı istediği temayı seçebilir
 */

const TEMA_SECENEKLERI = {
  "mavi-turkuaz": {
    name: "🔵 Mavi + Turkuaz (Profesyonel)",
    description: "Göz yormaz, kurumsal görünüm",
    badge_bg: "#2563EB",
    badge_text: "#FFFFFF",
    buton_gradient_start: "#38BDF8",
    buton_gradient_end: "#0284C7",
    buton_hover_start: "#60A5FA",
    buton_hover_end: "#2563EB",
    buton_text: "#FFFFFF",
  },
  "yesil-emerald": {
    name: "🟢 Yeşil + Emerald (Canlı)",
    description: "Pozitif, başarı hissi",
    badge_bg: "#16A34A",
    badge_text: "#ECFDF5",
    buton_gradient_start: "#34D399",
    buton_gradient_end: "#059669",
    buton_hover_start: "#6EE7B7",
    buton_hover_end: "#10B981",
    buton_text: "#FFFFFF",
  },
  "mor-purple": {
    name: "🟣 Mor + Purple (Modern)",
    description: "Şık, premium görünüm",
    badge_bg: "#7C3AED",
    badge_text: "#FFFFFF",
    buton_gradient_start: "#A78BFA",
    buton_gradient_end: "#7C3AED",
    buton_hover_start: "#C4B5FD",
    buton_hover_end: "#8B5CF6",
    buton_text: "#FFFFFF",
  },
  "turuncu-orange": {
    name: "🟠 Turuncu + Orange (Enerjik)",
    description: "Dinamik, dikkat çekici",
    badge_bg: "#EA580C",
    badge_text: "#FFFFFF",
    buton_gradient_start: "#FB923C",
    buton_gradient_end: "#EA580C",
    buton_hover_start: "#FDBA74",
    buton_hover_end: "#F97316",
    buton_text: "#FFFFFF",
  },
  "kirmizi-red": {
    name: "🔴 Kırmızı + Red (Güçlü)",
    description: "Cesur, dikkat çekici",
    badge_bg: "#DC2626",
    badge_text: "#FFFFFF",
    buton_gradient_start: "#F87171",
    buton_gradient_end: "#DC2626",
    buton_hover_start: "#FCA5A5",
    buton_hover_end: "#EF4444",
    buton_text: "#FFFFFF",
  },
  "pembe-pink": {
    name: "🩷 Pembe + Pink (Yumuşak)",
    description: "Nazik, modern",
    badge_bg: "#DB2777",
    badge_text: "#FFFFFF",
    buton_gradient_start: "#F472B6",
    buton_gradient_end: "#DB2777",
    buton_hover_start: "#F9A8D4",
    buton_hover_end: "#EC4899",
    buton_text: "#FFFFFF",
  },
  "sari-yellow": {
    name: "🟡 Sarı + Yellow (Neşeli)",
    description: "Parlak, pozitif",
    badge_bg: "#CA8A04",
    badge_text: "#FFFFFF",
    buton_gradient_start: "#FDE047",
    buton_gradient_end: "#CA8A04",
    buton_hover_start: "#FEF08A",
    buton_hover_end: "#EAB308",
    buton_text: "#000000",
  },
  "lacivert-indigo": {
    name: "🔷 Lacivert + Indigo (Klasik)",
    description: "Güvenilir, sakin",
    badge_bg: "#4F46E5",
    badge_text: "#FFFFFF",
    buton_gradient_start: "#818CF8",
    buton_gradient_end: "#4F46E5",
    buton_hover_start: "#A5B4FC",
    buton_hover_end: "#6366F1",
    buton_text: "#FFFFFF",
  },
};

// Aktif temayı localStorage'dan al
function getAktifTema() {
  const savedTema = localStorage.getItem("oda_kontrol_tema");
  return savedTema || "mavi-turkuaz";
}

// Temayı kaydet
function setAktifTema(temaAdi) {
  localStorage.setItem("oda_kontrol_tema", temaAdi);
}

// Tema renklerini al
function getTemaRenkleri(temaAdi = null) {
  const tema = temaAdi || getAktifTema();
  return TEMA_SECENEKLERI[tema] || TEMA_SECENEKLERI["mavi-turkuaz"];
}
