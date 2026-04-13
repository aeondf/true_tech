// ══ UI — sw(), toggleSb(), expandSb(), togglePop(), pickTemp(),
//         toggleTheme(), toggleBgWords(), handleK() ══

const PANELS=['chat','agents','settings'];
const PANEL_ORDER={chat:0,agents:1,settings:2};
let curPanel='chat';

function sw(name,btn){
  if(col) expandSb();
  const fromIdx=PANEL_ORDER[curPanel]??0, toIdx=PANEL_ORDER[name]??0;
  const dir=toIdx>fromIdx?'slide-left':'slide-right';
  PANELS.forEach(p=>{
    document.getElementById('panel-'+p).classList.remove('act','slide-left','slide-right');
    document.getElementById('nav-'+p).classList.remove('act');
  });
  const target=document.getElementById('panel-'+name);
  target.classList.add('act',dir);
  setTimeout(()=>target.classList.remove('slide-left','slide-right'),280);
  (btn||document.getElementById('nav-'+name)).classList.add('act');
  curPanel=name;
  if(name==='settings') document.querySelectorAll('#panel-settings .st-row').forEach((r,i)=>r.style.transitionDelay=(i*35)+'ms');
}

let col=false;
function toggleSb(){ col=true; document.getElementById('sb').classList.add('col'); }
function expandSb(){ col=false; document.getElementById('sb').classList.remove('col'); }

let openPop=null;
function togglePop(id,e,btn){
  e.stopPropagation();
  const pop=document.getElementById(id);
  if(openPop&&openPop!==id){ document.getElementById(openPop)?.classList.remove('open'); document.querySelectorAll('.sel-btn').forEach(b=>b.classList.remove('open')); }
  const isOpen=pop.classList.toggle('open');
  btn.classList.toggle('open',isOpen);
  openPop=isOpen?id:null;
  document.getElementById('ov').classList.toggle('on',!!(openPop||openDD));
}

function pickTemp(e,el,val,sub){
  e.stopPropagation();
  document.getElementById('tempVal').textContent=val; document.getElementById('tempSub').textContent=sub;
  const pop=document.getElementById('pTemp');
  pop.querySelectorAll('.sel-opt').forEach(o=>{ o.classList.remove('on'); o.querySelector('.sel-chk').textContent=''; });
  el.classList.add('on'); el.querySelector('.sel-chk').textContent='✓';
  pop.classList.remove('open'); document.getElementById('tempBtn').classList.remove('open');
  openPop=null; document.getElementById('ov').classList.remove('on');
}

function toggleTheme(btn){
  btn.classList.toggle('on');
  const isDark=!btn.classList.contains('on');
  document.documentElement.setAttribute('data-theme',isDark?'dark':'light');
  localStorage.setItem('mts-theme',isDark?'dark':'light');
}

function toggleBgWords(btn){
  const el=document.getElementById('bgWords');
  const off=el.classList.toggle('off');
  localStorage.setItem('bgWordsOff',off?'1':'0');
}

function handleK(e,src){ if(e.key==='Enter'&&!e.shiftKey){ e.preventDefault(); doSend(src); } }
