// ══ UTILS — uuid, esc, autoH, fmtTime, scrollBot, toast, burstParticles, addRipple, closeAll ══

function uuid(){
  return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, c=>{
    const r = Math.random()*16|0;
    return (c==='x'?r:(r&0x3|0x8)).toString(16);
  });
}

function esc(s){ return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;'); }

function autoH(el){ el.style.height='auto'; el.style.height=Math.min(el.scrollHeight,180)+'px'; }

function fmtTime(s){ return String(Math.floor(s/60)).padStart(2,'0')+':'+String(s%60).padStart(2,'0'); }

function scrollBot(){ const s=document.getElementById('chatScroll'); setTimeout(()=>s.scrollTop=s.scrollHeight,40); }

function toast(msg,type,dur){
  if(type===undefined) type='inf';
  if(dur===undefined) dur=2600;
  const root=document.getElementById('toastRoot');
  const icons={ok:'<svg width="12" height="12" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" viewBox="0 0 24 24"><polyline points="20 6 9 17 4 12"/></svg>',inf:'<svg width="12" height="12" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" viewBox="0 0 24 24"><circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/></svg>',err:'<svg width="12" height="12" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" viewBox="0 0 24 24"><circle cx="12" cy="12" r="10"/><line x1="15" y1="9" x2="9" y2="15"/><line x1="9" y1="9" x2="15" y2="15"/></svg>'};
  const t=document.createElement('div'); t.className='toast';
  t.innerHTML=`<div class="toast-ic ${type}">${icons[type]||icons.inf}</div><span>${esc(msg)}</span>`;
  root.appendChild(t);
  setTimeout(()=>{ t.classList.add('out'); t.addEventListener('animationend',()=>t.remove(),{once:true}); },dur);
}

function burstParticles(){
  const splash=document.getElementById('splash'); if(!splash) return;
  const cx=splash.clientWidth/2, cy=splash.clientHeight/2;
  for(let i=0;i<22;i++){
    const p=document.createElement('div'); p.className='sp';
    const size=2+Math.random()*4;
    const angle=(Math.PI*2/22)*i+Math.random()*.4;
    const dist=60+Math.random()*120;
    const tx=Math.cos(angle)*dist, ty=Math.sin(angle)*dist-30;
    const dur=(.5+Math.random()*.5)+'s';
    p.style.cssText=`width:${size}px;height:${size}px;left:${cx}px;top:${cy}px;--tx2:${tx}px;--ty2:${ty}px;--dur:${dur};`;
    splash.appendChild(p); setTimeout(()=>p.classList.add('burst'),10); setTimeout(()=>p.remove(),900);
  }
}

const _rippledEls = new WeakSet();
function addRipple(el){
  if(!el||_rippledEls.has(el)) return;
  _rippledEls.add(el); el.classList.add('rh');
  el.addEventListener('click', function(e){
    const rect=this.getBoundingClientRect();
    const r=document.createElement('span');
    const size=Math.max(rect.width,rect.height);
    r.className='rp';
    r.style.cssText=`width:${size}px;height:${size}px;left:${e.clientX-rect.left-size/2}px;top:${e.clientY-rect.top-size/2}px`;
    this.appendChild(r);
    r.addEventListener('animationend',()=>r.remove(),{once:true});
  });
}

function closeAll(){
  if(openDD){ document.getElementById(openDD)?.classList.remove('open'); openDD=null; }
  document.querySelectorAll('.m-pill').forEach(p=>p.setAttribute('aria-expanded','false'));
  if(openPop){ document.getElementById(openPop)?.classList.remove('open'); openPop=null; }
  document.querySelectorAll('.sel-btn').forEach(b=>b.classList.remove('open'));
  document.getElementById('ov').classList.remove('on');
  document.getElementById('agModal').classList.remove('show');
  document.getElementById('profileOverlay')?.classList.remove('show');
}
