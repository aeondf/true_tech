const API = (() => {
  const override = window.MTS_API_BASE || localStorage.getItem('mts-api-base');
  if (override) return override.replace(/\/$/, '');

  const protocol = window.location?.protocol || '';
  const host = window.location?.hostname || '';
  const port = window.location?.port || '';

  // If the frontend is served by a random static server on localhost, prefer the backend port directly.
  if (
    (host === '127.0.0.1' || host === 'localhost')
    && port
    && !['3000', '8000', '8010'].includes(port)
  ) {
    return 'http://localhost:8000/v1';
  }

  if (protocol === 'http:' || protocol === 'https:') {
    return `${window.location.origin}/v1`;
  }

  return 'http://localhost:8000/v1';
})();

let authToken = localStorage.getItem('mts-token') || null;
let userMemory = [];
let pendingMemorySync = null;

function authHeaders() {
  return authToken ? { Authorization: `Bearer ${authToken}` } : {};
}

async function readApiError(response, fallbackMessage) {
  const data = await response.json().catch(() => ({}));
  return data?.detail || data?.error?.message || data?.message || fallbackMessage;
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
  const index = userMemory.findIndex(item => item.key === fact.key);
  if (index >= 0) userMemory[index] = { ...userMemory[index], ...fact };
  else userMemory.push(fact);
  userMemory = sortMemoryFacts(userMemory);
}

function mergeMemoryFacts(facts) {
  (facts || []).forEach(upsertMemoryFactLocally);
  return userMemory;
}

async function apiAuthRegister(email, password) {
  const response = await fetch(`${API}/auth/register`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email, password }),
  });
  if (!response.ok) {
    throw new Error(await readApiError(response, 'Registration failed'));
  }
  return response.json();
}

async function apiAuthLogin(email, password) {
  const response = await fetch(`${API}/auth/login`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email, password }),
  });
  if (!response.ok) {
    throw new Error(await readApiError(response, 'Login failed'));
  }
  return response.json();
}

async function apiAuthMe() {
  const response = await fetch(`${API}/auth/me`, {
    headers: authHeaders(),
  });
  if (!response.ok) {
    throw new Error(await readApiError(response, 'Session is not valid'));
  }
  return response.json();
}

async function loadMemory() {
  if (!currentUserId) return;
  try {
    const response = await fetch(`${API}/memory/${currentUserId}`, {
      headers: authHeaders(),
    });
    if (response.ok) {
      const data = await response.json();
      userMemory = sortMemoryFacts(data.memories || []);
    }
  } catch {}
}

function buildMemoryBlock() {
  if (!userMemory.length) return null;
  const top = userMemory.slice(0, 8);
  return [
    'User memory context. Use only the facts that are relevant to the current answer.',
    ...top.map(item => `- [${item.category || 'general'}] ${item.key}: ${item.value}`),
  ].join('\n');
}

async function extractMemory(userText, assistantText) {
  const activeUserId = currentUserId;
  const combined = `${userText || ''}\n${assistantText || ''}`.trim();
  if (!activeUserId || !combined) return [];

  try {
    const response = await fetch(`${API}/memory/extract`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', ...authHeaders() },
      body: JSON.stringify({
        user_id: activeUserId,
        conv_id: currentConvId,
        user_message: userText || null,
        assistant_message: assistantText,
      }),
    });
    if (!response.ok) return [];

    const data = await response.json().catch(() => ({}));
    const facts = Array.isArray(data.memories) ? data.memories : [];
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
  if (!currentUserId || !currentConvId || !authToken) return;
  fetch(`${API}/history/${currentUserId}/${currentConvId}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', ...authHeaders() },
    body: JSON.stringify({ role, content, model_used: modelUsed || null }),
  }).catch(() => {});
}
