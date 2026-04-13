// ══ AUTH-UI — authSubmitEmail(), authGoBack(), togglePwdVis(),
//              authSubmitCode(), initSplash(), checkHealth() ══

let authEmailVal='';
let regMode=false;

function toggleRegMode(){
  regMode=!regMode;
  document.getElementById('authConfirmWrap').style.display=regMode?'block':'none';
  document.getElementById('authConfirmPwd').value='';
  document.getElementById('authCodeBtn').textContent=regMode?'Создать аккаунт':'Войти';
  document.getElementById('authStep2Title').textContent=regMode?'Создать аккаунт':'Введите пароль';
  document.getElementById('authModeToggleText').textContent=regMode?'Уже есть аккаунт? Войти →':'Нет аккаунта? Зарегистрироваться →';
}

function authSubmitEmail(){
  const inp=document.getElementById('authEmail');
  const val=inp.value.trim();
  if(!val||!val.includes('@')){ inp.style.borderColor='var(--red)'; inp.focus(); setTimeout(()=>inp.style.borderColor='',1200); return; }
  authEmailVal=val;
  document.getElementById('authEmailShow').textContent=val;
  const s1=document.getElementById('authStep1');
  s1.classList.add('exit-left');
  setTimeout(()=>{
    s1.style.display='none'; s1.classList.remove('exit-left');
    const s2=document.getElementById('authStep2');
    s2.style.display='flex'; s2.style.opacity='1';
    s2.classList.add('enter-right'); setTimeout(()=>s2.classList.remove('enter-right'),450);
    setTimeout(()=>document.getElementById('authPassword')?.focus(),80);
  },290);
}

function authGoBack(){
  const s2=document.getElementById('authStep2');
  s2.classList.add('exit-left');
  setTimeout(()=>{
    s2.style.display='none'; s2.classList.remove('exit-left');
    document.getElementById('authPassword').value='';
    document.getElementById('authConfirmPwd').value='';
    if(regMode){ regMode=false; document.getElementById('authConfirmWrap').style.display='none'; document.getElementById('authCodeBtn').textContent='Войти'; document.getElementById('authStep2Title').textContent='Введите пароль'; document.getElementById('authModeToggleText').textContent='Нет аккаунта? Зарегистрироваться →'; }
    const s1=document.getElementById('authStep1'); s1.style.display='flex';
    s1.classList.add('enter-right'); setTimeout(()=>s1.classList.remove('enter-right'),450);
    setTimeout(()=>document.getElementById('authEmail')?.focus(),80);
  },290);
}

function togglePwdVis(){
  const inp=document.getElementById('authPassword');
  const icon=document.getElementById('pwdEyeIcon');
  if(inp.type==='password'){ inp.type='text'; icon.innerHTML='<path d="M17.94 17.94A10.07 10.07 0 0112 20c-7 0-11-8-11-8a18.45 18.45 0 015.06-5.94"/><path d="M9.9 4.24A9.12 9.12 0 0112 4c7 0 11 8 11 8a18.5 18.5 0 01-2.16 3.19"/><line x1="1" y1="1" x2="23" y2="23"/>'; }
  else { inp.type='password'; icon.innerHTML='<path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/><circle cx="12" cy="12" r="3"/>'; }
}

function _authSuccess(d){
  authToken=d.token; currentUserId=d.user_id;
  localStorage.setItem('mts-token',authToken);
  localStorage.setItem('mts-user-id',currentUserId);
  localStorage.setItem('mts-user-email',d.email);
  document.getElementById('profInpEmail').value=d.email;
  const savedName=localStorage.getItem('mts-display-name');
  const displayName=savedName||d.email.split('@')[0];
  document.getElementById('profInpName').value=displayName;
  document.getElementById('sbUserName').textContent=displayName;
  document.getElementById('sbAvatar').textContent=getInitials(displayName);
  const org=localStorage.getItem('mts-org')||'';
  if(org) document.getElementById('profInpOrg').value=org;
  document.getElementById('authScreen').classList.add('out');
  setTimeout(()=>{ document.getElementById('authScreen').style.display='none'; initSplash(); },680);
}

function authSubmitCode(){
  const pwd=document.getElementById('authPassword').value;
  if(!pwd){ const inp=document.getElementById('authPassword'); inp.style.borderColor='var(--red)'; inp.focus(); setTimeout(()=>inp.style.borderColor='',1200); return; }
  const btn=document.getElementById('authCodeBtn');

  if(regMode){
    const conf=document.getElementById('authConfirmPwd').value;
    if(!conf){ const inp=document.getElementById('authConfirmPwd'); inp.style.borderColor='var(--red)'; inp.focus(); setTimeout(()=>inp.style.borderColor='',1200); return; }
    if(pwd!==conf){ toast('Пароли не совпадают','err'); return; }
    btn.textContent='Создаём...'; btn.disabled=true;
    apiAuthRegister(authEmailVal,pwd)
      .then(_authSuccess)
      .catch(e=>{ btn.textContent='Создать аккаунт'; btn.disabled=false; toast(e.message||'Ошибка регистрации','err',3000); });
  } else {
    btn.textContent='Входим...'; btn.disabled=true;
    apiAuthLogin(authEmailVal,pwd)
      .then(_authSuccess)
      .catch(e=>{ btn.textContent='Войти'; btn.disabled=false; const inp=document.getElementById('authPassword'); inp.style.borderColor='var(--red)'; inp.focus(); setTimeout(()=>inp.style.borderColor='',1800); toast(e.message||'Неверный пароль','err',3000); });
  }
}

function initSplash(){
  const letters=['sl-m','sl-t','sl-s'];
  setTimeout(()=>{ const b=document.getElementById('splash-brain'); b?.classList.add('show'); setTimeout(()=>b?.classList.add('glow'),700); },200);
  letters.forEach((id,i)=>{ setTimeout(()=>document.getElementById(id)?.classList.add('lit'),500+i*200); });
  setTimeout(burstParticles,1200);
  setTimeout(()=>document.getElementById('splash-sub')?.classList.add('show'),1550);
  setTimeout(()=>document.getElementById('splash-letters')?.classList.add('gather'),2100);
  setTimeout(()=>{ document.getElementById('splash')?.classList.add('out'); document.getElementById('appRoot')?.classList.add('vis'); },2900);
  setTimeout(()=>{
    document.getElementById('splash')?.remove();
    fetchModels();
    loadHistory();
    loadMemory();
    checkHealth();
    currentConvId=uuid();
  },3600);
}

async function checkHealth(){
  try {
    const r=await fetch(`${API}/health`,{signal:AbortSignal.timeout(4000)});
    const d=await r.json();
    toast(d.status==='ok'?'Бэкенд подключён ✓':'Бэкенд: деградированный режим',d.status==='ok'?'ok':'inf',2500);
  } catch { toast('Бэкенд недоступен — запустите backend на :8000','err',5000); }
}
