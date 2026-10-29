/* Chat compartido entre el panel flotante y /asistente. Sin claves ni HTML de IA. */
(() => {
  'use strict';
  const root = document.querySelector('[data-assistant]');
  if (!root) return;
  const q = selector => root.querySelector(selector);
  const launcher = document.querySelector('#assistant-launcher');
  const full = root.classList.contains('ma-full');
  const storageKey = 'm2-assistant-conversation-v1';
  const settingsKey = 'm2-assistant-settings-v1';
  const defaults = {name:'JARVIS',accent:'#40ddc5',avatar:'orb',image:'',frames:1,rows:1,voice:'',autoSpeak:true,voiceEngine:'browser',revision:6};
  function storage(name) {try {return window[name];} catch {return null;}}
  const localStore=storage('localStorage'), sessionStore=storage('sessionStorage');
  function read(store,key,fallback) {try {return JSON.parse(store.getItem(key)) || fallback;} catch {return fallback;}}
  function save(store,key,value) {try {store.setItem(key,JSON.stringify(value));return true;} catch {return false;}}
  function notice(text) {q('[data-status]').textContent = text;}
  const previousSettings=read(localStore,settingsKey,{});
  let settings = {...defaults,...previousSettings};
  if(!previousSettings.revision||previousSettings.revision<5){settings.voiceEngine='browser';settings.voice='';settings.autoSpeak=true;settings.revision=5;save(localStore,settingsKey,settings);}
  if(previousSettings.revision!==6){settings.name='JARVIS';settings.avatar='orb';settings.revision=6;save(localStore,settingsKey,settings);}
  const restored = read(sessionStore,storageKey,{});
  let messages = Array.isArray(restored.messages) ? restored.messages.filter(m => m && ['user','assistant'].includes(m.role) && typeof m.text === 'string' && m.text.length <= 6000).slice(-20) : [];
  let context = restored.context && typeof restored.context === 'object' ? restored.context : null;
  let contextTitle = typeof restored.contextTitle === 'string' ? restored.contextTitle.slice(0,120) : 'Ejercicio seleccionado';
  let busy = false, version = 0, requestController = null, recognition = null, listening = false, speechVersion = 0, avatarFrame = 0, spriteTimer = null;
  let phase = 'idle', audio=null, audioURL=null, speechController=null, finishAudio=null, silenceVersion=-1;
  const question = q('[data-question]');
  const synth = window.speechSynthesis;
  const Recognition = window.SpeechRecognition || window.webkitSpeechRecognition;
  const reduceMotion = window.matchMedia('(prefers-reduced-motion: reduce)');
  const phaseLabels = {idle:'Listo para ayudarte',listening:'Escuchando tu pregunta',thinking:'Preparando una respuesta',speaking:'Leyendo la respuesta'};

  function persist() {save(sessionStore,storageKey,{messages:messages.slice(-20),context,contextTitle});}
  function element(tag,text,parent,className='') {const el=document.createElement(tag);el.textContent=text;el.className=className;parent.append(el);return el;}
  function setPhase(value) {phase=value;root.dataset.state=value;q('[data-state]').textContent=phaseLabels[value];avatarFrame=0;paintFrame();}
  function paintFrame() {
    const avatar=q('[data-avatar]');
    if(settings.avatar!=='custom'||!settings.image)return;
    const row=settings.rows===4?['idle','listening','thinking','speaking'].indexOf(phase):0;
    const x=settings.frames>1?avatarFrame/(settings.frames-1)*100:0;
    avatar.style.backgroundPosition=`${x}% ${settings.rows===4?row/3*100:0}%`;
  }
  function animateSprite() {
    clearInterval(spriteTimer);spriteTimer=null;paintFrame();
    if(!document.hidden&&!reduceMotion.matches&&(settings.avatar==='custom'&&settings.frames>1&&!root.hidden)) {
      spriteTimer=setInterval(()=>{avatarFrame=(avatarFrame+1)%settings.frames;paintFrame();},160);
    }
  }
  function applySettings() {
    settings.name=String(settings.name||'JARVIS').slice(0,30);
    if(!/^#[0-9a-f]{6}$/i.test(settings.accent))settings.accent=defaults.accent;
    if(!['robot','orb','cat','custom'].includes(settings.avatar))settings.avatar='orb';
    settings.frames=Math.min(16,Math.max(1,Number(settings.frames)||1));settings.frames=Math.floor(settings.frames);
    settings.rows=Number(settings.rows)===4?4:1;
    if(typeof settings.image!=='string'||!/^data:image\/png;base64,[A-Za-z0-9+/=]+$/.test(settings.image)||settings.image.length>600000)settings.image='';
    settings.voiceEngine='browser';
    root.style.setProperty('--ma-accent',settings.accent);
    q('[data-name]').textContent=settings.name;
    const avatar=q('[data-avatar]');avatar.dataset.avatarKind=settings.avatar==='custom'&&!settings.image?'robot':settings.avatar;
    avatar.style.backgroundImage=settings.avatar==='custom'&&settings.image?`url("${settings.image}")`:'';
    avatar.style.backgroundSize=`${settings.frames*100}% ${settings.rows*100}%`;
    root.querySelectorAll('[data-setting]').forEach(input=>{const value=settings[input.dataset.setting];if(input.type==='checkbox')input.checked=!!value;else input.value=value;});
    if(launcher)launcher.querySelector('[data-launcher-name]').textContent=settings.name;
    animateSprite();
  }
  function updateContext() {
    q('[data-context]').hidden=!context;
    q('[data-context-label]').textContent=context?`Contexto: ${contextTitle}. Se volverá a calcular en el servidor.`:'';
  }
  function updateCount() {q('[data-count]').textContent=`${question.value.length} / 1500`;}

  function stopSpeech() {
    speechVersion++;speechController?.abort();speechController=null;
    if(audio){audio.onended=null;audio.onerror=null;audio.pause();audio.removeAttribute('src');audio.load();audio=null;}
    finishAudio?.();finishAudio=null;if(audioURL){URL.revokeObjectURL(audioURL);audioURL=null;}
    if(synth)synth.cancel();if(phase==='speaking')setPhase(busy?'thinking':'idle');
  }
  function speechText(text) {
    let result=text.replace(/```[\s\S]*?```/g,' Fragmento de código disponible en el texto. ')
      .replace(/\[([^\]]+)\]\([^)]*\)/g,'$1').replace(/https?:\/\/\S+/g,' enlace en el texto ');
    for(let i=0;i<5;i++)result=result.replace(/\\(?:d?frac)\s*\{([^{}]*)\}\s*\{([^{}]*)\}/g,' ( $1 ) dividido entre ( $2 ) ')
      .replace(/\\sqrt\s*\{([^{}]*)\}/g,' raíz cuadrada de ( $1 ) ');
    const names={partial:' derivada parcial ',nabla:' gradiente ',cdot:' por ',times:' por ',div:' dividido entre ',int:' integral ',iint:' integral doble ',iiint:' integral triple ',infty:' infinito ',pi:' pi ',theta:' teta ',alpha:' alfa ',beta:' beta ',lambda:' lambda ',Delta:' delta ',leq:' menor o igual que ',geq:' mayor o igual que ',neq:' distinto de ',approx:' aproximadamente ',to:' tiende a '};
    result=result.replace(/\\([a-zA-Z]+)/g,(_,name)=>names[name]||(['left','right','text','mathrm'].includes(name)?' ':` ${name} `));
    return result.replace(/\^(?:\{2\}|2(?![\d.]))/g,' al cuadrado ').replace(/\^(?:\{3\}|3(?![\d.]))/g,' al cubo ')
      .replace(/\^\{([^}]+)\}/g,' elevado a $1 ').replace(/\^([\w+-]+)/g,' elevado a $1 ')
      .replace(/_\{([^}]+)\}/g,' subíndice $1 ').replace(/_([a-zA-Z0-9])/g,' subíndice $1 ')
      .replace(/\\[()[\]]/g,' ').replace(/\\/g,' ').replace(/[*#`{}$]/g,' ')
      .replace(/²/g,' al cuadrado ').replace(/³/g,' al cubo ').replace(/π/g,' pi ').replace(/√/g,' raíz cuadrada de ').replace(/×/g,' por ').replace(/÷/g,' dividido entre ').replace(/=/g,' igual a ').replace(/\+/g,' más ').replace(/[−-]/g,' menos ').replace(/\//g,' dividido entre ')
      .replace(/</g,' menor que ').replace(/>/g,' mayor que ').replace(/\s+/g,' ').trim();
  }
  function chunksFor(text,limit) {
    const chunks=[];let remaining=text.trim();
    while(remaining.length>limit){let split=-1;const head=remaining.slice(0,limit+1);const ends=[...head.matchAll(/[.!?;:]\s/g)];if(ends.length)split=ends.at(-1).index+1;if(split<limit/3)split=head.lastIndexOf(' ');if(split<1)split=limit;chunks.push(remaining.slice(0,split).trim());remaining=remaining.slice(split).trim();}
    if(remaining)chunks.push(remaining);return chunks;
  }
  function isLatamVoice(voice) {
    return /^es[-_](MX|GT|419|AR|BO|CL|CO|CR|CU|DO|EC|SV|HN|NI|PA|PY|PE|PR|UY|VE|US)(?:$|[-_])/i.test(voice.lang);
  }
  function voiceScore(voice) {
    return (isLatamVoice(voice)?1000:0)+(/natural|neural|online/i.test(voice.name)?100:0)+(/google/i.test(voice.name)?50:0)+(/^es[-_](MX|GT)(?:$|[-_])/i.test(voice.lang)?10:0);
  }
  function spanishVoices() {
    return (synth?.getVoices()||[]).filter(v=>/^es(?:-|_|$)/i.test(v.lang)).sort((a,b)=>voiceScore(b)-voiceScore(a));
  }
  function spanishVoice() {
    const voices=spanishVoices();
    return voices.find(v=>v.voiceURI===settings.voice)||voices[0];
  }
  function speakBrowser(text,token,waited=false) {
    if(!synth||!window.SpeechSynthesisUtterance){notice('No hay voz española del navegador disponible. El texto sigue visible.');return;}
    if(token!==speechVersion)return;
    const selected=spanishVoice();
    if(!selected){
      if(!waited){notice('Cargando las voces en español…');setTimeout(()=>speakBrowser(text,token,true),1500);return;}
      notice('No hay voces en español disponibles en este navegador. Habilita una voz española en el sistema o prueba otro navegador; no usaré una voz inglesa.');return;
    }
    notice(isLatamVoice(selected)?`Voz latinoamericana: ${selected.name}.`:`Voz disponible: ${selected.name}. Este navegador no seleccionó una voz latinoamericana; revisa el selector de voz.`);
    const chunks=chunksFor(text,260);
    function next(index){
      if(token!==speechVersion)return;
      if(index>=chunks.length){setPhase(busy?'thinking':'idle');return;}
      const utterance=new SpeechSynthesisUtterance(chunks[index]);const voice=selected;
      utterance.lang=voice?.lang||'es-MX';if(voice)utterance.voice=voice;utterance.rate=.96;utterance.pitch=1;
      utterance.onstart=()=>{if(token===speechVersion)setPhase('speaking');};utterance.onend=()=>next(index+1);
      utterance.onerror=()=>{if(token===speechVersion){setPhase(busy?'thinking':'idle');notice('No se pudo reproducir la voz. Pulsa Escuchar o elige otra voz española.');}};
      synth.speak(utterance);
    }
    next(0);
  }
  function speak(text) {
    stopSpeech();if(listening)stopListening();speakBrowser(speechText(text),speechVersion);
  }
  function paintVoices() {
    const select=q('[data-voice]');select.replaceChildren();element('option','Automática · prioridad latinoamericana',select).value='';
    if(!synth){select.disabled=true;return;}
    spanishVoices().forEach(v=>{const option=element('option',`${v.name} (${v.lang})${isLatamVoice(v)?' · Latinoamérica':''}`,select);option.value=v.voiceURI;});
    select.value=settings.voice||'';
  }
  function addMessage(message) {
    const article=element('article','',q('[data-log]'),'ma-message'+(message.role==='user'?' ma-user':''));
    element('h3',message.role==='user'?'Tú':settings.name,article);
    const body=element('p',message.text,article);
    if(message.role==='assistant') {
      const play=element('button','▶ Escuchar',article);play.type='button';play.addEventListener('click',()=>speak(message.text));
      window.MathJax?.typesetPromise?.([body])?.catch(()=>{});
    }
    return article;
  }
  function renderLog() {
    const log=q('[data-log]');log.replaceChildren();
    if(!messages.length){const welcome=element('div','',log,'ma-welcome');element('strong','Aprendamos paso a paso.',welcome);element('p','Puedes escribir, dictar una pregunta o traer un cálculo de las unidades. Personaliza mi avatar para hacerlo tuyo.',welcome);}
    messages.forEach(addMessage);log.scrollTop=log.scrollHeight;
  }
  function setBusy(value) {busy=value;q('[data-send]').disabled=value;question.disabled=value;q('[data-mic]').disabled=value||!Recognition;setPhase(value?'thinking':'idle');}
  function show() {root.hidden=false;if(launcher)launcher.setAttribute('aria-expanded','true');animateSprite();question.focus();}
  function stopListening() {if(recognition){recognition.onresult=null;recognition.abort();recognition=null;}listening=false;q('[data-mic]').setAttribute('aria-pressed','false');q('[data-mic]').textContent='🎙 Dictar';if(phase==='listening')setPhase('idle');}
  function close() {stopListening();stopSpeech();root.hidden=true;animateSprite();if(launcher){launcher.setAttribute('aria-expanded','false');launcher.focus();}}
  function resetConversation() {
    version++;requestController?.abort();requestController=null;stopListening();stopSpeech();setBusy(false);
    messages=[];context=null;contextTitle='';persist();renderLog();updateContext();notice('Conversación borrada en esta sesión.');question.focus();
  }
  function payloadFor(message) {
    const payload={message,history:messages.slice(-8).map(m=>({role:m.role,text:m.text})),mode:q('[data-mode-select]').value,context};
    const size=()=>new TextEncoder().encode(JSON.stringify(payload)).length;
    while(payload.history.length&&(size()>14500||payload.history.reduce((n,m)=>n+m.text.length,0)+message.length>9500))payload.history.shift();
    if(size()>15500)throw new Error('La pregunta y el ejercicio son demasiado largos. Reduce la pregunta o quita el contexto.');
    return payload;
  }
  q('[data-chat-form]').addEventListener('submit',async event=>{
    event.preventDefault();if(busy)return;
    const message=question.value.trim();if(!message){question.focus();return;}
    if(message.length>1500){notice('Escribe hasta 1500 caracteres.');return;}
    let payload;try{payload=payloadFor(message);}catch(error){notice(error.message);return;}
    stopListening();stopSpeech();const current=++version;setBusy(true);notice('Consultando al asistente…');
    if(settings.autoSpeak&&settings.voiceEngine==='browser')speak('Claro. Estoy preparando tu respuesta.',{immediate:true});
    const pending=addMessage({role:'user',text:message});q('[data-log]').scrollTop=q('[data-log]').scrollHeight;
    const controller=new AbortController();requestController=controller;const timer=setTimeout(()=>controller.abort(),27000);
    try {
      const response=await fetch('/api/chat',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(payload),signal:controller.signal});
      const data=await response.json();if(!response.ok)throw new Error(data.error||'No se pudo obtener respuesta.');
      if(typeof data.reply!=='string'||!data.reply.trim())throw new Error('La respuesta está vacía. Intenta otra vez.');
      if(version!==current)return;
      messages.push({role:'user',text:message},{role:'assistant',text:data.reply});messages=messages.slice(-20);persist();
      question.value='';updateCount();renderLog();notice(data.calculation_used?'Se usó el resultado recalculado por SymPy. La explicación adicional es orientativa.':'Respuesta de IA. Para usar SymPy, adjunta un cálculo desde una calculadora.');
      if(settings.autoSpeak&&silenceVersion!==current&&!root.hidden&&!document.hidden)speak(data.reply);
    } catch(error) {if(version===current){pending.remove();notice(error.name==='AbortError'?'La respuesta tardó demasiado. Tu pregunta se conserva para volver a intentar.':error.message);}}
    finally {clearTimeout(timer);if(version===current){requestController=null;busy=false;q('[data-send]').disabled=false;question.disabled=false;q('[data-mic]').disabled=!Recognition;if(phase==='thinking')setPhase('idle');question.focus();}}
  });
  question.addEventListener('input',updateCount);
  question.addEventListener('keydown',event=>{if(event.key==='Enter'&&!event.shiftKey&&!event.isComposing){event.preventDefault();q('[data-chat-form]').requestSubmit();}});
  q('[data-clear]').addEventListener('click',resetConversation);
  q('[data-stop-speech]').addEventListener('click',()=>{silenceVersion=version;stopSpeech();});
  q('[data-customize]').addEventListener('click',()=>{const panel=q('[data-settings]');panel.open=!panel.open;q('[data-customize]').setAttribute('aria-expanded',String(panel.open));});
  q('[data-settings]').addEventListener('toggle',()=>q('[data-customize]').setAttribute('aria-expanded',String(q('[data-settings]').open)));
  q('[data-test-voice]').addEventListener('click',()=>speak('Hola. Soy tu asistente de Matemática dos. Vamos a aprender paso a paso, en español.'));
  q('[data-remove-context]').addEventListener('click',()=>{context=null;persist();updateContext();notice('Contexto retirado para las próximas preguntas.');});
  q('[data-mode-select]').addEventListener('change',()=>{root.dataset.mode=q('[data-mode-select]').value;notice('Estilo de conversación actualizado.');});
  root.querySelectorAll('[data-prompt]').forEach(button=>button.addEventListener('click',()=>{if(busy)return;question.value=button.dataset.prompt;updateCount();question.focus();}));
  root.querySelectorAll('[data-setting]').forEach(input=>input.addEventListener('change',()=>{settings[input.dataset.setting]=input.type==='checkbox'?input.checked:input.value;applySettings();if(!save(localStore,settingsKey,settings))notice('No hay espacio para guardar la personalización; se mantiene durante esta página.');if(input.dataset.setting==='autoSpeak'&&!input.checked)stopSpeech();}));
  q('[data-voice]').addEventListener('change',()=>{settings.voice=q('[data-voice]').value;save(localStore,settingsKey,settings);stopSpeech();});
  q('[data-reset-avatar]').addEventListener('click',()=>{settings={...defaults,voice:settings.voice,autoSpeak:settings.autoSpeak,voiceEngine:settings.voiceEngine};applySettings();save(localStore,settingsKey,settings);notice('Avatar restablecido.');});
  q('[data-upload]').addEventListener('change',async event=>{
    const file=event.target.files[0];if(!file)return;
    if(!['image/png','image/jpeg','image/webp'].includes(file.type)||file.size>2*1024*1024){notice('Elige PNG, JPG o WebP de hasta 2 MB.');event.target.value='';return;}
    const url=URL.createObjectURL(file);
    try {
      const img=new Image();img.src=url;await img.decode();
      if(img.width>2048||img.height>2048||img.width<1||img.height<1)throw new Error('La imagen debe medir como máximo 2048 × 2048 píxeles.');
      const canvas=document.createElement('canvas');canvas.width=img.width;canvas.height=img.height;canvas.getContext('2d').drawImage(img,0,0);
      const encoded=canvas.toDataURL('image/png');if(encoded.length>600000)throw new Error('La imagen ocupa demasiado espacio. Usa una imagen más pequeña o una hoja de sprites sencilla.');
      const next={...settings,image:encoded,avatar:'custom',frames:1,rows:1};
      if(!save(localStore,settingsKey,next))throw new Error('El navegador no pudo guardar la imagen. Libera almacenamiento o elige una más pequeña.');
      settings=next;applySettings();notice('Imagen guardada solo en este navegador. Si es una hoja de sprites, indica sus fotogramas y filas.');
    }catch(error){notice(error.message||'No se pudo leer esa imagen.');}
    finally{URL.revokeObjectURL(url);event.target.value='';}
  });
  q('[data-mic]').addEventListener('click',()=>{
    if(listening){stopListening();return;}
    if(!Recognition){notice('El dictado no está disponible en este navegador. Puedes escribir y usar Escuchar.');return;}
    if(!window.isSecureContext){notice('El micrófono requiere HTTPS o localhost.');return;}
    stopSpeech();const draft=question.value.trim();let finalText='';recognition=new Recognition();const active=recognition;
    active.lang='es-ES';active.interimResults=true;active.continuous=false;
    active.onstart=()=>{if(recognition!==active)return;listening=true;q('[data-mic]').setAttribute('aria-pressed','true');q('[data-mic]').textContent='■ Terminar';setPhase('listening');notice('Dictando. Revisa la transcripción y pulsa Enviar cuando esté lista.');};
    active.onresult=event=>{if(recognition!==active)return;let interim='';for(let i=event.resultIndex;i<event.results.length;i++){if(event.results[i].isFinal)finalText+=event.results[i][0].transcript+' ';else interim+=event.results[i][0].transcript;}question.value=[draft,finalText+interim].filter(Boolean).join(' ').slice(0,1500);updateCount();};
    active.onerror=event=>{if(recognition!==active)return;const errors={'not-allowed':'Permiso de micrófono denegado. Puedes escribir o permitirlo desde tu navegador.','audio-capture':'No se encontró un micrófono disponible.','network':'El servicio de dictado no tiene conexión.','no-speech':'No se detectó voz. Intenta de nuevo.'};notice(errors[event.error]||'El dictado se interrumpió. Puedes volver a intentarlo.');};
    active.onend=()=>{if(recognition!==active)return;recognition=null;listening=false;q('[data-mic]').setAttribute('aria-pressed','false');q('[data-mic]').textContent='🎙 Dictar';if(phase==='listening')setPhase('idle');question.focus();};
    try{active.start();}catch{stopListening();notice('No se pudo iniciar el micrófono. Revisa los permisos del navegador.');}
  });
  window.addEventListener('math-assistant-context',event=>{
    const detail=event.detail;if(!detail?.payload)return;
    version++;requestController?.abort();stopListening();stopSpeech();setBusy(false);
    context={operation:detail.payload.operation,expression:detail.payload.expression,params:detail.payload.params||{}};contextTitle=String(detail.title||'Cálculo seleccionado').slice(0,120);
    persist();updateContext();renderLog();show();question.value='Explícame este resultado y cómo interpretar sus pasos.';updateCount();notice('Ejercicio adjuntado. Puedes editar la pregunta antes de enviarla.');
  });
  launcher?.addEventListener('click',()=>root.hidden?show():close());q('[data-close]')?.addEventListener('click',close);
  root.addEventListener('keydown',event=>{if(event.key==='Escape'&&!full){event.preventDefault();close();}});
  window.addEventListener('pagehide',()=>{requestController?.abort();stopListening();stopSpeech();clearInterval(spriteTimer);});
  document.addEventListener('visibilitychange',()=>{if(document.hidden){stopListening();stopSpeech();clearInterval(spriteTimer);}else animateSprite();});
  reduceMotion.addEventListener?.('change',animateSprite);
  synth?.addEventListener('voiceschanged',paintVoices);
  applySettings();paintVoices();renderLog();updateContext();updateCount();setPhase('idle');
  if(!Recognition){q('[data-mic]').disabled=true;q('[data-mic]').title='Dictado no disponible en este navegador';notice('Dictado no disponible aquí. Puedes escribir y escuchar respuestas.');}
  q('[data-stop-speech]').disabled=false;
})();
