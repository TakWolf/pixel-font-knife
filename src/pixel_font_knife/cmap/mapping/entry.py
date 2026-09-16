from __future__ import annotations

from collections import UserDict
from typing import Any

from pixel_font_knife.cmap.mapping.reference import CmapGlyphReference
from pixel_font_knife.glyph.common import check_flavor


class CmapMappingEntry(UserDict[str | None, CmapGlyphReference]):
    def __setitem__(self, flavor: Any, glyph_reference: Any) -> None:
        if flavor is not None and flavor != '*':
            check_flavor(flavor)

        if glyph_reference is None:
            self.pop(flavor, None)
            return

        if not isinstance(glyph_reference, CmapGlyphReference):
            raise ValueError(f'illegal value type: {type(glyph_reference).__name__!r}')

        super().__setitem__(flavor, glyph_reference)
