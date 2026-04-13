// ══ PROFILE — openProfile(), closeProfile(), closeProfileOuter(), getInitials(),
//              saveProfile(), switchProfTab(), checkPwdStrength(), changePassword(),
//              selectPlan(), savePlan(), logoutProfile() ══

function openProfile(){
  document.getElementById('profName').textContent=document.getElementById('profInpName').value||'MTS User';
  document.getElementById('profAvInitials').textContent=getInitials(document.getElementById('profInpName').value||'MTS User');
  document.getElementById('profileOverlay').classList.add('show');
  document.getElementById('ov').classList.add('on');
}

function closeProfile(){
  document.getElementById('profileOverlay').classList.remove('show');
  document.getElementById('ov').classList.remove('on');
}

function closeProfileOuter(e){
  if(e.target===document.getElementById('profileOverlay')) closeProfile();
}

function getInitials(name){
  return name.trim().split(/\s+/).map(w=>w[0]||'').join('').toUpperCase().slice(0,2)||'МТ';
}

function saveProfile(){
  const name=document.getElementById('profInpName').value.trim()||'MTS User';
  const initials=getInitials(name);
  document.getElementById('sbUserName').textContent=name;
  document.getElementById('sbAvatar').textContent=initials;
  document.getElementById('profName').textContent=name;
  document.getElementById('profAvInitials').textContent=initials;
  const btn=document.querySelector('#profTab-account .prof-save');
  if(btn){ const orig=btn.textContent; btn.textContent='✓ Сохранено'; setTimeout(()=>btn.textContent=orig,1800); }
  toast('Профиль обновлён','ok');
}

function switchProfTab(tab,btn){
  document.querySelectorAll('.prof-tab').forEach(t=>t.classList.remove('act'));
  document.querySelectorAll('.prof-tab-panel').forEach(p=>p.classList.remove('act'));
  btn.classList.add('act'); document.getElementById('profTab-'+tab)?.classList.add('act');
}

function checkPwdStrength(val){
  const bar=document.getElementById('profPwdBar'); if(!bar) return;
  if(!val){ bar.style.width='0%'; return; }
  const hasUpper=/[A-Z]/.test(val),hasNum=/[0-9]/.test(val),hasSpec=/[^A-Za-z0-9]/.test(val);
  const score=val.length<6?1:val.length<10?2:(hasUpper&&hasNum&&hasSpec)?4:(hasUpper||hasNum)?3:2;
  bar.style.width=(score*25)+'%'; bar.style.background=['','#ef4444','#f97316','#eab308','#22c55e'][score];
}

function changePassword(){
  const curr=document.getElementById('profPwdCurrent');
  const newP=document.getElementById('profPwdNew');
  const conf=document.getElementById('profPwdConfirm');
  if(!curr||!newP||!conf) return;
  if(!curr.value){ toast('Введите текущий пароль','err'); return; }
  if(newP.value.length<6){ toast('Минимум 6 символов','err'); return; }
  if(newP.value!==conf.value){ toast('Пароли не совпадают','err'); return; }
  curr.value=''; newP.value=''; conf.value='';
  const bar=document.getElementById('profPwdBar'); if(bar) bar.style.width='0%';
  toast('Пароль изменён','ok');
}

let _selectedPlan='pro';

function selectPlan(id){
  _selectedPlan=id;
  document.querySelectorAll('.prof-plan-card').forEach(c=>c.classList.remove('selected'));
  document.getElementById('plan-'+id)?.classList.add('selected');
}

function savePlan(){
  const labels={free:'Бесплатный',pro:'Pro план',enterprise:'Enterprise'};
  const label=labels[_selectedPlan]||'Pro план';
  document.getElementById('sbUserPlan').textContent=label;
  document.getElementById('profPlan').textContent=label;
  toast('Тариф обновлён','ok');
}

function logoutProfile(){
  closeProfile();
  authToken = null;
  localStorage.removeItem('mts-token');
  localStorage.removeItem('mts-user-id');
  localStorage.removeItem('mts-user-email');
  userMemory = [];
  setTimeout(()=>{
    const auth=document.getElementById('authScreen');
    if(auth){
      auth.style.display='flex'; auth.classList.remove('out');
      document.getElementById('authStep1').style.display='flex';
      document.getElementById('authStep2').style.display='none';
      document.getElementById('authEmail').value=''; document.getElementById('authPassword').value='';
      const btn=document.getElementById('authCodeBtn'); if(btn){ btn.textContent='Войти'; btn.disabled=false; }
      auth.style.animation='none'; auth.style.opacity='1'; auth.style.transform='none';
      setTimeout(()=>document.getElementById('authEmail')?.focus(),200);
    }
    currentUserId=null; currentConvId=null; currentMessages=[];
    document.getElementById('sb-hist').innerHTML='';
    document.getElementById('sbUserName').textContent='MTS User';
    document.getElementById('sbAvatar').textContent='МТ';
  },350);
  toast('Выход из аккаунта','inf');
}
