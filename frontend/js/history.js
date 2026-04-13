// ══════════════════════════════════════════════
//  history.js — conversation history (save, load, render)
// ══════════════════════════════════════════════

function fireSaveMessage(role, content, modelUsed) {
  if (!currentUserId || !currentConvId) return;
  fetch(`${API}/history/${currentUserId}/${currentConvId}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', ...authHeaders() },
    body: JSON.stringify({ role, content, model_used: modelUsed || null }),
  }).catch(() => {});
}

async function loadHistory() {
  if (!currentUserId) return;
  try {
    const r = await fetch(`${API}/history/${currentUserId}?limit=50`, { headers: authHeaders() });
    if (r.ok) {
      const d = await r.json();
      renderSidebarHistory(d.conversations || []);
    }
  } catch {}
}

function renderSidebarHistory(convs) {
  const hist = document.getElementById('sb-hist');
  hist.innerHTML = '';
  if (!convs.length) return;
  const now = new Date();
  const today = new Date(now.getFullYear(), now.getMonth(), now.getDate());
  const yesterday = new Date(today - 86400000);
  const groups = { today: [], yesterday: [], earlier: [] };
  for (const c of convs) {
    const d = new Date(c.updated_at || c.created_at);
    if (d >= today) groups.today.push(c);
    else if (d >= yesterday) groups.yesterday.push(c);
    else groups.earlier.push(c);
  }
  const labels = { today: 'Сегодня', yesterday: 'Вчера', earlier: 'Ранее' };
  for (const [key, list] of Object.entries(groups)) {
    if (!list.length) continue;
    const grp = document.createElement('div');
    grp.className = 'h-grp';
    grp.textContent = labels[key];
    hist.appendChild(grp);
    for (const c of list) {
      const item = document.createElement('div');
      item.className = 'h-item' + (c.id === currentConvId ? ' active' : '');
      item.dataset.convId = c.id;
      item.textContent = c.title || 'Без названия';
      item.onclick = () => openH(item);
      hist.appendChild(item);
    }
  }
}

async function openConversation(convId) {
  if (!currentUserId) return;
  try {
    const r = await fetch(`${API}/history/${currentUserId}/${convId}?limit=200`, { headers: authHeaders() });
    if (!r.ok) return;
    const d = await r.json();
    const msgs = d.messages || [];
    const panel = document.getElementById('panel-chat');
    const ci = document.getElementById('chatInner');
    ci.innerHTML = '';
    currentMessages = [];
    currentConvId = convId;
    if (msgs.length) {
      panel.classList.add('has-messages');
      document.getElementById('inpZoneBottom').style.display = 'block';
    }
    for (const m of msgs) {
      if (m.role === 'system') continue;
      currentMessages.push({ role: m.role, content: m.content });
      appendMsg(m.role === 'user' ? 'user' : 'ai', m.content, m.role === 'assistant', m.model_used);
    }
    scrollBot();
    sw('chat', null);
  } catch {}
}

function openH(el) {
  document.querySelectorAll('.h-item').forEach(i => i.classList.remove('active'));
  el.classList.add('active');
  const convId = el.dataset.convId;
  openConversation(convId);
}

function newChat() {
  const panel = document.getElementById('panel-chat');
  panel.classList.remove('has-messages');
  document.getElementById('inpZoneBottom').style.display = 'none';
  document.getElementById('chatInner').innerHTML = '';
  currentMessages = [];
  currentConvId = null;
  document.querySelectorAll('.h-item').forEach(i => i.classList.remove('active'));
  sw('chat', null);
  setTimeout(() => document.getElementById('inpHero')?.focus(), 100);
}
