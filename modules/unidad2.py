"""Unidad 2: cálculo integral de funciones de varias variables."""
from __future__ import annotations

import sympy as sp

from .common import MathInputError, latex, make_surface, number, response, safe_expr, step, x, y, z, r, theta, rho, phi

OPERATIONS = {"double_integral", "triple_integral", "polar", "surface_area", "mass_center"}


def _bounds(params: dict, variable: str) -> tuple[sp.Expr, sp.Expr]:
    return number(params, variable + "min", 0), number(params, variable + "max", 1)


def double_integral(expression: str, params: dict):
    f = safe_expr(expression)
    if not f.free_symbols <= {x, y}:
        raise MathInputError("El integrando debe depender solo de x e y.")
    order = params.get("order", "xy")
    if order not in ("xy", "yx"):
        raise MathInputError("Elige el orden xy o yx.")
    inner, outer = (x, y) if order == "xy" else (y, x)
    low, high = _bounds(params, str(inner))
    a, b = _bounds(params, str(outer))
    if any(v.free_symbols or v.is_real is not True or v.is_finite is not True for v in (a, b)):
        raise MathInputError("Los límites exteriores deben ser constantes reales finitas.")
    if (b - a).is_positive is not True:
        raise MathInputError("El límite exterior inferior debe ser menor que el superior.")
    if any(not v.free_symbols <= {outer} for v in (low, high)):
        raise MathInputError("Los límites interiores solo pueden depender de la variable exterior.")
    width = sp.simplify(high - low)
    # La validación exacta por extremos solo se aplica a cotas afines.
    affine = all(v.is_polynomial(outer) and sp.diff(v, outer, 2) == 0 for v in (low, high))
    if affine and any(width.subs(outer, q).is_nonnegative is not True for q in (a, b)):
        raise MathInputError("La cota interior inferior supera a la superior.")
    primitive = sp.integrate(f, inner)
    first = sp.integrate(f, (inner, low, high))
    result = sp.simplify(sp.integrate(first, (outer, a, b)))
    integral = sp.Integral(f, (inner, low, high), (outer, a, b))
    residual = sp.simplify(sp.diff(primitive, inner) - f)
    steps = [step("Integral planteada", integral),
             step(f"Antiderivada respecto a {inner}", primitive, f"Se mantiene {outer} constante."),
             step("Comprobación de la antiderivada", residual, "Un residuo cero comprueba esta antiderivada, no la existencia de toda integral impropia."),
             step("Evaluación de límites interiores", first), step(f"Integración exterior en {outer}", result)]
    answer = response("Integral doble", result, steps,
                      "Acumulación sobre la región definida por los límites y el orden elegidos.",
                      "Permite calcular masa, carga o energía distribuida.", make_surface(f))
    answer["warnings"] = []
    if not affine:
        answer["warnings"].append("No se certificó el orden de las cotas no afines en todo el intervalo; revisa la región.")
    if not f.is_polynomial(x, y):
        answer["warnings"].append("Revisa dominio, singularidades y convergencia del integrando; el valor simbólico no certifica esas condiciones.")
    return answer


def triple_integral(expression: str, params: dict):
    f = safe_expr(expression); xa, xb = _bounds(params, "x"); ya, yb = _bounds(params, "y"); za, zb = _bounds(params, "z")
    i1 = sp.integrate(f, (x, xa, xb)); i2 = sp.integrate(i1, (y, ya, yb)); result = sp.simplify(sp.integrate(i2, (z, za, zb)))
    return response("Integral triple", result, [step("Integral triple", sp.Integral(f, (x, xa, xb), (y, ya, yb), (z, za, zb))), step("Integración en x", i1), step("Integración en y", i2), step("Integración en z", result)],
                    "La integral triple suma una cantidad distribuida dentro de un volumen.", "Se aplica a masa de sólidos, carga, energía, volumen y distribución de temperatura en un componente.")


def polar(expression: str, params: dict):
    f = safe_expr(expression); ra, rb = _bounds(params, "r"); ta, tb = _bounds(params, "theta")
    transformed = sp.simplify(f.subs({x: r*sp.cos(theta), y: r*sp.sin(theta)}) * r)
    first = sp.integrate(transformed, (r, ra, rb)); result = sp.simplify(sp.integrate(first, (theta, ta, tb)))
    return response("Integral en coordenadas polares", result,
                    [step("Transformación x,y", sp.Matrix([r*sp.cos(theta), r*sp.sin(theta)])), step("Jacobiano r", r), step("Integrando transformado", transformed), step("Resultado", result)],
                    "El factor r es el jacobiano que corrige el cambio de área al usar polares.", "Las coordenadas polares simplifican regiones circulares, discos, anillos y componentes con simetría radial.")


def surface_area(expression: str, params: dict):
    f = safe_expr(expression); xa, xb = _bounds(params, "x"); ya, yb = _bounds(params, "y")
    fx, fy = sp.diff(f, x), sp.diff(f, y); integrand = sp.sqrt(1 + fx**2 + fy**2)
    result = sp.simplify(sp.integrate(sp.integrate(integrand, (x, xa, xb)), (y, ya, yb)))
    return response("Área de superficie", result, [step("fx", fx), step("fy", fy), step("Elemento de área", integrand), step("Integral de área", sp.Integral(integrand, (x, xa, xb), (y, ya, yb))), step("Resultado", result)],
                    "El integrando mide cómo la inclinación local estira cada elemento de área.", "Sirve para estimar pintura, recubrimiento o material de una superficie curva.", make_surface(f))


def mass_center(expression: str, params: dict):
    density = safe_expr(expression); xa, xb = _bounds(params, "x"); ya, yb = _bounds(params, "y")
    mass = sp.simplify(sp.integrate(sp.integrate(density, (x, xa, xb)), (y, ya, yb)))
    if sp.simplify(mass) == 0:
        raise MathInputError("La masa total no puede ser cero.")
    mx = sp.simplify(sp.integrate(sp.integrate(x*density, (x, xa, xb)), (y, ya, yb)))
    my = sp.simplify(sp.integrate(sp.integrate(y*density, (x, xa, xb)), (y, ya, yb)))
    center = sp.Matrix([sp.simplify(mx/mass), sp.simplify(my/mass)])
    return response("Centro de masa", center, [step("Densidad", density), step("Masa total", mass), step("Momento respecto a y", mx), step("Momento respecto a x", my), step("Centro de masa", center)],
                    "El centro de masa es el punto de equilibrio de la lámina con densidad variable.", "Permite diseñar soportes, balances, piezas y distribución de material.", make_surface(density))


HANDLERS = {name: globals()[name] for name in OPERATIONS}


def solve(operation: str, expression: str, params: dict):
    return HANDLERS[operation](expression, params)
