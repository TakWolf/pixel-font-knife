from __future__ import annotations

from collections import UserDict
from copy import copy
from typing import Any

from pixel_font_knife.glyph.common import check_glyph_name_key, check_flavor
from pixel_font_knife.named.file import NamedGlyphFile


class NamedGlyphVariants(UserDict[str | None, NamedGlyphFile]):
    """Map requested flavors to glyph files for one name key.

    ``name_key`` is the unique name key for this variant set. Every contained
    ``NamedGlyphFile.name_key`` must match it; remapping a glyph file to a different
    name key is not allowed. Mapping keys are requested flavors, with ``None`` for
    the default variant. They are independent of ``NamedGlyphFile.flavors`` local
    storage metadata and need not match it. Multiple flavors may reference the
    same glyph file; editing this mapping does not change glyph file attributes.

    ``check()`` rechecks name key consistency after glyph attributes are edited.
    ``select()`` prefers the requested flavor. If it is missing, ``fallback_default``
    controls whether to try the default variant. If no glyph is found,
    ``allow_missing_glyph`` controls whether to return ``None`` or raise an error.
    ``copy()`` copies only the mapping container, retaining the same ``name_key``
    and sharing glyph file objects and canvas caches.
    """

    name_key: str

    def __init__(self, name_key: str) -> None:
        check_glyph_name_key(name_key)
        super().__init__()
        self.name_key = name_key

    def __setitem__(self, flavor: Any, glyph_file: Any) -> None:
        if flavor is not None:
            check_flavor(flavor)

        if not isinstance(glyph_file, NamedGlyphFile):
            raise TypeError(f'illegal value type: {type(glyph_file).__name__!r}')

        if glyph_file.name_key != self.name_key:
            raise ValueError(f'name key mismatch: {self.name_key!r} != {glyph_file.name_key!r}')

        super().__setitem__(flavor, glyph_file)

    def __copy__(self) -> NamedGlyphVariants:
        self.check()

        result = NamedGlyphVariants(self.name_key)
        result.update(self)
        return result

    def check(self) -> None:
        check_glyph_name_key(self.name_key)
        for glyph_file in self.values():
            if glyph_file.name_key != self.name_key:
                raise ValueError(f'name key mismatch: {self.name_key!r} != {glyph_file.name_key!r}')

    def select(
            self,
            flavor: str | None = None,
            fallback_default: bool = True,
            allow_missing_glyph: bool = False,
    ) -> NamedGlyphFile | None:
        if flavor is not None:
            check_flavor(flavor)

        self.check()

        if flavor in self:
            return self[flavor]

        if None in self and fallback_default:
            return self[None]

        if allow_missing_glyph:
            return None

        raise KeyError(f'no flavor file: {flavor!r}')

    def copy(self) -> NamedGlyphVariants:
        return copy(self)
