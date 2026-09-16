from collections import UserDict
from typing import Any

from pixel_font_knife.cmap.file import CmapGlyphFile
from pixel_font_knife.glyph.common import normalize_flavor


class CmapGlyphVariants(UserDict[str | None, CmapGlyphFile]):
    def __getitem__(self, flavor: Any) -> CmapGlyphFile:
        flavor = normalize_flavor(flavor)
        return super().__getitem__(flavor)

    def __setitem__(self, flavor: Any, glyph_file: Any) -> None:
        flavor = normalize_flavor(flavor)

        if glyph_file is None:
            self.pop(flavor, None)
            return

        if not isinstance(glyph_file, CmapGlyphFile):
            raise ValueError(f'illegal value type: {type(glyph_file).__name__!r}')

        super().__setitem__(flavor, glyph_file)

    def __delitem__(self, flavor: Any) -> None:
        flavor = normalize_flavor(flavor)
        super().__delitem__(flavor)

    def __contains__(self, flavor: Any) -> bool:
        flavor = normalize_flavor(flavor)
        return super().__contains__(flavor)

    def select(self, flavor: str | None = None) -> CmapGlyphFile:
        if flavor in self:
            return self[flavor]
        if None in self:
            return self[None]
        raise KeyError(f'no flavor file: {flavor!r}')
