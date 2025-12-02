// Akıllı Görev Öncelik Planı - JavaScript
let oncelikPlanData = null;

function openOncelikModal() {
  try {
    const modal = document.getElementById('oncelikPlanModal');
    if (!modal) {
      console.error('Modal bulunamadi!');
      alert('Modal yüklenemedi. Sayfayı yenileyin.');
      return;
    }
    modal.classList.remove('hidden');
    document.body.style.overflow = 'hidden';
    loadOncelikPlani();
  } catch (e) {
    console.error('Modal acma hatasi:', e);
    alert('Hata: ' + e.message);
  }
}

function closeOncelikModal() {
  const modal = document.getElementById('oncelikPlanModal');
  if (modal) {
    modal.classList.add('hidden');
  }
  document.body.style.overflow = '';
}

async function loadOncelikPlani() {
  const loading = document.getElementById('oncelikLoading');
  const error = document.getElementById('oncelikError');
  const content = document.getElementById('oncelikContent');
  
  if (loading) loading.classList.remove('hidden');
  if (error) error.classList.add('hidden');
  if (content) content.classList.add('hidden');
  
  try {
    const tarih = new Date().toISOString().split('T')[0];
    const response = await fetch('/gorevler/api/oncelik-plani?tarih=' + tarih);
    const data = await response.json();
    
    if (!data.success) {
      throw new Error(data.error || 'Bilinmeyen hata');
    }
    
    oncelikPlanData = data;
    renderOncelikPlani(data);
    
    if (loading) loading.classList.add('hidden');
    if (content) content.classList.remove('hidden');
    
  } catch (err) {
    console.error('API hatasi:', err);
    if (loading) loading.classList.add('hidden');
    if (error) error.classList.remove('hidden');
    const errMsg = document.getElementById('oncelikErrorMsg');
    if (errMsg) errMsg.textContent = err.message;
  }
}

function yenileOncelikPlani() {
  loadOncelikPlani();
}

function renderOncelikPlani(data) {
  const tarih = new Date();
  const gunler = ['Pazar', 'Pazartesi', 'Sali', 'Carsamba', 'Persembe', 'Cuma', 'Cumartesi'];
  
  const modalTarih = document.getElementById('modal-tarih');
  if (modalTarih) modalTarih.textContent = tarih.toLocaleDateString('tr-TR') + ' - ' + gunler[tarih.getDay()];
  
  const ozetToplam = document.getElementById('ozet-toplam');
  const ozetKritik = document.getElementById('ozet-kritik');
  const ozetCakisma = document.getElementById('ozet-cakisma');
  const ozetNormal = document.getElementById('ozet-normal');
  
  if (ozetToplam) ozetToplam.textContent = data.ozet.toplam;
  if (ozetKritik) ozetKritik.textContent = data.ozet.kritik;
  if (ozetCakisma) ozetCakisma.textContent = data.ozet.cakisma_sayisi || 0;
  if (ozetNormal) ozetNormal.textContent = data.ozet.normal;
  
  const briefingText = document.getElementById('briefing-text');
  if (briefingText) briefingText.textContent = data.briefing;
  
  const baslangicDiv = document.getElementById('baslangic-oneri');
  if (baslangicDiv) {
    if (data.baslangic_kat) {
      baslangicDiv.classList.remove('hidden');
      const baslangicKat = document.getElementById('baslangic-kat');
      const baslangicSebep = document.getElementById('baslangic-sebep');
      if (baslangicKat) baslangicKat.textContent = data.baslangic_kat.kat_adi + ' - Oda ' + data.baslangic_kat.ilk_oda;
      if (baslangicSebep) baslangicSebep.textContent = data.baslangic_kat.sebep;
    } else {
      baslangicDiv.classList.add('hidden');
    }
  }
  
  renderKatPlani(data.kat_plani);
  renderOncelikListesi(data.plan);
  
  if (data.guncelleme_zamani) {
    const guncelleme = new Date(data.guncelleme_zamani);
    const sonGuncelleme = document.getElementById('son-guncelleme');
    if (sonGuncelleme) sonGuncelleme.textContent = guncelleme.toLocaleTimeString('tr-TR');
  }
}

function renderKatPlani(katPlani) {
  const container = document.getElementById('kat-plani-container');
  if (!container) return;
  container.innerHTML = '';
  
  if (!katPlani || Object.keys(katPlani).length === 0) {
    container.innerHTML = '<p class="text-slate-500 text-center py-4">Kat planı bulunamadı</p>';
    return;
  }
  
  const siraliKatlar = Object.values(katPlani).sort((a, b) => a.oncelik_sirasi - b.oncelik_sirasi);
  
  siraliKatlar.forEach((kat, index) => {
    const katDiv = document.createElement('div');
    katDiv.className = 'bg-white dark:bg-slate-800 rounded-lg border border-slate-200 dark:border-slate-700 p-4';
    
    let kritikBadge = '';
    if (kat.kritik_gorev > 0) {
      kritikBadge = '<span class="px-2 py-1 bg-red-100 dark:bg-red-900/30 text-red-700 dark:text-red-300 text-xs font-medium rounded-full">' + kat.kritik_gorev + ' kritik</span>';
    }
    
    let odalar = kat.gorevler.slice(0, 6).map(function(g) {
      return '<span class="px-2 py-1 text-xs font-medium rounded ' + getOncelikClass(g.oncelik_tipi) + '">' + g.oda_no + '</span>';
    }).join('');
    
    if (kat.gorevler.length > 6) {
      odalar += '<span class="px-2 py-1 text-xs text-slate-500">+' + (kat.gorevler.length - 6) + '</span>';
    }
    
    katDiv.innerHTML = '<div class="flex items-center justify-between mb-3"><div class="flex items-center space-x-3"><div class="w-10 h-10 bg-indigo-100 dark:bg-indigo-900/30 rounded-lg flex items-center justify-center"><span class="text-indigo-600 dark:text-indigo-400 font-bold">' + kat.kat_no + '</span></div><div><h5 class="font-semibold text-slate-900 dark:text-white">' + kat.kat_adi + '</h5><span class="text-xs text-slate-500">' + kat.toplam_gorev + ' gorev</span></div></div><div class="flex items-center space-x-2">' + kritikBadge + '<span class="px-2 py-1 bg-slate-100 dark:bg-slate-700 text-slate-600 dark:text-slate-300 text-xs font-medium rounded-full">#' + (index + 1) + '</span></div></div><div class="flex flex-wrap gap-2">' + odalar + '</div>';
    
    container.appendChild(katDiv);
  });
}

function renderOncelikListesi(plan) {
  const container = document.getElementById('oncelik-listesi');
  if (!container) return;
  container.innerHTML = '';
  
  if (!plan || plan.length === 0) {
    container.innerHTML = '<p class="text-slate-500 text-center py-4">Bekleyen gorev yok</p>';
    return;
  }
  
  plan.forEach(function(gorev) {
    const gorevDiv = document.createElement('div');
    gorevDiv.className = 'flex items-center p-3 rounded-lg border-2 ' + getOncelikBorderClass(gorev.oncelik_tipi);
    
    let kalanSureText = '';
    if (gorev.kalan_sure_dakika !== null && gorev.kalan_sure_dakika !== undefined) {
      if (gorev.kalan_sure_dakika <= 0) {
        kalanSureText = '<span class="text-red-600 font-bold">GECTI!</span>';
      } else if (gorev.kalan_sure_dakika < 30) {
        kalanSureText = '<span class="text-red-600 font-bold">' + gorev.kalan_sure_dakika + ' dk</span>';
      } else if (gorev.kalan_sure_dakika < 60) {
        kalanSureText = '<span class="text-orange-600 font-bold">' + gorev.kalan_sure_dakika + ' dk</span>';
      } else {
        var saat = Math.floor(gorev.kalan_sure_dakika / 60);
        var dk = gorev.kalan_sure_dakika % 60;
        kalanSureText = '<span class="text-slate-600">' + saat + 's ' + dk + 'dk</span>';
      }
    }
    
    var kalanDiv = '';
    if (kalanSureText) {
      kalanDiv = '<div class="text-right ml-2"><div class="text-xs text-slate-500">Kalan</div>' + kalanSureText + '</div>';
    }
    
    gorevDiv.innerHTML = '<div class="w-8 h-8 bg-indigo-500 text-white rounded-full flex items-center justify-center font-bold text-sm mr-3 flex-shrink-0">' + gorev.oncelik_sirasi + '</div><div class="flex-1 min-w-0"><div class="flex flex-wrap items-center gap-1"><span class="font-bold text-slate-900 dark:text-white">Oda ' + gorev.oda_no + '</span><span class="text-xs px-2 py-0.5 rounded-full ' + getOncelikBadgeClass(gorev.oncelik_tipi) + '">' + getOncelikLabel(gorev.oncelik_tipi) + '</span></div><div class="text-xs text-slate-500 truncate">' + gorev.aciklama + '</div></div>' + kalanDiv;
    
    container.appendChild(gorevDiv);
  });
}

function getOncelikClass(tip) {
  var classes = {
    'DEPARTURE_ARRIVAL_CAKISMA': 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-300',
    'ARRIVAL': 'bg-purple-100 text-purple-700 dark:bg-purple-900/30 dark:text-purple-300',
    'DEPARTURE': 'bg-teal-100 text-teal-700 dark:bg-teal-900/30 dark:text-teal-300',
    'INHOUSE': 'bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-300',
    'DND_TEKRAR': 'bg-orange-100 text-orange-700 dark:bg-orange-900/30 dark:text-orange-300'
  };
  return classes[tip] || 'bg-slate-100 text-slate-700';
}

function getOncelikBorderClass(tip) {
  var classes = {
    'DEPARTURE_ARRIVAL_CAKISMA': 'bg-red-50 dark:bg-red-900/20 border-red-300 dark:border-red-700',
    'ARRIVAL': 'bg-purple-50 dark:bg-purple-900/20 border-purple-300 dark:border-purple-700',
    'DEPARTURE': 'bg-teal-50 dark:bg-teal-900/20 border-teal-300 dark:border-teal-700',
    'INHOUSE': 'bg-blue-50 dark:bg-blue-900/20 border-blue-300 dark:border-blue-700',
    'DND_TEKRAR': 'bg-orange-50 dark:bg-orange-900/20 border-orange-300 dark:border-orange-700'
  };
  return classes[tip] || '';
}

function getOncelikBadgeClass(tip) {
  var classes = {
    'DEPARTURE_ARRIVAL_CAKISMA': 'bg-red-500 text-white',
    'ARRIVAL': 'bg-purple-500 text-white',
    'DEPARTURE': 'bg-teal-500 text-white',
    'INHOUSE': 'bg-blue-500 text-white',
    'DND_TEKRAR': 'bg-orange-500 text-white'
  };
  return classes[tip] || 'bg-slate-500 text-white';
}

function getOncelikLabel(tip) {
  var labels = {
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

console.log('gorev_oncelik.js yuklendi');
