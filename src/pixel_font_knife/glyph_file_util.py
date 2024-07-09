import os
import re
from collections import UserDict
from os import PathLike
from pathlib import Path

from pixel_font_knife.mono_bitmap import MonoBitmap


class GlyphFile:
    @staticmethod
    def load(file_path: Path) -> 'GlyphFile':
        if file_path.suffix != '.png':
            raise ValueError(f"not '.png' file: '{file_path}'")

        tokens = re.split(r'\s+', file_path.stem.strip(), 1)
        if tokens[0] == 'notdef':
            if len(tokens) > 1:
                raise ValueError(f"'notdef' can't have flavors: '{file_path}'")
            return GlyphFile(file_path, -1, [])

        code_point = int(tokens[0], 16)
        flavors = []
        if len(tokens) > 1:
            for flavor in tokens[1].lower().split(','):
                if flavor not in flavors:
                    flavors.append(flavor)
        return GlyphFile(file_path, code_point, flavors)

    file_path: Path
    code_point: int
    flavors: list[str]
    _bitmap: MonoBitmap | None

    def __init__(self, file_path: Path, code_point: int, flavors: list[str]):
        self.file_path = file_path
        self.code_point = code_point
        self.flavors = flavors
        self._bitmap = None

    @property
    def bitmap(self) -> MonoBitmap:
        if self._bitmap is None:
            self._bitmap = MonoBitmap.load_png(self.file_path)
        return self._bitmap

    @property
    def width(self) -> int:
        return self.bitmap.width

    @property
    def height(self) -> int:
        return self.bitmap.height

    @property
    def glyph_name(self) -> str:
        if self.code_point == -1:
            return '.notdef'

        name = f'{self.code_point:04X}'
        if len(self.flavors) > 0:
            name = f'{name}-{self.flavors[0].upper()}'
        return name


class GlyphFlavorGroup(UserDict[str, GlyphFile]):
    code_point: int

    def __init__(self, code_point: int):
        super().__init__()
        self.code_point = code_point

    def add_file(self, glyph_file: GlyphFile):
        if glyph_file.code_point != self.code_point:
            raise ValueError(f"'code_point' unequal: 0x{glyph_file.code_point} -> 0x{self.code_point}")

        if len(glyph_file.flavors) > 0:
            for flavor in glyph_file.flavors:
                if flavor in self:
                    raise RuntimeError(f"Flavor '{flavor}' already exists: '{glyph_file.file_path}' -> '{self[flavor].file_path}'")
                self[flavor] = glyph_file
        else:
            if '' in self:
                raise RuntimeError(f"Default flavor already exists: '{glyph_file.file_path}' -> '{self[''].file_path}'")
            self[''] = glyph_file

    def get_file(
            self,
            flavor: str = '',
            fallback_default: bool = False,
            allow_none: bool = False,
    ) -> GlyphFile | None:
        if flavor in self:
            return self[flavor]
        if flavor != '' and fallback_default and '' in self:
            return self['']
        if allow_none:
            return None
        raise KeyError(flavor)


def load_context(root_dir: str | PathLike[str]) -> dict[int, GlyphFlavorGroup]:
    if isinstance(root_dir, str):
        root_dir = Path(root_dir)

    context = {}
    for file_dir, _, file_names in os.walk(root_dir):
        file_dir = Path(file_dir)
        for file_name in file_names:
            if not file_name.endswith('.png'):
                continue
            file_path = file_dir.joinpath(file_name)
            glyph_file = GlyphFile.load(file_path)

            if glyph_file.code_point not in context:
                flavor_group = GlyphFlavorGroup(glyph_file.code_point)
                context[glyph_file.code_point] = flavor_group
            else:
                flavor_group = context[glyph_file.code_point]
            flavor_group.add_file(glyph_file)
    return context
