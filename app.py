"""Punto de entrada de Matemática II Interactiva."""
from __future__ import annotations

from flask import Flask, jsonify, render_template, request

import os 
import cohere
import re

def formatear_latex_ia(texto: str) -> str:
    """Convierte los signos $ de la IA al formato seguro de MathJax."""
    if not texto:
        return ""
    texto = re.sub(r'\$\$(.*?)\$\$', r'\\[\1\\]', texto, flags=re.DOTALL)
    texto = re.sub(r'\$(.*?)\$', r'\\(\1\\)', texto)
    return texto

from modules import unidad1, unidad2, unidad3
from modules.common import MathInputError, make_surface, safe_expr


# Inicialización limpia de Cohere
cliente_cohere = cohere.Client(os.environ.get("COHERE_API_KEY"))

app = Flask(__name__)
app.config["JSON_SORT_KEYS"] = False


@app.get("/")
def index():
    return render_template("index.html")


@app.get("/unidad/<int:number>")
def unidad(number: int):
    if number not in (1, 2, 3):
        return render_template("index.html"), 404
    return render_template(f"unidad{number}.html", active=f"unidad{number}")


@app.get("/laboratorio")
def laboratorio():
    return render_template("laboratorio.html", active="laboratorio")


@app.get("/ejercicios")
def ejercicios():
    return render_template("ejercicios.html", active="ejercicios")


@app.get("/aplicaciones")
def aplicaciones():
    return render_template("aplicaciones.html", active="aplicaciones")


@app.get("/acerca")
def acerca():
    return render_template("acerca.html", active="acerca")


@app.post("/api/calculate")
def calculate():
    """Ejecuta una operación seleccionada usando solamente el motor seguro."""
    data = request.get_json(silent=True) or {}
    operation = str(data.get("operation", "")).strip().lower()
    expression = str(data.get("expression", "")).strip()
    params = data.get("params") or {}
    if not expression:
        return jsonify(error="Escribe una expresión matemática antes de calcular."), 400
    try:
        if operation in unidad1.OPERATIONS:
            answer = unidad1.solve(operation, expression, params)
        elif operation in unidad2.OPERATIONS:
            answer = unidad2.solve(operation, expression, params)
        elif operation in unidad3.OPERATIONS:
            answer = unidad3.solve(operation, expression, params)
        else:
            raise MathInputError("Selecciona una herramienta matemática válida.")
# --- BLOQUE IA: COHERE (MODO TRADUCTOR ESTRICTO) ---
        try:
            tema = answer.get('title', 'este cálculo')
            pasos = answer.get('steps', [])
            
            # 1. Extraemos TODOS los pasos que SymPy ya validó matemáticamente
            contexto_sympy = ""
            for i, p in enumerate(pasos):
                titulo = p.get('title', f'Paso {i+1}')
                formula = p.get('latex', '')
                contexto_sympy += f"- {titulo}: \\( {formula} \\)\n"

            # 2. Prompt restrictivo: La IA solo redacta texto, no calcula.
            prompt = f"""
            Eres un tutor de Cálculo Universitario. Tu única tarea es redactar una explicación en lenguaje natural que una los siguientes pasos matemáticos. 
            
            TEMA: {tema}
            PROCEDIMIENTO MATEMÁTICO EXACTO:
            {contexto_sympy}

            REGLAS ESTRICTAS E INQUEBRANTABLES:
            1. NO INVENTES NI CALCULES NADA. Usa EXCLUSIVAMENTE las ecuaciones del "PROCEDIMIENTO MATEMÁTICO EXACTO".
            2. Tu trabajo es explicar con palabras (ej. "Aplicamos la regla de la cadena", "Evaluamos la integral interna") qué ocurrió en cada paso listado arriba.
            3. Estructura tu respuesta enumerando los pasos: **Paso 1:** [Explicación textual] -> [Fórmula exacta].
            4. NUNCA uses el símbolo de dólar ($). Usa \\( ... \\) para las ecuaciones.
            """
            
            respuesta_chat = cliente_cohere.chat(
                model="command-r-08-2024",
                message=prompt,
                temperature=0.0 # Temperatura en 0 para máxima precisión y cero creatividad
            )
            
            # Sanitizamos el texto antes de enviarlo al Frontend
            answer["ai_explanation"] = formatear_latex_ia(respuesta_chat.text)
            
        except Exception as e:
            print(f"Error en Cohere: {e}", flush=True)
            answer["ai_explanation"] = "El resultado está listo, pero el texto explicativo no se pudo generar."
        # -----------------------------------------
        return jsonify(answer)
    except MathInputError as exc:
        return jsonify(error=str(exc)), 400
    except Exception:
        # Deliberadamente no se expone el traceback ni detalles internos al estudiante.
        return jsonify(error="No se pudo resolver esa entrada. Verifica la sintaxis, variables y límites."), 400


@app.post("/api/plot/surface")
def plot_surface():
    data = request.get_json(silent=True) or {}
    try:
        expression = safe_expr(str(data.get("expression", "")))
        return jsonify(make_surface(expression))
    except MathInputError as exc:
        return jsonify(error=str(exc)), 400
    except Exception:
        return jsonify(error="No fue posible generar la gráfica para esa función."), 400


EXERCISES = {
    "u1-basic": {"answer": "2*x+2*y", "hint": "Calcula primero las derivadas parciales."},
    "u2-basic": {"answer": "1", "hint": "Integra una variable a la vez en el cuadrado unidad."},
    "u3-basic": {"answer": "2", "hint": "La divergencia es P_x + Q_y."},
}


@app.post("/api/exercise/<exercise_id>")
def check_exercise(exercise_id: str):
    item = EXERCISES.get(exercise_id)
    if not item:
        return jsonify(error="Ejercicio no encontrado."), 404
    try:
        proposed = safe_expr(str((request.get_json(silent=True) or {}).get("answer", "")))
        expected = safe_expr(item["answer"])
        correct = bool((proposed - expected).simplify() == 0)
        return jsonify(correct=correct, solution=item["answer"], hint=item["hint"])
    except Exception:
        return jsonify(error="No se pudo interpretar tu respuesta."), 400


if __name__ == "__main__":
    app.run()
