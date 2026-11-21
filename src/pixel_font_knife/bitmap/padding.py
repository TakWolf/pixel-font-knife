from __future__ import annotations

from copy import copy, deepcopy
from typing import Any


class Padding:
    """Blank pixel counts between bitmap content and the four original canvas edges."""

    left: int
    right: int
    top: int
    bottom: int

    def __init__(
            self,
            left: int = 0,
            right: int = 0,
            top: int = 0,
            bottom: int = 0,
    ) -> None:
        self.left = left
        self.right = right
        self.top = top
        self.bottom = bottom

    def __copy__(self) -> Padding:
        return Padding(
            self.left,
            self.right,
            self.top,
            self.bottom,
        )

    def __deepcopy__(self, memo: dict[int, Any]) -> Padding:
        return copy(self)

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Padding):
            return NotImplemented
        return (self.left == other.left and
                self.right == other.right and
                self.top == other.top and
                self.bottom == other.bottom)

    def copy(self) -> Padding:
        return copy(self)

    def deepcopy(self) -> Padding:
        return deepcopy(self)
