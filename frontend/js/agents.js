// ══ AGENTS — openAgModal(), closeAgModal(), selectAgent(), filterAgents() ══

const AGENTS = [
  {id:'assistant', name:'Ассистент', desc:'Универсальный ИИ для любых задач', model:'mws-gpt-alpha',
   detail:'Универсальный ИИ-ассистент: от ответов на вопросы до анализа и генерации контента.',
   features:[{title:'Ответы на вопросы',sub:'Мгновенные ответы по любой теме'},{title:'Анализ текста',sub:'Суммаризация, извлечение данных'},{title:'Генерация контента',sub:'Тексты, сценарии, письма'},{title:'Решение задач',sub:'Логические, творческие, технические'}],
   ic:'<svg width="20" height="20" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" viewBox="0 0 24 24"><circle cx="12" cy="8" r="4"/><path d="M4 20c0-4 3.6-7 8-7s8 3 8 7"/></svg>'},
  {id:'code', name:'Код Агент', desc:'Генерация, ревью и отладка кода', model:'qwen3-coder-480b-a35b',
   detail:'Профессиональный агент для разработчиков: пишет, отлаживает и ревьюит код.',
   features:[{title:'Генерация кода',sub:'Написание кода по описанию'},{title:'Code Review',sub:'Анализ и улучшение кода'},{title:'Отладка',sub:'Поиск и исправление ошибок'},{title:'Документация',sub:'Автодокументирование'}],
   ic:'<svg width="20" height="20" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" viewBox="0 0 24 24"><polyline points="16 18 22 12 16 6"/><polyline points="8 6 2 12 8 18"/></svg>'},
  {id:'vision', name:'Анализ картинок', desc:'Распознавание и анализ изображений', model:'qwen2.5-vl',
   detail:'Анализирует изображения, читает текст на фото, описывает сцены.',
   features:[{title:'Объекты',sub:'Детектирование и классификация'},{title:'OCR',sub:'Текст с фото'},{title:'Сцены',sub:'Подробный анализ'},{title:'Сравнение',sub:'Отличия и сходства'}],
   ic:'<svg width="20" height="20" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" viewBox="0 0 24 24"><path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/><circle cx="12" cy="12" r="3"/></svg>'},
  {id:'imagegen', name:'Генерация изображений', desc:'Создание арта и фото по тексту', model:'qwen-image',
   detail:'Создаёт изображения, иллюстрации и арт по текстовому описанию.',
   features:[{title:'Промпт',sub:'Изображение из текста'},{title:'Стили',sub:'Реализм, арт, аниме'},{title:'Редактирование',sub:'Изменение изображений'},{title:'4K',sub:'Высокое разрешение'}],
   ic:'<svg width="20" height="20" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" viewBox="0 0 24 24"><rect x="3" y="3" width="18" height="18" rx="2"/><circle cx="8.5" cy="8.5" r="1.5"/><polyline points="21 15 16 10 5 21"/></svg>'},
  {id:'corporate', name:'Корпоративные задачи', desc:'Бизнес-процессы и документооборот', model:'mws-gpt-alpha',
   detail:'Отчёты, KPI, презентации и деловая переписка.',
   features:[{title:'Документы',sub:'Отчёты, протоколы, приказы'},{title:'KPI',sub:'Метрики и дашборды'},{title:'Презентации',sub:'Структура и контент'},{title:'Переписка',sub:'Письма и предложения'}],
   ic:'<svg width="20" height="20" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" viewBox="0 0 24 24"><rect x="2" y="7" width="20" height="14" rx="2"/><path d="M16 7V5a2 2 0 00-2-2h-4a2 2 0 00-2 2v2"/><line x1="12" y1="12" x2="12" y2="16"/><line x1="10" y1="14" x2="14" y2="14"/></svg>'},
  {id:'websearch', name:'Поиск в интернете', desc:'Актуальная информация с источниками', model:'mws-gpt-alpha',
   detail:'Ищет актуальную информацию со ссылками на источники.',
   features:[{title:'Реальное время',sub:'Актуальная информация'},{title:'Цитирование',sub:'Ссылки на источники'},{title:'Синтез',sub:'Объединение данных'},{title:'Факт-чек',sub:'Верификация'}],
   ic:'<svg width="20" height="20" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" viewBox="0 0 24 24"><circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/></svg>'},
  {id:'deepresearch', name:'Deep Research', desc:'Глубокий многошаговый анализ', model:'qwen2.5-72b-instruct',
   detail:'Глубокое исследование из множества источников с структурированным отчётом.',
   features:[{title:'Многошаговый поиск',sub:'Итеративный сбор данных'},{title:'Отчёт',sub:'Структурированный итог'},{title:'Анализ',sub:'Сопоставление точек зрения'},{title:'Источники',sub:'Список материалов'}],
   ic:'<svg width="20" height="20" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" viewBox="0 0 24 24"><path d="M2 3h6a4 4 0 014 4v14a3 3 0 00-3-3H2z"/><path d="M22 3h-6a4 4 0 00-4 4v14a3 3 0 013-3h7z"/></svg>'},
  {id:'audio', name:'Анализ по аудио', desc:'Транскрипция и анализ аудиозаписей', model:'mws-gpt-alpha',
   detail:'Транскрибирует аудио, определяет спикеров, извлекает ключевые моменты.',
   features:[{title:'Транскрипция',sub:'Речь в текст'},{title:'Спикеры',sub:'Разделение по голосам'},{title:'Тезисы',sub:'Пересказ'},{title:'Тональность',sub:'Эмоции'}],
   ic:'<svg width="20" height="20" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" viewBox="0 0 24 24"><path d="M12 1a3 3 0 00-3 3v7a3 3 0 006 0V4a3 3 0 00-3-3z"/><path d="M5 10a7 7 0 0014 0"/><line x1="12" y1="17" x2="12" y2="21"/><line x1="8" y1="21" x2="16" y2="21"/></svg>'},
  {id:'docs', name:'Анализ документов', desc:'Умная работа с PDF, Word, Excel', model:'mws-gpt-alpha',
   detail:'Читает и анализирует документы, отвечает на вопросы по содержимому.',
   features:[{title:'PDF/Word',sub:'Извлечение текста'},{title:'Суммаризация',sub:'Краткое изложение'},{title:'Q&A',sub:'Ответы по содержимому'},{title:'Сравнение',sub:'Поиск изменений'}],
   ic:'<svg width="20" height="20" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" viewBox="0 0 24 24"><path d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8z"/><polyline points="14 2 14 8 20 8"/><line x1="16" y1="13" x2="8" y2="13"/><line x1="16" y1="17" x2="8" y2="17"/></svg>'},
];

const AGENT_SYSTEM_PROMPTS = {
  assistant:    null,
  code:         'Ты — опытный разработчик программного обеспечения. Помогай с написанием, ревью, отладкой и документированием кода. Давай чистый, рабочий код с краткими пояснениями.',
  vision:       'Ты — мультимодальный ИИ-ассистент. Детально анализируй прикреплённые изображения, описывай содержимое, распознавай текст (OCR) и отвечай на вопросы о визуальных данных.',
  imagegen:     null,
  corporate:    'Ты — профессиональный бизнес-ассистент. Помогай с деловыми документами, отчётами, KPI-анализом, презентациями и корпоративной перепиской. Используй официально-деловой стиль.',
  websearch:    'Ты — ИИ-ассистент с доступом к поиску в интернете. Используй актуальную информацию для ответов. Обязательно указывай источники в формате [ссылка]. Если информация устарела, предупреди об этом.',
  deepresearch: null,
  audio:        'Ты — ассистент по анализу аудиоконтента. Помогай с транскрипцией, анализом речи, определением спикеров и извлечением ключевых моментов из записей.',
  docs:         'Ты — ассистент по работе с документами. Анализируй загруженные файлы (PDF, Word, Excel), делай краткое изложение, отвечай на вопросы по содержимому и сравнивай документы. Попроси пользователя прикрепить документ, если он не приложен.',
};

function openAgModal(idx){
  const a=AGENTS[idx];
  document.getElementById('agmIcon').innerHTML=a.ic.replace('width="20" height="20"','width="26" height="26"');
  document.getElementById('agmName').textContent=a.name;
  document.getElementById('agmModel').textContent=modelDisplayName(a.model)||a.model;
  document.getElementById('agmDesc').textContent=a.detail;
  const fl=document.getElementById('agmFeats'); fl.innerHTML='';
  a.features.forEach(f=>{
    const li=document.createElement('li');
    li.innerHTML=`<div class="agm-feat-ic"><svg width="11" height="11" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" viewBox="0 0 24 24"><polyline points="20 6 9 17 4 12"/></svg></div><div class="agm-feat-txt"><div class="agm-feat-title">${esc(f.title)}</div><div class="agm-feat-sub">${esc(f.sub)}</div></div>`;
    fl.appendChild(li);
  });
  document.getElementById('agmStart').onclick=()=>{ closeAgModal(); selectAgent(idx); };
  document.getElementById('agModal').classList.add('show');
  document.getElementById('ov').classList.add('on');
  toast('Подробно: '+a.name,'inf',1600);
}

function closeAgModal(e){
  if(e&&e.target!==document.getElementById('agModal')) return;
  document.getElementById('agModal').classList.remove('show');
  document.getElementById('ov').classList.remove('on');
}

function selectAgent(idx){
  const a=AGENTS[idx]; currentAgent=a; closeAll();
  const overlay=document.getElementById('agTrans');
  document.getElementById('agTrans-icon').innerHTML=a.ic.replace('width="20" height="20"','width="30" height="30"');
  document.getElementById('agTrans-text').textContent=a.name;
  const mName = modelDisplayName(a.model)||a.model;
  document.getElementById('agTrans-model').textContent=a.name+' · '+mName;
  overlay.classList.remove('out'); overlay.classList.add('show');
  setTimeout(()=>{
    overlay.classList.add('out');
    setTimeout(()=>{
      overlay.classList.remove('show','out');
      const heroIcon=document.getElementById('heroAgentIcon');
      heroIcon.style.display='flex';
      heroIcon.innerHTML=a.ic.replace('width="20" height="20"','width="24" height="24"');
      pickModel(a.model, modelDisplayName(a.model)||a.model, false);
      const panel=document.getElementById('panel-chat');
      panel.classList.remove('has-messages');
      document.getElementById('inpZoneBottom').style.display='none';
      document.getElementById('chatInner').innerHTML='';
      currentConvId=uuid();
      const sysPrompt = AGENT_SYSTEM_PROMPTS[a.id];
      currentMessages = sysPrompt ? [{role:'system', content:sysPrompt}] : [];
      sw('chat',document.getElementById('nav-chat'));
      setTimeout(()=>document.getElementById('inpHero').focus(),80);
    },350);
  },1300);
}

function filterAgents(q){
  const lower=q.toLowerCase();
  document.querySelectorAll('#agGrid .ag-card').forEach(card=>{
    const name=card.querySelector('.ag-name')?.textContent.toLowerCase()||'';
    const desc=card.querySelector('.ag-desc')?.textContent.toLowerCase()||'';
    card.style.display=(!q||name.includes(lower)||desc.includes(lower))?'':'none';
  });
}
