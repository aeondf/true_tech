// ══════════════════════════════════════════════
//  ui.js — i18n, models, agents, panels, render,
//           dropdowns, toast, auth, profile, init
// ══════════════════════════════════════════════

// ── i18n ──────────────────────────────────────
const LANG = {
  ru: {
    'nav.chat': 'Чат', 'nav.agents': 'Агенты', 'nav.settings': 'Настройки',
    'btn.newChat': 'Новый чат', 'hist.today': 'Сегодня', 'hist.yesterday': 'Вчера',
    'hist.earlier': 'Ранее', 'user.plan': 'Pro план',
    'hero.sub': 'Выберите агента или задайте вопрос напрямую',
    'ag.sub': 'Специализированные ИИ-агенты под конкретные задачи',
    'st.interface': 'Интерфейс', 'st.lightTheme': 'Светлая тема',
    'st.lightThemeSub': 'Переключить цветовую схему', 'st.lang': 'Язык интерфейса',
    'st.compact': 'Компактный режим', 'st.compactSub': 'Уменьшить отступы',
    'st.models': 'Модели и агенты', 'st.autoModel': 'Автовыбор модели',
    'st.autoModelSub': 'Оптимальная под задачу', 'st.temp': 'Температура',
    'st.memory': 'Память агентов', 'st.memorySub': 'Контекст между сессиями',
    'st.voice': 'Голос и ввод', 'st.voiceInput': 'Голосовой ввод',
    'st.voiceInputSub': 'Распознавание через микрофон',
    'st.enterSend': 'Отправка по Enter', 'st.enterSendSub': 'Shift+Enter — перенос строки',
    'st.privacy': 'Конфиденциальность', 'st.history': 'История чатов',
    'st.historySub': 'Сохранять на сервере', 'st.analytics': 'Аналитика',
    'st.analyticsSub': 'Анонимные данные',
  },
  en: {
    'nav.chat': 'Chat', 'nav.agents': 'Agents', 'nav.settings': 'Settings',
    'btn.newChat': 'New Chat', 'hist.today': 'Today', 'hist.yesterday': 'Yesterday',
    'hist.earlier': 'Earlier', 'user.plan': 'Pro Plan',
    'hero.sub': 'Choose an agent or ask a question',
    'ag.sub': 'Specialized AI agents for specific tasks',
    'st.interface': 'Interface', 'st.lightTheme': 'Light Theme',
    'st.lightThemeSub': 'Toggle color scheme', 'st.lang': 'Language',
    'st.compact': 'Compact Mode', 'st.compactSub': 'Reduce spacing',
    'st.models': 'Models & Agents', 'st.autoModel': 'Auto Model',
    'st.autoModelSub': 'Best model for task', 'st.temp': 'Temperature',
    'st.memory': 'Agent Memory', 'st.memorySub': 'Context between sessions',
    'st.voice': 'Voice & Input', 'st.voiceInput': 'Voice Input',
    'st.voiceInputSub': 'Recognition via microphone',
    'st.enterSend': 'Send on Enter', 'st.enterSendSub': 'Shift+Enter for new line',
    'st.privacy': 'Privacy', 'st.history': 'Chat History',
    'st.historySub': 'Save on server', 'st.analytics': 'Analytics',
    'st.analyticsSub': 'Anonymous usage data',
  },
};
let curLang = localStorage.getItem('mts-lang') || 'ru';
function applyLang(code) {
  curLang = code; localStorage.setItem('mts-lang', code);
  document.documentElement.setAttribute('data-lang', code);
  const d = LANG[code] || LANG.ru;
  document.querySelectorAll('[data-i18n]').forEach(el => {
    const k = el.getAttribute('data-i18n'); if (d[k] !== undefined) el.textContent = d[k];
  });
}

// ══════════════════════════════════════════════
//  MODELS
// ══════════════════════════════════════════════
const EXCLUDE_PREFIXES = ['bge-', 'whisper-', 'qwen-image', 'BAAI/', 'qwen3-embedding'];
function isChatModel(id) {
  return !EXCLUDE_PREFIXES.some(p => id.startsWith(p));
}

function modelGroup(id) {
  if (id === 'mws-gpt-alpha')       return 'МТС';
  if (id.startsWith('qwen'))        return 'Qwen';
  if (id.startsWith('Qwen'))        return 'Qwen';
  if (id.startsWith('llama'))       return 'Meta';
  if (id.startsWith('gemma'))       return 'Google';
  if (id.startsWith('deepseek'))    return 'DeepSeek';
  if (id.startsWith('gpt-oss'))     return 'MTS OSS';
  if (id.startsWith('glm'))         return 'Zhipu';
  if (id.startsWith('kimi'))        return 'Kimi';
  if (id.startsWith('T-pro'))       return 'T-Bank';
  if (id.startsWith('cotype'))      return 'Cotype';
  if (id.startsWith('QwQ'))         return 'Qwen';
  return 'Другие';
}

function modelDisplayName(id) {
  const map = {
    'mws-gpt-alpha':                     'MWS GPT Alpha',
    'qwen3-coder-480b-a35b':             'Qwen3 Coder 480B',
    'qwen3-32b':                         'Qwen3 32B',
    'qwen3-vl-30b-a3b-instruct':         'Qwen3-VL 30B',
    'qwen2.5-72b-instruct':              'Qwen2.5 72B',
    'qwen2.5-vl':                        'Qwen2.5-VL',
    'qwen2.5-vl-72b':                    'Qwen2.5-VL 72B',
    'QwQ-32B':                           'QwQ 32B',
    'Qwen3-235B-A22B-Instruct-2507-FP8': 'Qwen3 235B',
    'deepseek-r1-distill-qwen-32b':      'DeepSeek-R1 32B',
    'llama-3.1-8b-instruct':             'Llama 3.1 8B',
    'llama-3.3-70b-instruct':            'Llama 3.3 70B',
    'gemma-3-27b-it':                    'Gemma 3 27B',
    'gpt-oss-20b':                       'GPT-OSS 20B',
    'gpt-oss-120b':                      'GPT-OSS 120B',
    'glm-4.6-357b':                      'GLM-4.6 357B',
    'kimi-k2-instruct':                  'Kimi K2',
    'T-pro-it-1.0':                      'T-Pro 1.0',
    'cotype-pro-vl-32b':                 'Cotype-Pro VL',
  };
  return map[id] || id;
}

function modelIcon(id) {
  if (id.includes('coder') || id.includes('code'))
    return '<svg width="13" height="13" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" viewBox="0 0 24 24"><polyline points="16 18 22 12 16 6"/><polyline points="8 6 2 12 8 18"/></svg>';
  if (id.includes('vl') || id.includes('vision') || id.includes('VL'))
    return '<svg width="13" height="13" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" viewBox="0 0 24 24"><path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/><circle cx="12" cy="12" r="3"/></svg>';
  if (id.includes('qwen3-coder') || id === 'QwQ-32B' || id.includes('deepseek') || id.includes('r1'))
    return '<svg width="13" height="13" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" viewBox="0 0 24 24"><circle cx="12" cy="12" r="3"/><path d="M12 1v4M12 19v4M4.22 4.22l2.83 2.83M16.95 16.95l2.83 2.83M1 12h4M19 12h4M4.22 19.78l2.83-2.83M16.95 7.05l2.83-2.83"/></svg>';
  if (id.includes('llama'))
    return '<svg width="13" height="13" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" viewBox="0 0 24 24"><path d="M13 2L3 14h9l-1 8 10-12h-9z"/></svg>';
  return '<svg width="13" height="13" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" viewBox="0 0 24 24"><circle cx="12" cy="8" r="4"/><path d="M4 20c0-4 3.6-7 8-7s8 3 8 7"/></svg>';
}

let CHAT_MODELS = [];

async function fetchModels() {
  try {
    const r = await fetch(`${API}/models`);
    const d = await r.json();
    const raw = (d.data || []).filter(m => isChatModel(m.id));
    CHAT_MODELS = raw.map(m => ({
      id: m.id, name: modelDisplayName(m.id), group: modelGroup(m.id), icon: modelIcon(m.id)
    }));
  } catch {
    CHAT_MODELS = [
      { id: 'mws-gpt-alpha',           name: 'MWS GPT Alpha',    group: 'МТС' },
      { id: 'qwen3-32b',               name: 'Qwen3 32B',        group: 'Qwen' },
      { id: 'qwen3-coder-480b-a35b',   name: 'Qwen3 Coder 480B', group: 'Qwen' },
      { id: 'qwen2.5-72b-instruct',    name: 'Qwen2.5 72B',      group: 'Qwen' },
      { id: 'llama-3.3-70b-instruct',  name: 'Llama 3.3 70B',    group: 'Meta' },
    ].map(m => ({ ...m, icon: modelIcon(m.id) }));
  }
  buildDD('mDDH');
  buildDD('mDDB');
}

function buildDD(ddId) {
  const dd = document.getElementById(ddId);
  if (!dd) return;
  dd.innerHTML = '';

  const autoDiv = document.createElement('div');
  autoDiv.className = 'dd-opt' + (selectedModel === 'auto' ? ' sel' : '');
  autoDiv.innerHTML = `<div class="dd-ico"><svg width="13" height="13" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" viewBox="0 0 24 24"><circle cx="12" cy="12" r="3"/><path d="M12 1v4M12 19v4M4.22 4.22l2.83 2.83M16.95 16.95l2.83 2.83M1 12h4M19 12h4M4.22 19.78l2.83-2.83M16.95 7.05l2.83-2.83"/></svg></div><div class="dd-info"><div class="dd-nm">Авто</div><div class="dd-sb">Оптимальная модель подбирается автоматически</div></div>${selectedModel === 'auto' ? '<span class="dd-chk">✓</span>' : ''}`;
  autoDiv.onclick = e => { e.stopPropagation(); pickModel('auto', 'Авто', true); };
  dd.appendChild(autoDiv);

  const groups = {};
  CHAT_MODELS.forEach(m => {
    if (!groups[m.group]) groups[m.group] = [];
    groups[m.group].push(m);
  });

  for (const [grpName, models] of Object.entries(groups)) {
    const sep = document.createElement('div'); sep.className = 'dd-sep'; dd.appendChild(sep);
    const hdr = document.createElement('div'); hdr.className = 'dd-hdr'; hdr.textContent = grpName; dd.appendChild(hdr);
    models.forEach(m => {
      const opt = document.createElement('div');
      opt.className = 'dd-opt' + (selectedModel === m.id ? ' sel' : '');
      opt.innerHTML = `<div class="dd-ico">${m.icon}</div><div class="dd-info"><div class="dd-nm">${esc(m.name)}</div><div class="dd-sb">${esc(m.id)}</div></div>${selectedModel === m.id ? '<span class="dd-chk">✓</span>' : ''}`;
      opt.onclick = e => { e.stopPropagation(); pickModel(m.id, m.name, false); };
      dd.appendChild(opt);
    });
  }
}

function pickModel(id, name, isAuto) {
  selectedModel = id;
  selectedModelName = name;
  document.querySelectorAll('.m-name-txt').forEach(el => el.textContent = isAuto ? 'Авто' : name);
  document.querySelectorAll('.mp-dot').forEach(el => {
    el.className = 'mp-dot ' + (isAuto ? 'auto-dot' : 'ready-dot');
  });
  buildDD('mDDH'); buildDD('mDDB');
  closeAll();
  toast((isAuto ? 'Авто — роутер выберет модель' : name + ' выбрана'), 'ok');
}

// ══════════════════════════════════════════════
//  AGENTS
// ══════════════════════════════════════════════
const AGENTS = [
  { id: 'assistant', name: 'Ассистент', desc: 'Универсальный ИИ для любых задач', model: 'mws-gpt-alpha',
    detail: 'Универсальный ИИ-ассистент: от ответов на вопросы до анализа и генерации контента.',
    features: [{ title: 'Ответы на вопросы', sub: 'Мгновенные ответы по любой теме' }, { title: 'Анализ текста', sub: 'Суммаризация, извлечение данных' }, { title: 'Генерация контента', sub: 'Тексты, сценарии, письма' }, { title: 'Решение задач', sub: 'Логические, творческие, технические' }],
    ic: '<svg width="20" height="20" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" viewBox="0 0 24 24"><circle cx="12" cy="8" r="4"/><path d="M4 20c0-4 3.6-7 8-7s8 3 8 7"/></svg>' },
  { id: 'code', name: 'Код Агент', desc: 'Генерация, ревью и отладка кода', model: 'qwen3-coder-480b-a35b',
    detail: 'Профессиональный агент для разработчиков: пишет, отлаживает и ревьюит код.',
    features: [{ title: 'Генерация кода', sub: 'Написание кода по описанию' }, { title: 'Code Review', sub: 'Анализ и улучшение кода' }, { title: 'Отладка', sub: 'Поиск и исправление ошибок' }, { title: 'Документация', sub: 'Автодокументирование' }],
    ic: '<svg width="20" height="20" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" viewBox="0 0 24 24"><polyline points="16 18 22 12 16 6"/><polyline points="8 6 2 12 8 18"/></svg>' },
  { id: 'vision', name: 'Анализ картинок', desc: 'Распознавание и анализ изображений', model: 'qwen2.5-vl',
    detail: 'Анализирует изображения, читает текст на фото, описывает сцены.',
    features: [{ title: 'Объекты', sub: 'Детектирование и классификация' }, { title: 'OCR', sub: 'Текст с фото' }, { title: 'Сцены', sub: 'Подробный анализ' }, { title: 'Сравнение', sub: 'Отличия и сходства' }],
    ic: '<svg width="20" height="20" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" viewBox="0 0 24 24"><path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/><circle cx="12" cy="12" r="3"/></svg>' },
  { id: 'imagegen', name: 'Генерация изображений', desc: 'Создание арта и фото по тексту', model: 'qwen-image',
    detail: 'Создаёт изображения, иллюстрации и арт по текстовому описанию.',
    features: [{ title: 'Промпт', sub: 'Изображение из текста' }, { title: 'Стили', sub: 'Реализм, арт, аниме' }, { title: 'Редактирование', sub: 'Изменение изображений' }, { title: '4K', sub: 'Высокое разрешение' }],
    ic: '<svg width="20" height="20" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" viewBox="0 0 24 24"><rect x="3" y="3" width="18" height="18" rx="2"/><circle cx="8.5" cy="8.5" r="1.5"/><polyline points="21 15 16 10 5 21"/></svg>' },
  { id: 'corporate', name: 'Корпоративные задачи', desc: 'Бизнес-процессы и документооборот', model: 'mws-gpt-alpha',
    detail: 'Отчёты, KPI, презентации и деловая переписка.',
    features: [{ title: 'Документы', sub: 'Отчёты, протоколы, приказы' }, { title: 'KPI', sub: 'Метрики и дашборды' }, { title: 'Презентации', sub: 'Структура и контент' }, { title: 'Переписка', sub: 'Письма и предложения' }],
    ic: '<svg width="20" height="20" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" viewBox="0 0 24 24"><rect x="2" y="7" width="20" height="14" rx="2"/><path d="M16 7V5a2 2 0 00-2-2h-4a2 2 0 00-2 2v2"/><line x1="12" y1="12" x2="12" y2="16"/><line x1="10" y1="14" x2="14" y2="14"/></svg>' },
  { id: 'websearch', name: 'Поиск в интернете', desc: 'Актуальная информация с источниками', model: 'mws-gpt-alpha',
    detail: 'Ищет актуальную информацию со ссылками на источники.',
    features: [{ title: 'Реальное время', sub: 'Актуальная информация' }, { title: 'Цитирование', sub: 'Ссылки на источники' }, { title: 'Синтез', sub: 'Объединение данных' }, { title: 'Факт-чек', sub: 'Верификация' }],
    ic: '<svg width="20" height="20" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" viewBox="0 0 24 24"><circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/></svg>' },
  { id: 'deepresearch', name: 'Deep Research', desc: 'Глубокий многошаговый анализ', model: 'qwen2.5-72b-instruct',
    detail: 'Глубокое исследование из множества источников с структурированным отчётом.',
    features: [{ title: 'Многошаговый поиск', sub: 'Итеративный сбор данных' }, { title: 'Отчёт', sub: 'Структурированный итог' }, { title: 'Анализ', sub: 'Сопоставление точек зрения' }, { title: 'Источники', sub: 'Список материалов' }],
    ic: '<svg width="20" height="20" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" viewBox="0 0 24 24"><path d="M2 3h6a4 4 0 014 4v14a3 3 0 00-3-3H2z"/><path d="M22 3h-6a4 4 0 00-4 4v14a3 3 0 013-3h7z"/></svg>' },
  { id: 'audio', name: 'Анализ по аудио', desc: 'Транскрипция и анализ аудиозаписей', model: 'mws-gpt-alpha',
    detail: 'Транскрибирует аудио, определяет спикеров, извлекает ключевые моменты.',
    features: [{ title: 'Транскрипция', sub: 'Речь в текст' }, { title: 'Спикеры', sub: 'Разделение по голосам' }, { title: 'Тезисы', sub: 'Пересказ' }, { title: 'Тональность', sub: 'Эмоции' }],
    ic: '<svg width="20" height="20" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" viewBox="0 0 24 24"><path d="M12 1a3 3 0 00-3 3v7a3 3 0 006 0V4a3 3 0 00-3-3z"/><path d="M5 10a7 7 0 0014 0"/><line x1="12" y1="17" x2="12" y2="21"/><line x1="8" y1="21" x2="16" y2="21"/></svg>' },
  { id: 'docs', name: 'Анализ документов', desc: 'Умная работа с PDF, Word, Excel', model: 'mws-gpt-alpha',
    detail: 'Читает и анализирует документы, отвечает на вопросы по содержимому.',
    features: [{ title: 'PDF/Word', sub: 'Извлечение текста' }, { title: 'Суммаризация', sub: 'Краткое изложение' }, { title: 'Q&A', sub: 'Ответы по содержимому' }, { title: 'Сравнение', sub: 'Поиск изменений' }],
    ic: '<svg width="20" height="20" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" viewBox="0 0 24 24"><path d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8z"/><polyline points="14 2 14 8 20 8"/><line x1="16" y1="13" x2="8" y2="13"/><line x1="16" y1="17" x2="8" y2="17"/></svg>' },
];

// ── Ripple effect ─────────────────────────────
const _rippledEls = new WeakSet();
function addRipple(el) {
  if (!el || _rippledEls.has(el)) return;
  _rippledEls.add(el); el.classList.add('rh');
  el.addEventListener('click', function (e) {
    const rect = this.getBoundingClientRect();
    const r = document.createElement('span');
    const size = Math.max(rect.width, rect.height);
    r.className = 'rp';
    r.style.cssText = `width:${size}px;height:${size}px;left:${e.clientX - rect.left - size / 2}px;top:${e.clientY - rect.top - size / 2}px`;
    this.appendChild(r);
    r.addEventListener('animationend', () => r.remove(), { once: true });
  });
}

// ── Build agents grid ─────────────────────────
function buildAgentGrid() {
  const g = document.getElementById('agGrid');
  if (!g) return;
  AGENTS.forEach((a, i) => {
    const c = document.createElement('div');
    c.className = 'ag-card rh'; c.style.animationDelay = (i * 40) + 'ms';
    c.innerHTML = `<div class="ag-ico">${a.ic}</div><div class="ag-name">${esc(a.name)}</div><div class="ag-desc">${esc(a.desc)}</div>`;
    c.onclick = () => openAgModal(i);
    g.appendChild(c); addRipple(c);
  });
}

// ── Agent modal ───────────────────────────────
function openAgModal(idx) {
  const a = AGENTS[idx];
  document.getElementById('agmIcon').innerHTML = a.ic.replace('width="20" height="20"', 'width="26" height="26"');
  document.getElementById('agmName').textContent = a.name;
  document.getElementById('agmModel').textContent = modelDisplayName(a.model) || a.model;
  document.getElementById('agmDesc').textContent = a.detail;
  const fl = document.getElementById('agmFeats'); fl.innerHTML = '';
  a.features.forEach(f => {
    const li = document.createElement('li');
    li.innerHTML = `<div class="agm-feat-ic"><svg width="11" height="11" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" viewBox="0 0 24 24"><polyline points="20 6 9 17 4 12"/></svg></div><div class="agm-feat-txt"><div class="agm-feat-title">${esc(f.title)}</div><div class="agm-feat-sub">${esc(f.sub)}</div></div>`;
    fl.appendChild(li);
  });
  document.getElementById('agmStart').onclick = () => { closeAgModal(); selectAgent(idx); };
  document.getElementById('agModal').classList.add('show');
  document.getElementById('ov').classList.add('on');
  toast('Подробно: ' + a.name, 'inf', 1600);
}

function closeAgModal(e) {
  if (e && e.target !== document.getElementById('agModal')) return;
  document.getElementById('agModal').classList.remove('show');
  document.getElementById('ov').classList.remove('on');
}

function selectAgent(idx) {
  const a = AGENTS[idx]; currentAgent = a; closeAll();
  const overlay = document.getElementById('agTrans');
  document.getElementById('agTrans-icon').innerHTML = a.ic.replace('width="20" height="20"', 'width="30" height="30"');
  document.getElementById('agTrans-text').textContent = a.name;
  const mName = modelDisplayName(a.model) || a.model;
  document.getElementById('agTrans-model').textContent = a.name + ' · ' + mName;
  overlay.classList.remove('out'); overlay.classList.add('show');
  setTimeout(() => {
    overlay.classList.add('out');
    setTimeout(() => {
      overlay.classList.remove('show', 'out');
      const heroIcon = document.getElementById('heroAgentIcon');
      heroIcon.style.display = 'flex';
      heroIcon.innerHTML = a.ic.replace('width="20" height="20"', 'width="24" height="24"');
      pickModel(a.model, modelDisplayName(a.model) || a.model, false);
      const panel = document.getElementById('panel-chat');
      panel.classList.remove('has-messages');
      document.getElementById('inpZoneBottom').style.display = 'none';
      document.getElementById('chatInner').innerHTML = '';
      currentMessages = []; currentConvId = uuid();
      sw('chat', document.getElementById('nav-chat'));
      setTimeout(() => document.getElementById('inpHero').focus(), 80);
    }, 350);
  }, 1300);
}

// ── Panels ────────────────────────────────────
const PANELS = ['chat', 'agents', 'settings'];
const PANEL_ORDER = { chat: 0, agents: 1, settings: 2 };
let curPanel = 'chat';
function sw(name, btn) {
  if (col) expandSb();
  const fromIdx = PANEL_ORDER[curPanel] ?? 0, toIdx = PANEL_ORDER[name] ?? 0;
  const dir = toIdx > fromIdx ? 'slide-left' : 'slide-right';
  PANELS.forEach(p => {
    document.getElementById('panel-' + p).classList.remove('act', 'slide-left', 'slide-right');
    document.getElementById('nav-' + p).classList.remove('act');
  });
  const target = document.getElementById('panel-' + name);
  target.classList.add('act', dir);
  setTimeout(() => target.classList.remove('slide-left', 'slide-right'), 280);
  (btn || document.getElementById('nav-' + name)).classList.add('act');
  curPanel = name;
  if (name === 'settings') document.querySelectorAll('#panel-settings .st-row').forEach((r, i) => r.style.transitionDelay = (i * 35) + 'ms');
}
let col = false;
function toggleSb() { col = true; document.getElementById('sb').classList.add('col'); }
function expandSb() { col = false; document.getElementById('sb').classList.remove('col'); }

// ══════════════════════════════════════════════
//  MARKDOWN + APPEND MESSAGE
// ══════════════════════════════════════════════
function renderMd(raw) {
  if (!raw) return '';
  let t = raw.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
  t = t.replace(/```[\w]*\n?([\s\S]*?)```/g, (_, code) => `<pre style="background:var(--s2);border:1px solid var(--border);border-radius:8px;padding:10px 13px;overflow-x:auto;margin:8px 0;font-size:12px;font-family:Consolas,monospace;white-space:pre">${code.trim()}</pre>`);
  t = t.replace(/`([^`\n]+)`/g, '<code style="background:var(--s2);padding:1px 6px;border-radius:4px;font-family:monospace;font-size:12.5px">$1</code>');
  t = t.replace(/\*\*\*(.+?)\*\*\*/g, '<strong><em>$1</em></strong>');
  t = t.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>');
  t = t.replace(/\*(.+?)\*/g, '<em>$1</em>');
  t = t.replace(/^### (.+)$/gm, '<strong style="font-size:14px;display:block;margin:10px 0 3px">$1</strong>');
  t = t.replace(/^## (.+)$/gm, '<strong style="font-size:15px;display:block;margin:12px 0 4px">$1</strong>');
  t = t.replace(/^# (.+)$/gm, '<strong style="font-size:16px;display:block;margin:14px 0 5px">$1</strong>');
  t = t.replace(/^[\-\*] (.+)$/gm, '<div style="padding-left:14px;margin:2px 0">• $1</div>');
  t = t.replace(/\[([^\]]+)\]\((https?:\/\/[^\)]+)\)/g, '<a href="$2" target="_blank" style="color:var(--red);text-decoration:underline">$1</a>');
  t = t.replace(/(^|\s)(https?:\/\/[^\s<"]+)/g, '$1<a href="$2" target="_blank" style="color:var(--red);text-decoration:underline">$2</a>');
  t = t.replace(/\n/g, '<br>');
  t = t.replace(/(<\/pre>|<\/div>)<br>/g, '$1');
  return t;
}

function appendMsg(who, content, isMarkdown, usedModel) {
  const ci = document.getElementById('chatInner');
  const el = document.createElement('div');
  const displayBadge = usedModel
    ? (modelDisplayName(usedModel) || usedModel)
    : (selectedModel === 'auto' ? 'Авто' : (selectedModelName || selectedModel));

  if (who === 'user') {
    el.className = 'msg u';
    el.innerHTML = `<div class="msg-av usr">Вы</div><div class="msg-body"><div class="msg-actions"><button class="msg-act copyBtn" title="Копировать"><svg width="11" height="11" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" viewBox="0 0 24 24"><rect x="9" y="9" width="13" height="13" rx="2"/><path d="M5 15H4a2 2 0 01-2-2V4a2 2 0 012-2h9a2 2 0 012 2v1"/></svg></button></div><div class="msg-meta" style="justify-content:flex-end"><span class="msg-sender">Вы</span></div><div class="msg-bbl">${esc(content)}</div></div>`;
    el.querySelector('.copyBtn').onclick = () => { navigator.clipboard.writeText(content).then(() => toast('Скопировано', 'ok', 1500)); };
  } else {
    el.className = 'msg';
    el.innerHTML = `<div class="msg-av ai">AI</div><div class="msg-body"><div class="msg-actions"><button class="msg-act copyBtn" title="Копировать"><svg width="11" height="11" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" viewBox="0 0 24 24"><rect x="9" y="9" width="13" height="13" rx="2"/><path d="M5 15H4a2 2 0 01-2-2V4a2 2 0 012-2h9a2 2 0 012 2v1"/></svg></button><button class="msg-act likeBtn" title="Полезно"><svg width="11" height="11" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" viewBox="0 0 24 24"><path d="M14 9V5a3 3 0 00-3-3l-4 9v11h11.28a2 2 0 002-1.7l1.38-9a2 2 0 00-2-2.3H14z"/><path d="M7 22H4a2 2 0 01-2-2v-7a2 2 0 012-2h3"/></svg></button></div><div class="msg-meta"><span class="msg-sender msg-model-name">${esc(displayBadge)}</span><span class="msg-badge msg-model-badge">${esc(displayBadge)}</span></div><div class="msg-bbl" style="line-height:1.7"></div></div>`;
    const bbl = el.querySelector('.msg-bbl');
    if (isMarkdown) bbl.innerHTML = renderMd(content);
    else if (content) bbl.textContent = content;
    el.querySelector('.copyBtn').onclick = () => { navigator.clipboard.writeText(content).then(() => toast('Скопировано', 'ok', 1500)); };
    el.querySelector('.likeBtn').onclick = () => { el.querySelector('.likeBtn').style.color = '#22C55E'; toast('Отмечено как полезное', 'ok', 1800); };
  }
  ci.appendChild(el);
  return el;
}

function updateMsgModel(el, modelId) {
  if (!el || !modelId) return;
  const name = modelDisplayName(modelId) || modelId;
  const senderEl = el.querySelector('.msg-model-name');
  const badgeEl = el.querySelector('.msg-model-badge');
  if (senderEl) senderEl.textContent = name;
  if (badgeEl) badgeEl.textContent = name;
}

// ══════════════════════════════════════════════
//  HELPERS
// ══════════════════════════════════════════════
function fillQ(txt) { const ta = document.getElementById('inpHero'); ta.value = txt; autoH(ta); ta.focus(); }
function syncTA(el) { autoH(el); }
function scrollBot() { const s = document.getElementById('chatScroll'); setTimeout(() => s.scrollTop = s.scrollHeight, 40); }
function esc(s) { return String(s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;'); }
function autoH(el) { el.style.height = 'auto'; el.style.height = Math.min(el.scrollHeight, 180) + 'px'; }
function handleK(e, src) { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); doSend(src); } }

// ── Dropdowns ─────────────────────────────────
let openPop = null;
function togglePop(id, e, btn) {
  e.stopPropagation();
  const pop = document.getElementById(id);
  if (openPop && openPop !== id) { document.getElementById(openPop)?.classList.remove('open'); document.querySelectorAll('.sel-btn').forEach(b => b.classList.remove('open')); }
  const isOpen = pop.classList.toggle('open');
  btn.classList.toggle('open', isOpen);
  openPop = isOpen ? id : null;
  document.getElementById('ov').classList.toggle('on', !!(openPop || openDD));
}

function pickLang(e, el, code, label, sub) {
  e.stopPropagation();
  document.getElementById('langVal').textContent = label;
  document.getElementById('langSub').textContent = sub;
  const pop = document.getElementById('pLang');
  pop.querySelectorAll('.sel-opt').forEach(o => { o.classList.remove('on'); o.querySelector('.sel-chk').textContent = ''; });
  el.classList.add('on'); el.querySelector('.sel-chk').textContent = '✓';
  pop.classList.remove('open'); document.getElementById('langBtn').classList.remove('open');
  openPop = null; document.getElementById('ov').classList.remove('on');
  applyLang(code); toast('Язык изменён: ' + label, 'ok');
}

function pickTemp(e, el, val, sub) {
  e.stopPropagation();
  document.getElementById('tempVal').textContent = val; document.getElementById('tempSub').textContent = sub;
  const pop = document.getElementById('pTemp');
  pop.querySelectorAll('.sel-opt').forEach(o => { o.classList.remove('on'); o.querySelector('.sel-chk').textContent = ''; });
  el.classList.add('on'); el.querySelector('.sel-chk').textContent = '✓';
  pop.classList.remove('open'); document.getElementById('tempBtn').classList.remove('open');
  openPop = null; document.getElementById('ov').classList.remove('on');
}

let openDD = null;
function toggleMDD(e, ddId, pillId) {
  e.stopPropagation();
  const dd = document.getElementById(ddId); const pill = document.getElementById(pillId);
  if (openDD && openDD !== ddId) { document.getElementById(openDD)?.classList.remove('open'); document.querySelectorAll('.m-pill').forEach(p => p.setAttribute('aria-expanded', 'false')); }
  const open = dd.classList.toggle('open');
  pill.setAttribute('aria-expanded', open);
  openDD = open ? ddId : null;
  document.getElementById('ov').classList.toggle('on', !!(openDD || openPop));
}

function toggleTheme(btn) {
  btn.classList.toggle('on');
  const isDark = !btn.classList.contains('on');
  document.documentElement.setAttribute('data-theme', isDark ? 'dark' : 'light');
  localStorage.setItem('mts-theme', isDark ? 'dark' : 'light');
}

function closeAll() {
  if (openDD) { document.getElementById(openDD)?.classList.remove('open'); openDD = null; }
  document.querySelectorAll('.m-pill').forEach(p => p.setAttribute('aria-expanded', 'false'));
  if (openPop) { document.getElementById(openPop)?.classList.remove('open'); openPop = null; }
  document.querySelectorAll('.sel-btn').forEach(b => b.classList.remove('open'));
  document.getElementById('ov').classList.remove('on');
  document.getElementById('agModal').classList.remove('show');
  document.getElementById('profileOverlay')?.classList.remove('show');
}

// ── Toast ─────────────────────────────────────
function toast(msg, type = 'inf', dur = 2600) {
  const root = document.getElementById('toastRoot');
  const icons = {
    ok: '<svg width="12" height="12" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" viewBox="0 0 24 24"><polyline points="20 6 9 17 4 12"/></svg>',
    inf: '<svg width="12" height="12" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" viewBox="0 0 24 24"><circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/></svg>',
    err: '<svg width="12" height="12" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" viewBox="0 0 24 24"><circle cx="12" cy="12" r="10"/><line x1="15" y1="9" x2="9" y2="15"/><line x1="9" y1="9" x2="15" y2="15"/></svg>',
  };
  const t = document.createElement('div'); t.className = 'toast';
  t.innerHTML = `<div class="toast-ic ${type}">${icons[type] || icons.inf}</div><span>${esc(msg)}</span>`;
  root.appendChild(t);
  setTimeout(() => { t.classList.add('out'); t.addEventListener('animationend', () => t.remove(), { once: true }); }, dur);
}

function copyMsg(btn, text) {
  navigator.clipboard?.writeText(text).then(() => {
    btn.classList.add('copied'); toast('Скопировано', 'ok', 1800);
    setTimeout(() => btn.classList.remove('copied'), 2000);
  }).catch(() => toast('Не удалось скопировать', 'err'));
}
function likeMsg(btn) { btn.style.color = '#22C55E'; btn.querySelector('svg').style.fill = 'rgba(34,197,94,.2)'; toast('Отмечено как полезное', 'ok', 1800); }

// ── Agent search ──────────────────────────────
function filterAgents(q) {
  const lower = q.toLowerCase();
  document.querySelectorAll('#agGrid .ag-card').forEach(card => {
    const name = card.querySelector('.ag-name')?.textContent.toLowerCase() || '';
    const desc = card.querySelector('.ag-desc')?.textContent.toLowerCase() || '';
    card.style.display = (!q || name.includes(lower) || desc.includes(lower)) ? '' : 'none';
  });
}

// ── Splash + particles ────────────────────────
function burstParticles() {
  const splash = document.getElementById('splash'); if (!splash) return;
  const cx = splash.clientWidth / 2, cy = splash.clientHeight / 2;
  for (let i = 0; i < 22; i++) {
    const p = document.createElement('div'); p.className = 'sp';
    const size = 2 + Math.random() * 4;
    const angle = (Math.PI * 2 / 22) * i + Math.random() * .4;
    const dist = 60 + Math.random() * 120;
    const tx = Math.cos(angle) * dist, ty = Math.sin(angle) * dist - 30;
    const dur = (.5 + Math.random() * .5) + 's';
    p.style.cssText = `width:${size}px;height:${size}px;left:${cx}px;top:${cy}px;--tx2:${tx}px;--ty2:${ty}px;--dur:${dur};`;
    splash.appendChild(p); setTimeout(() => p.classList.add('burst'), 10); setTimeout(() => p.remove(), 900);
  }
}

// ── Auth ──────────────────────────────────────
let authEmailVal = '';
function authSubmitEmail() {
  const inp = document.getElementById('authEmail');
  const val = inp.value.trim();
  if (!val || !val.includes('@')) { inp.style.borderColor = 'var(--red)'; inp.focus(); setTimeout(() => inp.style.borderColor = '', 1200); return; }
  authEmailVal = val;
  document.getElementById('authEmailShow').textContent = val;
  const s1 = document.getElementById('authStep1');
  s1.classList.add('exit-left');
  setTimeout(() => {
    s1.style.display = 'none'; s1.classList.remove('exit-left');
    const s2 = document.getElementById('authStep2');
    s2.style.display = 'flex'; s2.style.opacity = '1';
    s2.classList.add('enter-right'); setTimeout(() => s2.classList.remove('enter-right'), 450);
    setTimeout(() => document.getElementById('authPassword')?.focus(), 80);
  }, 290);
}

function authGoBack() {
  const s2 = document.getElementById('authStep2');
  s2.classList.add('exit-left');
  setTimeout(() => {
    s2.style.display = 'none'; s2.classList.remove('exit-left');
    document.getElementById('authPassword').value = '';
    const s1 = document.getElementById('authStep1'); s1.style.display = 'flex';
    s1.classList.add('enter-right'); setTimeout(() => s1.classList.remove('enter-right'), 450);
    setTimeout(() => document.getElementById('authEmail')?.focus(), 80);
  }, 290);
}

function togglePwdVis() {
  const inp = document.getElementById('authPassword');
  const icon = document.getElementById('pwdEyeIcon');
  if (inp.type === 'password') {
    inp.type = 'text';
    icon.innerHTML = '<path d="M17.94 17.94A10.07 10.07 0 0112 20c-7 0-11-8-11-8a18.45 18.45 0 015.06-5.94"/><path d="M9.9 4.24A9.12 9.12 0 0112 4c7 0 11 8 11 8a18.5 18.5 0 01-2.16 3.19"/><line x1="1" y1="1" x2="23" y2="23"/>';
  } else {
    inp.type = 'password';
    icon.innerHTML = '<path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/><circle cx="12" cy="12" r="3"/>';
  }
}

function authSubmitCode() {
  const pwd = document.getElementById('authPassword').value;
  if (!pwd) { const inp = document.getElementById('authPassword'); inp.style.borderColor = 'var(--red)'; inp.focus(); setTimeout(() => inp.style.borderColor = '', 1200); return; }
  const btn = document.getElementById('authCodeBtn');
  btn.textContent = 'Входим...'; btn.disabled = true;

  const doLogin = () => apiAuthLogin(authEmailVal, pwd)
    .then(d => {
      authToken = d.token;
      currentUserId = d.user_id;
      localStorage.setItem('mts-token', authToken);
      localStorage.setItem('mts-user-id', currentUserId);
      localStorage.setItem('mts-user-email', d.email);
      document.getElementById('profInpEmail').value = d.email;
      document.getElementById('sbUserName').textContent = d.email.split('@')[0];
      document.getElementById('authScreen').classList.add('out');
      setTimeout(() => { document.getElementById('authScreen').style.display = 'none'; initSplash(); }, 680);
    })
    .catch(() => apiAuthRegister(authEmailVal, pwd)
      .then(d => {
        authToken = d.token;
        currentUserId = d.user_id;
        localStorage.setItem('mts-token', authToken);
        localStorage.setItem('mts-user-id', currentUserId);
        localStorage.setItem('mts-user-email', d.email);
        document.getElementById('profInpEmail').value = d.email;
        document.getElementById('sbUserName').textContent = d.email.split('@')[0];
        document.getElementById('authScreen').classList.add('out');
        setTimeout(() => { document.getElementById('authScreen').style.display = 'none'; initSplash(); }, 680);
      })
      .catch(regErr => {
        btn.textContent = 'Войти'; btn.disabled = false;
        const inp = document.getElementById('authPassword');
        inp.style.borderColor = 'var(--red)'; inp.focus();
        setTimeout(() => inp.style.borderColor = '', 1800);
        toast(regErr.message || 'Ошибка входа', 'err', 3000);
      })
    );

  doLogin();
}

function initSplash() {
  const letters = ['sl-m', 'sl-t', 'sl-s'];
  setTimeout(() => { const b = document.getElementById('splash-brain'); b?.classList.add('show'); setTimeout(() => b?.classList.add('glow'), 700); }, 200);
  letters.forEach((id, i) => { setTimeout(() => document.getElementById(id)?.classList.add('lit'), 500 + i * 200); });
  setTimeout(burstParticles, 1200);
  setTimeout(() => document.getElementById('splash-sub')?.classList.add('show'), 1550);
  setTimeout(() => document.getElementById('splash-letters')?.classList.add('gather'), 2100);
  setTimeout(() => { document.getElementById('splash')?.classList.add('out'); document.getElementById('appRoot')?.classList.add('vis'); }, 2900);
  setTimeout(() => {
    document.getElementById('splash')?.remove();
    fetchModels();
    loadHistory();
    loadMemory();
    checkHealth();
    currentConvId = uuid();
  }, 3600);
}

async function checkHealth() {
  try {
    const r = await fetch(`${API}/health`, { signal: AbortSignal.timeout(4000) });
    const d = await r.json();
    toast(d.status === 'ok' ? 'Бэкенд подключён ✓' : 'Бэкенд: деградированный режим', d.status === 'ok' ? 'ok' : 'inf', 2500);
  } catch { toast('Бэкенд недоступен — запустите backend на :8000', 'err', 5000); }
}

// ── Profile ───────────────────────────────────
function openProfile() {
  document.getElementById('profName').textContent = document.getElementById('profInpName').value || 'MTS User';
  document.getElementById('profAvInitials').textContent = getInitials(document.getElementById('profInpName').value || 'MTS User');
  document.getElementById('profileOverlay').classList.add('show');
  document.getElementById('ov').classList.add('on');
}
function closeProfile() { document.getElementById('profileOverlay').classList.remove('show'); document.getElementById('ov').classList.remove('on'); }
function closeProfileOuter(e) { if (e.target === document.getElementById('profileOverlay')) closeProfile(); }
function getInitials(name) { return name.trim().split(/\s+/).map(w => w[0] || '').join('').toUpperCase().slice(0, 2) || 'МТ'; }

function saveProfile() {
  const name = document.getElementById('profInpName').value.trim() || 'MTS User';
  const initials = getInitials(name);
  document.getElementById('sbUserName').textContent = name;
  document.getElementById('sbAvatar').textContent = initials;
  document.getElementById('profName').textContent = name;
  document.getElementById('profAvInitials').textContent = initials;
  const btn = document.querySelector('#profTab-account .prof-save');
  if (btn) { const orig = btn.textContent; btn.textContent = '✓ Сохранено'; setTimeout(() => btn.textContent = orig, 1800); }
  toast('Профиль обновлён', 'ok');
}

function switchProfTab(tab, btn) {
  document.querySelectorAll('.prof-tab').forEach(t => t.classList.remove('act'));
  document.querySelectorAll('.prof-tab-panel').forEach(p => p.classList.remove('act'));
  btn.classList.add('act'); document.getElementById('profTab-' + tab)?.classList.add('act');
}

function checkPwdStrength(val) {
  const bar = document.getElementById('profPwdBar'); if (!bar) return;
  if (!val) { bar.style.width = '0%'; return; }
  const hasUpper = /[A-Z]/.test(val), hasNum = /[0-9]/.test(val), hasSpec = /[^A-Za-z0-9]/.test(val);
  const score = val.length < 6 ? 1 : val.length < 10 ? 2 : (hasUpper && hasNum && hasSpec) ? 4 : (hasUpper || hasNum) ? 3 : 2;
  bar.style.width = (score * 25) + '%'; bar.style.background = ['', '#ef4444', '#f97316', '#eab308', '#22c55e'][score];
}

function changePassword() {
  const curr = document.getElementById('profPwdCurrent');
  const newP = document.getElementById('profPwdNew');
  const conf = document.getElementById('profPwdConfirm');
  if (!curr || !newP || !conf) return;
  if (!curr.value) { toast('Введите текущий пароль', 'err'); return; }
  if (newP.value.length < 6) { toast('Минимум 6 символов', 'err'); return; }
  if (newP.value !== conf.value) { toast('Пароли не совпадают', 'err'); return; }
  curr.value = ''; newP.value = ''; conf.value = '';
  const bar = document.getElementById('profPwdBar'); if (bar) bar.style.width = '0%';
  toast('Пароль изменён', 'ok');
}

let _selectedPlan = 'pro';
function selectPlan(id) {
  _selectedPlan = id;
  document.querySelectorAll('.prof-plan-card').forEach(c => c.classList.remove('selected'));
  document.getElementById('plan-' + id)?.classList.add('selected');
}
function savePlan() {
  const labels = { free: 'Бесплатный', pro: 'Pro план', enterprise: 'Enterprise' };
  const label = labels[_selectedPlan] || 'Pro план';
  document.getElementById('sbUserPlan').textContent = label;
  document.getElementById('profPlan').textContent = label;
  toast('Тариф обновлён', 'ok');
}

function logoutProfile() {
  closeProfile();
  authToken = null;
  localStorage.removeItem('mts-token');
  localStorage.removeItem('mts-user-id');
  localStorage.removeItem('mts-user-email');
  userMemory = [];
  setTimeout(() => {
    const auth = document.getElementById('authScreen');
    if (auth) {
      auth.style.display = 'flex'; auth.classList.remove('out');
      document.getElementById('authStep1').style.display = 'flex';
      document.getElementById('authStep2').style.display = 'none';
      document.getElementById('authEmail').value = ''; document.getElementById('authPassword').value = '';
      const btn = document.getElementById('authCodeBtn'); if (btn) { btn.textContent = 'Войти'; btn.disabled = false; }
      auth.style.animation = 'none'; auth.style.opacity = '1'; auth.style.transform = 'none';
      setTimeout(() => document.getElementById('authEmail')?.focus(), 200);
    }
    currentUserId = null; currentConvId = null; currentMessages = [];
    document.getElementById('sb-hist').innerHTML = '';
  }, 350);
  toast('Выход из аккаунта', 'inf');
}

// ── BG floating words ─────────────────────────
function initBgWords() {
  const phrases = ['Искусственный интеллект', 'Artificial Intelligence', '人工智能', 'Intelligence Artificielle', 'Künstliche Intelligenz', 'Inteligencia Artificial', '人工知能', 'الذكاء الاصطناعي', 'Inteligência Artificial', '인공지능', 'Intelligenza Artificiale', 'Yapay Zeka', 'Kunstmatige Intelligentie', 'Sztuczna Inteligencja', 'Artificiell Intelligens', 'Kunstig Intelligens', 'Tekoäly', 'Mesterséges Intelligencia', 'Artificiální Inteligence', 'Umelá Inteligencia', 'Τεχνητή Νοημοσύνη', 'कृत्रिम बुद्धिमत्ता', 'কৃত্রিম বুদ্ধিমত্তা', 'செயற்கை நுண்ணறிவு', 'Dirbtinis Intelektas'];
  const durations = [38, 44, 32, 50, 40, 46, 34, 52, 41, 47, 36, 54, 39, 45, 33, 51, 43, 48, 35, 53, 37, 49, 42, 55, 31, 57, 44, 38, 50, 36];
  const wrap = document.getElementById('bgWords-inner'); if (!wrap) return;
  for (let i = 0; i < 160; i++) {
    const row = document.createElement('div');
    row.className = 'bgr ' + (i % 2 === 0 ? 'ev' : 'od');
    row.textContent = (phrases[i % phrases.length] + '   ').repeat(55);
    row.style.setProperty('--dur', durations[i % durations.length] + 's');
    wrap.appendChild(row);
  }
  if (localStorage.getItem('bgWordsOff') === '1') {
    document.getElementById('bgWords').classList.add('off');
    const tgl = document.getElementById('bgWordsTgl'); if (tgl) tgl.classList.remove('on');
  }
}

function toggleBgWords() {
  const el = document.getElementById('bgWords');
  const off = el.classList.toggle('off');
  localStorage.setItem('bgWordsOff', off ? '1' : '0');
}

// ── Init ──────────────────────────────────────
(function init() {
  const t = localStorage.getItem('mts-theme');
  if (t === 'light') { document.documentElement.setAttribute('data-theme', 'light'); document.getElementById('thTgl').classList.add('on'); }
  const l = localStorage.getItem('mts-lang') || 'ru';
  if (l !== 'ru') applyLang(l);
  buildDD('mDDH'); buildDD('mDDB');
  buildAgentGrid();
  initBgWords();
  document.querySelectorAll('.rh').forEach(addRipple);
  document.querySelectorAll('.prof-save,.prof-logout').forEach(addRipple);
  document.addEventListener('keydown', e => { if (e.key === 'Escape') closeAll(); });

  const savedToken = localStorage.getItem('mts-token');
  const savedUserId = localStorage.getItem('mts-user-id');
  const savedEmail = localStorage.getItem('mts-user-email');
  if (savedToken && savedUserId) {
    authToken = savedToken;
    currentUserId = savedUserId;
    if (savedEmail) {
      document.getElementById('profInpEmail').value = savedEmail;
      const nameEl = document.getElementById('sbUserName');
      if (nameEl) nameEl.textContent = savedEmail.split('@')[0];
    }
    const auth = document.getElementById('authScreen');
    if (auth) auth.style.display = 'none';
    initSplash();
  } else {
    setTimeout(() => document.getElementById('authEmail')?.focus(), 400);
  }
})();
