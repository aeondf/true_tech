// ══ API — const API, authHeaders(), apiAuthRegister(), apiAuthLogin(),
//          loadMemory(), queueMemorySync(), waitForMemorySync(), fireSaveMessage() ══

const API = 'http://localhost:8000/v1';

// Auth state
let authToken = localStorage.getItem('mts-token') || null;
let userMemory = [];   // [{key, value, category, score, updated_at}]
let pendingMemorySync = null;

function authHeaders() {
  return authToken ? { 'Authorization': 'Bearer ' + authToken } : {};
}

function sortMemoryFacts(memories) {
  return [...memories].sort((a, b) => {
    const scoreDiff = (Number(b?.score) || 0) - (Number(a?.score) || 0);
    if (scoreDiff) return scoreDiff;
    const aTs = Date.parse(a?.updated_at || '') || 0;
    const bTs = Date.parse(b?.updated_at || '') || 0;
    return bTs - aTs;
  });
}

function upsertMemoryFactLocally(fact) {
  if (!fact?.key || !fact?.value) return;
  const idx = userMemory.findIndex(item => item.key === fact.key);
  if (idx >= 0) userMemory[idx] = { ...userMemory[idx], ...fact };
  else userMemory.push(fact);
  userMemory = sortMemoryFacts(userMemory);
}

function mergeMemoryFacts(facts) {
  (facts || []).forEach(upsertMemoryFactLocally);
  return userMemory;
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
      userMemory = sortMemoryFacts(d.memories || []);
    }
  } catch {}
}

function buildMemoryBlock() {
  if (!userMemory.length) return null;
  const top = userMemory.slice(0, 8);
  return [
    'Контекст о пользователе. Используй только релевантные факты.',
    ...top.map(m => `- [${m.category || 'general'}] ${m.key}: ${m.value}`),
  ].join('\n');
}

async function extractMemory(userText, assistantText) {
  const activeUserId = currentUserId;
  const combined = `${userText || ''}\n${assistantText || ''}`.trim();
  if (!activeUserId || !combined) return [];
  try {
    const r = await fetch(`${API}/memory/extract`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', ...authHeaders() },
      body: JSON.stringify({
        user_id: activeUserId,
        conv_id: currentConvId,
        user_message: userText || null,
        assistant_message: assistantText,
      }),
    });
    if (!r.ok) return [];
    const d = await r.json().catch(() => ({}));
    const facts = Array.isArray(d.memories) ? d.memories : [];
    if (currentUserId === activeUserId) mergeMemoryFacts(facts);
    return facts;
  } catch {
    return [];
  }
}

function queueMemorySync(userText, assistantText) {
  const previous = pendingMemorySync || Promise.resolve([]);
  const next = previous.catch(() => []).then(() => extractMemory(userText, assistantText));
  pendingMemorySync = next;
  next.finally(() => {
    if (pendingMemorySync === next) pendingMemorySync = null;
  });
  return next;
}

async function waitForMemorySync() {
  if (!pendingMemorySync) return;
  try {
    await pendingMemorySync;
  } catch {}
}

function fireSaveMessage(role, content, modelUsed) {
  if (!currentUserId || !currentConvId) return;
  fetch(`${API}/history/${currentUserId}/${currentConvId}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', ...authHeaders() },
    body: JSON.stringify({ role, content, model_used: modelUsed || null }),
  }).catch(() => {});
}
