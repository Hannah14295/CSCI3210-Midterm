"""Pure text comparisons: no browser-supplied percentages or scores."""
from decimal import Decimal, ROUND_HALF_UP


def calculate_wpm(correct_characters, elapsed_seconds):
    elapsed = Decimal(str(elapsed_seconds))
    if elapsed <= 0:
        return Decimal("0.00")
    return (Decimal(correct_characters) * 12 / elapsed).quantize(
        Decimal("0.01"), rounding=ROUND_HALF_UP,
    )


def typing_metrics(target, typed):
    prefix = 0
    for expected, actual in zip(target, typed):
        if expected != actual:
            break
        prefix += 1
    correct = sum(expected == actual for expected, actual in zip(target, typed))
    return {
        "typed_characters": len(typed),
        "correct_characters": correct,
        "correct_prefix": prefix,
        "progress": round(len(typed) / len(target) * 100, 2) if target else 0,
        "accuracy": round(correct / len(typed) * 100, 2) if typed else 100,
        "complete": bool(target) and len(typed) == len(target),
    }


def text_difference(previous, current):
    """One suffix replacement represents insertion, deletion, or correction."""
    start = 0
    for before, after in zip(previous, current):
        if before != after:
            break
        start += 1
    return {
        "start": start,
        "delete_count": len(previous) - start,
        "insert": current[start:],
    }
