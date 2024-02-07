from typing import Optional, TypeVar, Callable

T = TypeVar("T")


def some(arr: list[T], f: Callable[[T], bool]) -> Optional[T]:
    for x in arr:
        if f(x):
            return x
    return None
