"""Matemática II: el cálculo no depende de gráficas ni de servicios de IA."""
from flask import Flask, jsonify, render_template, request
from werkzeug.exceptions import RequestEntityTooLarge
import subprocess
import uuid
from modules.runtime import SLOTS, run_worker

app = Flask(__name__)
app.config.update(MAX_CONTENT_LENGTH=16 * 1024, MATH_TIMEOUT=12, AI_TIMEOUT=20, SPEECH_TIMEOUT=24)
app.json.sort_keys = False


@app.get("/")
def index():
    return render_template("index.html")


@app.get("/unidad/<int:number>")
def unidad(number):
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


@app.errorhandler(RequestEntityTooLarge)
def too_large(error):
    return jsonify(error="La solicitud supera el máximo de 16 KiB."), 413


def execute(action, extra=None):
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return jsonify(error="Envía un objeto JSON válido."), 400
    if extra:
        data.update(extra)
    if not SLOTS.acquire(blocking=False):
        return jsonify(error="Hay cálculos en curso. Intenta de nuevo en unos segundos."), 503
    try:
        timeout = app.config["SPEECH_TIMEOUT" if action == "speech" else "AI_TIMEOUT" if action in ("explain", "chat") else "MATH_TIMEOUT"]
        result = run_worker(data, action=action, timeout=timeout)
        if not result["ok"]:
            status = result.get("status", 500)
            if status >= 500:
                incident = uuid.uuid4().hex[:12]
                app.logger.error("Fallo de operación %s: %s", action, incident)
                return jsonify(error=result["error"], incident=incident), status
            return jsonify(error=result["error"]), status
        answer = result["answer"]
        status = answer.pop("status", 200)
        return jsonify(answer), status
    except subprocess.TimeoutExpired:
        return jsonify(error="Se agotó el tiempo de esta operación. Prueba una expresión más sencilla; los resultados anteriores se conservan."), 504
    except Exception:
        incident = uuid.uuid4().hex[:12]
        app.logger.error("Fallo de proceso %s: %s", action, incident)
        return jsonify(error="No se pudo completar esta operación.", incident=incident), 500
    finally:
        SLOTS.release()


@app.get("/asistente")
def assistant_page():
    return render_template("asistente.html", active="asistente")


@app.post("/api/speech")
def assistant_speech():
    response, status = execute("speech")
    response.headers["Cache-Control"] = "no-store"
    return response, status


@app.post("/api/chat")
def assistant_chat():
    return execute("chat")


@app.post("/api/calculate")
def calculate():
    return execute("calculate")


@app.post("/api/plot")
def plot():
    return execute("plot")


@app.post("/api/plot/surface")
def plot_surface():
    return execute("surface")


@app.post("/api/explain")
def explain():
    return execute("explain")


@app.post("/api/exercise/<exercise_id>")
def check_exercise(exercise_id):
    return execute("exercise", {"exercise_id": exercise_id})


if __name__ == "__main__":
    app.run()
