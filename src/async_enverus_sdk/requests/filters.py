"""Filter DSL matching the Enverus API filtering reference.

All functions return filter expression strings that can be passed as query
parameter values. They are composable: ``not_(in_("A", "B"))`` → ``"not(in(A,B))"``.
"""

from __future__ import annotations

from typing import Any


def eq(value: Any) -> str:
    """Equal to: ``eq(value)``."""
    return f"eq({value})"


def ne(value: Any) -> str:
    """Not equal to: ``ne(value)``."""
    return f"ne({value})"


def lt(value: Any) -> str:
    """Less than: ``lt(value)``."""
    return f"lt({value})"


def le(value: Any) -> str:
    """Less than or equal to: ``le(value)``."""
    return f"le({value})"


def gt(value: Any) -> str:
    """Greater than: ``gt(value)``."""
    return f"gt({value})"


def ge(value: Any) -> str:
    """Greater than or equal to: ``ge(value)``."""
    return f"ge({value})"


def in_(*values: Any) -> str:
    """In set: ``in(v1,v2,...)``."""
    return "in({})".format(",".join(str(v) for v in values))


def btw(low: Any, high: Any) -> str:
    """Between (inclusive): ``btw(low,high)``."""
    return f"btw({low},{high})"


def nil() -> str:
    """Is null: ``nil``."""
    return "nil"


def not_(expr: str) -> str:
    """Negate an expression: ``not(expr)``."""
    return f"not({expr})"
