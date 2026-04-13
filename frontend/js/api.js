// ══════════════════════════════════════════════
//  api.js — base URL + auth headers
// ══════════════════════════════════════════════

// Relative URL: works both locally and in Docker (nginx proxies /v1/* → backend)
const API = '/v1';

// ── Auth state ────────────────────────────────
let authToken   = localStorage.getItem('mts-token') || null;
let userMemory  = [];   // [{key, value, category, score}]

function authHeaders() {
  return authToken ? { 'Authorization': 'Bearer ' + authToken } : {};
}

// ── Auth API ──────────────────────────────────
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

// ── Utils ─────────────────────────────────────
function uuid() {
  return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, c => {
    const r = Math.random() * 16 | 0;
    return (c === 'x' ? r : (r & 0x3 | 0x8)).toString(16);
  });
}

function fileToBase64(file) {
  return new Promise((res, rej) => {
    const fr = new FileReader();
    fr.onload = () => res(fr.result.split(',')[1]);
    fr.onerror = rej;
    fr.readAsDataURL(file);
  });
}
