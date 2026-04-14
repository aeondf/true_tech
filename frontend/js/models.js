// ══ MODELS — isChatModel(), modelGroup(), modelDisplayName(), modelIcon(),
//             fetchModels(), buildDD(), pickModel(), toggleMDD() ══

const EXCLUDE_PREFIXES = ['bge-','whisper-','qwen-image','BAAI/','qwen3-embedding'];
const CONVERSATION_MODEL_STORAGE_KEY = 'mts-conversation-models';

function readConversationModelState(){
  try {
    const raw = localStorage.getItem(CONVERSATION_MODEL_STORAGE_KEY);
    const parsed = raw ? JSON.parse(raw) : {};
    return parsed && typeof parsed === 'object' ? parsed : {};
  } catch {
    return {};
  }
}

let conversationModelState = readConversationModelState();

function writeConversationModelState(){
  try {
    const keys = Object.keys(conversationModelState);
    if(!keys.length) localStorage.removeItem(CONVERSATION_MODEL_STORAGE_KEY);
    else localStorage.setItem(CONVERSATION_MODEL_STORAGE_KEY, JSON.stringify(conversationModelState));
  } catch {}
}

function normalizeModelId(id){
  const value = String(id || '').trim();
  return value && value !== 'auto' ? value : 'auto';
}

function resolveModelName(id){
  const normalized = normalizeModelId(id);
  return normalized === 'auto' ? autoModelLabel() : (modelDisplayName(normalized) || normalized);
}

function hasConversationModel(convId){
  return Boolean(convId && Object.prototype.hasOwnProperty.call(conversationModelState, convId));
}

function getConversationModel(convId){
  return hasConversationModel(convId) ? normalizeModelId(conversationModelState[convId]) : 'auto';
}

function setConversationModel(convId, modelId){
  if(!convId) return;
  const normalized = normalizeModelId(modelId);
  if(normalized === 'auto') delete conversationModelState[convId];
  else conversationModelState[convId] = normalized;
  writeConversationModelState();
}

function removeConversationModel(convId){
  if(!convId || !hasConversationModel(convId)) return;
  delete conversationModelState[convId];
  writeConversationModelState();
}
function isChatModel(id){
  return !EXCLUDE_PREFIXES.some(p => id.startsWith(p));
}

function modelGroup(id){
  if(id==='mws-gpt-alpha')             return 'МТС';
  if(id.startsWith('qwen'))            return 'Qwen';
  if(id.startsWith('Qwen'))            return 'Qwen';
  if(id.startsWith('llama'))           return 'Meta';
  if(id.startsWith('gemma'))           return 'Google';
  if(id.startsWith('deepseek'))        return 'DeepSeek';
  if(id.startsWith('gpt-oss'))         return 'MTS OSS';
  if(id.startsWith('glm'))             return 'Zhipu';
  if(id.startsWith('kimi'))            return 'Kimi';
  if(id.startsWith('T-pro'))           return 'T-Bank';
  if(id.startsWith('cotype'))          return 'Cotype';
  if(id.startsWith('QwQ'))             return 'Qwen';
  return 'Другие';
}

function modelDisplayName(id){
  const map = {
    'mws-gpt-alpha':                  'MWS GPT Alpha',
    'qwen3-coder-480b-a35b':          'Qwen3 Coder 480B',
    'qwen3-32b':                      'Qwen3 32B',
    'qwen3-vl-30b-a3b-instruct':      'Qwen3-VL 30B',
    'qwen2.5-72b-instruct':           'Qwen2.5 72B',
    'qwen2.5-vl':                     'Qwen2.5-VL',
    'qwen2.5-vl-72b':                 'Qwen2.5-VL 72B',
    'QwQ-32B':                        'QwQ 32B',
    'Qwen3-235B-A22B-Instruct-2507-FP8': 'Qwen3 235B',
    'deepseek-r1-distill-qwen-32b':   'DeepSeek-R1 32B',
    'llama-3.1-8b-instruct':          'Llama 3.1 8B',
    'llama-3.3-70b-instruct':         'Llama 3.3 70B',
    'gemma-3-27b-it':                 'Gemma 3 27B',
    'gpt-oss-20b':                    'GPT-OSS 20B',
    'gpt-oss-120b':                   'GPT-OSS 120B',
    'glm-4.6-357b':                   'GLM-4.6 357B',
    'kimi-k2-instruct':               'Kimi K2',
    'T-pro-it-1.0':                   'T-Pro 1.0',
    'cotype-pro-vl-32b':              'Cotype-Pro VL',
  };
  return map[id] || id;
}

function autoModelLabel(){
  return curLang==='ru' ? 'Авто' : 'Auto';
}

function autoModelSubtitle(){
  return curLang==='ru' ? 'Оптимальная модель подбирается автоматически' : 'The best model is selected automatically';
}

function modelIcon(id){
  if(id.includes('coder')||id.includes('code'))
    return '<svg width="13" height="13" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" viewBox="0 0 24 24"><polyline points="16 18 22 12 16 6"/><polyline points="8 6 2 12 8 18"/></svg>';
  if(id.includes('vl')||id.includes('vision')||id.includes('VL'))
    return '<svg width="13" height="13" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" viewBox="0 0 24 24"><path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/><circle cx="12" cy="12" r="3"/></svg>';
  if(id.includes('qwen3-coder')||id==='QwQ-32B'||id.includes('deepseek')||id.includes('r1'))
    return '<svg width="13" height="13" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" viewBox="0 0 24 24"><circle cx="12" cy="12" r="3"/><path d="M12 1v4M12 19v4M4.22 4.22l2.83 2.83M16.95 16.95l2.83 2.83M1 12h4M19 12h4M4.22 19.78l2.83-2.83M16.95 7.05l2.83-2.83"/></svg>';
  if(id.includes('llama'))
    return '<svg width="13" height="13" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" viewBox="0 0 24 24"><path d="M13 2L3 14h9l-1 8 10-12h-9z"/></svg>';
  return '<svg width="13" height="13" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" viewBox="0 0 24 24"><circle cx="12" cy="8" r="4"/><path d="M4 20c0-4 3.6-7 8-7s8 3 8 7"/></svg>';
}

let CHAT_MODELS = []; // [{id, name, group, icon}]

function applyModelSelection(id, options){
  const opts = options || {};
  const normalized = normalizeModelId(id);
  const exists = normalized === 'auto' || !CHAT_MODELS.length || CHAT_MODELS.some(model => model.id === normalized);
  selectedModel = exists ? normalized : 'auto';
  selectedModelName = resolveModelName(selectedModel);

  if(!opts.skipConversationSync && currentConvId) setConversationModel(currentConvId, selectedModel);

  syncModelSelectionUI();
  if(!opts.skipDropdownRebuild){
    buildDD('mDDH');
    buildDD('mDDB');
  }
}

function restoreConversationModel(convId){
  applyModelSelection(getConversationModel(convId), { skipConversationSync: true });
}

function resetConversationModel(convId){
  if(convId) removeConversationModel(convId);
  applyModelSelection('auto', { skipConversationSync: true });
}

function syncModelSelectionUI(){
  const isAuto = !selectedModel || selectedModel === 'auto';
  const label = isAuto ? autoModelLabel() : (selectedModelName || resolveModelName(selectedModel));

  document.querySelectorAll('.m-name-txt').forEach(el => el.textContent = label);
  document.querySelectorAll('.mp-dot').forEach(el => {
    el.className = 'mp-dot ' + (isAuto ? 'auto-dot' : 'ready-dot');
  });
}

async function fetchModels(){
  try {
    const r = await fetch(`${API}/models`);
    const d = await r.json();
    const raw = (d.data||[]).filter(m => isChatModel(m.id));
    CHAT_MODELS = raw.map(m=>({
      id: m.id,
      name: modelDisplayName(m.id),
      group: modelGroup(m.id),
      icon: modelIcon(m.id)
    }));
  } catch {
    CHAT_MODELS = [
      {id:'mws-gpt-alpha',      name:'MWS GPT Alpha',    group:'МТС'},
      {id:'qwen3-32b',          name:'Qwen3 32B',         group:'Qwen'},
      {id:'qwen3-coder-480b-a35b', name:'Qwen3 Coder 480B', group:'Qwen'},
      {id:'qwen2.5-72b-instruct',  name:'Qwen2.5 72B',    group:'Qwen'},
      {id:'llama-3.3-70b-instruct',name:'Llama 3.3 70B',  group:'Meta'},
    ].map(m=>({...m, icon: modelIcon(m.id)}));
  }
  applyModelSelection(selectedModel, { skipConversationSync: true });
}

function buildDD(ddId){
  const dd = document.getElementById(ddId);
  if(!dd) return;
  dd.innerHTML = '';

  const searchWrap = document.createElement('div'); searchWrap.className='dd-search-wrap';
  const searchInp  = document.createElement('input');
  searchInp.className='dd-search'; searchInp.placeholder='Поиск модели...'; searchInp.type='text';
  searchInp.onclick = e=>e.stopPropagation();
  searchWrap.appendChild(searchInp);
  dd.appendChild(searchWrap);

  const list = document.createElement('div'); list.className='dd-list';
  dd.appendChild(list);

  const autoDiv = document.createElement('div');
  autoDiv.className = 'dd-opt' + (selectedModel==='auto'?' sel':'');
  autoDiv.dataset.search = 'авто auto';
  autoDiv.innerHTML = `<div class="dd-ico"><svg width="13" height="13" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" viewBox="0 0 24 24"><circle cx="12" cy="12" r="3"/><path d="M12 1v4M12 19v4M4.22 4.22l2.83 2.83M16.95 16.95l2.83 2.83M1 12h4M19 12h4M4.22 19.78l2.83-2.83M16.95 7.05l2.83-2.83"/></svg></div><div class="dd-info"><div class="dd-nm">${autoModelLabel()}</div><div class="dd-sb">${autoModelSubtitle()}</div></div>${selectedModel==='auto'?'<span class="dd-chk">✓</span>':''}`;
  autoDiv.onclick = e=>{ e.stopPropagation(); pickModel('auto',autoModelLabel(),true); };
  list.appendChild(autoDiv);

  const groups = {};
  CHAT_MODELS.forEach(m=>{
    if(!groups[m.group]) groups[m.group]=[];
    groups[m.group].push(m);
  });

  const groupEls = [];
  for(const [grpName, models] of Object.entries(groups)){
    const sep = document.createElement('div'); sep.className='dd-sep'; list.appendChild(sep);
    const hdr = document.createElement('div'); hdr.className='dd-hdr'; hdr.textContent=grpName; list.appendChild(hdr);
    const grpOpts = [];
    models.forEach(m=>{
      const opt = document.createElement('div');
      opt.className = 'dd-opt'+(selectedModel===m.id?' sel':'');
      opt.dataset.search = (m.name+' '+m.id+' '+grpName).toLowerCase();
      opt.innerHTML = `<div class="dd-ico">${m.icon}</div><div class="dd-info"><div class="dd-nm">${esc(m.name)}</div><div class="dd-sb">${esc(m.id)}</div></div>${selectedModel===m.id?'<span class="dd-chk">✓</span>':''}`;
      opt.onclick = e=>{ e.stopPropagation(); pickModel(m.id, m.name, false); };
      list.appendChild(opt);
      grpOpts.push(opt);
    });
    groupEls.push({sep, hdr, opts: grpOpts});
  }

  const emptyMsg = document.createElement('div'); emptyMsg.className='dd-empty'; emptyMsg.textContent='Ничего не найдено'; emptyMsg.style.display='none'; list.appendChild(emptyMsg);

  searchInp.oninput = ()=>{
    const q = searchInp.value.toLowerCase().trim();
    let anyVisible = false;
  const autoMatch = !q || 'авто auto'.includes(q);
    autoDiv.classList.toggle('hidden', !autoMatch);
    groupEls.forEach(({sep, hdr, opts})=>{
      let grpAny = false;
      opts.forEach(opt=>{
        const match = !q || opt.dataset.search.includes(q);
        opt.classList.toggle('hidden', !match);
        if(match) grpAny = true;
      });
      sep.style.display = grpAny ? '' : 'none';
      hdr.style.display = grpAny ? '' : 'none';
      if(grpAny) anyVisible = true;
    });
    emptyMsg.style.display = (!anyVisible && !autoMatch) ? '' : 'none';
  };
}

function pickModel(id, name, isAuto){
  applyModelSelection(id);
  if(typeof closeFloatingOverlays === 'function') closeFloatingOverlays();
  else closeAll();
  toast(isAuto ? (curLang==='ru' ? 'Авто выберет модель под задачу' : 'Auto will choose the right model') : (curLang==='ru' ? `${name} выбрана` : `${name} selected`), 'ok');
}

let openDD=null;
function toggleMDD(e,ddId,pillId){
  e.stopPropagation();
  const dd=document.getElementById(ddId); const pill=document.getElementById(pillId);
  if(openPop){
    document.getElementById(openPop)?.classList.remove('open');
    openPop=null;
    document.querySelectorAll('.sel-btn').forEach(btn => btn.classList.remove('open'));
  }
  if(openDD&&openDD!==ddId){ document.getElementById(openDD)?.classList.remove('open'); document.querySelectorAll('.m-pill').forEach(p=>p.setAttribute('aria-expanded','false')); }
  const open=dd.classList.toggle('open');
  pill.setAttribute('aria-expanded',open);
  openDD=open?ddId:null;
  refreshOverlayState();
}
