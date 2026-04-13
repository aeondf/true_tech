// ══ AUTH-UI — authSubmitEmail(), authGoBack(), togglePwdVis(),
//              authSubmitCode(), initSplash(), checkHealth() ══

let authEmailVal='';

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

function authSubmitCode(){
  const pwd=document.getElementById('authPassword').value;
  if(!pwd){ const inp=document.getElementById('authPassword'); inp.style.borderColor='var(--red)'; inp.focus(); setTimeout(()=>inp.style.borderColor='',1200); return; }
  const btn=document.getElementById('authCodeBtn');
  btn.textContent='Входим...'; btn.disabled=true;

  const doLogin = () => apiAuthLogin(authEmailVal, pwd)
    .then(d => {
      authToken = d.token;
      currentUserId = d.user_id;
      localStorage.setItem('mts-token', authToken);
      localStorage.setItem('mts-user-id', currentUserId);
      localStorage.setItem('mts-user-email', d.email);
      document.getElementById('profInpEmail').value = d.email;
      const nameFromEmail = d.email.split('@')[0];
      document.getElementById('sbUserName').textContent = nameFromEmail;
      document.getElementById('sbAvatar').textContent = getInitials(nameFromEmail);
      document.getElementById('authScreen').classList.add('out');
      setTimeout(() => { document.getElementById('authScreen').style.display='none'; initSplash(); }, 680);
    })
    .catch(() => {
      return apiAuthRegister(authEmailVal, pwd)
        .then(d => {
          authToken = d.token;
          currentUserId = d.user_id;
          localStorage.setItem('mts-token', authToken);
          localStorage.setItem('mts-user-id', currentUserId);
          localStorage.setItem('mts-user-email', d.email);
          document.getElementById('profInpEmail').value = d.email;
          const nameFromEmail = d.email.split('@')[0];
          document.getElementById('sbUserName').textContent = nameFromEmail;
          document.getElementById('sbAvatar').textContent = getInitials(nameFromEmail);
          document.getElementById('authScreen').classList.add('out');
          setTimeout(() => { document.getElementById('authScreen').style.display='none'; initSplash(); }, 680);
        })
        .catch(regErr => {
          btn.textContent='Войти'; btn.disabled=false;
          const inp=document.getElementById('authPassword');
          inp.style.borderColor='var(--red)'; inp.focus();
          setTimeout(()=>inp.style.borderColor='',1800);
          toast(regErr.message || 'Ошибка входа', 'err', 3000);
        });
    });

  doLogin();
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
