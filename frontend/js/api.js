// ══ API — const API, authHeaders(), apiAuthRegister(), apiAuthLogin(),
//          loadMemory(), buildMemoryBlock(), fireExtractMemory(), fireSaveMessage() ══

const API = 'http://localhost:8000/v1';

// Auth state
let authToken = localStorage.getItem('mts-token') || null;
let userMemory = [];   // [{key, value, category, score}]

function authHeaders() {
  return authToken ? { 'Authorization': 'Bearer ' + authToken } : {};
}

async function apiAuthRegister(email, password) {
  const r = await fetch(`${API}/auth/register`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email, password }),
  });
  if (!r.ok) {
    const d = await r.json().catch(() => ({}));
    throw new Error(d.detail || 'Ошибка регистрации');
  }
  return r.json();
}

async function apiAuthLogin(email, password) {
  const r = await fetch(`${API}/auth/login`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email, password }),
  });
  if (!r.ok) {
    const d = await r.json().catch(() => ({}));
    throw new Error(d.detail || 'Неверный email или пароль');
  }
  return r.json();
}

async function loadMemory() {
  if (!currentUserId) return;
  try {
    const r = await fetch(`${API}/memory/${currentUserId}`, { headers: authHeaders() });
    if (r.ok) {
      const d = await r.json();
      userMemory = d.memories || [];
    }
  } catch {}
}

function buildMemoryBlock() {
  if (!userMemory.length) return null;
  const top = userMemory.slice(0, 10);
  return 'Факты о пользователе:\n' + top.map(m => `- ${m.key}: ${m.value}`).join('\n');
}

function fireExtractMemory(assistantText) {
  if (!currentUserId || !assistantText || assistantText.length < 30) return;
  fetch(`${API}/memory/extract`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', ...authHeaders() },
    body: JSON.stringify({
      user_id: currentUserId,
      conv_id: currentConvId,
      assistant_message: assistantText,
    }),
  }).catch(() => {});
}

function fireSaveMessage(role, content, modelUsed) {
  if (!currentUserId || !currentConvId) return;
  fetch(`${API}/history/${currentUserId}/${currentConvId}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', ...authHeaders() },
    body: JSON.stringify({ role, content, model_used: modelUsed || null }),
  }).catch(() => {});
}
