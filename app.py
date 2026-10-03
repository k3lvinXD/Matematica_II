"""Punto de entrada de Matemática II Interactiva."""
from __future__ import annotations

from flask import Flask, jsonify, render_template, request

from dotenv import load_dotenv

import os 
import google.generativeai as genai
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


# Cargar variables e inicializar Gemini
load_dotenv()
gemini_key = os.getenv("GEMINI_API_KEY")
genai.configure(api_key=gemini_key)

# Configurar el modelo (gemini-1.5-pro es ideal para razonamiento matemático)
modelo_gemini = genai.GenerativeModel('gemini-3.8-flash')

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

           # 2. Prompt calibrado: Desarrollo algebraico anclado a resultados exactos
            prompt = f"""
            Eres un tutor de Cálculo Universitario desarrollando el procedimiento para: {tema}
            
            RESULTADOS EXACTOS DEL MOTOR (DEBES LLEGAR A ESTOS):
            {contexto_sympy}

            TAREA:
            Escribe la explicación paso a paso mostrando el desarrollo algebraico intermedio detallado para llegar a cada uno de esos resultados.
            
            REGLAS ESTRICTAS E INQUEBRANTABLES:
            1. Muestra la aplicación de reglas matemáticas (cadena, producto, sumas) término por término ANTES de dar la respuesta final del paso.
            2. Tu desarrollo intermedio DEBE desembocar EXACTAMENTE en los resultados provistos por el motor. No inventes variables adicionales.
            3. Si derivas parcialmente respecto a una variable, trata a las demás estrictamente como constantes fijas desde el primer momento.
            4. NUNCA uses el símbolo de dólar ($). Usa \\( ... \\) para fórmulas en la misma línea y \\[ ... \\] para fórmulas centradas.
            5. INICIA DIRECTAMENTE CON EL PASO 1. Cero saludos, cero introducciones, no digas "Por supuesto" ni "Aquí tienes".

            Estructura cada paso estrictamente así:
            **Paso 1 ([Nombre de la operación]):** [Breve explicación textual]
            \\[ [Desarrollo algebraico intermedio mostrando la regla aplicada] \\]
            \\[ [Resultado final de este paso que coincida con el motor] \\]
            """
            
            respuesta_chat = modelo_gemini.generate_content(
            prompt,
            generation_config=genai.types.GenerationConfig(
                temperature=0.0
            )
        )
            
            # Sanitizamos el texto antes de enviarlo al Frontend
            answer["ai_explanation"] = formatear_latex_ia(respuesta_chat.text)
            
        except Exception as e:
            print(f"Error en Gemini: {e}", flush=True)
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
