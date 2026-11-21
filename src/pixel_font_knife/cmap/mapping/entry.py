from __future__ import annotations

from collections import UserDict
from typing import Any

from pixel_font_knife.cmap.mapping.reference import CmapGlyphReference
from pixel_font_knife.glyph.common import check_flavor


class CmapMappingEntry(UserDict[str | None, CmapGlyphReference]):
    """Map target flavors to concrete glyph references for one target code point.

    ``None`` denotes the default target flavor; ``'*'`` copies the source glyph's
    entire variant set. Wildcard structure is checked when ``CmapMapping`` loads
    or saves data and when ``CmapContext`` applies mappings.
    """

    def __setitem__(self, flavor: Any, glyph_reference: Any) -> None:
        if flavor is not None and flavor != '*':
            check_flavor(flavor)

        if not isinstance(glyph_reference, CmapGlyphReference):
            raise TypeError(f'illegal value type: {type(glyph_reference).__name__!r}')

        super().__setitem__(flavor, glyph_reference)
