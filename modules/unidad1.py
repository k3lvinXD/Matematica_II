"""Unidad 1: cálculo diferencial de funciones de varias variables."""
from __future__ import annotations

import sympy as sp

from .common import MathInputError, latex, make_surface, tangent_plot, number, response, safe_expr, step, x, y, z, t, lam

OPERATIONS = {"partials", "gradient", "directional", "tangent", "extrema", "lagrange", "exact", "chain", "jacobian", "limit"}


def _point(params: dict) -> tuple[sp.Expr, sp.Expr]:
    point = number(params, "x0", 0), number(params, "y0", 0)
    if any(v.free_symbols or v.is_real is not True or v.is_finite is not True for v in point):
        raise MathInputError("Las coordenadas del punto deben ser constantes reales finitas.")
    return point


def _finite_at_point(value):
    if value.has(sp.zoo, sp.oo, -sp.oo, sp.nan) or (any(v.is_real is False for v in value) if hasattr(value, "rows") else value.is_real is False):
        raise MathInputError("La función o sus derivadas no tienen valor real finito en ese punto.")
    return value


def partials(expression: str, params: dict):
    f = safe_expr(expression)
    fx, fy = sp.diff(f, x), sp.diff(f, y)
    fxx, fyy, fxy, fyx = sp.diff(fx, x), sp.diff(fy, y), sp.diff(fx, y), sp.diff(fy, x)
    steps = [step("Función", f), step("Derivada parcial respecto a x", fx),
             step("Derivada parcial respecto a y", fy), step("Derivada mixta fxy", fxy),
             step("Derivada mixta fyx", fyx)]
    note = "Las derivadas mixtas calculadas coinciden. Schwarz requiere además continuidad de las segundas derivadas en un entorno del punto." if sp.simplify(fxy-fyx) == 0 else "Las derivadas mixtas no coinciden en esta expresión."
    return response("Derivadas parciales", sp.Matrix([fx, fy]), steps, note,
                    "Las tasas parciales modelan cómo cambia una magnitud de ingeniería al variar una variable y mantener la otra fija.", make_surface(f))
    

def gradient(expression: str, params: dict):
    f = safe_expr(expression); x0, y0 = _point(params)
    grad = sp.Matrix([sp.diff(f, x), sp.diff(f, y)])
    at_point = _finite_at_point(grad.subs({x: x0, y: y0}))
    steps = [step("Función escalar", f), step("Derivada respecto a x", grad[0], "Se mantiene y constante."), step("Derivada respecto a y", grad[1], "Se mantiene x constante."), step("Gradiente", grad), step("Evaluación en el punto", at_point)]
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
    result = _finite_at_point(sp.simplify(grad.dot(unit)))
    return response("Derivada direccional", result,
                    [step("Gradiente evaluado", grad), step("Vector unitario", unit), step("Producto punto ∇f·u", result)],
                    "La derivada direccional mide la tasa de cambio instantánea en la dirección elegida.",
                    "Sirve para estudiar el cambio de temperatura, esfuerzo o potencial a lo largo de una dirección de diseño.", make_surface(f))


def tangent(expression: str, params: dict):
    f = safe_expr(expression); x0, y0 = _point(params)
    z0 = sp.simplify(f.subs({x: x0, y: y0})); fx = sp.diff(f, x).subs({x: x0, y: y0}); fy = sp.diff(f, y).subs({x: x0, y: y0})
    plane = sp.expand(z0 + fx * (x - x0) + fy * (y - y0))
    _finite_at_point(sp.Matrix([z0, fx, fy]))
    normal = sp.Matrix([-fx, -fy, 1])
    plot = tangent_plot(f, plane, x0, y0, z0)
    return response("Plano tangente", plane,
                    [step("Punto sobre la superficie", z0), step("Pendientes fx y fy", sp.Matrix([fx, fy])), step("Vector normal", normal), step("Plano tangente", plane)],
                    "El plano es la mejor aproximación lineal local de la superficie.",
                    "Permite aproximar el comportamiento local de una superficie de respuesta en ingeniería.", plot)


def extrema(expression: str, params: dict):
    f = safe_expr(expression)
    if not f.free_symbols <= {x, y}:
        raise MathInputError("Para extremos locales usa una función de x e y.")
    fx, fy = sp.diff(f, x), sp.diff(f, y)
    points = [{}] if fx == 0 and fy == 0 else sp.solve([fx, fy], [x, y], dict=True)
    points = [p for p in points if all(v.is_real is not False for v in p.values())]
    if not points:
        raise MathInputError("No se localizaron puntos críticos reales con este método; no demuestra que no existan.")
    hessian = sp.hessian(f, (x, y))
    steps = [step("Ecuaciones críticas", sp.Matrix([fx, fy])), step("Hessiano", hessian)]
    rows = []
    for point in points[:12]:
        coords = [point.get(x, x), point.get(y, y)]
        rows.append(coords)
        family = set(point) != {x, y} or any(v.free_symbols for v in coords)
        determinant = sp.simplify(hessian.det().subs(point))
        xx = sp.simplify(hessian[0, 0].subs(point))
        if family:
            label = "Familia de puntos críticos: las variables que permanecen son libres. El criterio hessiano no clasifica la familia."
        elif determinant.is_positive and xx.is_positive: label = "Mínimo local estricto."
        elif determinant.is_positive and xx.is_negative: label = "Máximo local estricto."
        elif determinant.is_negative: label = "Punto silla."
        else: label = "Criterio hessiano inconcluso: se necesita otro análisis."
        steps.append(step("Familia crítica" if family else "Punto crítico", sp.Matrix(coords), label))
        steps.append(step("Determinante del Hessiano", determinant))
    note = "Clasificación local en puntos donde la función es dos veces continuamente diferenciable; no determina extremos absolutos ni analiza el borde."
    if len(points) > 12:
        note += " Se muestran las primeras doce soluciones."
    return response("Extremos locales", sp.Matrix(rows), steps, note,
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
    return response("Potencial candidato de la diferencial", potential, [step("M", m), step("N", n), step("Derivadas cruzadas", my), step("Función potencial Φ", potential)],
                    "La igualdad de derivadas cruzadas es un criterio local. Verifica las derivadas del potencial y un dominio donde sea diferenciable antes de concluir exactitud global.", "Un potencial permite calcular trabajo o energía sin recorrer toda la trayectoria.")


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
    return response("Límite en una variable", result, [step("Función", f), {"title": "Límite", "latex": r"\\lim_{" + latex(variable) + r"\\to" + latex(point) + "}" + latex(f)}, step("Resultado", result)],
                    "Se varía únicamente la variable seleccionada y se mantienen las demás fijas. No es una prueba de existencia de un límite multivariable.", "Sirve para comprobar estabilidad y continuidad de modelos locales.")


HANDLERS = {name: globals()[name] for name in OPERATIONS}


def solve(operation: str, expression: str, params: dict):
    return HANDLERS[operation](expression, params)
