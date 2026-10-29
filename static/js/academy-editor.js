/* Reutiliza MathLive y la barra matemática de las calculadoras. */
(() => {
  if (!window.customElements) return;
  customElements.whenDefined('math-field').then(() => {
    document.querySelectorAll('.academy-math-editor').forEach((wrapper, index) => {
      const input=wrapper.querySelector('[data-answer-input]');
      const field=document.createElement('math-field');
      field.className='math-input';field.id=`academy-math-${index}`;
      field.setAttribute('aria-label',wrapper.querySelector('label').textContent);
      field.mathVirtualKeyboardPolicy='manual';field.value=input.value;
      wrapper.querySelector('[data-math-host]').append(field);
      input.type='hidden';wrapper.querySelector('label').htmlFor=field.id;
      wrapper.querySelector('[data-answer-toolbar]').hidden=false;
      field.addEventListener('input',()=>{
        input.value=field.getValue('latex');
        input.dispatchEvent(new Event('input',{bubbles:true}));
      });
      wrapper.querySelectorAll('[data-insert]').forEach(button=>button.addEventListener('click',()=>{
        field.focus();field.executeCommand(['insert',button.dataset.insert]);
      }));
      wrapper.querySelector('[data-keyboard]').addEventListener('click',()=>{
        field.focus();window.mathVirtualKeyboard?.show();
      });
      input.form?.addEventListener('submit',()=>{input.value=field.getValue('latex');});
    });
  });
})();
