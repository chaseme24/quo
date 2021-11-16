"""
Example to show how to print a traceback of an exception
"""
from typing import List, Tuple
from quo import Console

console = Console()


def divide_by(number: float, divisor: float) -> float:
    """Divide any number by zero."""
    # Will throw a ZeroDivisionError if divisor is 0
    result = number / divisor
    return result


def divide_all(divides: List[Tuple[float, float]]) -> None:
    """Do something impossible every day."""

    for number, divisor in divides:
        console.echo(f"dividing {number} by {divisor}")
        try:
            result = divide_by(number, divisor)
        except Exception:
            console.print_exception(extra_lines=8, show_locals=True)
        else:
            console.echo(f" = {result}")


DIVIDES = [
    (1000, 200),
    (10000, 500),
    (1, 0),
    (0, 1000000),
    (3.1427, 2),
    (888, 0),
    (2 ** 32, 2 ** 16),
]

divide_all(DIVIDES)
