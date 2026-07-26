# laser_animations/animator_tab/equation_parser.py
"""
Parses the "graphing calculator" style path input for the Animate tab,
e.g. "(10, 10cos(t), 10sin(t))", plus scalar t-range expressions like
"pi/2", into numeric Python callables using sympy.

Requires: sympy (pip install sympy)
"""
import sympy as sp
from sympy.parsing.sympy_parser import (
    parse_expr,
    standard_transformations,
    implicit_multiplication_application,
    convert_xor,
)

_T = sp.symbols('t')
_TRANSFORMATIONS = standard_transformations + (implicit_multiplication_application, convert_xor)


class EquationParseError(ValueError):
    """Raised when the path equation or a t-range value can't be parsed."""
    pass


def _split_top_level(s, sep=','):
    """Splits `s` on `sep`, but only at paren-depth 0 (so the commas inside
    function calls like cos(t) don't get treated as component separators)."""
    parts = []
    depth = 0
    current = ''
    for ch in s:
        if ch == '(':
            depth += 1
        elif ch == ')':
            depth -= 1
        if ch == sep and depth == 0:
            parts.append(current)
            current = ''
        else:
            current += ch
    parts.append(current)
    return parts


def parse_vector_equation(text):
    """
    Parses a string like "(10, 10cos(t), 10sin(t))" into three numeric
    callables x(t), y(t), z(t).

    Implicit multiplication ("10cos(t)" -> "10*cos(t)") and standard math
    functions/constants (sin, cos, tan, sqrt, pi, e, ...) are supported
    via sympy's parser.

    Returns:
        ((x_fn, y_fn, z_fn), (x_expr, y_expr, z_expr))
    """
    stripped = text.strip()
    if stripped.startswith('(') and stripped.endswith(')'):
        inner = stripped[1:-1]
    else:
        inner = stripped

    components = _split_top_level(inner)
    if len(components) != 3:
        raise EquationParseError(
            f"Expected 3 comma-separated components like (x, y, z), got "
            f"{len(components)} in: {text}"
        )

    exprs = []
    for comp in components:
        comp = comp.strip()
        if not comp:
            raise EquationParseError(f"Empty component in: {text}")
        try:
            expr = parse_expr(comp, local_dict={'t': _T}, transformations=_TRANSFORMATIONS)
        except Exception as e:
            raise EquationParseError(f"Could not parse '{comp}': {e}") from e
        exprs.append(expr)

    try:
        funcs = tuple(sp.lambdify(_T, e, modules=['math']) for e in exprs)
    except Exception as e:
        raise EquationParseError(f"Could not build numeric functions from '{text}': {e}") from e

    return funcs, tuple(exprs)


def parse_scalar(text):
    """Parses a single numeric/expression value, e.g. '0', 'pi/2', '-10'."""
    stripped = text.strip()
    try:
        expr = parse_expr(stripped, transformations=_TRANSFORMATIONS)
        return float(expr.evalf())
    except Exception as e:
        raise EquationParseError(f"Could not parse '{text}' as a number/expression: {e}") from e
