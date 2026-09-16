from __future__ import annotations

from collections.abc import Sequence
from os import PathLike
from pathlib import Path

from pixel_font_knife.glyph.common import check_glyph_name_key, check_flavors
from pixel_font_knife.glyph.file import GlyphFile


class NamedGlyphFile(GlyphFile):
    @staticmethod
    def load(file_path: str | PathLike[str]) -> NamedGlyphFile:
        if not isinstance(file_path, Path):
            file_path = Path(file_path)

        name_key, separator, flavors_text = file_path.stem.partition(' ')
        flavors = flavors_text.split(',') if separator else []
        return NamedGlyphFile(file_path, name_key, flavors)

    @staticmethod
    def load_notdef(file_path: str | PathLike[str]) -> NamedGlyphFile:
        return NamedGlyphFile(file_path, '.notdef')

    name_key: str
    flavors: list[str]

    def __init__(
            self,
            file_path: str | PathLike[str],
            name_key: str,
            flavors: list[str] | None = None,
    ):
        check_glyph_name_key(name_key)
        if flavors is not None:
            check_flavors(flavors)

        super().__init__(file_path)
        self.name_key = name_key
        self.flavors = flavors if flavors is not None else []

    @property
    def glyph_name(self) -> str:
        name = self.name_key
        if len(self.flavors) > 0:
            name = f'{name}.{self.flavors[0]}'
        return name

    def normalize(self, flavor_order: Sequence[str] | None = None) -> None:
        if not self.file_path.exists():
            raise RuntimeError(f"missing glyph file:\n'{self.file_path}'")

        check_glyph_name_key(self.name_key)
        check_flavors(self.flavors)

        if len(self.flavors) > 0:
            if flavor_order is None:
                flavors = self.flavors
            else:
                flavors = sorted(self.flavors, key=lambda x: flavor_order.index(x))
            file_name = f'{self.name_key} {",".join(flavors)}.png'
        else:
            file_name = f'{self.name_key}.png'

        if self.file_path.name != file_name:
            file_path = self.file_path.with_name(file_name)
            if file_path.exists():
                raise RuntimeError(f"duplicate glyph files:\n'{self.file_path}'\n'{file_path}'")
            else:
                self.file_path.rename(file_path)
                self.file_path = file_path
