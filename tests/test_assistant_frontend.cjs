const assert=require('node:assert/strict'),vm=require('node:vm'),fs=require('node:fs');
const source=fs.readFileSync('static/js/assistant.js','utf8');
class El{constructor(){this.handlers={};this.children=[];this.dataset={};this.style={setProperty(){}};this.classList={contains:()=>false};this.value='';this.hidden=false;}addEventListener(n,f){this.handlers[n]=f;}append(e){e.parent=this;this.children.push(e);}replaceChildren(){this.children=[];}remove(){this.parent.children=this.parent.children.filter(e=>e!==this);}setAttribute(){}focus(){}querySelector(){return new El();}fire(n,e={}){return this.handlers[n]?.({preventDefault(){},...e});}}
function setup(denied=false){
 const nodes={},get=s=>nodes[s]??=new El(),root=get('root');root.hidden=true;root.querySelector=get;root.querySelectorAll=()=>[];get('[data-mode-select]').value='mentor';
 const stores={'m2-assistant-settings-v1':JSON.stringify({revision:5,voiceEngine:'browser',autoSpeak:false})},storage={getItem:k=>stores[k]||null,setItem:(k,v)=>stores[k]=v};let complete,calls=0,recognition;const spoken=[];
 class Recognition{constructor(){recognition=this;}start(){this.onstart?.();}abort(){this.onend?.();}}
 const win={handlers:{},isSecureContext:true,matchMedia:()=>({matches:false,addEventListener(){}}),addEventListener(n,f){this.handlers[n]=f;}};
 if(!denied){win.SpeechRecognition=Recognition;win.SpeechSynthesisUtterance=class{constructor(t){this.text=t;}};win.speechSynthesis={cancel(){},getVoices:()=>[{voiceURI:'es',lang:'es-ES',name:'Español'}],addEventListener(){},speak:u=>{spoken.push(u);u.onstart?.();}};}
 for(const key of ['localStorage','sessionStorage'])Object.defineProperty(win,key,{get(){if(denied)throw Error('denied');return storage;}});
 const doc={hidden:false,querySelector:s=>s==='[data-assistant]'?root:get('launcher'),createElement:()=>new El(),addEventListener(){}};
 vm.runInNewContext(source,{window:win,document:doc,SpeechSynthesisUtterance:win.SpeechSynthesisUtterance,Image:class{},TextEncoder,AbortController,setInterval:()=>1,clearInterval(){},setTimeout:()=>1,clearTimeout(){},fetch:async()=>{calls++;return new Promise(r=>complete=r);}});
 return {get,root,win,stores,spoken,send:()=>get('[data-chat-form]').fire('submit'),reply:(data,ok=true)=>complete({ok,json:async()=>data}),calls:()=>calls,recognition:()=>recognition};
}
(async()=>{
 let t=setup(true);assert.equal(t.get('[data-mic]').disabled,true);assert.equal(t.root.dataset.state,'idle');
 t=setup();assert.equal(t.calls(),0);await t.get('launcher').fire('click');assert.equal(t.root.hidden,false);
 t.get('[data-question]').value='¿Qué es el gradiente?';let pending=t.send();assert.equal(t.root.dataset.state,'thinking');assert.equal(t.get('[data-send]').disabled,true);
 t.reply({reply:'<img src=x onerror=alert(1)>',calculation_used:false});await pending;assert.equal(t.root.dataset.state,'idle');assert.equal(t.get('[data-question]').value,'');assert.equal(JSON.parse(t.stores['m2-assistant-conversation-v1']).messages.length,2);
 const answer=t.get('[data-log]').children.at(-1);assert.equal(answer.children[1].textContent,'<img src=x onerror=alert(1)>');assert.equal(answer.children[1].children.length,0);
 await answer.children[2].fire('click');assert.equal(t.root.dataset.state,'speaking');assert.equal(t.spoken.length,1);await t.get('[data-stop-speech]').fire('click');assert.equal(t.root.dataset.state,'idle');
 t.get('[data-question]').value='Conservar pregunta';pending=t.send();t.reply({error:'Sin cuota'},false);await pending;assert.equal(t.get('[data-question]').value,'Conservar pregunta');assert.equal(t.get('[data-status]').textContent,'Sin cuota');
 pending=t.send();await t.get('[data-clear]').fire('click');t.reply({reply:'Respuesta vieja'});await pending;assert.equal(JSON.parse(t.stores['m2-assistant-conversation-v1']).messages.length,0);
 t.win.handlers['math-assistant-context']({detail:{payload:{operation:'gradient',expression:'x**2',params:{}},title:'Gradiente'}});assert.equal(t.get('[data-context]').hidden,false);
 t.get('[data-question]').value='';await t.get('[data-mic]').fire('click');assert.equal(t.root.dataset.state,'listening');
 t.recognition().onresult({resultIndex:0,results:[Object.assign([{transcript:'Explica el gradiente'}],{isFinal:true})]});assert.equal(t.get('[data-question]').value.trim(),'Explica el gradiente');assert.equal(t.calls(),3);
 await t.get('[data-mic]').fire('click');assert.equal(t.root.dataset.state,'idle');
 console.log('Chat OK: almacenamiento bloqueado, envío, errores, DOM seguro, voz, dictado sin autoenvío, contexto y descarte de respuestas antiguas.');
})().catch(e=>{console.error(e);process.exitCode=1;});
