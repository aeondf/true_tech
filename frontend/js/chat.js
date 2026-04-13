// ══ CHAT — renderMd(), appendMsg(), updateMsgModel(), doSend(), sendVoiceMsg(),
//           doDeepResearch(), doVlmAnalyze(), doImageGen(), downloadImg(),
//           doWebSearch(), copyMsg(), likeMsg(), fillQ(), syncTA() ══

function renderMd(raw){
  if(!raw) return '';
  let t=raw.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
  t=t.replace(/```[\w]*\n?([\s\S]*?)```/g,(_,code)=>`<pre style="background:var(--s2);border:1px solid var(--border);border-radius:8px;padding:10px 13px;overflow-x:auto;margin:8px 0;font-size:12px;font-family:Consolas,monospace;white-space:pre">${code.trim()}</pre>`);
  t=t.replace(/`([^`\n]+)`/g,'<code style="background:var(--s2);padding:1px 6px;border-radius:4px;font-family:monospace;font-size:12.5px">$1</code>');
  t=t.replace(/\*\*\*(.+?)\*\*\*/g,'<strong><em>$1</em></strong>');
  t=t.replace(/\*\*(.+?)\*\*/g,'<strong>$1</strong>');
  t=t.replace(/\*(.+?)\*/g,'<em>$1</em>');
  t=t.replace(/^### (.+)$/gm,'<strong style="font-size:14px;display:block;margin:10px 0 3px">$1</strong>');
  t=t.replace(/^## (.+)$/gm,'<strong style="font-size:15px;display:block;margin:12px 0 4px">$1</strong>');
  t=t.replace(/^# (.+)$/gm,'<strong style="font-size:16px;display:block;margin:14px 0 5px">$1</strong>');
  t=t.replace(/^[\-\*] (.+)$/gm,'<div style="padding-left:14px;margin:2px 0">• $1</div>');
  t=t.replace(/\[([^\]]+)\]\((https?:\/\/[^\)]+)\)/g,'<a href="$2" target="_blank" style="color:var(--red);text-decoration:underline">$1</a>');
  t=t.replace(/(^|\s)(https?:\/\/[^\s<"]+)/g,'$1<a href="$2" target="_blank" style="color:var(--red);text-decoration:underline">$2</a>');
  t=t.replace(/\n/g,'<br>');
  t=t.replace(/(<\/pre>|<\/div>)<br>/g,'$1');
  return t;
}

function appendMsg(who, content, isMarkdown, usedModel){
  const ci=document.getElementById('chatInner');
  const el=document.createElement('div');

  const displayBadge = usedModel
    ? (modelDisplayName(usedModel)||usedModel)
    : (selectedModel==='auto' ? 'Авто' : (selectedModelName||selectedModel));

  if(who==='user'){
    el.className='msg u';
    el.innerHTML=`<div class="msg-av usr">Вы</div><div class="msg-body"><div class="msg-actions"><button class="msg-act copyBtn" title="Копировать"><svg width="11" height="11" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" viewBox="0 0 24 24"><rect x="9" y="9" width="13" height="13" rx="2"/><path d="M5 15H4a2 2 0 01-2-2V4a2 2 0 012-2h9a2 2 0 012 2v1"/></svg></button></div><div class="msg-meta" style="justify-content:flex-end"><span class="msg-sender">Вы</span></div><div class="msg-bbl">${esc(content)}</div></div>`;
    el.querySelector('.copyBtn').onclick=()=>{ navigator.clipboard.writeText(content).then(()=>toast('Скопировано','ok',1500)); };
  } else {
    el.className='msg';
    el.innerHTML=`<div class="msg-av ai">AI</div><div class="msg-body"><div class="msg-actions"><button class="msg-act copyBtn" title="Копировать"><svg width="11" height="11" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" viewBox="0 0 24 24"><rect x="9" y="9" width="13" height="13" rx="2"/><path d="M5 15H4a2 2 0 01-2-2V4a2 2 0 012-2h9a2 2 0 012 2v1"/></svg></button><button class="msg-act likeBtn" title="Полезно"><svg width="11" height="11" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" viewBox="0 0 24 24"><path d="M14 9V5a3 3 0 00-3-3l-4 9v11h11.28a2 2 0 002-1.7l1.38-9a2 2 0 00-2-2.3H14z"/><path d="M7 22H4a2 2 0 01-2-2v-7a2 2 0 012-2h3"/></svg></button></div><div class="msg-meta"><span class="msg-sender msg-model-name">${esc(displayBadge)}</span><span class="msg-badge msg-model-badge">${esc(displayBadge)}</span></div><div class="msg-bbl" style="line-height:1.7"></div></div>`;
    const bbl=el.querySelector('.msg-bbl');
    if(isMarkdown) bbl.innerHTML=renderMd(content);
    else if(content) bbl.textContent=content;
    el.querySelector('.copyBtn').onclick=()=>{ navigator.clipboard.writeText(content).then(()=>toast('Скопировано','ok',1500)); };
    el.querySelector('.likeBtn').onclick=()=>{ el.querySelector('.likeBtn').style.color='#22C55E'; toast('Отмечено как полезное','ok',1800); };
  }
  ci.appendChild(el);
  return el;
}

function updateMsgModel(el, modelId){
  if(!el||!modelId) return;
  const name = modelDisplayName(modelId)||modelId;
  const senderEl=el.querySelector('.msg-model-name');
  const badgeEl =el.querySelector('.msg-model-badge');
  if(senderEl) senderEl.textContent=name;
  if(badgeEl)  badgeEl.textContent=name;
}

function buildResearchMetaSection(sources, subQueries, stats){
  const safeSources = Array.isArray(sources) ? sources : [];
  const safeQueries = Array.isArray(subQueries) ? subQueries : [];
  const safeStats = stats && typeof stats === 'object' ? stats : null;
  if(!safeSources.length && !safeQueries.length && !safeStats) return null;

  const wrap=document.createElement('div');
  wrap.style.cssText='margin-top:12px;padding-top:10px;border-top:1px solid var(--border);display:flex;flex-direction:column;gap:8px';

  if(safeQueries.length){
    const queries=document.createElement('div');
    queries.style.cssText='display:flex;flex-wrap:wrap;gap:6px';
    safeQueries.forEach(q=>{
      const chip=document.createElement('span');
      chip.style.cssText='font-size:11px;padding:3px 8px;border-radius:999px;background:var(--s2);border:1px solid var(--border);color:var(--muted)';
      chip.textContent=q;
      queries.appendChild(chip);
    });
    wrap.appendChild(queries);
  }

  if(safeSources.length){
    const title=document.createElement('div');
    title.style.cssText='font-size:12px;font-weight:600;color:var(--muted)';
    title.textContent='Источники';
    wrap.appendChild(title);

    const list=document.createElement('div');
    list.style.cssText='display:flex;flex-direction:column;gap:6px';
    safeSources.forEach(source=>{
      const item=document.createElement('a');
      item.href=source.url||'#';
      item.target='_blank';
      item.rel='noreferrer';
      item.style.cssText='padding:8px 10px;border-radius:10px;background:var(--s2);border:1px solid var(--border);text-decoration:none;color:inherit;display:block';
      item.innerHTML=`<div style="display:flex;justify-content:space-between;gap:8px;align-items:flex-start"><strong style="font-size:12px">${esc(source.title||source.url||'Источник')}</strong><span style="font-size:10px;color:var(--red)">${esc(source.source_id||'')}</span></div><div style="font-size:11px;color:var(--muted);margin-top:3px">${esc(source.excerpt||source.snippet||'')}</div><div style="font-size:10px;color:var(--dim);margin-top:4px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis">${esc(source.url||'')}</div>`;
      list.appendChild(item);
    });
    wrap.appendChild(list);
  }

  if(safeStats){
    const statsEl=document.createElement('div');
    statsEl.style.cssText='font-size:11px;color:var(--dim)';
    const parts=[];
    if(Number.isFinite(safeStats.pages_fetched)) parts.push(`источников собрано: ${safeStats.pages_fetched}`);
    if(Number.isFinite(safeStats.sources_used)) parts.push(`использовано: ${safeStats.sources_used}`);
    if(Number.isFinite(safeStats.queries_completed) && Number.isFinite(safeStats.queries_total)) parts.push(`запросов: ${safeStats.queries_completed}/${safeStats.queries_total}`);
    if(safeStats.timed_out) parts.push('достигнут лимит времени');
    statsEl.textContent=parts.join(' • ');
    if(statsEl.textContent) wrap.appendChild(statsEl);
  }

  return wrap;
}

function appendResearchMeta(container, sources, subQueries, stats){
  if(!container) return;
  const section = buildResearchMetaSection(sources, subQueries, stats);
  if(section) container.appendChild(section);
}

function formatResearchProgress(data){
  if(data?.message) return data.message;
  if(Array.isArray(data?.sub_queries) && data.sub_queries.length){
    return data.sub_queries.slice(0,4).join(' • ');
  }
  if(data?.query){
    const completed = Number.isFinite(data.queries_completed) ? data.queries_completed : 0;
    const total = Number.isFinite(data.queries_total) ? data.queries_total : '?';
    const sourcesTotal = Number.isFinite(data.sources_total) ? data.sources_total : 0;
    return `${data.query} (${completed}/${total}), источников: ${sourcesTotal}`;
  }
  if(Number.isFinite(data?.pages_fetched)){
    return `источников собрано ${data.pages_fetched}${data.timed_out ? ' • достигнут лимит времени' : ''}`;
  }
  return '';
}

async function doSend(src){
  if(isStreaming) return;
  const ta=src==='hero'?document.getElementById('inpHero'):document.getElementById('inpBot');
  const chipsId=src==='hero'?'fChipsHero':'fChipsBot';
  const chips=document.getElementById(chipsId);
  let txt=ta.value.trim();
  const voiceId=src==='hero'?'H':'B';
  const voiceChip=chips?.querySelector('.v-chip');

  if(voiceChip&&vBlob[voiceId]){
    const textContext=txt||'';
    await sendVoiceMsg(voiceId,chips,textContext);
    ta.value=''; ta.style.height='auto';
    return;
  }

  const pendingFileChips = chips?[...chips.querySelectorAll('.f-chip:not(.v-chip)')]:[];
  if(!txt && !pendingFileChips.length) return;

  const panel=document.getElementById('panel-chat');
  const ci=document.getElementById('chatInner');
  if(!panel.classList.contains('has-messages')){
    panel.classList.add('has-messages');
    document.getElementById('inpZoneBottom').style.display='block';
    if(!currentConvId) currentConvId=uuid();
    setTimeout(()=>document.getElementById('inpBot').focus(),50);
  }

  const attachments=[];
  let injectedDocText='';
  for(const ch of pendingFileChips){
    const att={name:ch.dataset.name, mime:ch.dataset.mime||'application/octet-stream'};
    if(ch.dataset.b64) att.data=ch.dataset.b64;
    if(ch.dataset.textContent) injectedDocText+=`\n\n[Содержимое файла ${esc(ch.dataset.name)}]:\n${ch.dataset.textContent}`;
    attachments.push(att);
  }

  if(!txt && attachments.length){
    const hasDoc = attachments.some(a=>/\.(pdf|docx|txt)$/i.test(a.name||''));
    const hasImg = attachments.some(a=>a.data || /\.(png|jpg|jpeg|gif|webp)$/i.test(a.name||''));
    if(hasDoc)      txt='Проанализируй этот документ';
    else if(hasImg) txt='Опиши это изображение';
    else            txt='Проанализируй прикреплённый файл';
  }
  if(!txt) return;

  const IMAGE_GEN_RE=/нарисуй|нарисуйте|сгенерируй\s*(изображение|картинку|арт|рисунок|фото|картин)?|создай\s*(изображение|картинку|рисунок|арт)|сделай\s*(изображение|картинку|рисунок)|draw\s|generate\s*(image|picture|art|photo|illustration)|imagine\s|paint\s/i;
  const hasImageAtt = attachments.some(a=>a.data||(a.mime||'').startsWith('image/'));
  const isImageGenRequest = !hasImageAtt && IMAGE_GEN_RE.test(txt);

  ta.value=''; ta.style.height='auto';
  if(chips) chips.innerHTML='';
  document.getElementById(src==='hero'?'fChipsBot':'fChipsHero').innerHTML='';

  currentMessages.push({role:'user',content:txt});
  const userEl=appendMsg('user',txt,false,null);
  if(pendingFileChips.length){
    const fileList=document.createElement('div');
    fileList.style.cssText='margin-top:6px;display:flex;flex-wrap:wrap;gap:4px;justify-content:flex-end';
    pendingFileChips.forEach(ch=>{
      const span=document.createElement('span');
      span.style.cssText='font-size:11px;background:var(--s2);border:1px solid var(--border);border-radius:6px;padding:2px 7px;color:var(--muted);display:inline-flex;align-items:center;gap:4px';
      span.innerHTML=`<svg width="9" height="9" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" viewBox="0 0 24 24"><path d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8z"/><polyline points="14 2 14 8 20 8"/></svg>${esc(ch.dataset.name||'файл')}`;
      fileList.appendChild(span);
    });
    userEl.querySelector('.msg-bbl').appendChild(fileList);
  }

  const typing=document.createElement('div');
  typing.className='msg'; typing.id='typing';
  const tBadge=selectedModel==='auto'?'Авто':(selectedModelName||selectedModel);
  typing.innerHTML=`<div class="msg-av ai">AI</div><div class="msg-body"><div class="msg-meta"><span class="msg-sender">${esc(tBadge)}</span></div><div class="msg-bbl" style="color:var(--muted)"><span style="display:inline-block;animation:vwa 1s ease-in-out 0s infinite">●</span><span style="display:inline-block;animation:vwa 1s ease-in-out .18s infinite"> ●</span><span style="display:inline-block;animation:vwa 1s ease-in-out .36s infinite"> ●</span></div></div>`;
  ci.appendChild(typing); scrollBot();

  if(currentAgent?.id==='deepresearch'){ typing.remove(); await doDeepResearch(txt,ci); return; }
  if(currentAgent?.id==='imagegen' || isImageGenRequest){ typing.remove(); await doImageGen(txt,ci); return; }
  if(currentAgent?.id==='websearch'){    typing.remove(); await doWebSearch(txt,ci);    return; }

  if(hasImageAtt && (!currentAgent?.id || currentAgent?.id==='vision')){
    typing.remove();
    await doVlmAnalyze(txt, attachments, ci);
    return;
  }

  if(isHistoryEnabled()) fireSaveMessage('user', txt, null);

  isStreaming=true; setSendStop(true);
  abortCtrl=new AbortController();
  try {
    await waitForMemorySync();
    const messages = [...currentMessages];
    if(injectedDocText){
      const last=messages[messages.length-1];
      if(last && last.role==='user') messages[messages.length-1]={...last, content: last.content+injectedDocText};
    }
    const body={
      model: selectedModel,
      messages,
      stream: true,
      temperature: getTemperature(),
      user: currentUserId||'anonymous',
      conversation_id: currentConvId,
      use_memory: true,
    };
    if(attachments.length) body.attachments=attachments;

    const resp=await fetch(`${API}/chat/completions`,{
      method:'POST', headers:{'Content-Type':'application/json', ...authHeaders()}, body:JSON.stringify(body),
      signal: abortCtrl.signal,
    });
    if(!resp.ok){
      const err=await resp.json().catch(()=>({}));
      throw new Error(err?.error?.message||`HTTP ${resp.status}`);
    }

    document.getElementById('typing')?.remove();

    const ct = resp.headers.get('content-type')||'';
    let full=''; let usedModelId=null;

    if(ct.includes('application/json')){
      const data = await resp.json();
      if(data.data && data.data[0]){
        const imgItem = data.data[0];
        const imgSrc = imgItem.url || (imgItem.b64_json ? `data:image/png;base64,${imgItem.b64_json}` : null);
        if(imgSrc){
          const imgEl=document.createElement('div'); imgEl.className='msg';
          imgEl.innerHTML=`<div class="msg-av ai">AI</div><div class="msg-body"><div class="msg-meta"><span class="msg-sender">Image Gen</span></div><div class="msg-bbl"><img src="${imgSrc}" alt="${esc(txt)}" style="max-width:100%;border-radius:10px;margin-top:6px;display:block" onerror="this.parentElement.innerHTML='<span style=color:var(--muted)>⚠ Не удалось загрузить изображение</span>'"><br><small style="color:var(--muted)">${esc(imgItem.revised_prompt||txt)}</small></div></div>`;
          ci.appendChild(imgEl); scrollBot();
          full=`[Изображение: ${imgItem.revised_prompt||txt}]`;
        }
      } else {
        usedModelId = data.model||null;
        full = data.choices?.[0]?.message?.content
            || data.answer
            || data.description
            || data.error
            || 'Ответ получен';
        const aiEl=appendMsg('ai',full,true,usedModelId);
        appendResearchMeta(aiEl.querySelector('.msg-bbl'), data.sources, data.sub_queries, data.stats);
        aiEl.querySelector('.copyBtn').onclick=()=>{ navigator.clipboard.writeText(full).then(()=>toast('Скопировано','ok',1500)); };
      }
    } else {
      const aiEl=appendMsg('ai','',false,null);
      const bbl=aiEl.querySelector('.msg-bbl');
      let buf='';
      const reader=resp.body.getReader();
      const dec=new TextDecoder();
      let researchStream=false;
      while(true){
        const {done,value}=await reader.read();
        if(done) break;
        buf+=dec.decode(value,{stream:true});
        const lines=buf.split('\n'); buf=lines.pop()||'';
        for(const line of lines){
          if(!line.startsWith('data:')) continue;
          const data=line.slice(5).trim();
          if(data==='[DONE]') continue;
          try {
            const json=JSON.parse(data);
            if(json.research_event==='progress'){
              researchStream=true;
              const msg=formatResearchProgress(json);
              if(msg){
                const div=document.createElement('div');
                div.style.cssText='color:var(--muted);font-size:12.5px;margin:3px 0';
                div.textContent=(json.step?`Шаг ${json.step}: `:'')+msg;
                bbl.appendChild(div);
                scrollBot();
              }
              continue;
            }
            if(json.research_event==='done'){
              researchStream=true;
              usedModelId=json.model||usedModelId||'deep_research';
              updateMsgModel(aiEl,usedModelId);
              full=json.answer||json.choices?.[0]?.delta?.content||full;
              bbl.innerHTML=renderMd(full);
              appendResearchMeta(bbl, json.sources, json.sub_queries, json.stats);
              scrollBot();
              continue;
            }
            if(json.research_event==='error'){
              researchStream=true;
              const message=json.error?.message||json.message||'Ошибка исследования';
              full='';
              bbl.innerHTML=`<span style="color:var(--red)">Error: ${esc(message)}</span>`;
              appendResearchMeta(bbl, json.sources, json.sub_queries, json.stats);
              toast(`Deep Research: ${message}`,'err',4000);
              scrollBot();
              continue;
            }
            if(json.model && json.model!=='auto' && !usedModelId){
              usedModelId=json.model; updateMsgModel(aiEl,usedModelId);
            }
            const delta=json.choices?.[0]?.delta?.content||'';
            if(delta){ full+=delta; bbl.innerHTML=renderMd(full); scrollBot(); }
          } catch {}
        }
      }
      if(!usedModelId && selectedModel!=='auto' && !researchStream) updateMsgModel(aiEl, selectedModel);
      aiEl.querySelector('.copyBtn').onclick=()=>{ navigator.clipboard.writeText(full).then(()=>toast('Скопировано','ok',1500)); };
    }

    if(full){
      currentMessages.push({role:'assistant',content:full});
      if(isHistoryEnabled()) fireSaveMessage('assistant', full, usedModelId || (selectedModel !== 'auto' ? selectedModel : null));
      queueMemorySync(txt, full);
      setTimeout(()=>loadHistory(),800);
    }
  } catch(e){
    document.getElementById('typing')?.remove();
    if(e.name!=='AbortError'){
      appendMsg('ai','⚠ Ошибка соединения: '+e.message,false,null);
      toast('Ошибка API: '+e.message,'err',4000);
    }
  } finally { isStreaming=false; abortCtrl=null; setSendStop(false); }
}

async function sendVoiceMsg(id, chips, textContext){
  const blob=vBlob[id];
  if(!blob){ toast('Нет аудиозаписи','err'); return; }
  const panel=document.getElementById('panel-chat');
  const ci=document.getElementById('chatInner');
  if(!panel.classList.contains('has-messages')){
    panel.classList.add('has-messages');
    document.getElementById('inpZoneBottom').style.display='block';
    if(!currentConvId) currentConvId=uuid();
  }
  if(chips) chips.innerHTML=''; vBlob[id]=null;

  const userLabel=textContext?`🎤 ${textContext}`:'🎤 Голосовое сообщение';
  const sendEl=appendMsg('user',userLabel,false,null);
  const typing=document.createElement('div');
  typing.className='msg'; typing.id='typing';
  typing.innerHTML=`<div class="msg-av ai">AI</div><div class="msg-body"><div class="msg-meta"><span class="msg-sender">Голос → AI</span></div><div class="msg-bbl" style="color:var(--muted)"><span style="display:inline-block;animation:vwa 1s ease-in-out 0s infinite">●</span><span style="display:inline-block;animation:vwa 1s ease-in-out .18s infinite"> ●</span><span style="display:inline-block;animation:vwa 1s ease-in-out .36s infinite"> ●</span></div></div>`;
  ci.appendChild(typing); scrollBot();
  isStreaming=true;
  try {
    const fd=new FormData();
    fd.append('audio',blob,'recording.webm');
    fd.append('user_id',currentUserId||'anonymous');
    const resp=await fetch(`${API}/voice/message`,{method:'POST',body:fd});
    document.getElementById('typing')?.remove();
    const ct=resp.headers.get('content-type')||'';
    if(ct.includes('audio')){
      const transcript=decodeURIComponent(resp.headers.get('X-Transcript')||'');
      const answer=decodeURIComponent(resp.headers.get('X-Answer')||'');
      sendEl.querySelector('.msg-bbl').textContent=transcript||userLabel;
      appendMsg('ai',answer,false,null); scrollBot();
      const audioBlob=await resp.blob();
      const url=URL.createObjectURL(audioBlob);
      const audio=new Audio(url);
      audio.play().catch(()=>{});
      audio.onended=()=>URL.revokeObjectURL(url);
      if(transcript) currentMessages.push({role:'user',content:transcript});
      if(answer)     currentMessages.push({role:'assistant',content:answer});
      if(transcript && answer) queueMemorySync(transcript, answer);
    } else {
      const data=await resp.json();
      const transcript=data.transcript||userLabel;
      const answer=data.answer||'Голосовой ответ получен';
      sendEl.querySelector('.msg-bbl').textContent=transcript;
      appendMsg('ai',answer,false,null); scrollBot();
      toast('TTS недоступен — только текст','inf');
      currentMessages.push({role:'user',content:transcript});
      currentMessages.push({role:'assistant',content:answer});
      queueMemorySync(transcript, answer);
    }
    setTimeout(()=>loadHistory(),800);
  } catch(e){
    document.getElementById('typing')?.remove();
    appendMsg('ai','⚠ Ошибка голосового API: '+e.message,false,null);
    toast('Ошибка голосового API: '+e.message,'err');
  } finally { isStreaming=false; }
}

async function doDeepResearchLegacy(query,ci){
  isStreaming=true; setSendStop(true);
  abortCtrl=new AbortController();
  const el=document.createElement('div'); el.className='msg';
  el.innerHTML=`<div class="msg-av ai">AI</div><div class="msg-body"><div class="msg-meta"><span class="msg-sender">Deep Research</span><span class="msg-badge">Deep Research</span></div><div class="msg-bbl" id="researchProg" style="line-height:1.75"><div style="color:var(--muted)">🔍 Начинаю исследование...</div></div></div>`;
  ci.appendChild(el); scrollBot();
  const prog=document.getElementById('researchProg');
  let finalAnswer='';
  try {
    if(isHistoryEnabled()) fireSaveMessage('user', query, null);
    const resp=await fetch(`${API}/research`,{
      method:'POST',
      headers:{'Content-Type':'application/json', ...authHeaders()},
      body:JSON.stringify({query,user_id:currentUserId||'anonymous'}),
      signal: abortCtrl.signal,
    });
    if(!resp.ok) throw new Error(`HTTP ${resp.status}`);
    const reader=resp.body.getReader(); const dec=new TextDecoder();
    let buf=''; let evType='';
    while(true){
      const {done,value}=await reader.read(); if(done) break;
      buf+=dec.decode(value,{stream:true});
      const lines=buf.split('\n'); buf=lines.pop()||'';
      for(const line of lines){
        if(line.startsWith('event:')) evType=line.slice(6).trim();
        else if(line.startsWith('data:')){
          try {
            const data=JSON.parse(line.slice(5).trim());
            if(evType==='done'){
              finalAnswer=data.answer||'Готово.';
              prog.innerHTML=renderMd(finalAnswer);
              appendResearchMeta(prog, data.sources, data.sub_queries, data.stats);
              currentMessages.push({role:'assistant',content:finalAnswer});
              if(isHistoryEnabled()) fireSaveMessage('assistant', finalAnswer, data.model||'deep_research');
              queueMemorySync(query, finalAnswer);
              setTimeout(()=>loadHistory(),800);
              scrollBot();
            }
            else if(evType==='error'){
              const message=data.message||'Ошибка исследования';
              prog.innerHTML=`<span style="color:var(--red)">⚠ ${esc(message)}</span>`;
              appendResearchMeta(prog, data.sources, data.sub_queries, data.stats);
              toast(`Deep Research: ${message}`,'err',4000);
              scrollBot();
            }
            else if(evType==='progress'){
              const msg=formatResearchProgress(data);
              if(msg){ const div=document.createElement('div'); div.style.cssText='color:var(--muted);font-size:12.5px;margin:3px 0'; div.textContent=(data.step?`Шаг ${data.step}: `:'')+msg; prog.appendChild(div); scrollBot(); }
            }
          } catch {} evType='';
        }
      }
    }
  } catch(e){ prog.innerHTML=`<span style="color:var(--red)">⚠ Ошибка: ${esc(e.message)}</span>`; toast('Deep Research: ошибка','err'); }
  finally { isStreaming=false; }
}

// Override legacy handler with a stable abort-aware implementation.
async function doDeepResearch(query,ci){
  isStreaming=true;
  setSendStop(true);
  abortCtrl=new AbortController();

  const el=document.createElement('div');
  el.className='msg';
  el.innerHTML=`<div class="msg-av ai">AI</div><div class="msg-body"><div class="msg-meta"><span class="msg-sender">Deep Research</span><span class="msg-badge">Deep Research</span></div><div class="msg-bbl" id="researchProg" style="line-height:1.75"><div style="color:var(--muted)">Starting research...</div></div></div>`;
  ci.appendChild(el);
  scrollBot();

  const prog=document.getElementById('researchProg');
  let finalAnswer='';
  let terminalSeen=false;

  try {
    if(isHistoryEnabled()) fireSaveMessage('user', query, null);

    const resp=await fetch(`${API}/research`,{
      method:'POST',
      headers:{'Content-Type':'application/json', ...authHeaders()},
      body:JSON.stringify({query,user_id:currentUserId||'anonymous'}),
      signal: abortCtrl.signal,
    });
    if(!resp.ok) throw new Error(`HTTP ${resp.status}`);
    if(!resp.body) throw new Error('Empty research response');

    const reader=resp.body.getReader();
    const dec=new TextDecoder();
    let buf='';
    let evType='';

    while(true){
      const {done,value}=await reader.read();
      if(done) break;
      buf+=dec.decode(value,{stream:true});
      const lines=buf.split('\n');
      buf=lines.pop()||'';

      for(const line of lines){
        if(line.startsWith('event:')){
          evType=line.slice(6).trim();
          continue;
        }
        if(!line.startsWith('data:')) continue;

        try {
          const data=JSON.parse(line.slice(5).trim());
          if(evType==='done'){
            terminalSeen=true;
            finalAnswer=data.answer||'Research completed.';
            prog.innerHTML=renderMd(finalAnswer);
            appendResearchMeta(prog, data.sources, data.sub_queries, data.stats);
            currentMessages.push({role:'assistant',content:finalAnswer});
            if(isHistoryEnabled()) fireSaveMessage('assistant', finalAnswer, data.model||'deep_research');
            queueMemorySync(query, finalAnswer);
            setTimeout(()=>loadHistory(),800);
            scrollBot();
          } else if(evType==='error'){
            terminalSeen=true;
            const message=data.message||'Research failed';
            prog.innerHTML=`<span style="color:var(--red)">Error: ${esc(message)}</span>`;
            appendResearchMeta(prog, data.sources, data.sub_queries, data.stats);
            toast(`Deep Research: ${message}`,'err',4000);
            scrollBot();
          } else if(evType==='progress'){
            const msg=formatResearchProgress(data);
            if(msg){
              const div=document.createElement('div');
              div.style.cssText='color:var(--muted);font-size:12.5px;margin:3px 0';
              div.textContent=(data.step?`Step ${data.step}: `:'')+msg;
              prog.appendChild(div);
              scrollBot();
            }
          }
        } catch {}

        evType='';
      }
    }

    if(!terminalSeen){
      prog.innerHTML='<span style="color:var(--red)">Research stopped before a final result.</span>';
      toast('Deep Research: incomplete response','err',3000);
      scrollBot();
    }
  } catch(e){
    if(e.name==='AbortError'){
      prog.innerHTML='<span style="color:var(--muted)">Research stopped.</span>';
      scrollBot();
    } else {
      prog.innerHTML=`<span style="color:var(--red)">Error: ${esc(e.message)}</span>`;
      toast(`Deep Research: ${e.message}`,'err',4000);
      scrollBot();
    }
  } finally {
    isStreaming=false;
    abortCtrl=null;
    setSendStop(false);
  }
}

async function doVlmAnalyze(txt, attachments, ci){
  isStreaming=true;
  const wrapEl=document.createElement('div'); wrapEl.className='msg';
  wrapEl.innerHTML=`<div class="msg-av ai">AI</div><div class="msg-body"><div class="msg-meta"><span class="msg-sender">Vision</span></div><div class="msg-bbl" id="vlmBbl" style="line-height:1.6"><div style="color:var(--muted)">🔍 Анализирую изображение...</div></div></div>`;
  ci.appendChild(wrapEl); scrollBot();
  const bbl=document.getElementById('vlmBbl');
  try {
    const imgAtt=attachments.find(a=>a.data||(a.mime||'').startsWith('image/'));
    if(!imgAtt){ bbl.innerHTML='<span style="color:var(--red)">⚠ Изображение не найдено</span>'; isStreaming=false; return; }
    const imageUrl=imgAtt.data
      ? `data:${imgAtt.mime||'image/jpeg'};base64,${imgAtt.data}`
      : imgAtt.url||'';
    const r=await fetch(`${API}/vlm/analyze`,{
      method:'POST', headers:{'Content-Type':'application/json',...authHeaders()},
      body:JSON.stringify({image_url:imageUrl, question:txt||'Опиши это изображение', model:'cotype-pro-vl-32b'})
    });
    const d=await r.json();
    const answer=d.choices?.[0]?.message?.content || d.answer || d.description || d.error || 'Анализ завершён';
    bbl.innerHTML=renderMd(answer);
    currentMessages.push({role:'assistant',content:answer});
    fireSaveMessage('assistant', answer, 'cotype-pro-vl-32b');
    queueMemorySync(txt || 'Опиши это изображение', answer);
    setTimeout(()=>loadHistory(),600);
  } catch(e){
    bbl.innerHTML=`<span style="color:var(--red)">⚠ Ошибка: ${esc(e.message)}</span>`;
    toast('Ошибка VLM','err');
  } finally { isStreaming=false; scrollBot(); }
}

async function doImageGen(prompt,ci){
  isStreaming=true;
  const wrapEl=document.createElement('div'); wrapEl.className='msg';
  wrapEl.innerHTML=`<div class="msg-av ai">AI</div><div class="msg-body"><div class="msg-meta"><span class="msg-sender">Image Gen</span></div><div class="msg-bbl" id="imgGenBbl" style="line-height:1.6"><div style="color:var(--muted)">🎨 Генерирую изображение по запросу: <em>${esc(prompt)}</em>...</div></div></div>`;
  ci.appendChild(wrapEl); scrollBot();
  const bbl=document.getElementById('imgGenBbl');
  try {
    const r=await fetch(`${API}/image/generate`,{
      method:'POST',headers:{'Content-Type':'application/json'},
      body:JSON.stringify({prompt, model:'qwen-image', size:'1024x1024'})
    });
    const d=await r.json();

    let imgSrc=null, caption=prompt;
    if(d.data&&d.data[0]){
      const item=d.data[0];
      if(item.url)           imgSrc=item.url;
      else if(item.b64_json) imgSrc=`data:image/png;base64,${item.b64_json}`;
      if(item.revised_prompt) caption=item.revised_prompt;
    }

    if(imgSrc){
      bbl.innerHTML=`
        <img src="${imgSrc}" alt="${esc(prompt)}"
          style="max-width:100%;border-radius:12px;margin-top:8px;display:block;box-shadow:0 4px 20px rgba(0,0,0,.4)"
          onload="this.style.opacity=1"
          onerror="this.parentElement.innerHTML='<span style=color:var(--red)>⚠ Изображение недоступно (URL истёк или сервис вернул ошибку)</span><br><small style=color:var(--muted)>${esc(prompt)}</small>'"
          style="max-width:100%;border-radius:12px;margin-top:8px;display:block;opacity:0;transition:opacity .4s">
        <small style="color:var(--muted);display:block;margin-top:6px">${esc(caption)}</small>
        <a href="${imgSrc.startsWith('data:') ? '#' : imgSrc}" ${imgSrc.startsWith('data:') ? `onclick="downloadImg('${prompt}')" style="cursor:pointer"` : 'target="_blank"'} style="font-size:11px;color:var(--red);text-decoration:none;display:inline-flex;align-items:center;gap:4px;margin-top:4px">
          <svg width="10" height="10" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" viewBox="0 0 24 24"><path d="M21 15v4a2 2 0 01-2 2H5a2 2 0 01-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/></svg>
          Скачать
        </a>`;
      currentMessages.push({role:'assistant',content:`[Сгенерированное изображение: ${caption}]`});
      fireSaveMessage('user', prompt, null);
      fireSaveMessage('assistant', `[Сгенерированное изображение: ${caption}]`, 'qwen-image');
      setTimeout(()=>loadHistory(),600);
    } else if(d.fallback){
      bbl.innerHTML=`<span style="color:var(--muted)">⚠ Сервис генерации изображений сейчас недоступен.</span><br><small style="color:var(--dim)">Промпт сохранён: ${esc(prompt)}</small>`;
      toast('Image Gen недоступен','err',3500);
    } else {
      bbl.innerHTML=`<span style="color:var(--red)">⚠ ${esc(d.error||'Неизвестная ошибка')}</span>`;
    }
    scrollBot();
  } catch(e){
    bbl.innerHTML=`<span style="color:var(--red)">⚠ Ошибка: ${esc(e.message)}</span>`;
    toast('Ошибка генерации','err');
  }
  finally { isStreaming=false; }
}

function downloadImg(prompt){
  const img=document.querySelector('#imgGenBbl img');
  if(!img) return;
  const a=document.createElement('a');
  a.href=img.src; a.download=(prompt||'image').slice(0,40).replace(/[^a-zа-я0-9]/gi,'_')+'.png';
  a.click();
}

async function doWebSearch(query, ci){
  isStreaming=true;
  const el=document.createElement('div'); el.className='msg';
  el.innerHTML=`<div class="msg-av ai">AI</div><div class="msg-body"><div class="msg-meta"><span class="msg-sender">Поиск</span><span class="msg-badge">Web Search</span></div><div class="msg-bbl" id="searchProg" style="line-height:1.75"><div style="color:var(--muted)">🔍 Ищу в интернете...</div></div></div>`;
  ci.appendChild(el); scrollBot();
  const prog=document.getElementById('searchProg');
  try {
    const sr=await fetch(`${API}/tools/web-search`,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({query,max_results:5})});
    if(!sr.ok) throw new Error('Поиск недоступен');
    const sd=await sr.json();
    const results=sd.results||[];
    if(!results.length){ prog.innerHTML='<span style="color:var(--muted)">Результатов не найдено.</span>'; isStreaming=false; return; }

    const srcDiv=document.createElement('div');
    srcDiv.style.cssText='margin-bottom:10px;display:flex;flex-wrap:wrap;gap:5px';
    results.forEach(r=>{
      const chip=document.createElement('a');
      chip.href=r.url; chip.target='_blank';
      chip.style.cssText='font-size:10.5px;padding:2px 8px;border-radius:5px;background:var(--s3);color:var(--muted);text-decoration:none;border:1px solid var(--border);max-width:160px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;display:block';
      chip.textContent=r.title||r.url;
      chip.title=r.url;
      srcDiv.appendChild(chip);
    });
    prog.innerHTML=''; prog.appendChild(srcDiv);
    const ansDiv=document.createElement('div'); prog.appendChild(ansDiv);

    const context=results.map((r,i)=>`[${i+1}] ${r.title}\n${r.snippet}\nURL: ${r.url}`).join('\n\n');
    const synthMessages=[
      {role:'system',content:'Ты — поисковый ассистент. Дай чёткий, структурированный ответ на основе найденных результатов. Цитируй источники в формате [N]. Отвечай на языке вопроса.'},
      {role:'user',content:`Вопрос: ${query}\n\nНайденные материалы:\n${context}`}
    ];
    const resp=await fetch(`${API}/chat/completions`,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({model:'auto',messages:synthMessages,stream:true,user:currentUserId||'anonymous'})});
    if(!resp.ok) throw new Error('LLM недоступен');
    const reader=resp.body.getReader(); const dec=new TextDecoder();
    let full=''; let buf='';
    while(true){
      const {done,value}=await reader.read(); if(done) break;
      buf+=dec.decode(value,{stream:true});
      const lines=buf.split('\n'); buf=lines.pop()||'';
      for(const line of lines){
        if(!line.startsWith('data:')) continue;
        const data=line.slice(5).trim();
        if(data==='[DONE]') break;
        try { const json=JSON.parse(data); const delta=json.choices?.[0]?.delta?.content||''; if(delta){ full+=delta; ansDiv.innerHTML=renderMd(full); scrollBot(); } } catch {}
      }
    }
    currentMessages.push({role:'assistant',content:full});
    setTimeout(()=>loadHistory(),800);
  } catch(e){ prog.innerHTML=`<span style="color:var(--red)">⚠ Ошибка: ${esc(e.message)}</span>`; toast('Поиск: ошибка','err'); }
  finally { isStreaming=false; }
}

function copyMsg(btn,text){ navigator.clipboard?.writeText(text).then(()=>{ btn.classList.add('copied'); toast('Скопировано','ok',1800); setTimeout(()=>btn.classList.remove('copied'),2000); }).catch(()=>toast('Не удалось скопировать','err')); }
function likeMsg(btn){ btn.style.color='#22C55E'; btn.querySelector('svg').style.fill='rgba(34,197,94,.2)'; toast('Отмечено как полезное','ok',1800); }
function fillQ(txt){ const ta=document.getElementById('inpHero'); ta.value=txt; autoH(ta); ta.focus(); }
function syncTA(el){ autoH(el); }
