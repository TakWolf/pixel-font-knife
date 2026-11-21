from __future__ import annotations

import sys
from collections.abc import Sequence
from os import PathLike
from pathlib import Path

import unicodedata2
import unidata_blocks

from pixel_font_knife.glyph.common import check_code_point, check_flavors, normalize_flavor_order
from pixel_font_knife.glyph.file import GlyphFile


class CmapGlyphFile(GlyphFile):
    """Glyph file entity following the cmap PNG naming convention.

    ``code_point`` and ``flavors`` describe glyph identity and local storage, and
    together determine the canonical path. They do not represent usage keys in
    ``CmapContext``. These attributes may be edited while designing assets; call
    ``normalize()`` promptly afterward to move the file to its canonical path.

    The glyph name is derived from the code point and the first flavor only, to
    limit its length within the font. Without flavors, it uses only the code point.
    ``load()`` parses attributes from the filename and validates flavors without
    changing their case or other characters. ``normalize()`` only normalizes the
    local path; it neither updates context mappings nor checks whether the whole
    directory can be reloaded without conflicts.
    """

    @staticmethod
    def get_normalized_dir(
            code_point: int,
            root_dir: str | PathLike[str],
    ) -> Path:
        if not isinstance(root_dir, Path):
            root_dir = Path(root_dir)

        block = unidata_blocks.get_block_by_code_point(code_point)
        if block is not None:
            file_dir = root_dir.joinpath(f'{block.code_start:04X}-{block.code_end:04X} {block.name}')
            if block == unidata_blocks.BLOCK_CJK_UNIFIED_IDEOGRAPHS:
                code_name = f'{code_point:04X}'
                file_dir = file_dir.joinpath(f'{code_name[0:-2]}-')
        else:
            file_dir = root_dir
        return file_dir

    @staticmethod
    def load(file_path: str | PathLike[str]) -> CmapGlyphFile:
        if not isinstance(file_path, Path):
            file_path = Path(file_path)

        if file_path.suffix != '.png':
            raise ValueError(f'illegal glyph file extension: {str(file_path)!r}')

        code_point_text, separator, flavors_text = file_path.stem.partition(' ')
        code_point = int(code_point_text, 16)
        flavors = flavors_text.split(',') if separator else []
        return CmapGlyphFile(file_path, code_point, flavors)

    code_point: int
    flavors: list[str]

    def __init__(
            self,
            file_path: str | PathLike[str],
            code_point: int,
            flavors: list[str] | None = None,
    ):
        check_code_point(code_point)
        if flavors is not None:
            check_flavors(flavors)

        super().__init__(file_path)
        self.code_point = code_point
        self.flavors = flavors if flavors is not None else []

    @property
    def glyph_name(self) -> str:
        name = f'u{self.code_point:04X}'
        if self.flavors:
            name = f'{name}.{self.flavors[0]}'
        return name

    def suggest_advance_width(self) -> int:
        if 0 <= self.code_point <= sys.maxunicode:
            c = chr(self.code_point)
            category = unicodedata2.category(c)
            if category == 'Mn':
                return 0
        return super().suggest_advance_width()

    def normalize(
            self,
            root_dir: str | PathLike[str],
            flavor_order: str | Sequence[str | None] | None = None,
    ) -> None:
        if not self.file_path.exists():
            raise FileNotFoundError(f'missing glyph file:\n{str(self.file_path)!r}')

        check_code_point(self.code_point)
        check_flavors(self.flavors)

        flavor_order = normalize_flavor_order(flavor_order)

        file_dir = CmapGlyphFile.get_normalized_dir(self.code_point, root_dir)

        if self.flavors:
            if flavor_order is None:
                flavors = self.flavors
            else:
                flavors = sorted(self.flavors, key=lambda x: flavor_order.index(x))
            file_name = f'{self.code_point:04X} {",".join(flavors)}.png'
        else:
            file_name = f'{self.code_point:04X}.png'

        file_path = file_dir.joinpath(file_name)
        if self.file_path != file_path:
            if file_path.exists():
                raise FileExistsError(f'duplicate glyph files:\n{str(self.file_path)!r}\n{str(file_path)!r}')
            else:
                file_dir.mkdir(parents=True, exist_ok=True)
                self.file_path.rename(file_path)
                self.file_path = file_path
