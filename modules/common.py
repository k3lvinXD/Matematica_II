"""Utilidades seguras, serialización y gráficas para el motor simbólico."""
from __future__ import annotations

import re
from typing import Any

import numpy as np
import sympy as sp
from sympy.parsing.sympy_parser import (
    convert_xor,
    implicit_multiplication_application,
    parse_expr,
    standard_transformations,
)


x, y, z, t, r, theta, phi, rho, lam = sp.symbols("x y z t r theta phi rho lambda", real=True)
SYMBOLS = {v.name: v for v in (x, y, z, t, r, theta, phi, rho, lam)}
SAFE_FUNCTIONS = {
    "sin": sp.sin, "cos": sp.cos, "tan": sp.tan, "asin": sp.asin, "acos": sp.acos,
    "atan": sp.atan, "exp": sp.exp, "log": sp.log, "sqrt": sp.sqrt, "abs": sp.Abs,
    "pi": sp.pi, "E": sp.E,
}
SAFE_LOCALS = {**SYMBOLS, **SAFE_FUNCTIONS}
TRANSFORMS = standard_transformations + (convert_xor, implicit_multiplication_application)
IDENTIFIER = re.compile(r"[A-Za-z_]+")
ALLOWED_CHARACTERS = re.compile(r"^[A-Za-z0-9_+\-*/^().,\s]+$")
# `parse_expr` needs these constructors internally for numeric literals.  They are
# explicit, harmless SymPy constructors; user-provided identifiers are still
# checked against SAFE_LOCALS before parsing.
SAFE_GLOBALS = {
    "__builtins__": {}, "Integer": sp.Integer, "Float": sp.Float,
    "Rational": sp.Rational, "Symbol": sp.Symbol, "Function": sp.Function,
}


class MathInputError(ValueError):
    """Error de entrada traducible a un mensaje amigable para la interfaz."""


def safe_expr(text: str) -> sp.Expr:
    """Convierte una expresión sin permitir atributos, strings ni ejecución de Python."""
    text = text.strip().replace("−", "-").replace("×", "*").replace("÷", "/")
    if not text:
        raise MathInputError("La expresión está vacía.")
    if len(text) > 240 or not ALLOWED_CHARACTERS.fullmatch(text):
        raise MathInputError("La expresión contiene símbolos no admitidos.")
    names = set(IDENTIFIER.findall(text))
    allowed = set(SAFE_LOCALS) | {"e"}
    if any(name not in allowed for name in names):
        raise MathInputError("Usa solo variables x, y, z, t, r, theta, phi, rho y funciones matemáticas admitidas.")
    try:
        parsed = parse_expr(text.replace("^", "**"), local_dict=SAFE_LOCALS,
                            global_dict=SAFE_GLOBALS, transformations=TRANSFORMS,
                            evaluate=True)
        if not isinstance(parsed, sp.Expr):
            raise MathInputError("La entrada no representa una expresión escalar válida.")
        return sp.simplify(parsed)
    except MathInputError:
        raise
    except Exception as exc:
        raise MathInputError("No se pudo interpretar la expresión matemática.") from exc


def number(params: dict[str, Any], key: str, default: float | None = None) -> sp.Expr:
    raw = params.get(key, default)
    if raw is None or str(raw).strip() == "":
        raise MathInputError(f"Falta el valor de {key}.")
    return safe_expr(str(raw))


def latex(value: Any) -> str:
    return sp.latex(value)


def decimal(value: Any) -> str:
    try:
        return str(sp.N(value, 8))
    except Exception:
        return "No aplica"


def step(title: str, expression: Any, note: str | None = None) -> dict[str, str]:
    item = {"title": title, "latex": latex(expression)}
    if note:
        item["note"] = note
    return item


def response(title: str, result: Any, steps: list[dict[str, str]], interpretation: str,
             engineering: str, plot: dict | None = None) -> dict[str, Any]:
    return {
        "title": title,
        "result_latex": latex(result),
        "result_decimal": decimal(result),
        "steps": steps,
        "interpretation": interpretation,
        "engineering": engineering,
        "plot": plot,
    }


def make_surface(expr: sp.Expr, lower: float = -4, upper: float = 4, n: int = 45) -> dict[str, Any]:
    if not expr.free_symbols <= {x, y}:
        raise MathInputError("La gráfica de superficie admite funciones de x e y.")
    values = np.linspace(lower, upper, n)
    xx, yy = np.meshgrid(values, values)
    func = sp.lambdify((x, y), expr, "numpy")
    zz = np.asarray(func(xx, yy), dtype=float)
    if zz.ndim == 0:
        zz = np.full_like(xx, float(zz))
    zz[~np.isfinite(zz)] = np.nan
    return {"kind": "surface", "x": values.tolist(), "y": values.tolist(), "z": zz.tolist(),
            "title": f"z = {latex(expr)}"}


def vector_components(text: str, dimensions: int = 2) -> list[sp.Expr]:
    parts = [item.strip() for item in text.replace("<", "").replace(">", "").split(",")]
    if len(parts) != dimensions:
        raise MathInputError(f"Escribe exactamente {dimensions} componentes separadas por coma.")
    return [safe_expr(part) for part in parts]


def vector_field_plot(parts: list[sp.Expr]) -> dict[str, Any]:
    if len(parts) != 2:
        return {"kind": "message", "title": "El campo 3D se calculó simbólicamente."}
    coords = np.linspace(-4, 4, 13)
    xx, yy = np.meshgrid(coords, coords)
    p = np.asarray(sp.lambdify((x, y), parts[0], "numpy")(xx, yy), dtype=float)
    q = np.asarray(sp.lambdify((x, y), parts[1], "numpy")(xx, yy), dtype=float)
    p = np.broadcast_to(p, xx.shape).copy(); q = np.broadcast_to(q, xx.shape).copy()
    magnitude = np.hypot(p, q); magnitude[magnitude == 0] = 1
    scale = 0.32 / magnitude
    return {"kind": "vector", "x": xx.ravel().tolist(), "y": yy.ravel().tolist(),
            "u": (p * scale).ravel().tolist(), "v": (q * scale).ravel().tolist(),
            "title": "Campo vectorial"}
