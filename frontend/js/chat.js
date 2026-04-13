// ══════════════════════════════════════════════
//  chat.js — main send, streaming, file handling
// ══════════════════════════════════════════════

async function handleF(files, chipsId) {
  const c = document.getElementById(chipsId);
  for (const f of Array.from(files)) {
    const ch = document.createElement('div');
    ch.className = 'f-chip';
    ch.dataset.name = f.name;
    ch.dataset.mime = f.type || 'application/octet-stream';
    const ext = f.name.split('.').pop().toLowerCase();
    const isImg = ['jpg', 'jpeg', 'png', 'gif', 'webp', 'svg'].includes(ext);
    ch.dataset.isImage = isImg ? '1' : '0';
    ch.innerHTML = `<svg width="11" height="11" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round" viewBox="0 0 24 24"><path d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8z"/><polyline points="14 2 14 8 20 8"/></svg>${esc(f.name)}<span class="chip-status" style="margin-left:3px;font-size:10px;color:var(--dim)">⏳</span><button onclick="this.parentElement.remove()">×</button>`;
    c.appendChild(ch);
    chipFileMap.set(ch, f);

    if (!isImg) {
      // Document upload — fire & forget, show status
      try {
        const fd = new FormData();
        fd.append('file', f);
        fd.append('user_id', currentUserId || 'anonymous');
        const r = await fetch(`${API}/files/upload`, { method: 'POST', body: fd, headers: authHeaders() });
        const st = ch.querySelector('.chip-status');
        if (r.ok) {
          const d = await r.json().catch(() => ({}));
          ch.dataset.fileId = d.file_id || '';
          if (st) { st.textContent = '✓'; st.style.color = '#22C55E'; }
          toast(`Файл загружен: ${f.name}`, 'ok', 2000);
        } else {
          if (st) { st.textContent = '✗'; st.style.color = 'var(--red)'; }
          toast(`Ошибка загрузки ${f.name}`, 'err');
        }
      } catch {
        const st = ch.querySelector('.chip-status');
        if (st) { st.textContent = '✗'; st.style.color = 'var(--red)'; }
        toast(`Ошибка: ${f.name}`, 'err');
      }
    } else {
      // Image — read as base64 for VLM
      try {
        const b64 = await fileToBase64(f);
        ch.dataset.b64 = b64;
        const st = ch.querySelector('.chip-status');
        if (st) { st.textContent = '✓'; st.style.color = '#22C55E'; }
      } catch {
        const st = ch.querySelector('.chip-status');
        if (st) { st.textContent = '✗'; st.style.color = 'var(--red)'; }
      }
    }
  }
}

async function doSend(src) {
  if (isStreaming) return;
  const ta = src === 'hero' ? document.getElementById('inpHero') : document.getElementById('inpBot');
  const chipsId = src === 'hero' ? 'fChipsHero' : 'fChipsBot';
  const chips = document.getElementById(chipsId);
  const txt = ta.value.trim();
  const voiceId = src === 'hero' ? 'H' : 'B';
  const voiceChip = chips?.querySelector('.v-chip');

  // Voice recording takes priority
  if (voiceChip && vBlob[voiceId]) {
    const textContext = txt || '';
    await sendVoiceMsg(voiceId, chips, textContext);
    ta.value = ''; ta.style.height = 'auto';
    return;
  }
  if (!txt) return;

  const panel = document.getElementById('panel-chat');
  const ci = document.getElementById('chatInner');
  if (!panel.classList.contains('has-messages')) {
    panel.classList.add('has-messages');
    document.getElementById('inpZoneBottom').style.display = 'block';
    if (!currentConvId) currentConvId = uuid();
    setTimeout(() => document.getElementById('inpBot').focus(), 50);
  }

  // Collect attachments from chips
  const attachments = [];
  const fileChips = chips ? [...chips.querySelectorAll('.f-chip:not(.v-chip)')] : [];
  for (const ch of fileChips) {
    const att = { name: ch.dataset.name, mime: ch.dataset.mime || 'application/octet-stream' };
    if (ch.dataset.b64) att.data = ch.dataset.b64;
    attachments.push(att);
  }

  ta.value = ''; ta.style.height = 'auto';
  if (chips) chips.innerHTML = '';
  document.getElementById(src === 'hero' ? 'fChipsBot' : 'fChipsHero').innerHTML = '';

  currentMessages.push({ role: 'user', content: txt });
  appendMsg('user', txt, false, null);

  const typing = document.createElement('div');
  typing.className = 'msg'; typing.id = 'typing';
  const tBadge = selectedModel === 'auto' ? 'Авто' : (selectedModelName || selectedModel);
  typing.innerHTML = `<div class="msg-av ai">AI</div><div class="msg-body"><div class="msg-meta"><span class="msg-sender">${esc(tBadge)}</span></div><div class="msg-bbl" style="color:var(--muted)"><span style="display:inline-block;animation:vwa 1s ease-in-out 0s infinite">●</span><span style="display:inline-block;animation:vwa 1s ease-in-out .18s infinite"> ●</span><span style="display:inline-block;animation:vwa 1s ease-in-out .36s infinite"> ●</span></div></div>`;
  ci.appendChild(typing); scrollBot();

  // Agent routing
  if (currentAgent?.id === 'deepresearch') { typing.remove(); await doDeepResearch(txt, ci); return; }
  if (currentAgent?.id === 'imagegen')     { typing.remove(); await doImageGen(txt, ci);     return; }

  fireSaveMessage('user', txt, null);

  isStreaming = true;
  try {
    const memBlock = buildMemoryBlock();
    const body = {
      model: selectedModel,
      messages: [...currentMessages],
      stream: true,
      user: currentUserId || 'anonymous',
      conversation_id: currentConvId,
      ...(memBlock && { system_prompt: memBlock }),
    };
    if (attachments.length) body.attachments = attachments;

    const resp = await fetch(`${API}/chat/completions`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', ...authHeaders() },
      body: JSON.stringify(body),
    });
    if (!resp.ok) {
      const err = await resp.json().catch(() => ({}));
      throw new Error(err?.error?.message || `HTTP ${resp.status}`);
    }

    document.getElementById('typing')?.remove();
    const aiEl = appendMsg('ai', '', false, null);
    const bbl = aiEl.querySelector('.msg-bbl');
    let full = ''; let buf = ''; let usedModelId = null;

    const reader = resp.body.getReader();
    const dec = new TextDecoder();
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      buf += dec.decode(value, { stream: true });
      const lines = buf.split('\n'); buf = lines.pop() || '';
      for (const line of lines) {
        if (!line.startsWith('data:')) continue;
        const data = line.slice(5).trim();
        if (data === '[DONE]') break;
        try {
          const json = JSON.parse(data);
          if (json.model && json.model !== 'auto' && !usedModelId) {
            usedModelId = json.model;
            updateMsgModel(aiEl, usedModelId);
          }
          const delta = json.choices?.[0]?.delta?.content || '';
          if (delta) { full += delta; bbl.innerHTML = renderMd(full); scrollBot(); }
        } catch {}
      }
    }

    if (!usedModelId && selectedModel !== 'auto') updateMsgModel(aiEl, selectedModel);

    aiEl.querySelector('.copyBtn').onclick = () => {
      navigator.clipboard.writeText(full).then(() => toast('Скопировано', 'ok', 1500));
    };
    currentMessages.push({ role: 'assistant', content: full });
    fireSaveMessage('assistant', full, usedModelId || (selectedModel !== 'auto' ? selectedModel : null));
    fireExtractMemory(full);
    setTimeout(() => loadHistory(), 800);
  } catch (e) {
    document.getElementById('typing')?.remove();
    appendMsg('ai', '⚠ Ошибка соединения: ' + e.message, false, null);
    toast('Ошибка API: ' + e.message, 'err', 4000);
  } finally { isStreaming = false; }
}
