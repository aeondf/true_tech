// History sidebar interactions.

async function loadHistory() {
  if (!currentUserId) return;
  try {
    const response = await fetch(`${API}/history/${currentUserId}?limit=50`, {
      headers: authHeaders(),
    });
    if (!response.ok) return;
    const data = await response.json();
    renderSidebarHistory(data.conversations || []);
  } catch {}
}

async function deleteConversation(convId) {
  if (!currentUserId || !convId) return;
  try {
    const response = await fetch(`${API}/history/${currentUserId}/${convId}`, {
      method: 'DELETE',
      headers: authHeaders(),
    });
    if (response.ok) {
      if (currentConvId === convId) {
        newChat();
      }
      loadHistory();
      toast('Dialog deleted', 'ok', 2000);
    } else {
      toast('Delete failed', 'err');
    }
  } catch {
    toast('Delete failed', 'err');
  }
}

async function renameConversation(convId, currentTitle) {
  const newTitle = prompt('New chat title:', currentTitle || '');
  if (!newTitle || !newTitle.trim()) return;

  try {
    const response = await fetch(`${API}/history/${currentUserId}/${convId}`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json', ...authHeaders() },
      body: JSON.stringify({ title: newTitle.trim() }),
    });
    if (response.ok) {
      loadHistory();
      toast('Renamed', 'ok', 1800);
    } else {
      toast('Rename failed', 'err');
    }
  } catch {
    toast('Rename failed', 'err');
  }
}

function renderSidebarHistory(convs) {
  const historyNode = document.getElementById('sb-hist');
  historyNode.innerHTML = '';
  if (!convs.length) {
    historyNode.innerHTML = '<div style="padding:12px 10px;font-size:11.5px;color:var(--dim)">History is empty</div>';
    return;
  }

  const now = new Date();
  const today = new Date(now.getFullYear(), now.getMonth(), now.getDate());
  const yesterday = new Date(today - 86400000);
  const groups = { today: [], yesterday: [], earlier: [] };

  convs.forEach(conv => {
    const updatedAt = new Date(conv.updated_at || conv.created_at);
    if (updatedAt >= today) groups.today.push(conv);
    else if (updatedAt >= yesterday) groups.yesterday.push(conv);
    else groups.earlier.push(conv);
  });

  const labels = { today: 'Today', yesterday: 'Yesterday', earlier: 'Earlier' };
  for (const [key, list] of Object.entries(groups)) {
    if (!list.length) continue;

    const groupLabel = document.createElement('div');
    groupLabel.className = 'h-grp';
    groupLabel.textContent = labels[key];
    historyNode.appendChild(groupLabel);

    list.forEach(conv => {
      const item = document.createElement('div');
      item.className = 'h-item rh';
      item.dataset.convId = conv.id;
      const safeTitle = esc((conv.title || 'Untitled').slice(0, 40));

      item.innerHTML = `<div class="h-dot"></div><span class="h-item-lb">${safeTitle}</span><div class="h-actions"><button class="h-act-btn" title="Rename" onclick="event.stopPropagation();renameConversation('${conv.id}','${esc(conv.title || '')}')"><svg width="10" height="10" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" viewBox="0 0 24 24"><path d="M11 4H4a2 2 0 00-2 2v14a2 2 0 002 2h14a2 2 0 002-2v-7"/><path d="M18.5 2.5a2.121 2.121 0 013 3L12 15l-4 1 1-4z"/></svg></button><button class="h-act-btn h-del-btn" title="Delete" onclick="event.stopPropagation();deleteConversation('${conv.id}')"><svg width="10" height="10" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" viewBox="0 0 24 24"><polyline points="3 6 5 6 21 6"/><path d="M19 6l-1 14a2 2 0 01-2 2H8a2 2 0 01-2-2L5 6"/><path d="M10 11v6M14 11v6"/></svg></button></div>`;
      item.onclick = () => {
        document.querySelectorAll('.h-item').forEach(node => node.classList.remove('act'));
        item.classList.add('act');
        openConversation(conv.id);
      };
      historyNode.appendChild(item);
      addRipple(item);
    });
  }
}

async function openConversation(convId) {
  currentConvId = convId;
  currentMessages = [];
  sw('chat', document.getElementById('nav-chat'));

  try {
    const response = await fetch(`${API}/history/${currentUserId}/${convId}?limit=200`, {
      headers: authHeaders(),
    });
    if (!response.ok) return;

    const data = await response.json();
    const messages = data.messages || [];
    const panel = document.getElementById('panel-chat');
    const chatInner = document.getElementById('chatInner');
    chatInner.innerHTML = '';

    if (messages.length) {
      panel.classList.add('has-messages');
      document.getElementById('inpZoneBottom').style.display = 'block';
      messages.forEach(message => {
        if (message.role === 'system') return;
        currentMessages.push({ role: message.role, content: message.content });
        appendMsg(message.role === 'user' ? 'user' : 'ai', message.content, message.role === 'assistant', null);
      });
      scrollBot();
    }
  } catch {
    toast('Could not load dialog', 'err');
  }
}

function openH(el) {
  if (col) expandSb();
  document.querySelectorAll('.h-item').forEach(item => item.classList.remove('act'));
  el.classList.add('act');
  const convId = el.dataset.convId;
  if (convId) openConversation(convId);
  else sw('chat', document.getElementById('nav-chat'));
}

function newChat() {
  const panel = document.getElementById('panel-chat');
  panel.classList.remove('has-messages');
  document.getElementById('inpZoneBottom').style.display = 'none';
  document.getElementById('chatInner').innerHTML = '';
  document.querySelectorAll('.h-item').forEach(item => item.classList.remove('act'));
  document.getElementById('heroAgentIcon').style.display = 'none';
  currentMessages = [];
  currentConvId = uuid();
  currentAgent = null;
  sw('chat', document.getElementById('nav-chat'));
  setTimeout(() => document.getElementById('inpHero').focus(), 50);
}
