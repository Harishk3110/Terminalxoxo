"""Bounded Decimal inputs and explicit display rounding."""

from __future__ import annotations

from decimal import ROUND_HALF_EVEN, Decimal, InvalidOperation, localcontext

ZERO = Decimal("0")
ONE = Decimal("1")
MAX_AMOUNT = Decimal("1e16")


def decimal(
    value: object,
    name: str = "amount",
    *,
    positive: bool = False,
    nonnegative: bool = False,
) -> Decimal:
    try:
        number = Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError) as exc:
        raise ValueError(f"{name} must be numeric") from exc
    if not number.is_finite() or abs(number) > MAX_AMOUNT:
        raise ValueError(f"{name} must be finite and within accounting bounds")
    if (positive and number <= ZERO) or (nonnegative and number < ZERO):
        constraint = "positive" if positive else "non-negative"
        raise ValueError(f"{name} must be {constraint}")
    return number


def money(value: Decimal, places: int = 2) -> Decimal:
    if not 0 <= places <= 12:
        raise ValueError("Money rounding places must be between zero and twelve")
    if not value.is_finite():
        raise ValueError("Cannot round a non-finite monetary value")
    with localcontext() as context:
        context.prec = max(34, len(value.as_tuple().digits) + places + 2)
        rounded = value.quantize(ONE.scaleb(-places), rounding=ROUND_HALF_EVEN)
    return abs(rounded) if rounded == ZERO else rounded


def allocate(total: Decimal, weights: list[Decimal]) -> list[Decimal]:
    """Allocate exactly; place division residual on the final positive weight."""
    if any(not weight.is_finite() or weight < ZERO for weight in weights):
        raise ValueError("Allocation weights must be finite and non-negative")
    denominator = sum(weights, ZERO)
    if denominator <= ZERO:
        raise ValueError("Allocation requires a positive total weight")
    if not total.is_finite():
        raise ValueError("Allocation total must be finite")
    result = [ZERO for _ in weights]
    remainder = total
    positive = [index for index, weight in enumerate(weights) if weight > ZERO]
    for index in positive[:-1]:
        result[index] = total * weights[index] / denominator
        remainder -= result[index]
    result[positive[-1]] = remainder
    return result
