/* Texto externo se presenta con textContent. Las peticiones tienen estados independientes. */
const $ = (selector, root = document) => root.querySelector(selector);
const $$ = (selector, root = document) => [...root.querySelectorAll(selector)];

function latexToSympy(value) {
  const text = String(value || '').replace(/\\sin\^\{-1\}/g, '\\arcsin').replace(/\\cos\^\{-1\}/g, '\\arccos').replace(/\\tan\^\{-1\}/g, '\\arctan').replace(/\\left|\\right/g, '').replace(/\\(?:,|;|!|quad|qquad)|\u200b/g, '');
  let pos = 0;
  function group() {
    while (/\s/.test(text[pos] || '') && pos < text.length) pos++;
    if (text[pos] !== '{') throw new Error('Falta agrupar un argumento de la fórmula.');
    pos++;
    return read(true);
  }
  function read(nested = false) {
    let out = '';
    while (pos < text.length) {
      const ch = text[pos++];
      if (ch === '}') {
        if (!nested) throw new Error('Hay una llave sin apertura.');
        return out;
      }
      if (ch === '{') { out += '(' + read(true) + ')'; continue; }
      if (ch !== '\\') { out += ch; continue; }
      const match = /^[A-Za-z]+/.exec(text.slice(pos));
      if (!match) throw new Error('Notación no admitida. Usa los ejemplos de la calculadora.');
      const cmd = match[0]; pos += cmd.length;
      if (cmd === 'frac' || cmd === 'dfrac' || cmd === 'tfrac') {
        const top = group(), bottom = group();
        out += '((' + top + ')/(' + bottom + '))';
      } else if (cmd === 'sqrt') out += 'sqrt(' + group() + ')';
      else if (cmd === 'cdot' || cmd === 'times') out += '*';
      else if (cmd === 'div') out += '/';
      else if (cmd === 'mathrm' || cmd === 'operatorname') {
        const name = group();
        if (!/^(e|E|sin|cos|tan|asin|acos|atan|exp|log|abs)$/.test(name)) throw new Error('Función no admitida.');
        out += name;
      } else {
        const names = {pi:'pi',theta:'theta',rho:'rho',phi:'phi',sin:'sin',cos:'cos',tan:'tan',arcsin:'asin',arccos:'acos',arctan:'atan',ln:'log',log:'log',exp:'exp'};
        if (!names[cmd]) throw new Error('Notación no admitida: ' + cmd + '.');
        out += names[cmd];
      }
    }
    if (nested) throw new Error('Hay una llave sin cierre.');
    return out;
  }
  const result = read();
  if (/(sin|cos|tan)\s*\^/.test(result)) throw new Error('Escribe la potencia después del argumento: sin(x)^2; para la inversa usa asin(x).');
  return result.trim();
}

function expressionFor(card) {
  const field = $('[data-math-input]', card);
  return latexToSympy(field?.getValue ? field.getValue('latex') : field?.textContent);
}
function paramsFor(card) {
  return Object.fromEntries($$('[data-param]', card).map(input => [input.dataset.param, input.value]));
}
function append(parent, tag, text, className = '') {
  const element = document.createElement(tag);
  if (text != null) element.textContent = String(text);
  element.className = className; parent.append(element); return element;
}
function maths(latex) { return `\\(${latex}\\)`; }
function typeset(target) { window.MathJax?.typesetPromise?.([target])?.catch(() => {}); }
function notify(message, type = 'danger') {
  const toast = append($('#toast-region'), 'div', message, `toast align-items-center text-bg-${type} border-0 p-3`);
  if (window.bootstrap) new bootstrap.Toast(toast, {delay: 5000}).show();
  else toast.classList.add('show');
  toast.addEventListener('hidden.bs.toast', () => toast.remove());
}

const states = new WeakMap();
function stateFor(card) {
  if (!states.has(card)) states.set(card, {version: 0, controllers: new Set(), payload: null});
  return states.get(card);
}
function resetCard(card) {
  const state = stateFor(card); state.version++; state.payload = null;
  state.controllers.forEach(controller => controller.abort()); state.controllers.clear();
  $('[data-result]', card).classList.add('d-none');
  const plot = $('[data-plot]', card);
  if (window.Plotly) Plotly.purge(plot);
  plot.replaceChildren(); plot.classList.add('d-none');
  const button = $('[data-calculate]', card); button.disabled = false; button.textContent = '🧮 Calcular';
}
async function postJSON(url, payload, state, timeout = 18000) {
  const controller = new AbortController(); state?.controllers.add(controller);
  const timer = setTimeout(() => controller.abort(), timeout);
  try {
    const response = await fetch(url, {method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify(payload), signal: controller.signal});
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || 'No se pudo completar la operación.');
    return data;
  } catch (error) {
    if (error.name === 'AbortError') throw new Error('La solicitud se canceló o tardó demasiado.');
    throw error;
  } finally { clearTimeout(timer); state?.controllers.delete(controller); }
}

function renderResult(card, data, payload, version) {
  const result = $('[data-result]', card); result.replaceChildren();
  const value = append(result, 'div', null, 'result-value');
  append(value, 'b', 'RESULTADO EXACTO'); append(value, 'div', maths(data.result_latex), 'math mt-2');
  append(value, 'span', 'Aproximación: ' + data.result_decimal, 'decimal');
  for (const warning of data.warnings || []) append(result, 'p', warning, 'alert alert-warning mt-2');
  const steps = append(result, 'div', null, 'steps');
  for (const item of data.steps) {
    const article = append(steps, 'article', null, 'step');
    append(article, 'h4', item.title); append(article, 'div', maths(item.latex), 'math');
    if (item.note) append(article, 'p', item.note, 'step-note');
  }
  const grid = append(result, 'div', null, 'explain-grid');
  for (const [label, text] of [['Interpretación matemática', data.interpretation], ['Aplicación en ingeniería', data.engineering]]) {
    const section = append(grid, 'div'); append(section, 'b', label); append(section, 'p', text);
  }
  const ai = append(result, 'div', null, 'ia-container mt-3');
  const button = append(ai, 'button', 'Explicar con IA (opcional)', 'btn btn-outline-secondary'); button.type = 'button';
  const explanation = append(ai, 'div', '', 'texto-ia mt-2'); explanation.style.whiteSpace = 'pre-wrap'; explanation.setAttribute('aria-live', 'polite');
  button.addEventListener('click', async () => {
    button.disabled = true; explanation.textContent = 'Preparando una explicación adicional…';
    try {
      const data = await postJSON('/api/explain', payload, stateFor(card), 26000);
      if (stateFor(card).version !== version) return;
      explanation.textContent = 'Explicación orientativa de IA; sus pasos adicionales no están certificados.\n\n' + data.ai_explanation;
      typeset(explanation);
    } catch (error) { if (stateFor(card).version === version) explanation.textContent = error.message; }
    finally { button.disabled = false; }
  });
  const ask = append(result, 'button', 'Preguntar al asistente sobre este cálculo', 'btn btn-outline-primary mt-3');
  ask.type = 'button';
  ask.addEventListener('click', () => window.dispatchEvent(new CustomEvent('math-assistant-context', {detail: {payload, title: data.title}})));
  result.classList.remove('d-none'); typeset(result); addHistory(data.title, data.result_latex);
}
async function renderPlot(card, plot) {
  const target = $("[data-plot]", card);
  if (!target) return;
  if (plot.kind === "message") { target.textContent = plot.title; target.classList.remove("d-none"); return; }
  if (!window.Plotly) { target.textContent = "La biblioteca de gráficas no está disponible. El resultado matemático se conserva."; target.classList.remove("d-none"); return; }
  target.replaceChildren();
  target.classList.remove("d-none");
  let traces = [], layout = { title: { text: plot.title || "Visualización", font: { size: 15 } }, margin: { l: 42, r: 18, t: 45, b: 35 }, paper_bgcolor: "#fff", plot_bgcolor: "#fff", font: { family: "Manrope", color: "#173052" } };
  if (plot.kind === "surface" || plot.kind === "tangent") {
    traces = [{ type: "surface", x: plot.x, y: plot.y, z: plot.z, colorscale: "Viridis", opacity: .92, showscale: false, name: "f(x,y)" }];
    if (plot.kind === "tangent") { traces.push({ type: "surface", x: plot.x, y: plot.y, z: plot.plane, colorscale: [[0, "#ffb55c"], [1, "#ffb55c"]], opacity: .58, showscale: false, name: "Plano tangente" }, { type: "scatter3d", mode: "markers", x: [plot.point[0]], y: [plot.point[1]], z: [plot.point[2]], marker: { size: 5, color: "#ff496c" }, name: "Punto" }); }
    layout.scene = { xaxis: { title: "x" }, yaxis: { title: "y" }, zaxis: { title: "z" }, camera: { eye: { x: 1.5, y: 1.5, z: 1.2 } } };
  } else if (plot.kind === "vector") {
    const lines = []; for (let i = 0; i < plot.x.length; i += 1) { lines.push({ x: [plot.x[i], plot.x[i] + plot.u[i], null], y: [plot.y[i], plot.y[i] + plot.v[i], null] }); }
    traces = [{ type: "scatter", mode: "lines", x: lines.flatMap(v => v.x), y: lines.flatMap(v => v.y), line: { color: "#4385f5", width: 1.5 }, hoverinfo: "skip" }]; layout.xaxis = { scaleanchor: "y", range: [-4.5, 4.5] }; layout.yaxis = { range: [-4.5, 4.5] };
  } else if (plot.kind === "curve3d") { traces = [{ type: "scatter3d", mode: "lines", x: plot.x, y: plot.y, z: plot.z, line: { color: "#44d8c5", width: 6 } }]; layout.scene = { xaxis: { title: "x" }, yaxis: { title: "y" }, zaxis: { title: "z" } }; }
  await Plotly.newPlot(target, traces, layout, { responsive: true, displaylogo: false });
}

async function loadPlot(card, payload, version) {
  const target = $('[data-plot]', card);
  target.textContent = 'Preparando la gráfica…'; target.classList.remove('d-none');
  try {
    const plot = await postJSON('/api/plot', payload, stateFor(card));
    if (stateFor(card).version !== version) return;
    await renderPlot(card, plot);
  } catch (error) { if (stateFor(card).version === version) target.textContent = 'Gráfica: ' + error.message; }
}
async function calculate(card) {
  resetCard(card);
  const state = stateFor(card), version = state.version, button = $('[data-calculate]', card);
  button.disabled = true; button.textContent = 'Calculando…';
  try {
    const payload = {operation: card.dataset.operation, expression: expressionFor(card), params: paramsFor(card)};
    const data = await postJSON('/api/calculate', payload, state);
    if (state.version !== version) return;
    state.payload = payload;
    renderResult(card, data, payload, version);
    if ($('[data-plot-surface]', card)) loadPlot(card, payload, version);
  } catch (error) { if (state.version === version) notify(error.message); }
  finally { if (state.version === version) {button.disabled = false; button.textContent = '🧮 Calcular';} }
}
async function surfaceOnly(card) {
  const state = stateFor(card);
  try {
    const payload = {operation: card.dataset.operation, expression: expressionFor(card), params: paramsFor(card)};
    await loadPlot(card, payload, state.version);
  } catch (error) { notify(error.message); }
}
function historyItems() {
  try { const list = JSON.parse(sessionStorage.getItem('math-history') || '[]'); return Array.isArray(list) ? list.slice(0,10) : []; }
  catch { return []; }
}
function addHistory(title, result) {
  try {sessionStorage.setItem('math-history', JSON.stringify([{title,result}, ...historyItems()].slice(0,10)));} catch {}
  paintHistory();
}
function paintHistory() {
  const target = $('[data-history]'); if (!target) return;
  target.replaceChildren(); const list = historyItems();
  if (!list.length) append(target,'p','Aún no has realizado cálculos en esta sesión.','text-secondary');
  for (const item of list) { const row = append(target,'div',null,'history-entry'); append(row,'b',item.title); append(row,'span',maths(item.result)); }
  typeset(target);
}
async function checkExercise(card) {
  const input = $('input', card), feedback = $('.exercise-feedback', card);
  const button = $('[data-check-exercise]',card); button.disabled = true;
  try {
    const data = await postJSON(`/api/exercise/${card.dataset.exercise}`, {answer: input.value});
    feedback.className = `exercise-feedback mt-3 ${data.correct ? 'success' : 'failure'}`;
    feedback.textContent = data.correct ? '✓ La respuesta es equivalente. Comprueba también tu procedimiento.' : `Aún no. Pista: ${data.hint}`;
  } catch (error) { feedback.textContent = error.message; }
  finally {button.disabled = false;}
}
document.addEventListener('DOMContentLoaded', () => {
  $$('[data-calculator]').forEach(card => {
    $('[data-calculate]', card)?.addEventListener('click', () => calculate(card));
    $('[data-plot-surface]', card)?.addEventListener('click', () => surfaceOnly(card));
    $('[data-toggle-results]', card)?.addEventListener('click', () => {if (stateFor(card).payload) $('[data-result]', card).classList.toggle('d-none');});
    $('[data-reset]', card)?.addEventListener('click', () => resetCard(card));
    card.addEventListener('input', event => {if (event.target.matches('[data-math-input], [data-param]')) resetCard(card);});
    $$('[data-insert]', card).forEach(button => button.addEventListener('click', () => {
      const field = $('[data-math-input]', card);
      if (field?.executeCommand) {field.focus(); field.executeCommand(['insert', button.dataset.insert]);}
      else {field.textContent += button.dataset.insert; resetCard(card);}
    }));
  });
  $$('[data-check-exercise]').forEach(button => button.addEventListener('click', () => checkExercise(button.closest('[data-exercise]'))));
  $('[data-clear-history]')?.addEventListener('click', () => {sessionStorage.removeItem('math-history'); paintHistory();});
  const bibliography = $('.bibliography');
  if (bibliography) {
    try { bibliography.value = localStorage.getItem('math-bibliography') || ''; } catch {}
    $('[data-save-bibliography]')?.addEventListener('click', () => {
      try {localStorage.setItem('math-bibliography', bibliography.value); notify('Bibliografía guardada en este navegador.', 'success');}
      catch {notify('No se pudo guardar en este navegador.');}
    });
  }
  paintHistory();
  if ($("#hero-surface") && window.Plotly) { const axis = [-4, -3, -2, -1, 0, 1, 2, 3, 4]; const z = axis.map(y => axis.map(x => Math.sin(x) * Math.cos(y) + (x * x - y * y) / 12)); Plotly.newPlot("hero-surface", [{ type: "surface", x: axis, y: axis, z, colorscale: [[0, "#142f58"], [.5, "#4385f5"], [1, "#44d8c5"]], showscale: false }], { margin: { l: 0, r: 0, t: 0, b: 0 }, paper_bgcolor: "rgba(0,0,0,0)", scene: { bgcolor: "rgba(0,0,0,0)", xaxis: { visible: false }, yaxis: { visible: false }, zaxis: { visible: false }, camera: { eye: { x: 1.55, y: 1.45, z: 1.1 } } } }, { responsive: true, displayModeBar: false }); }
});
