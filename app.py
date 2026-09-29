"""Punto de entrada de Matemática II Interactiva."""
from __future__ import annotations

from flask import Flask, jsonify, render_template, request

import os 
from openai import OpenAI

from modules import unidad1, unidad2, unidad3
from modules.common import MathInputError, make_surface, safe_expr

cliente_openrouter = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=os.environ.get("OPENROUTER_API_KEY")),

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
# --- BLOQUE DE IA CON OPENROUTER ---
        try:
            pasos_texto = "\n".join([f"- {paso.get('title', '')}: {paso.get('latex', '')}" for paso in answer.get('steps', [])])
            
            prompt = f"""
            Eres un profesor experto en Cálculo de Varias Variables para estudiantes de ingeniería.
            Explica este procedimiento paso a paso de forma didáctica, breve y clara.
            Tema: {answer.get('title')}
            Contexto físico/ingeniería: {answer.get('engineering', 'No aplica')}
            Pasos matemáticos ya resueltos:
            {pasos_texto}
            Resultado final: {answer.get('result_latex')}
            
            Redacta solo la explicación sin repetir las ecuaciones en crudo, enfócate en el 'por qué' de cada paso.
            """
            
            respuesta_chat = cliente_openrouter.chat.completions.create(
                model="meta-llama/llama-3.1-8b-instruct:free", # Modelo gratuito y actualizado
                messages=[
                    {
                        "role": "user",
                        "content": prompt,
                    }
                ]
            )
            
            answer["ai_explanation"] = respuesta_chat.choices[0].message.content
            
        except Exception as e:
            print(f"Error de IA (OpenRouter): {e}")
            answer["ai_explanation"] = "Explicación de IA no disponible en este momento."
        # -----------------------------------
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
