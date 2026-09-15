from __future__ import annotations

import shutil
from collections import UserDict
from os import PathLike
from pathlib import Path
from typing import Any

from pixel_font_knife.cmap.file import CmapGlyphFile
from pixel_font_knife.cmap.variants import CmapGlyphVariants
from pixel_font_knife.utils import fs_util


class CmapContext(UserDict[int, CmapGlyphVariants]):
    @staticmethod
    def load(root_dir: str | PathLike[str]) -> CmapContext:
        if not isinstance(root_dir, Path):
            root_dir = Path(root_dir)

        context = CmapContext()
        for file_dir, _, file_names in root_dir.walk():
            for file_name in file_names:
                if not file_name.endswith('.png'):
                    continue

                file_path = file_dir.joinpath(file_name)
                glyph_file = CmapGlyphFile.load(file_path)

                if glyph_file.code_point not in context:
                    glyph_variants = CmapGlyphVariants()
                    context[glyph_file.code_point] = glyph_variants
                else:
                    glyph_variants = context[glyph_file.code_point]

                if len(glyph_file.flavors) > 0:
                    for flavor in glyph_file.flavors:
                        if flavor in glyph_variants:
                            raise RuntimeError(f"flavor {flavor!r} already exists:\n'{file_path}'\n'{glyph_variants[flavor].file_path}'")
                        glyph_variants[flavor] = glyph_file
                else:
                    if None in glyph_variants:
                        raise RuntimeError(f"default flavor already exists:\n'{file_path}'\n'{glyph_variants[None].file_path}'")
                    glyph_variants[None] = glyph_file
        return context

    def __setitem__(self, code_point: Any, glyph_variants: Any) -> None:
        if not isinstance(code_point, int):
            raise KeyError(f'illegal code point type: {type(code_point).__name__!r}')

        if code_point < 0:
            raise KeyError(f'illegal code point: {code_point}')

        if not isinstance(glyph_variants, CmapGlyphVariants):
            raise ValueError(f'illegal value type: {type(glyph_variants).__name__!r}')

        super().__setitem__(code_point, glyph_variants)

    def normalize(
            self,
            root_dir: str | PathLike[str],
            flavor_order: list[str] | None = None,
    ) -> None:
        if not isinstance(root_dir, Path):
            root_dir = Path(root_dir)

        for glyph_variants in self.values():
            for glyph_file in glyph_variants.values():
                glyph_file.normalize(root_dir, flavor_order)

        for file_dir, _, _ in root_dir.walk(top_down=False):
            if fs_util.is_empty_dir(file_dir):
                shutil.rmtree(file_dir)

    def get_glyph_sequence(self, flavor_order: list[str | None] | None = None) -> list[CmapGlyphFile]:
        if flavor_order is None:
            flavor_order = [None]

        context = sorted(self.items())

        sequence = []
        glyph_names = set()
        for flavor in flavor_order:
            for code_point, glyph_variants in context:
                glyph_file = glyph_variants.select(flavor)
                glyph_name = glyph_file.glyph_name
                if glyph_name not in glyph_names:
                    glyph_names.add(glyph_name)
                    sequence.append(glyph_file)
        return sequence

    def get_character_mapping(self, flavor: str | None = None) -> dict[int, str]:
        character_mapping = {}
        for code_point, glyph_variants in self.items():
            glyph_file = glyph_variants.select(flavor)
            character_mapping[code_point] = glyph_file.glyph_name
        return character_mapping
