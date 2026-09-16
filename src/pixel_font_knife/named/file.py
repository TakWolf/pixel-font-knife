from __future__ import annotations

from os import PathLike
from pathlib import Path

from pixel_font_knife.glyph.common import check_flavors
from pixel_font_knife.glyph.file import GlyphFile


def _check_glyph_name(glyph_name: str) -> None:
    if glyph_name == '':
        raise KeyError('glyph name cannot be empty')

    if any(character.isspace() for character in glyph_name):
        raise KeyError(f'illegal glyph name: {glyph_name!r}')


class NamedGlyphFile(GlyphFile):
    @staticmethod
    def load(file_path: str | PathLike[str]) -> NamedGlyphFile:
        if not isinstance(file_path, Path):
            file_path = Path(file_path)

        glyph_name, separator, flavors_text = file_path.stem.partition(' ')
        flavors = flavors_text.split(',') if separator else []
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
        _check_glyph_name(glyph_name)
        if flavors is not None:
            check_flavors(flavors)

        super().__init__(file_path)
        self._glyph_name = glyph_name
        self.flavors = flavors if flavors is not None else []

    @property
    def glyph_name(self) -> str:
        return self._glyph_name

    @glyph_name.setter
    def glyph_name(self, value: str) -> None:
        _check_glyph_name(value)
        self._glyph_name = value
