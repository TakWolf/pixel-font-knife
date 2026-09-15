from __future__ import annotations

from os import PathLike
from pathlib import Path

from pixel_font_knife.glyph.file import GlyphFile
from pixel_font_knife.glyph.flavor import normalize_flavor


class NamedGlyphFile(GlyphFile):
    @staticmethod
    def load(file_path: str | PathLike[str]) -> NamedGlyphFile:
        if not isinstance(file_path, Path):
            file_path = Path(file_path)

        parts = file_path.stem.split(maxsplit=1)
        glyph_name = parts[0]
        flavors = []
        if len(parts) > 1:
            for flavor in parts[1].split(','):
                flavor = normalize_flavor(flavor)
                if flavor not in flavors:
                    flavors.append(flavor)
        return NamedGlyphFile(file_path, glyph_name, flavors)

    @staticmethod
    def load_notdef(file_path: str | PathLike[str]) -> NamedGlyphFile:
        return NamedGlyphFile(file_path, '.notdef')

    _glyph_name: str
    flavors: list[str]

    def __init__(
            self,
            file_path: str | PathLike[str],
            glyph_name: str,
            flavors: list[str] | None = None,
    ):
        super().__init__(file_path)
        self._glyph_name = glyph_name
        self.flavors = flavors if flavors is not None else []

    @property
    def glyph_name(self) -> str:
        return self._glyph_name

    @glyph_name.setter
    def glyph_name(self, value: str) -> None:
        self._glyph_name = value
