(() => {
  const form=document.querySelector('#exam-form'),clock=document.querySelector('#exam-clock'),status=document.querySelector('#save-status');
  if(!form||!clock)return;
  const end=Date.now()+Number(clock.dataset.remaining)*1000;let saving=null,dirty=false,version=0,submitting=false,retryAfter=0;
  function save(){
    if(saving||submitting||!dirty||Date.now()<retryAfter||Date.now()>=end)return;
    const sentVersion=version,data=new FormData(form);data.set('action','save');
    status.textContent='Guardando…';
    saving=fetch(location.href,{method:'POST',body:data,headers:{'X-Autosave':'1'}})
      .then(async response=>{const result=await response.json();if(!response.ok||!result.saved)throw Error();if(version===sentVersion)dirty=false;status.textContent='Respuestas guardadas en el servidor.';})
      .catch(()=>{retryAfter=Date.now()+10000;status.textContent='No se pudo guardar. Revisa la conexión y pulsa Guardar respuestas.';})
      .finally(()=>{saving=null;});
  }
  let debounce;
  form.addEventListener('input',()=>{dirty=true;version++;clearTimeout(debounce);debounce=setTimeout(save,600);});
  form.addEventListener('change',()=>{dirty=true;version++;save();});
  form.addEventListener('submit',async event=>{
    event.preventDefault();if(submitting)return;submitting=true;
    if(saving)await saving;
    const button=event.submitter;const hidden=document.createElement('input');hidden.type='hidden';hidden.name='action';hidden.value=button?.value||'save';form.append(hidden);
    HTMLFormElement.prototype.submit.call(form);
  });
  const timer=setInterval(()=>{const left=Math.max(0,Math.ceil((end-Date.now())/1000));clock.textContent=`${Math.floor(left/60)}:${String(left%60).padStart(2,'0')}`;if(!left){clearInterval(timer);status.textContent='Tiempo terminado. Se conservará la última respuesta guardada.';submitting=true;location.reload();}else save();},1000);
  window.addEventListener('beforeunload',event=>{if(dirty&&!submitting){event.preventDefault();event.returnValue='';}});
})();
