"""Unidad 3: análisis vectorial y curvas espaciales."""
from __future__ import annotations

import sympy as sp

from .common import MathInputError, latex, response, safe_expr, step, vector_components, vector_field_plot, curve_plot, x, y, z, t

OPERATIONS = {"vector_curve", "vector_field", "divergence", "curl", "laplacian", "line_integral", "conservative", "green"}


def _field(expression: str, dimensions: int = 2) -> list[sp.Expr]:
    return vector_components(expression, dimensions)


def vector_curve(expression: str, params: dict):
    parts = _field(expression, 3); velocity = sp.Matrix([sp.diff(p, t) for p in parts]); acceleration = sp.Matrix([sp.diff(v, t) for v in velocity])
    plot = curve_plot(parts)
    return response("Función vectorial", sp.Matrix(parts), [step("r(t)", sp.Matrix(parts)), step("Velocidad r′(t)", velocity), step("Aceleración r′′(t)", acceleration)],
                    "La derivada de la posición es velocidad; la segunda derivada es aceleración.", "Describe trayectorias de mecanismos, vehículos autónomos, partículas o robots.", plot)


def vector_field(expression: str, params: dict):
    parts = _field(expression, 2)
    return response("Campo vectorial", sp.Matrix(parts), [step("Componentes P,Q", sp.Matrix(parts))],
                    "Cada vector representa dirección y magnitud de la magnitud local.", "Un campo puede modelar flujo de fluido, fuerza, velocidad o campo eléctrico.", vector_field_plot(parts))


def divergence(expression: str, params: dict):
    dimensions = str(params.get("dimensions", len(expression.split(","))))
    if dimensions not in ("2", "3"):
        raise MathInputError("Selecciona dos o tres dimensiones.")
    parts = _field(expression, int(dimensions))
    variables = (x, y, z)[:len(parts)]
    if any(not part.free_symbols <= set(variables) for part in parts):
        raise MathInputError("Usa únicamente las variables correspondientes a la dimensión del campo.")
    terms = [sp.diff(part, variable) for part, variable in zip(parts, variables)]
    result = sp.simplify(sum(terms))
    return response("Divergencia", result, [step("Campo", sp.Matrix(parts)), step("Derivadas de las componentes", sp.Matrix(terms)), step("∇·F", result)],
                    "La divergencia positiva indica una fuente local; la negativa, un sumidero.", "Se usa para analizar expansión de flujo, fuentes térmicas o conservación de masa.", vector_field_plot(parts))


def curl(expression: str, params: dict):
    parts = _field(expression, 3) if str(params.get("dimensions", "2")) == "3" else _field(expression, 2)
    if len(parts) == 2:
        result = sp.simplify(sp.diff(parts[1], x) - sp.diff(parts[0], y))
        steps = [step("Campo", sp.Matrix(parts)), step("∂Q/∂x−∂P/∂y", result)]
    else:
        result = sp.Matrix([sp.diff(parts[2], y)-sp.diff(parts[1], z), sp.diff(parts[0], z)-sp.diff(parts[2], x), sp.diff(parts[1], x)-sp.diff(parts[0], y)])
        steps = [step("Campo", sp.Matrix(parts)), step("∇×F", result)]
    return response("Rotacional", result, steps, "El rotacional cuantifica la tendencia local a girar.", "Permite estudiar vórtices en fluidos y efectos rotacionales en campos físicos.", vector_field_plot(parts))


def laplacian(expression: str, params: dict):
    f = safe_expr(expression); result = sp.simplify(sp.diff(f, x, 2)+sp.diff(f, y, 2)+sp.diff(f, z, 2))
    return response("Laplaciano", result, [step("Función escalar", f), step("∂²f/∂x²", sp.diff(f, x, 2)), step("∂²f/∂y²", sp.diff(f, y, 2)), step("∂²f/∂z²", sp.diff(f, z, 2)), step("Δf", result)],
                    "El laplaciano resume la curvatura o difusión neta de un campo escalar.", "Aparece en ecuaciones de conducción de calor, potencial eléctrico y difusión.")


def line_integral(expression: str, params: dict):
    parts = _field(expression, 2); xt = safe_expr(str(params.get("xt", "t"))); yt = safe_expr(str(params.get("yt", "t^2"))); a = safe_expr(str(params.get("tmin", "0"))); b = safe_expr(str(params.get("tmax", "1")))
    substituted = sp.simplify(parts[0].subs({x: xt, y: yt})*sp.diff(xt,t) + parts[1].subs({x: xt,y:yt})*sp.diff(yt,t))
    result = sp.simplify(sp.integrate(substituted, (t, a, b)))
    return response("Integral de línea", result, [step("Campo F", sp.Matrix(parts)), step("Curva r(t)", sp.Matrix([xt,yt])), step("F(r(t))·r′(t)", substituted), step("Integral", result)],
                    "La integral acumula la componente tangencial del campo a lo largo de la curva orientada.", "Calcula trabajo efectuado por una fuerza o circulación de un fluido.", vector_field_plot(parts))


def conservative(expression: str, params: dict):
    p, q = _field(expression, 2); py, qx = sp.diff(p,y), sp.diff(q,x)
    if sp.simplify(py-qx) != 0:
        return response("Campo no conservativo", py-qx, [step("∂P/∂y", py), step("∂Q/∂x", qx)], "El rotacional escalar no es cero; no existe potencial global bajo este criterio.", "El trabajo puede depender de la trayectoria de un proceso.", vector_field_plot([p,q]))
    potential = sp.integrate(p,x); potential = sp.simplify(potential + sp.integrate(q-sp.diff(potential,y),y))
    return response("Potencial candidato", potential, [step("∂P/∂y", py), step("∂Q/∂x", qx), step("Potencial Φ", potential)], "Las derivadas cruzadas coinciden. El potencial debe comprobarse en un dominio donde sea diferenciable; esta igualdad no demuestra conservatividad global en dominios con agujeros.", "La diferencia de potencial permite calcular trabajo de forma eficiente e independiente de la trayectoria.", vector_field_plot([p,q]))


def green(expression: str, params: dict):
    p, q = _field(expression, 2); xa=safe_expr(str(params.get("xmin","0"))); xb=safe_expr(str(params.get("xmax","1"))); ya=safe_expr(str(params.get("ymin","0"))); yb=safe_expr(str(params.get("ymax","1")))
    integrand=sp.simplify(sp.diff(q,x)-sp.diff(p,y)); area=sp.simplify(sp.integrate(sp.integrate(integrand,(x,xa,xb)),(y,ya,yb)))
    # Recorrido antihorario del rectángulo para la verificación de Green.
    bottom=sp.integrate(p.subs(y,ya),(x,xa,xb)); right=sp.integrate(q.subs(x,xb),(y,ya,yb)); top=sp.integrate(p.subs(y,yb),(x,xb,xa)); left=sp.integrate(q.subs(x,xa),(y,yb,ya)); line=sp.simplify(bottom+right+top+left)
    return response("Teorema de Green", area, [step("Rotacional escalar", integrand), step("Integral doble", area), step("Integral de línea cerrada", line)], "Compara ambos valores. Green requiere un campo continuamente diferenciable en un entorno de la región y frontera positivamente orientada; esta herramienta no verifica todas esas hipótesis.", "Green conecta circulación de borde con comportamiento interno de una región, útil en fluidos y electromagnetismo.", vector_field_plot([p,q]))


HANDLERS = {name: globals()[name] for name in OPERATIONS}


def solve(operation: str, expression: str, params: dict):
    return HANDLERS[operation](expression, params)
