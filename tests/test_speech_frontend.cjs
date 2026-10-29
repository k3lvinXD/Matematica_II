const assert=require('node:assert/strict'),vm=require('node:vm'),fs=require('node:fs');
const source=fs.readFileSync('static/js/assistant.js','utf8').replace("  applySettings();paintVoices();renderLog();updateContext();updateCount();setPhase('idle');", "window.test={speechText,chunksFor,spanishVoice,getSettings:()=>settings};applySettings();paintVoices();renderLog();updateContext();updateCount();setPhase('idle');");
class El{constructor(){this.handlers={};this.children=[];this.dataset={};this.style={setProperty(){}};this.classList={contains:()=>false};this.value='';this.hidden=false;}addEventListener(n,f){this.handlers[n]=f;}append(e){e.parent=this;this.children.push(e);}replaceChildren(){this.children=[];}remove(){this.parent.children=this.parent.children.filter(e=>e!==this);}setAttribute(){}focus(){}querySelector(){return new El();}fire(n,e={}){return this.handlers[n]?.({preventDefault(){},...e});}}
function setup(denied=false){
 const nodes={},get=s=>nodes[s]??=new El(),root=get('root');root.hidden=true;root.querySelector=get;root.querySelectorAll=()=>[];get('[data-mode-select]').value='mentor';
 const stores={'m2-assistant-settings-v1':JSON.stringify({revision:2,avatar:'robot',autoSpeak:false,voiceEngine:'browser'})},storage={getItem:k=>stores[k]||null,setItem:(k,v)=>stores[k]=v};let complete,calls=0,recognition;const spoken=[],played=[],urls=[];
 class Recognition{constructor(){recognition=this;}start(){this.onstart?.();}abort(){this.onend?.();}}
 const win={handlers:{},isSecureContext:true,matchMedia:()=>({matches:false,addEventListener(){}}),addEventListener(n,f){this.handlers[n]=f;}};
 if(!denied){win.SpeechRecognition=Recognition;win.SpeechSynthesisUtterance=class{constructor(t){this.text=t;}};win.speechSynthesis={cancel(){},getVoices:()=>[{voiceURI:'en',lang:'en-US',name:'Natural English'},{voiceURI:'es',lang:'es-ES',name:'Español'},{voiceURI:'mx',lang:'es-MX',name:'Microsoft Natural Español'}],addEventListener(){},speak:u=>{spoken.push(u);u.onstart?.();}};}
 for(const key of ['localStorage','sessionStorage'])Object.defineProperty(win,key,{get(){if(denied)throw Error('denied');return storage;}});
 const doc={hidden:false,querySelector:s=>s==='[data-assistant]'?root:get('launcher'),createElement:()=>new El(),addEventListener(){}};
 vm.runInNewContext(source,{window:win,document:doc,SpeechSynthesisUtterance:win.SpeechSynthesisUtterance,Image:class{},Audio:class{constructor(src){this.src=src;}play(){played.push(this.src);queueMicrotask(()=>this.onended?.());return Promise.resolve();}pause(){}load(){}removeAttribute(){}},Blob,Uint8Array,atob,URL:{createObjectURL:()=>{urls.push('created');return 'blob:test';},revokeObjectURL:()=>urls.push('revoked')},TextEncoder,AbortController,setInterval:()=>1,clearInterval(){},setTimeout:()=>1,clearTimeout(){},fetch:async()=>{calls++;return new Promise(r=>complete=r);}});
 return {get,root,win,stores,spoken,played,urls,send:()=>get('[data-chat-form]').fire('submit'),reply:(data,ok=true)=>complete({ok,json:async()=>data}),calls:()=>calls,recognition:()=>recognition};
}


(async()=>{
 const t=setup(),api=t.win.test;
 assert.equal(api.getSettings().voiceEngine,'browser');assert.equal(api.getSettings().autoSpeak,true);assert.equal(api.getSettings().voice,'');
 assert.equal(api.spanishVoice().voiceURI,'mx');
 t.win.speechSynthesis.getVoices=()=>[{voiceURI:'en',lang:'en-US',name:'Natural English'},{voiceURI:'spain',lang:'es-ES',name:'Natural Spain'},{voiceURI:'mx',lang:'es-MX',name:'Español México'}];
 assert.equal(api.spanishVoice().voiceURI,'mx');
 api.getSettings().voice='en';assert.equal(api.spanishVoice().voiceURI,'mx');
 api.getSettings().voice='';
 await t.get('launcher').fire('click');t.get('[data-question]').value='Hola';const pending=t.send();
 assert.equal(t.spoken[0].lang,'es-MX');t.reply({reply:'La derivada es dos equis.'});await pending;
 assert.equal(t.calls(),1);assert.equal(t.spoken.at(-1).lang,'es-MX');assert.equal(t.spoken.at(-1).text,'La derivada es dos equis.');
 const before=t.spoken.length;t.win.speechSynthesis.getVoices=()=>[{voiceURI:'en',lang:'en-US',name:'English'}];
 await t.get('[data-test-voice]').fire('click');assert.equal(t.spoken.length,before);assert.equal(api.spanishVoice(),undefined);
 assert.match(api.speechText('x^20'),/elevado a 20/);assert.match(api.speechText('x² + π'),/al cuadrado más pi/);
 console.log('Voz latinoamericana OK: migra preferencias, prioriza México, excluye inglés y lee sin solicitudes a proveedores de audio.');
})().catch(e=>{console.error(e);process.exitCode=1;});
