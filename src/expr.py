"""Evaluate visible_if expressions against raw JSON values."""
from __future__ import annotations

import re

_COMPARISON_RE = re.compile(r"^(.+?)(==|!=|>=|<=|>|<)(.+)$")


def _parse_value(raw: str, values: dict):
    """Resolve a value: field reference, boolean, number, or quoted string."""
    s = raw.strip()
    if s in ("true", "True"):
        return True
    if s in ("false", "False"):
        return False
    if s.startswith('"') and s.endswith('"'):
        return s[1:-1]
    if s.startswith("'") and s.endswith("'"):
        return s[1:-1]
    try:
        return int(s)
    except ValueError:
        pass
    try:
        return float(s)
    except ValueError:
        pass
    # Field reference -- look up in raw values
    return values.get(s, s)


def _eval_comparison(expr: str, values: dict) -> bool:
    """Evaluate a single comparison: field op value."""
    m = _COMPARISON_RE.match(expr.strip())
    if not m:
        # Bare field reference -- truthy check
        val = values.get(expr.strip())
        return bool(val)
    left_raw, op, right_raw = m.group(1), m.group(2), m.group(3)
    left = _parse_value(left_raw, values)
    right = _parse_value(right_raw, values)
    if op == "==":
        return left == right
    if op == "!=":
        return left != right
    # Numeric comparisons -- coerce to float
    try:
        lf, rf = float(left), float(right)
    except (ValueError, TypeError):
        return False
    if op == ">":
        return lf > rf
    if op == "<":
        return lf < rf
    if op == ">=":
        return lf >= rf
    if op == "<=":
        return lf <= rf
    return False


def evaluate(expr: str, values: dict) -> bool:
    """Evaluate a visible_if expression. Supports ==, !=, >, <, >=, <=, &&, ||."""
    # Split on || first (lowest precedence)
    or_groups = expr.split("||")
    for or_group in or_groups:
        # Split on && (higher precedence)
        and_parts = or_group.split("&&")
        if all(_eval_comparison(part, values) for part in and_parts):
            return True
    return False
