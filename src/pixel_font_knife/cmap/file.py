from __future__ import annotations

from os import PathLike
from pathlib import Path

from pixel_font_knife.glyph.file import GlyphFile


class CmapGlyphFile(GlyphFile):
    @staticmethod
    def load(file_path: str | PathLike[str]) -> CmapGlyphFile:
        if not isinstance(file_path, Path):
            file_path = Path(file_path)

        parts = file_path.stem.split(maxsplit=1)
        code_point = int(parts[0], 16)
        flavors = []
        if len(parts) > 1:
            for flavor in parts[1].lower().split(','):
                if flavor not in flavors:
                    flavors.append(flavor)
        return CmapGlyphFile(file_path, code_point, flavors)

    code_point: int
    flavors: list[str]

    def __init__(
            self,
            file_path: str | PathLike[str],
            code_point: int,
            flavors: list[str] | None = None,
    ):
        super().__init__(file_path)
        self.code_point = code_point
        self.flavors = flavors if flavors is not None else []

    @property
    def glyph_name(self) -> str:
        name = f'u{self.code_point:04X}'
        if len(self.flavors) > 0:
            name = f'{name}.{self.flavors[0].lower()}'
        return name
