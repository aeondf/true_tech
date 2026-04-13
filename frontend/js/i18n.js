// ══ I18N — const LANG, applyLang(), pickLang() ══

const LANG={
  ru:{'nav.chat':'Чат','nav.agents':'Агенты','nav.settings':'Настройки','btn.newChat':'Новый чат',
      'hist.today':'Сегодня','hist.yesterday':'Вчера','hist.earlier':'Ранее','user.plan':'Pro план',
      'hero.sub':'Выберите агента или задайте вопрос напрямую','ag.sub':'Специализированные ИИ-агенты под конкретные задачи',
      'st.interface':'Интерфейс','st.lightTheme':'Светлая тема','st.lightThemeSub':'Переключить цветовую схему',
      'st.lang':'Язык интерфейса','st.compact':'Компактный режим','st.compactSub':'Уменьшить отступы',
      'st.models':'Модели и агенты','st.autoModel':'Автовыбор модели','st.autoModelSub':'Оптимальная под задачу',
      'st.temp':'Температура','st.memory':'Память агентов','st.memorySub':'Контекст между сессиями',
      'st.voice':'Голос и ввод','st.voiceInput':'Голосовой ввод','st.voiceInputSub':'Распознавание через микрофон',
      'st.enterSend':'Отправка по Enter','st.enterSendSub':'Shift+Enter — перенос строки',
      'st.privacy':'Конфиденциальность','st.history':'История чатов','st.historySub':'Сохранять на сервере',
      'st.analytics':'Аналитика','st.analyticsSub':'Анонимные данные'},
  en:{'nav.chat':'Chat','nav.agents':'Agents','nav.settings':'Settings','btn.newChat':'New Chat',
      'hist.today':'Today','hist.yesterday':'Yesterday','hist.earlier':'Earlier','user.plan':'Pro Plan',
      'hero.sub':'Choose an agent or ask a question','ag.sub':'Specialized AI agents for specific tasks',
      'st.interface':'Interface','st.lightTheme':'Light Theme','st.lightThemeSub':'Toggle color scheme',
      'st.lang':'Language','st.compact':'Compact Mode','st.compactSub':'Reduce spacing',
      'st.models':'Models & Agents','st.autoModel':'Auto Model','st.autoModelSub':'Best model for task',
      'st.temp':'Temperature','st.memory':'Agent Memory','st.memorySub':'Context between sessions',
      'st.voice':'Voice & Input','st.voiceInput':'Voice Input','st.voiceInputSub':'Recognition via microphone',
      'st.enterSend':'Send on Enter','st.enterSendSub':'Shift+Enter for new line',
      'st.privacy':'Privacy','st.history':'Chat History','st.historySub':'Save on server',
      'st.analytics':'Analytics','st.analyticsSub':'Anonymous usage data'},
};
let curLang = localStorage.getItem('mts-lang')||'ru';

function applyLang(code){
  curLang=code; localStorage.setItem('mts-lang',code);
  document.documentElement.setAttribute('data-lang',code);
  const d=LANG[code]||LANG.ru;
  document.querySelectorAll('[data-i18n]').forEach(el=>{
    const k=el.getAttribute('data-i18n'); if(d[k]!==undefined) el.textContent=d[k];
  });
}

function pickLang(e,el,code,label,sub){
  e.stopPropagation();
  document.getElementById('langVal').textContent=label;
  document.getElementById('langSub').textContent=sub;
  const pop=document.getElementById('pLang');
  pop.querySelectorAll('.sel-opt').forEach(o=>{ o.classList.remove('on'); o.querySelector('.sel-chk').textContent=''; });
  el.classList.add('on'); el.querySelector('.sel-chk').textContent='✓';
  pop.classList.remove('open'); document.getElementById('langBtn').classList.remove('open');
  openPop=null; document.getElementById('ov').classList.remove('on');
  applyLang(code); toast('Язык изменён: '+label,'ok');
}
