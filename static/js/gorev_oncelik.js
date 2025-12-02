// Akıllı Görev Öncelik Planı - JavaScript
let oncelikPlanData = null;

function openOncelikModal() {
  document.getElementById('oncelikPlanModal').classList.remove('hidden');
  document.body.style.overflow = 'hidden';
  loadOncelikPlani();
}

function closeOncelikModal() {
  document.getElementById('oncelikPlanModal').classList.add('hidden');
  document.body.style.overflow = '';
}

async function loadOncelikPlani() {
  const loading = document.getElementById('oncelikLoading');
  const error = document.getElementById('oncelikError');
  const content = document.getElementById('oncelikContent');
  
  loading.classList.remove('hidden');
  error.classList.add('hidden');
  content.classList.add('hidden');
  
  try {
    const tarih = new Date().toISOString().split('T')[0];
    const response = await fetch('/gorevler/api/oncelik-plani?tarih=' + tarih);
    const data = await response.json();
    
    if (!data.success) {
      throw new Error(data.error || 'Bilinmeyen hata');
    }
    
    oncelikPlanData = data;
    renderOncelikPlani(data);
    
    loading.classList.add('hidden');
    content.classList.remove('hidden');
    
  } catch (err) {
    loading.classList.add('hidden');
    error.classList.remove('hidden');
    document.getElementById('oncelikErrorMsg').textContent = err.message;
  }
}

function yenileOncelikPlani() {
  loadOncelikPlani();
}

function renderOncelikPlani(data) {
  const tarih = new Date();
  const gunler = ['Pazar', 'Pazartesi', 'Sali', 'Carsamba', 'Persembe', 'Cuma', 'Cumartesi'];
  document.getElementById('modal-tarih').textContent = tarih.toLocaleDateString('tr-TR') + ' - ' + gunler[tarih.getDay()];
  
  document.getElementById('ozet-toplam').textContent = data.ozet.toplam;
  document.getElementById('ozet-kritik').textContent = data.ozet.kritik;
  document.getElementById('ozet-cakisma').textContent = data.ozet.cakisma_sayisi || 0;
  document.getElementById('ozet-normal').textContent = data.ozet.normal;
  
  document.getElementById('briefing-text').textContent = data.briefing;
  
  const baslangicDiv = document.getElementById('baslangic-oneri');
  if (data.baslangic_kat) {
    baslangicDiv.classList.remove('hidden');
    document.getElementById('baslangic-kat').textContent = data.baslangic_kat.kat_adi + ' - Oda ' + data.baslangic_kat.ilk_oda;
    document.getElementById('baslangic-sebep').textContent = data.baslangic_kat.sebep;
  } else {
    baslangicDiv.classList.add('hidden');
  }
  
  renderKatPlani(data.kat_plani);
  renderOncelikListesi(data.plan);
  
  if (data.guncelleme_zamani) {
    const guncelleme = new Date(data.guncelleme_zamani);
    document.getElementById('son-guncelleme').textContent = guncelleme.toLocaleTimeString('tr-TR');
  }
}

function renderKatPlani(katPlani) {
  const container = document.getElementById('kat-plani-container');
  container.innerHTML = '';
  
  const siraliKatlar = Object.values(katPlani).sort((a, b) => a.oncelik_sirasi - b.oncelik_sirasi);
  
  siraliKatlar.forEach((kat, index) => {
    const katDiv = document.createElement('div');
    katDiv.className = 'bg-white dark:bg-slate-800 rounded-lg border border-slate-200 dark:border-slate-700 p-4';
    
    let kritikBadge = '';
    if (kat.kritik_gorev > 0) {
      kritikBadge = '<span class="px-2 py-1 bg-red-100 dark:bg-red-900/30 text-red-700 dark:text-red-300 text-xs font-medium rounded-full">' + kat.kritik_gorev + ' kritik</span>';
    }
    
    let odalar = kat.gorevler.slice(0, 8).map(g => '<span class="px-2 py-1 text-xs font-medium rounded ' + getOncelikClass(g.oncelik_tipi) + '">' + g.oda_no + '</span>').join('');
    if (kat.gorevler.length > 8) {
      odalar += '<span class="px-2 py-1 text-xs text-slate-500 dark:text-slate-400">+' + (kat.gorevler.length - 8) + ' daha</span>';
    }
    
    katDiv.innerHTML = '<div class="flex items-center justify-between mb-3"><div class="flex items-center space-x-3"><div class="w-10 h-10 bg-indigo-100 dark:bg-indigo-900/30 rounded-lg flex items-center justify-center"><span class="text-indigo-600 dark:text-indigo-400 font-bold">' + kat.kat_no + '</span></div><div><h5 class="font-semibold text-slate-900 dark:text-white">' + kat.kat_adi + '</h5><span class="text-xs text-slate-500 dark:text-slate-400">' + kat.toplam_gorev + ' gorev</span></div></div><div class="flex items-center space-x-2">' + kritikBadge + '<span class="px-2 py-1 bg-slate-100 dark:bg-slate-700 text-slate-600 dark:text-slate-300 text-xs font-medium rounded-full">#' + (index + 1) + '. sira</span></div></div><div class="flex flex-wrap gap-2">' + odalar + '</div>';
    
    container.appendChild(katDiv);
  });
}

function renderOncelikListesi(plan) {
  const container = document.getElementById('oncelik-listesi');
  container.innerHTML = '';
  
  plan.forEach(gorev => {
    const gorevDiv = document.createElement('div');
    gorevDiv.className = 'flex items-center p-3 rounded-lg border-2 ' + getOncelikBorderClass(gorev.oncelik_tipi);
    
    let kalanSureText = '';
    if (gorev.kalan_sure_dakika !== null) {
      if (gorev.kalan_sure_dakika <= 0) {
        kalanSureText = '<span class="text-red-600 font-bold animate-pulse">GECTI!</span>';
      } else if (gorev.kalan_sure_dakika < 30) {
        kalanSureText = '<span class="text-red-600 font-bold">' + gorev.kalan_sure_dakika + ' dk</span>';
      } else if (gorev.kalan_sure_dakika < 60) {
        kalanSureText = '<span class="text-orange-600 font-bold">' + gorev.kalan_sure_dakika + ' dk</span>';
      } else {
        const saat = Math.floor(gorev.kalan_sure_dakika / 60);
        const dk = gorev.kalan_sure_dakika % 60;
        kalanSureText = '<span class="text-slate-600 dark:text-slate-400">' + saat + 's ' + dk + 'dk</span>';
      }
    }
    
    let kalanDiv = '';
    if (kalanSureText) {
      kalanDiv = '<div class="text-right"><div class="text-xs text-slate-500 dark:text-slate-400">Kalan</div>' + kalanSureText + '</div>';
    }
    
    gorevDiv.innerHTML = '<div class="w-8 h-8 bg-indigo-500 text-white rounded-full flex items-center justify-center font-bold text-sm mr-3">' + gorev.oncelik_sirasi + '</div><div class="flex-1"><div class="flex items-center space-x-2"><span class="font-bold text-slate-900 dark:text-white">Oda ' + gorev.oda_no + '</span><span class="text-xs px-2 py-0.5 rounded-full ' + getOncelikBadgeClass(gorev.oncelik_tipi) + '">' + getOncelikLabel(gorev.oncelik_tipi) + '</span><span class="text-xs text-slate-500 dark:text-slate-400">' + gorev.kat_adi + '</span></div><div class="text-sm text-slate-600 dark:text-slate-400">' + gorev.aciklama + '</div></div>' + kalanDiv;
    
    container.appendChild(gorevDiv);
  });
}

function getOncelikClass(tip) {
  const classes = {
    'DEPARTURE_ARRIVAL_CAKISMA': 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-300',
    'ARRIVAL': 'bg-purple-100 text-purple-700 dark:bg-purple-900/30 dark:text-purple-300',
    'DEPARTURE': 'bg-teal-100 text-teal-700 dark:bg-teal-900/30 dark:text-teal-300',
    'INHOUSE': 'bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-300',
    'DND_TEKRAR': 'bg-orange-100 text-orange-700 dark:bg-orange-900/30 dark:text-orange-300'
  };
  return classes[tip] || 'bg-slate-100 text-slate-700';
}

function getOncelikBorderClass(tip) {
  const classes = {
    'DEPARTURE_ARRIVAL_CAKISMA': 'bg-red-50 dark:bg-red-900/20 border-red-300 dark:border-red-700',
    'ARRIVAL': 'bg-purple-50 dark:bg-purple-900/20 border-purple-300 dark:border-purple-700',
    'DEPARTURE': 'bg-teal-50 dark:bg-teal-900/20 border-teal-300 dark:border-teal-700',
    'INHOUSE': 'bg-blue-50 dark:bg-blue-900/20 border-blue-300 dark:border-blue-700',
    'DND_TEKRAR': 'bg-orange-50 dark:bg-orange-900/20 border-orange-300 dark:border-orange-700'
  };
  return classes[tip] || '';
}

function getOncelikBadgeClass(tip) {
  const classes = {
    'DEPARTURE_ARRIVAL_CAKISMA': 'bg-red-500 text-white',
    'ARRIVAL': 'bg-purple-500 text-white',
    'DEPARTURE': 'bg-teal-500 text-white',
    'INHOUSE': 'bg-blue-500 text-white',
    'DND_TEKRAR': 'bg-orange-500 text-white'
  };
  return classes[tip] || 'bg-slate-500 text-white';
}

function getOncelikLabel(tip) {
  const labels = {
    'DEPARTURE_ARRIVAL_CAKISMA': 'Cakisma',
    'ARRIVAL': 'Arrival',
    'DEPARTURE': 'Departure',
    'INHOUSE': 'In-House',
    'DND_TEKRAR': 'DND'
  };
  return labels[tip] || tip;
}

document.addEventListener('keydown', function(e) {
  if (e.key === 'Escape') {
    closeOncelikModal();
  }
});
