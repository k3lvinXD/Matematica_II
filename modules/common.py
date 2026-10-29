"""Utilidades seguras, serialización y gráficas para el motor simbólico."""
from __future__ import annotations

import re
import ast
from contextvars import ContextVar
from functools import lru_cache, wraps
from typing import Any

import numpy as np
import sympy as sp
from sympy.parsing.sympy_parser import (
    convert_xor,
    implicit_multiplication_application,
    stringify_expr,
    standard_transformations,
)


x, y, z, t, r, theta, phi, rho, lam = sp.symbols("x y z t r theta phi rho lambda", real=True)
SYMBOLS = {v.name: v for v in (x, y, z, t, r, theta, phi, rho, lam)}
SAFE_FUNCTIONS = {
    "sin": sp.sin, "cos": sp.cos, "tan": sp.tan, "asin": sp.asin, "acos": sp.acos,
    "atan": sp.atan, "exp": sp.exp, "log": sp.log, "sqrt": sp.sqrt, "abs": sp.Abs,
    "pi": sp.pi, "E": sp.E, "e" : sp.E
}
SAFE_LOCALS = {**SYMBOLS, **SAFE_FUNCTIONS}
TRANSFORMS = standard_transformations + (convert_xor, implicit_multiplication_application)
IDENTIFIER = re.compile(r"[A-Za-z_]+")
ALLOWED_CHARACTERS = re.compile(r"^[A-Za-z0-9_+\-*/^().,\s]+$")
# Los transformadores solo normalizan texto; el AST se interpreta con una lista permitida.
# No se evalúa el código Python que producen.
SAFE_GLOBALS = {
    "__builtins__": {}, "Integer": sp.Integer, "Float": sp.Float,
    "Rational": sp.Rational, "Symbol": sp.Symbol, "Function": sp.Function,
}
KNOWN_WORDS = tuple(sorted(SAFE_LOCALS, key=len, reverse=True))


class MathInputError(ValueError):
    """Error de entrada traducible a un mensaje amigable para la interfaz."""

def _split_math_word(word: str) -> list[str] | None:
    """Separa xsin en x, sin de forma segura."""
    if word in SAFE_LOCALS:
        return [word]

    @lru_cache(maxsize=256)
    def divide(position: int) -> list[str] | None:
        if position == len(word):
            return []

        for item in KNOWN_WORDS:
            if word.startswith(item, position):
                remaining = divide(position + len(item))
                if remaining is not None:
                    return [item, *remaining]
        return None

    pieces = divide(0)
    return pieces if pieces and len(pieces) > 1 else None


def normalize_math_notation(text: str) -> str:
    """Convierte 2xsin(x), xy y xpi en productos explícitos."""
    def replace_word(match: re.Match[str]) -> str:
        word = match.group(0)
        pieces = _split_math_word(word)

        if pieces is None:
            if word in SAFE_LOCALS:
                return word
            raise MathInputError(
                "Usa solo variables x, y, z, t, r, theta, phi, rho "
                "y funciones matemáticas admitidas."
            )

        return "*".join(pieces)

    return IDENTIFIER.sub(replace_word, text)


def safe_expr(text: str) -> sp.Expr:
    """Construye SymPy desde un AST permitido, sin ejecutar texto de entrada."""
    if not isinstance(text, str):
        raise MathInputError("La expresión debe ser texto.")
    text = text.strip().replace("−", "-").replace("×", "*").replace("÷", "/")
    if not text or len(text) > 240 or not ALLOWED_CHARACTERS.fullmatch(text):
        raise MathInputError("Escribe una expresión válida de hasta 240 caracteres.")
    text = normalize_math_notation(text)
    if len(text) > 480:
        raise MathInputError("Reduce la complejidad de la expresión.")
    try:
        code = stringify_expr(text, dict(SAFE_LOCALS), SAFE_GLOBALS, TRANSFORMS)
        tree = ast.parse(code, mode="eval")
        if sum(1 for _ in ast.walk(tree)) > 180:
            raise MathInputError("Reduce la complejidad de la expresión.")

        def checked(value):
            if value.has(sp.zoo, sp.oo, -sp.oo, sp.nan) or value.is_real is False:
                raise MathInputError("La expresión no tiene un valor real finito.")
            return value

        def visit(node, depth=0):
            if depth > 18:
                raise MathInputError("Demasiados niveles de anidación.")
            child = lambda item: visit(item, depth + 1)
            if isinstance(node, ast.Name) and node.id in SAFE_LOCALS:
                value = SAFE_LOCALS[node.id]
                if isinstance(value, sp.Expr):
                    return value
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and not node.keywords:
                name = node.func.id
                if name in ("Integer", "Float") and len(node.args) == 1 and isinstance(node.args[0], ast.Constant):
                    token = str(node.args[0].value)
                    if not re.fullmatch(r"(?:\d{1,12}(?:\.\d{0,12})?|\.\d{1,12})", token):
                        raise MathInputError("Usa números de hasta doce cifras enteras y decimales.")
                    return sp.Rational(token)
                if name in SAFE_FUNCTIONS and callable(SAFE_FUNCTIONS[name]) and len(node.args) == 1:
                    return checked(SAFE_FUNCTIONS[name](child(node.args[0])))
            if isinstance(node, ast.UnaryOp) and isinstance(node.op, (ast.UAdd, ast.USub)):
                value = child(node.operand)
                return value if isinstance(node.op, ast.UAdd) else -value
            if isinstance(node, ast.BinOp):
                left, right = child(node.left), child(node.right)
                if isinstance(node.op, ast.Add): value = left + right
                elif isinstance(node.op, ast.Sub): value = left - right
                elif isinstance(node.op, ast.Mult): value = left * right
                elif isinstance(node.op, ast.Div):
                    if right.is_zero is True:
                        raise MathInputError("No se permite dividir entre cero.")
                    value = left / right
                elif isinstance(node.op, ast.Pow):
                    if right.is_number and (right.is_real is not True or abs(right) > 100):
                        raise MathInputError("Usa exponentes numéricos entre -100 y 100.")
                    if left.is_Rational and right.is_Integer and abs(right) * max(int(left.p).bit_length(), int(left.q).bit_length()) > 4096:
                        raise MathInputError("La potencia numérica es demasiado grande.")
                    value = left ** right
                else:
                    raise MathInputError("Operación no admitida.")
                return checked(value)
            raise MathInputError("La entrada contiene una operación no admitida.")

        return checked(visit(tree.body))
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
    if hasattr(result, "has") and result.has(sp.zoo, sp.nan):
        raise MathInputError("El resultado es indefinido. Revisa el dominio y el punto elegido.")
    return {
        "title": title,
        "result_latex": latex(result),
        "result_decimal": decimal(result),
        "steps": steps,
        "interpretation": interpretation,
        "engineering": engineering,
        "plot": plot,
    }


PLOTS_ENABLED = ContextVar("plots_enabled", default=True)


def optional_plot(function):
    @wraps(function)
    def wrapped(*args, **kwargs):
        if not PLOTS_ENABLED.get():
            return None
        try:
            with np.errstate(all="ignore"):
                return function(*args, **kwargs)
        except Exception:
            return {"kind": "message", "title": "El cálculo se conserva, pero no se pudo representar esta gráfica en el dominio elegido."}
    return wrapped


def finite_list(values):
    array = np.asarray(values, dtype=float)
    return np.where(np.isfinite(array), array, None).tolist()


@optional_plot
def make_surface(expr: sp.Expr, lower: float = -4, upper: float = 4, n: int = 45) -> dict[str, Any]:
    if not expr.free_symbols <= {x, y}:
        raise MathInputError("La gráfica de superficie admite funciones de x e y.")
    values = np.linspace(lower, upper, n)
    xx, yy = np.meshgrid(values, values)
    func = sp.lambdify((x, y), expr, "numpy")
    zz = np.asarray(func(xx, yy), dtype=float)
    if zz.ndim == 0:
        zz = np.full_like(xx, float(zz))
    return {"kind": "surface", "x": values.tolist(), "y": values.tolist(), "z": finite_list(zz),
            "title": f"z = {latex(expr)}"}


def vector_components(text: str, dimensions: int = 2) -> list[sp.Expr]:
    parts = [item.strip() for item in text.replace("<", "").replace(">", "").split(",")]
    if len(parts) != dimensions:
        raise MathInputError(f"Escribe exactamente {dimensions} componentes separadas por coma.")
    return [safe_expr(part) for part in parts]


@optional_plot
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
            "u": finite_list((p * scale).ravel()), "v": finite_list((q * scale).ravel()),
            "title": "Campo vectorial"}


@optional_plot
def curve_plot(parts):
    values = np.linspace(-5, 5, 100)
    coordinates = [finite_list(np.broadcast_to(sp.lambdify(t, part, "numpy")(values), values.shape)) for part in parts]
    return {"kind": "curve3d", "x": coordinates[0], "y": coordinates[1], "z": coordinates[2], "title": "Trayectoria vectorial r(t)"}


@optional_plot
def tangent_plot(f, plane, x0, y0, z0):
    plot, other = make_surface(f), make_surface(plane)
    if plot["kind"] == "message" or other["kind"] == "message":
        return {"kind": "message", "title": "El plano se calculó; no fue posible dibujarlo."}
    plot.update(kind="tangent", plane=other["z"], point=[float(x0), float(y0), float(z0)], title="Superficie y plano tangente")
    return plot
