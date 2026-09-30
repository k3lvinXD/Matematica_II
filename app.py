"""Punto de entrada de Matemática II Interactiva."""
from __future__ import annotations

from flask import Flask, jsonify, render_template, request

import os 
import cohere

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
# --- BLOQUE IA: COHERE (MODO SYMBOLAB) ---
        try:
            tema = answer.get('title', 'este cálculo')
            resultado_final = answer.get('result_latex', '')
            pasos = answer.get('steps', [])
            funcion_inicial = pasos[0].get('latex', '') if pasos else 'la función dada'
            
            prompt = f"""
            Eres un profesor de cálculo multivariable claro y conciso.
            Explica la resolución de: {tema}
            Función inicial: {funcion_inicial}
            Resultado final exacto: {resultado_final}

            REGLAS STRICTAS DE FORMATO Y MATEMÁTICA:
            1. Tratamiento directo de variables: Si derivas respecto a 'x', trata a 'y' como una constante directamente (ej: d/dx(y) = 0). NO escribas derivadas implícitas ni cadenas innecesarias como dy/dx.
            2. Formato LaTeX: Para ecuaciones inline dentro de texto usa EXCLUSIVAMENTE \\( ... \\). NUNCA uses el símbolo de dólar ($).
            3. Ecuaciones en bloque: Para fórmulas centradas usa \\[ ... \\]. Divide expresiones muy largas en pasos cortos para que quepan en pantalla.
            
            Estructura la respuesta así:
            **Paso 1:** [Explicación y desarrollo simple]
            **Paso 2:** [Siguiente desarrollo]
            """
            
            # Llamada al modelo Command R de Cohere
            respuesta_chat = cliente_cohere.chat(
                model="command-r-08-2024",
                message=prompt,
                temperature=0.1
            )
            
            answer["ai_explanation"] = respuesta_chat.text
            
        except Exception as e:
            print(f"Error en Cohere: {e}", flush=True)
            answer["ai_explanation"] = "El resultado está listo, pero el desglose paso a paso no se pudo generar por un error de red."
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
