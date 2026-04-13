// ══════════════════════════════════════════════
//  voice.js — recording + voice message API
// ══════════════════════════════════════════════

const vOn   = {};   // {id: bool}
const vBlob = {};   // {id: Blob|null}
const vInt  = {};   // {id: intervalId}
const vSec  = {};   // {id: seconds}

function fmtTime(s) { return String(Math.floor(s / 60)).padStart(2, '0') + ':' + String(s % 60).padStart(2, '0'); }

function toggleV(id) { if (vOn[id]) stopVoice(id); else startVoice(id); }

function startVoice(id) {
  if (vOn[id]) return;
  vOn[id] = true; vSec[id] = 0; vBlob[id] = null;
  const btn = document.getElementById('vBtn' + id);
  const timer = document.getElementById('vTimer' + id);
  const wave = document.getElementById('vWave' + id);
  if (btn) btn.classList.add('on');
  if (wave) wave.classList.add('on');
  if (timer) { timer.textContent = '00:00'; timer.classList.add('on'); }
  document.getElementById('send' + id)?.classList.add('voice-mode');

  if (!navigator.mediaDevices?.getUserMedia) {
    vOn[id] = false;
    toast('Микрофон недоступен', 'err');
    if (btn) btn.classList.remove('on');
    if (wave) wave.classList.remove('on');
    if (timer) timer.classList.remove('on');
    document.getElementById('send' + id)?.classList.remove('voice-mode');
    return;
  }

  navigator.mediaDevices.getUserMedia({ audio: true }).then(stream => {
    const chunks = [];
    const mr = new MediaRecorder(stream);
    mr.ondataavailable = e => { if (e.data.size > 0) chunks.push(e.data); };
    mr.onstop = () => {
      const blob = new Blob(chunks, { type: 'audio/webm' });
      vBlob[id] = blob;
      stream.getTracks().forEach(t => t.stop());
      // Add visual chip
      const chipsId = id === 'H' ? 'fChipsHero' : 'fChipsBot';
      const c = document.getElementById(chipsId);
      if (c) {
        c.querySelector('.v-chip')?.remove();
        const ch = document.createElement('div');
        ch.className = 'f-chip v-chip';
        ch.innerHTML = `<svg width="11" height="11" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" viewBox="0 0 24 24"><path d="M12 1a3 3 0 00-3 3v7a3 3 0 006 0V4a3 3 0 00-3-3z"/><path d="M5 10a7 7 0 0014 0"/><line x1="12" y1="17" x2="12" y2="21"/></svg>Голосовое<span class="v-chip-dur">${fmtTime(vSec[id])}</span><button onclick="this.parentElement.remove();vBlob['${id}']=null">×</button>`;
        c.appendChild(ch);
      }
    };
    mr.start();
    vInt[id] = setInterval(() => {
      vSec[id]++;
      if (timer) timer.textContent = fmtTime(vSec[id]);
      if (vSec[id] >= 120) stopVoice(id); // auto-stop at 2 min
    }, 1000);
    vOn[id + '_mr'] = mr;
  }).catch(e => {
    vOn[id] = false;
    toast('Микрофон недоступен: ' + e.message, 'err');
    if (btn) btn.classList.remove('on');
    if (wave) wave.classList.remove('on');
    if (timer) timer.classList.remove('on');
    document.getElementById('send' + id)?.classList.remove('voice-mode');
  });
}

function stopVoice(id) {
  vOn[id] = false;
  clearInterval(vInt[id]);
  const btn = document.getElementById('vBtn' + id);
  const timer = document.getElementById('vTimer' + id);
  const wave = document.getElementById('vWave' + id);
  if (btn) btn.classList.remove('on');
  if (wave) wave.classList.remove('on');
  if (timer) { timer.classList.remove('on'); }
  document.getElementById('send' + id)?.classList.remove('voice-mode');
  const mr = vOn[id + '_mr'];
  if (mr && mr.state !== 'inactive') mr.stop();
  vOn[id + '_mr'] = null;
}

// Called by the send button when voice chip is present
function sendOrStopVoice(id) {
  if (vOn[id]) stopVoice(id);
  else doSend(id === 'H' ? 'hero' : 'bot');
}

async function sendVoiceMsg(id, chips, textContext) {
  const blob = vBlob[id];
  if (!blob) { toast('Нет аудиозаписи', 'err'); return; }
  const panel = document.getElementById('panel-chat');
  const ci = document.getElementById('chatInner');
  if (!panel.classList.contains('has-messages')) {
    panel.classList.add('has-messages');
    document.getElementById('inpZoneBottom').style.display = 'block';
    if (!currentConvId) currentConvId = uuid();
  }
  if (chips) chips.innerHTML = '';
  vBlob[id] = null;

  const userLabel = textContext ? `🎤 ${textContext}` : '🎤 Голосовое сообщение';
  const sendEl = appendMsg('user', userLabel, false, null);
  const typing = document.createElement('div');
  typing.className = 'msg'; typing.id = 'typing';
  typing.innerHTML = `<div class="msg-av ai">AI</div><div class="msg-body"><div class="msg-meta"><span class="msg-sender">Голос → AI</span></div><div class="msg-bbl" style="color:var(--muted)"><span style="display:inline-block;animation:vwa 1s ease-in-out 0s infinite">●</span><span style="display:inline-block;animation:vwa 1s ease-in-out .18s infinite"> ●</span><span style="display:inline-block;animation:vwa 1s ease-in-out .36s infinite"> ●</span></div></div>`;
  ci.appendChild(typing); scrollBot();
  isStreaming = true;
  try {
    const fd = new FormData();
    fd.append('audio', blob, 'recording.webm');
    fd.append('user_id', currentUserId || 'anonymous');
    const resp = await fetch(`${API}/voice/message`, { method: 'POST', body: fd, headers: authHeaders() });
    document.getElementById('typing')?.remove();

    // FIX: check HTTP status before reading headers
    if (!resp.ok) {
      const err = await resp.json().catch(() => ({}));
      throw new Error(err.error || err.detail || `HTTP ${resp.status}`);
    }

    const ct = resp.headers.get('content-type') || '';
    if (ct.includes('audio')) {
      const transcript = decodeURIComponent(resp.headers.get('X-Transcript') || '');
      const answer = decodeURIComponent(resp.headers.get('X-Answer') || '');
      sendEl.querySelector('.msg-bbl').textContent = transcript || userLabel;
      appendMsg('ai', answer, false, null); scrollBot();
      const audioBlob = await resp.blob();
      const url = URL.createObjectURL(audioBlob);
      const audio = new Audio(url);
      audio.play().catch(() => {});
      audio.onended = () => URL.revokeObjectURL(url);
      if (transcript) currentMessages.push({ role: 'user', content: transcript });
      if (answer)     currentMessages.push({ role: 'assistant', content: answer });
      fireSaveMessage('user', transcript || userLabel, null);
      fireSaveMessage('assistant', answer, null);
      fireExtractMemory(answer);
    } else {
      // TTS unavailable — JSON fallback
      const data = await resp.json();
      const transcript = data.transcript || userLabel;
      const answer = data.answer || 'Голосовой ответ получен';
      sendEl.querySelector('.msg-bbl').textContent = transcript;
      appendMsg('ai', answer, false, null); scrollBot();
      toast('TTS недоступен — только текст', 'inf');
      currentMessages.push({ role: 'user', content: transcript });
      currentMessages.push({ role: 'assistant', content: answer });
      fireSaveMessage('user', transcript, null);
      fireSaveMessage('assistant', answer, null);
      fireExtractMemory(answer);
    }
    setTimeout(() => loadHistory(), 800);
  } catch (e) {
    document.getElementById('typing')?.remove();
    appendMsg('ai', '⚠ Ошибка голосового API: ' + e.message, false, null);
    toast('Ошибка голосового API: ' + e.message, 'err');
  } finally { isStreaming = false; }
}
