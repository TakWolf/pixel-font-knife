from __future__ import annotations

from collections import UserDict
from typing import Any

from pixel_font_knife.glyph.common import check_flavor
from pixel_font_knife.named.file import NamedGlyphFile


class NamedGlyphVariants(UserDict[str | None, NamedGlyphFile]):
    def __setitem__(self, flavor: Any, glyph_file: Any) -> None:
        if flavor is not None:
            check_flavor(flavor)

        if glyph_file is None:
            self.pop(flavor, None)
            return

        if not isinstance(glyph_file, NamedGlyphFile):
            raise ValueError(f'illegal value type: {type(glyph_file).__name__!r}')

        super().__setitem__(flavor, glyph_file)

    def __copy__(self) -> NamedGlyphVariants:
        return self.copy()

    def select(self, flavor: str | None = None) -> NamedGlyphFile:
        if flavor is not None:
            check_flavor(flavor)

        if flavor in self:
            return self[flavor]

        if None in self:
            return self[None]

        raise KeyError(f'no flavor file: {flavor!r}')

    def copy(self) -> NamedGlyphVariants:
        return NamedGlyphVariants(self)
