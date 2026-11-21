from __future__ import annotations

from collections import UserDict
from copy import copy
from typing import Any

from pixel_font_knife.cmap.file import CmapGlyphFile
from pixel_font_knife.glyph.common import check_flavor


class CmapGlyphVariants(UserDict[str | None, CmapGlyphFile]):
    """Map requested flavors to glyph files for one context code point.

    Keys are requested flavors; ``None`` denotes the default variant. They are
    independent of the local storage metadata in ``CmapGlyphFile.flavors`` and
    need not match it. Multiple flavors may reference the same ``CmapGlyphFile``;
    editing this mapping does not change glyph file attributes.

    ``select()`` prefers the requested flavor. If it is missing, ``fallback_default``
    controls whether to try the default variant. If no glyph is found,
    ``allow_missing_glyph`` controls whether to return ``None`` or raise an error.
    ``copy()`` copies only the mapping container, sharing the original glyph file
    objects and their canvas caches.
    """

    def __setitem__(self, flavor: Any, glyph_file: Any) -> None:
        if flavor is not None:
            check_flavor(flavor)

        if not isinstance(glyph_file, CmapGlyphFile):
            raise TypeError(f'illegal value type: {type(glyph_file).__name__!r}')

        super().__setitem__(flavor, glyph_file)

    def __copy__(self) -> CmapGlyphVariants:
        return CmapGlyphVariants(self)

    def select(
            self,
            flavor: str | None = None,
            fallback_default: bool = True,
            allow_missing_glyph: bool = False,
    ) -> CmapGlyphFile | None:
        if flavor is not None:
            check_flavor(flavor)

        if flavor in self:
            return self[flavor]

        if None in self and fallback_default:
            return self[None]

        if allow_missing_glyph:
            return None

        raise KeyError(f'no flavor file: {flavor!r}')

    def copy(self) -> CmapGlyphVariants:
        return copy(self)
