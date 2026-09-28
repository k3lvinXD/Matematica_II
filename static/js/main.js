/* Interfaz de Matemática II Interactiva: sin eval del lado cliente. */
const $ = (selector, root = document) => root.querySelector(selector);
const $$ = (selector, root = document) => [...root.querySelectorAll(selector)];

function latexToSympy(value) {
  let text = value || "";
  text = text.replace(/\\left|\\right/g, "").replace(/\\cdot|\\times/g, "*");
  text = text.replace(/\\pi/g, "pi").replace(/\\theta/g, "theta").replace(/\\rho/g, "rho").replace(/\\phi/g, "phi");
  text = text.replace(/\\sin|\\cos|\\tan|\\sqrt|\\log|\\exp/g, m => m.slice(1));
  // MathLive gives standard LaTeX. Repeated replacement covers simple nested fractions.
  for (let i = 0; i < 4; i += 1) text = text.replace(/\\frac\{([^{}]+)\}\{([^{}]+)\}/g, "($1)/($2)");
  text = text.replace(/\\sqrt\{([^{}]+)\}/g, "sqrt($1)");
  text = text.replace(/\^\{([^{}]+)\}/g, "^($1)").replace(/[{}]/g, "");
  return text.replace(/\\,/g, "").trim();
}

function expressionFor(card) {
  const field = $("[data-math-input]", card);
  return latexToSympy(field?.getValue ? field.getValue("latex") : field?.textContent);
}

function paramsFor(card) {
  return Object.fromEntries($$("[data-param]", card).map(input => [input.dataset.param, input.value]));
}

function notify(message, type = "danger") {
  const toast = document.createElement("div");
  toast.className = `toast align-items-center text-bg-${type} border-0`;
  toast.innerHTML = `<div class="d-flex"><div class="toast-body">${message}</div><button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast"></button></div>`;
  $("#toast-region").append(toast); new bootstrap.Toast(toast, { delay: 4200 }).show();
}

function maths(latex) { return `\\(${latex}\\)`; }

function renderResult(card, data) {
  const result = $("[data-result]", card);
  const steps = data.steps.map(item => `<article class="step"><h4>${item.title}</h4><div class="math">${maths(item.latex)}</div>${item.note ? `<p class="step-note">${item.note}</p>` : ""}</article>`).join("");

  // --- NUEVO: Construimos el bloque de la IA si existe la explicación ---
  // Además, usamos un pequeño truco con .replace para convertir los asteriscos de Markdown a negritas HTML
  const bloqueIA = data.ai_explanation
    ? `<div class="ia-container">
           <h3>🤖 Explicación de la IA</h3>
           <div class="texto-ia">${data.ai_explanation.replace(/\*\*(.*?)\*\*/g, '<b>$1</b>')}</div>
         </div>`
    : "";

  // --- MODIFICADO: Inyectamos ${bloqueIA} en el HTML final ---
  result.innerHTML = `
      <div class="result-value">
          <b>RESULTADO</b>
          <div class="math mt-2">${maths(data.result_latex)}</div>
          <span class="decimal">≈ ${data.result_decimal}</span>
      </div>
      ${bloqueIA}
      <div class="steps">${steps}</div>
      <div class="explain-grid">
          <div><b>Interpretación matemática</b>${data.interpretation}</div>
          <div><b>Aplicación en ingeniería</b>${data.engineering}</div>
      </div>
  `;
  result.classList.remove("d-none");
  window.MathJax?.typesetPromise?.([result]);
  addHistory(data.title, data.result_latex);
  if (data.plot) renderPlot(card, data.plot);
}

function renderPlot(card, plot) {
  const target = $("[data-plot]", card);
  if (!target || !window.Plotly || plot.kind === "message") return;
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
  Plotly.newPlot(target, traces, layout, { responsive: true, displaylogo: false });
}

async function calculate(card) {
  const button = $("[data-calculate]", card); const prior = button.innerHTML; button.disabled = true; button.textContent = "Calculando…";
  try {
    const res = await fetch("/api/calculate", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ operation: card.dataset.operation, expression: expressionFor(card), params: paramsFor(card) }) });
    const data = await res.json(); if (!res.ok) throw new Error(data.error || "No se pudo realizar el cálculo."); renderResult(card, data);
  } catch (error) { notify(error.message); } finally { button.disabled = false; button.innerHTML = prior; }
}

async function surfaceOnly(card) {
  try { const res = await fetch("/api/plot/surface", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ expression: expressionFor(card) }) }); const data = await res.json(); if (!res.ok) throw new Error(data.error); renderPlot(card, data); } catch (error) { notify(error.message); }
}

function addHistory(title, result) { const list = JSON.parse(sessionStorage.getItem("math-history") || "[]"); list.unshift({ title, result }); sessionStorage.setItem("math-history", JSON.stringify(list.slice(0, 10))); paintHistory(); }
function paintHistory() { const target = $("[data-history]"); if (!target) return; const list = JSON.parse(sessionStorage.getItem("math-history") || "[]"); target.innerHTML = list.length ? list.map(i => `<div class="history-entry"><b>${i.title}</b><span>${maths(i.result)}</span></div>`).join("") : '<p class="text-secondary">Aún no has realizado cálculos en esta sesión.</p>'; window.MathJax?.typesetPromise?.([target]); }

async function checkExercise(card) { const input = $("input", card); const feedback = $(".exercise-feedback", card); try { const res = await fetch(`/api/exercise/${card.dataset.exercise}`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ answer: input.value }) }); const data = await res.json(); if (!res.ok) throw new Error(data.error); feedback.className = `exercise-feedback mt-3 ${data.correct ? "success" : "failure"}`; feedback.textContent = data.correct ? "✓ Correcto. Excelente razonamiento." : `Aún no. Pista: ${data.hint} Solución esperada: ${data.solution}`; } catch (e) { feedback.className = "exercise-feedback mt-3 failure"; feedback.textContent = e.message; } }

document.addEventListener("DOMContentLoaded", () => {
  $$('[data-calculator]').forEach(card => {
    $("[data-calculate]", card)?.addEventListener("click", () => calculate(card));
    $("[data-plot-surface]", card)?.addEventListener("click", () => surfaceOnly(card));
    $("[data-toggle-results]", card)?.addEventListener("click", () => $("[data-result]", card)?.classList.toggle("d-none"));
    $("[data-reset]", card)?.addEventListener("click", () => { $("[data-result]", card).classList.add("d-none"); $("[data-plot]", card).classList.add("d-none"); });
    $$('[data-insert]', card).forEach(button => button.addEventListener("click", () => { const field = $("[data-math-input]", card); if (field?.executeCommand) { field.focus(); field.executeCommand(["insert", button.dataset.insert]); } else field.textContent += button.dataset.insert; }));
  });
  $$('[data-check-exercise]').forEach(button => button.addEventListener("click", () => checkExercise(button.closest("[data-exercise]"))));
  $('[data-clear-history]')?.addEventListener("click", () => { sessionStorage.removeItem("math-history"); paintHistory(); });
  const bibliography = $(".bibliography"); if (bibliography) { bibliography.value = localStorage.getItem("math-bibliography") || ""; $('[data-save-bibliography]')?.addEventListener("click", () => { localStorage.setItem("math-bibliography", bibliography.value); notify("Bibliografía guardada en este navegador.", "success"); }); }
  paintHistory();
  if ($("#hero-surface") && window.Plotly) { const axis = [-4, -3, -2, -1, 0, 1, 2, 3, 4]; const z = axis.map(y => axis.map(x => Math.sin(x) * Math.cos(y) + (x * x - y * y) / 12)); Plotly.newPlot("hero-surface", [{ type: "surface", x: axis, y: axis, z, colorscale: [[0, "#142f58"], [.5, "#4385f5"], [1, "#44d8c5"]], showscale: false }], { margin: { l: 0, r: 0, t: 0, b: 0 }, paper_bgcolor: "rgba(0,0,0,0)", scene: { bgcolor: "rgba(0,0,0,0)", xaxis: { visible: false }, yaxis: { visible: false }, zaxis: { visible: false }, camera: { eye: { x: 1.55, y: 1.45, z: 1.1 } } } }, { responsive: true, displayModeBar: false }); }
});
