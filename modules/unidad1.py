"""Unidad 1: cálculo diferencial de funciones de varias variables."""
from __future__ import annotations

import sympy as sp

from .common import MathInputError, latex, make_surface, number, response, safe_expr, step, x, y, z, t, lam

OPERATIONS = {"partials", "gradient", "directional", "tangent", "extrema", "lagrange", "exact", "chain", "jacobian", "limit"}


def _point(params: dict) -> tuple[sp.Expr, sp.Expr]:
    return number(params, "x0", 0), number(params, "y0", 0)


def partials(expression: str, params: dict):
    f = safe_expr(expression)
    
    # 1. Creamos el planteamiento (no evaluado)
    df_dx = sp.Derivative(f, x)
    df_dy = sp.Derivative(f, y)
    
    # 2. Calculamos el resultado real con .doit()
    fx, fy = df_dx.doit(), df_dy.doit()
    
    # 3. Derivadas de segundo orden
    fxx, fyy = sp.diff(fx, x), sp.diff(fy, y)
    fxy, fyx = sp.diff(fx, y), sp.diff(fy, x)
    
    # 4. Desglosamos el planteamiento y el resultado
    steps = [
        step("Función original", f),
        step("Planteamiento respecto a x", df_dx),
        step("Derivada parcial fx", fx),
        step("Planteamiento respecto a y", df_dy),
        step("Derivada parcial fy", fy),
        step("Derivada mixta fxy", fxy),
        step("Derivada mixta fyx", fyx)
    ]
    
    note = "Las derivadas mixtas coinciden: se cumple el teorema de Schwarz." if sp.simplify(fxy-fyx) == 0 else "Las derivadas mixtas no coinciden."
    return response("Derivadas parciales", sp.Matrix([fx, fy]), steps, note,
                    "Las tasas parciales modelan cómo cambia una magnitud de ingeniería al variar una variable y mantener la otra fija.", make_surface(f))


def gradient(expression: str, params: dict):
    f = safe_expr(expression); x0, y0 = _point(params)
    grad = sp.Matrix([sp.diff(f, x), sp.diff(f, y)])
    at_point = grad.subs({x: x0, y: y0})
    steps = [step("Función escalar", f), step("Gradiente", grad), step("Evaluación en el punto", at_point)]
    return response("Vector gradiente", at_point, steps,
                    "El gradiente apunta hacia el máximo incremento local y su norma indica la rapidez de ese incremento.",
                    "En una superficie de temperatura, señala hacia dónde aumentar más rápidamente la temperatura.", make_surface(f))


def directional(expression: str, params: dict):
    f = safe_expr(expression); x0, y0 = _point(params)
    a, b = number(params, "a", 1), number(params, "b", 0)
    direction = sp.Matrix([a, b]); norm = sp.sqrt(direction.dot(direction))
    if sp.simplify(norm) == 0:
        raise MathInputError("El vector dirección no puede ser el vector cero.")
    unit = sp.simplify(direction / norm)
    grad = sp.Matrix([sp.diff(f, x), sp.diff(f, y)]).subs({x: x0, y: y0})
    result = sp.simplify(grad.dot(unit))
    return response("Derivada direccional", result,
                    [step("Gradiente evaluado", grad), step("Vector unitario", unit), step("Producto punto ∇f·u", result)],
                    "La derivada direccional mide la tasa de cambio instantánea en la dirección elegida.",
                    "Sirve para estudiar el cambio de temperatura, esfuerzo o potencial a lo largo de una dirección de diseño.", make_surface(f))


def tangent(expression: str, params: dict):
    f = safe_expr(expression); x0, y0 = _point(params)
    z0 = sp.simplify(f.subs({x: x0, y: y0})); fx = sp.diff(f, x).subs({x: x0, y: y0}); fy = sp.diff(f, y).subs({x: x0, y: y0})
    plane = sp.expand(z0 + fx * (x - x0) + fy * (y - y0))
    normal = sp.Matrix([-fx, -fy, 1])
    plot = make_surface(f); plot.update({"kind": "tangent", "plane": make_surface(plane)["z"], "point": [float(x0), float(y0), float(z0)], "title": "Superficie y plano tangente"})
    return response("Plano tangente", plane,
                    [step("Punto sobre la superficie", z0), step("Pendientes fx y fy", sp.Matrix([fx, fy])), step("Vector normal", normal), step("Plano tangente", plane)],
                    "El plano es la mejor aproximación lineal local de la superficie.",
                    "Permite aproximar el comportamiento local de una superficie de respuesta en ingeniería.", plot)


def extrema(expression: str, params: dict):
    f = safe_expr(expression); fx, fy = sp.diff(f, x), sp.diff(f, y)
    try:
        points = sp.solve([fx, fy], [x, y], dict=True)
    except Exception as exc:
        raise MathInputError("No fue posible localizar los puntos críticos simbólicamente.") from exc
    if not points:
        raise MathInputError("No se encontraron puntos críticos reales con el método simbólico.")
    fxx, fyy, fxy = sp.diff(fx, x), sp.diff(fy, y), sp.diff(fx, y)
    classifications = []
    for point in points[:12]:
        d = sp.simplify((fxx * fyy - fxy**2).subs(point))
        xx = sp.simplify(fxx.subs(point))
        if d.is_positive and xx.is_positive: label = "mínimo local"
        elif d.is_positive and xx.is_negative: label = "máximo local"
        elif d.is_negative: label = "punto silla"
        else: label = "inconcluso"
        classifications.append(f"{point}: {label}")
    result = sp.Matrix([[p.get(x), p.get(y)] for p in points])
    steps = [step("Ecuaciones críticas", sp.Matrix([fx, fy])), step("Hessiano", sp.Matrix([[fxx, fxy], [fxy, fyy]])),
             {"title": "Clasificación", "latex": r"\\text{" + r";\\ ".join(classifications) + "}"}]
    return response("Extremos locales", result, steps, "Se emplea el determinante D=fxx·fyy−fxy² para clasificar cada punto crítico.",
                    "La optimización local ayuda a buscar máximos de rendimiento o mínimos de costo.", make_surface(f))


def lagrange(expression: str, params: dict):
    f = safe_expr(expression); restriction = safe_expr(str(params.get("constraint", "x^2+y^2-1")))
    equations = [sp.diff(f, x) - lam * sp.diff(restriction, x), sp.diff(f, y) - lam * sp.diff(restriction, y), restriction]
    try:
        solutions = sp.solve(equations, [x, y, lam], dict=True)
    except Exception as exc:
        raise MathInputError("No se pudo resolver el sistema de Lagrange.") from exc
    evaluations = [(item, sp.simplify(f.subs(item))) for item in solutions[:12]]
    result = sp.Matrix([value for _, value in evaluations]) if evaluations else sp.Symbol("sin_solución")
    return response("Multiplicadores de Lagrange", result,
                    [step("Función objetivo", f), step("Restricción g=0", restriction), step("Sistema ∇f−λ∇g", sp.Matrix(equations)),
                     {"title": "Puntos y evaluación", "latex": r"\\text{" + str(evaluations).replace("_", "") + "}"}],
                    "Los extremos restringidos aparecen cuando los gradientes de f y g son paralelos.",
                    "Se usa para optimizar diseño bajo restricciones de material, perímetro, energía o capacidad.", make_surface(f))


def exact(expression: str, params: dict):
    parts = expression.split(",")
    if len(parts) != 2:
        raise MathInputError("Escribe M,N; por ejemplo: 2*x*y, x^2.")
    m, n = safe_expr(parts[0]), safe_expr(parts[1]); my, nx = sp.diff(m, y), sp.diff(n, x)
    if sp.simplify(my-nx) != 0:
        return response("Diferencial no exacta", my-nx, [step("∂M/∂y", my), step("∂N/∂x", nx)],
                        "Como las derivadas cruzadas son distintas, la forma no es exacta.", "En física esto puede representar trabajo dependiente de la trayectoria.")
    potential = sp.integrate(m, x)
    correction = sp.simplify(sp.integrate(n - sp.diff(potential, y), y))
    potential = sp.simplify(potential + correction)
    return response("Diferencial exacta", potential, [step("M", m), step("N", n), step("Derivadas cruzadas", my), step("Función potencial Φ", potential)],
                    "Existe una función potencial Φ cuya diferencial es Mdx+Ndy.", "Un potencial permite calcular trabajo o energía sin recorrer toda la trayectoria.")


def chain(expression: str, params: dict):
    f = safe_expr(expression); xt = safe_expr(str(params.get("xt", "t"))); yt = safe_expr(str(params.get("yt", "t")))
    composed = sp.simplify(f.subs({x: xt, y: yt})); derivative = sp.diff(composed, t)
    rule = sp.simplify(sp.diff(f, x).subs({x: xt, y: yt}) * sp.diff(xt, t) + sp.diff(f, y).subs({x: xt, y: yt}) * sp.diff(yt, t))
    return response("Regla de la cadena", derivative, [step("Composición z(t)", composed), step("Regla de la cadena", rule), step("dz/dt", derivative)],
                    "La regla encadena cambios simultáneos de x(t) y y(t).", "Modela una magnitud que evoluciona con un proceso o trayectoria de operación.")


def jacobian(expression: str, params: dict):
    parts = expression.split(",")
    if len(parts) != 2:
        raise MathInputError("Escribe u,v; por ejemplo: x^2-y, x+y^2.")
    u, v = safe_expr(parts[0]), safe_expr(parts[1]); matrix = sp.Matrix([[sp.diff(u, x), sp.diff(u, y)], [sp.diff(v, x), sp.diff(v, y)]])
    return response("Jacobiano", sp.det(matrix), [step("Matriz jacobiana", matrix), step("Determinante", sp.det(matrix))],
                    "El determinante jacobiano mide el cambio local de área y orientación.", "Es central en transformaciones de coordenadas y análisis de sensibilidad.")


def limit(expression: str, params: dict):
    f = safe_expr(expression); variable_name = str(params.get("variable", "x")); point = number(params, "point", 0)
    variable = {"x": x, "y": y, "z": z, "t": t}.get(variable_name)
    if variable is None:
        raise MathInputError("La variable del límite debe ser x, y, z o t.")
    result = sp.limit(f, variable, point)
    return response("Límite", result, [step("Función", f), {"title": "Límite", "latex": r"\\lim_{" + latex(variable) + r"\\to" + latex(point) + "}" + latex(f)}, step("Resultado", result)],
                    "El límite describe el comportamiento de la función al acercarse al punto.", "Sirve para comprobar estabilidad y continuidad de modelos locales.")


HANDLERS = {name: globals()[name] for name in OPERATIONS}


def solve(operation: str, expression: str, params: dict):
    return HANDLERS[operation](expression, params)
