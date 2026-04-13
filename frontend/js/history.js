// ══ HISTORY — loadHistory(), deleteConversation(), renameConversation(),
//              renderSidebarHistory(), openConversation(), openH(), newChat() ══

async function loadHistory(){
  if(!currentUserId) return;
  try {
    const r=await fetch(`${API}/history/${currentUserId}?limit=50`);
    if(!r.ok) return;
    const d=await r.json();
    renderSidebarHistory(d.conversations||[]);
  } catch {}
}

async function deleteConversation(convId){
  if(!currentUserId||!convId) return;
  try {
    const r=await fetch(`${API}/history/${currentUserId}/${convId}`,{method:'DELETE'});
    if(r.ok){
      if(currentConvId===convId){
        newChat();
      }
      loadHistory();
      toast('Диалог удалён','ok',2000);
    } else { toast('Ошибка удаления','err'); }
  } catch { toast('Ошибка удаления','err'); }
}

async function renameConversation(convId, currentTitle){
  const newTitle=prompt('Новое название диалога:', currentTitle||'');
  if(!newTitle||!newTitle.trim()) return;
  try {
    const r=await fetch(`${API}/history/${currentUserId}/${convId}`,{
      method:'PATCH', headers:{'Content-Type':'application/json'},
      body:JSON.stringify({title:newTitle.trim()})
    });
    if(r.ok){ loadHistory(); toast('Переименовано','ok',1800); }
    else { toast('Ошибка переименования','err'); }
  } catch { toast('Ошибка переименования','err'); }
}

function renderSidebarHistory(convs){
  const hist=document.getElementById('sb-hist'); hist.innerHTML='';
  if(!convs.length){ hist.innerHTML='<div style="padding:12px 10px;font-size:11.5px;color:var(--dim)">История пустая</div>'; return; }
  const now=new Date();
  const today=new Date(now.getFullYear(),now.getMonth(),now.getDate());
  const yesterday=new Date(today-86400000);
  const groups={today:[],yesterday:[],earlier:[]};
  convs.forEach(c=>{
    const d=new Date(c.updated_at||c.created_at);
    if(d>=today) groups.today.push(c);
    else if(d>=yesterday) groups.yesterday.push(c);
    else groups.earlier.push(c);
  });
  const labels={today:'Сегодня',yesterday:'Вчера',earlier:'Ранее'};
  for(const [key,list] of Object.entries(groups)){
    if(!list.length) continue;
    const grp=document.createElement('div'); grp.className='h-grp'; grp.textContent=labels[key]; hist.appendChild(grp);
    list.forEach(c=>{
      const item=document.createElement('div');
      item.className='h-item rh'; item.dataset.convId=c.id;
      const title=esc((c.title||'Без названия').slice(0,40));
      item.innerHTML=`<div class="h-dot"></div><span class="h-item-lb">${title}</span><div class="h-actions"><button class="h-act-btn" title="Переименовать" onclick="event.stopPropagation();renameConversation('${c.id}','${esc(c.title||'')}')"><svg width="10" height="10" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" viewBox="0 0 24 24"><path d="M11 4H4a2 2 0 00-2 2v14a2 2 0 002 2h14a2 2 0 002-2v-7"/><path d="M18.5 2.5a2.121 2.121 0 013 3L12 15l-4 1 1-4z"/></svg></button><button class="h-act-btn h-del-btn" title="Удалить" onclick="event.stopPropagation();deleteConversation('${c.id}')"><svg width="10" height="10" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" viewBox="0 0 24 24"><polyline points="3 6 5 6 21 6"/><path d="M19 6l-1 14a2 2 0 01-2 2H8a2 2 0 01-2-2L5 6"/><path d="M10 11v6M14 11v6"/></svg></button></div>`;
      item.onclick=()=>{ document.querySelectorAll('.h-item').forEach(h=>h.classList.remove('act')); item.classList.add('act'); openConversation(c.id); };
      hist.appendChild(item); addRipple(item);
    });
  }
}

async function openConversation(convId){
  currentConvId=convId; currentMessages=[];
  sw('chat',document.getElementById('nav-chat'));
  try {
    const r=await fetch(`${API}/history/${currentUserId}/${convId}?limit=200`);
    if(!r.ok) return;
    const d=await r.json();
    const msgs=d.messages||[];
    const panel=document.getElementById('panel-chat');
    const ci=document.getElementById('chatInner'); ci.innerHTML='';
    if(msgs.length){
      panel.classList.add('has-messages');
      document.getElementById('inpZoneBottom').style.display='block';
      msgs.forEach(m=>{
        if(m.role==='system') return;
        currentMessages.push({role:m.role,content:m.content});
        appendMsg(m.role==='user'?'user':'ai', m.content, m.role==='assistant', null);
      });
      scrollBot();
    }
  } catch { toast('Не удалось загрузить диалог','err'); }
}

function openH(el){
  if(col) expandSb();
  document.querySelectorAll('.h-item').forEach(h=>h.classList.remove('act'));
  el.classList.add('act');
  const convId=el.dataset.convId;
  if(convId) openConversation(convId);
  else sw('chat',document.getElementById('nav-chat'));
}

function newChat(){
  const panel=document.getElementById('panel-chat');
  panel.classList.remove('has-messages');
  document.getElementById('inpZoneBottom').style.display='none';
  document.getElementById('chatInner').innerHTML='';
  document.querySelectorAll('.h-item').forEach(h=>h.classList.remove('act'));
  document.getElementById('heroAgentIcon').style.display='none';
  currentMessages=[]; currentConvId=uuid(); currentAgent=null;
  sw('chat',document.getElementById('nav-chat'));
  setTimeout(()=>document.getElementById('inpHero').focus(),50);
}
