// ══ MAIN — global state, DOMContentLoaded init, event listeners ══

// ── Global state ──────────────────────────────
let currentUserId     = null;
let currentConvId     = null;
let currentMessages   = [];   // [{role, content}]
let currentAgent      = null;
let isStreaming       = false;
let selectedModel     = 'auto';   // actual API id
let selectedModelName = 'Авто';   // display name

// ── Init ──────────────────────────────────────
(function init(){
  const t=localStorage.getItem('mts-theme');
  if(t==='light'){ document.documentElement.setAttribute('data-theme','light'); document.getElementById('thTgl').classList.add('on'); }
  const l=localStorage.getItem('mts-lang')||'ru';
  if(l!=='ru') applyLang(l);
  buildDD('mDDH'); buildDD('mDDB');

  // Auto-login: если токен уже есть в localStorage — пропускаем authScreen
  const savedToken = localStorage.getItem('mts-token');
  const savedUserId = localStorage.getItem('mts-user-id');
  const savedEmail = localStorage.getItem('mts-user-email');
  if(savedToken && savedUserId){
    authToken = savedToken;
    currentUserId = savedUserId;
    if(savedEmail){
      document.getElementById('profInpEmail').value = savedEmail;
      const nameFromEmail = savedEmail.split('@')[0];
      document.getElementById('sbUserName').textContent = nameFromEmail;
      document.getElementById('sbAvatar').textContent   = getInitials(nameFromEmail);
    }
    document.getElementById('authScreen').style.display='none';
    initSplash();
  } else {
    setTimeout(()=>document.getElementById('authEmail')?.focus(),400);
  }
})();

// ── Build agents grid ────────────────────────
(function(){
  const g=document.getElementById('agGrid');
  AGENTS.forEach((a,i)=>{
    const c=document.createElement('div');
    c.className='ag-card rh'; c.style.animationDelay=(i*40)+'ms';
    c.innerHTML=`<div class="ag-ico">${a.ic}</div><div class="ag-name">${esc(a.name)}</div><div class="ag-desc">${esc(a.desc)}</div>`;
    c.onclick=()=>openAgModal(i);
    g.appendChild(c); addRipple(c);
  });
})();

// ── BG floating words ─────────────────────────
(function(){
  const phrases=['Искусственный интеллект','Artificial Intelligence','人工智能','Intelligence Artificielle','Künstliche Intelligenz','Inteligencia Artificial','人工知能','الذكاء الاصطناعي','Inteligência Artificial','인공지능','Intelligenza Artificiale','Yapay Zeka','Kunstmatige Intelligentie','Sztuczna Inteligencja','Artificiell Intelligens','Kunstig Intelligens','Tekoäly','Mesterséges Intelligencia','Artificiální Inteligence','Umelá Inteligencia','Τεχνητή Νοημοσύνη','कृत्रिम बुद्धिमत्ता','কৃত্রিম বুদ্ধিমত্তা','செயற்கை நுண்ணறிவு','Dirbtinis Intelektas'];
  const durations=[38,44,32,50,40,46,34,52,41,47,36,54,39,45,33,51,43,48,35,53,37,49,42,55,31,57,44,38,50,36];
  const wrap=document.getElementById('bgWords-inner'); if(!wrap) return;
  for(let i=0;i<160;i++){
    const row=document.createElement('div');
    row.className='bgr '+(i%2===0?'ev':'od');
    row.textContent=(phrases[i%phrases.length]+'   ').repeat(55);
    row.style.setProperty('--dur',durations[i%durations.length]+'s');
    wrap.appendChild(row);
  }
  if(localStorage.getItem('bgWordsOff')==='1'){
    document.getElementById('bgWords').classList.add('off');
    const tgl=document.getElementById('bgWordsTgl'); if(tgl) tgl.classList.remove('on');
  }
})();

// ── Global event wiring ───────────────────────
document.querySelectorAll('.rh').forEach(addRipple);
document.querySelectorAll('.prof-save,.prof-logout').forEach(addRipple);
document.addEventListener('keydown',e=>{ if(e.key==='Escape') closeAll(); });
