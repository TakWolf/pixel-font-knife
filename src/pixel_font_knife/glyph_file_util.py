import os
import re
from collections import UserDict
from os import PathLike
from pathlib import Path
from typing import Any

import png
import unidata_blocks

from pixel_font_knife.mono_bitmap import MonoBitmap


class GlyphData:
    @staticmethod
    def load_png(file_path: str | PathLike[str]) -> 'GlyphData':
        width, height, pixels, _ = png.Reader(filename=file_path).read()
        bitmap = MonoBitmap()
        bitmap.width = width
        bitmap.height = height
        mask = MonoBitmap()
        mask.width = width
        mask.height = height
        for pixels_row in pixels:
            bitmap_row = []
            mask_row = []
            for i in range(0, width * 4, 4):
                red = pixels_row[i]
                green = pixels_row[i + 1]
                blue = pixels_row[i + 2]
                alpha = pixels_row[i + 3]
                if red == 255 and green == 0 and blue == 255:
                    bitmap_color = 0
                    mask_color = 1
                elif alpha > 127:
                    bitmap_color = 1
                    mask_color = 0
                else:
                    bitmap_color = 0
                    mask_color = 0
                bitmap_row.append(bitmap_color)
                mask_row.append(mask_color)
            bitmap.append(bitmap_row)
            mask.append(mask_row)
        return GlyphData(bitmap, mask)

    bitmap: MonoBitmap
    mask: MonoBitmap

    def __init__(self, bitmap: MonoBitmap, mask: MonoBitmap):
        self.bitmap = bitmap
        self.mask = mask

    @property
    def width(self) -> int:
        return self.bitmap.width

    @property
    def height(self) -> int:
        return self.bitmap.height

    def save_png(self, file_path: str | PathLike[str]):
        pixels = []
        for bitmap_row, mask_row in zip(self.bitmap, self.mask):
            pixels_row = []
            for bitmap_color, mask_color in zip(bitmap_row, mask_row):
                if bitmap_color != 0:
                    red = 0
                    green = 0
                    blue = 0
                    alpha = 255
                elif mask_color != 0:
                    red = 255
                    green = 0
                    blue = 255
                    alpha = 255
                else:
                    red = 0
                    green = 0
                    blue = 0
                    alpha = 0
                pixels_row.append(red)
                pixels_row.append(green)
                pixels_row.append(blue)
                pixels_row.append(alpha)
            pixels.append(pixels_row)
        return png.from_array(pixels, 'RGBA').save(file_path)


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
    _data: GlyphData | None

    def __init__(self, file_path: Path, code_point: int, flavors: list[str]):
        self.file_path = file_path
        self.code_point = code_point
        self.flavors = flavors
        self._data = None

    @property
    def data(self) -> GlyphData:
        if self._data is None:
            self._data = GlyphData.load_png(self.file_path)
        return self._data

    @property
    def bitmap(self) -> MonoBitmap:
        return self.data.bitmap

    @property
    def mask(self) -> MonoBitmap:
        return self.data.mask

    @property
    def width(self) -> int:
        return self.data.width

    @property
    def height(self) -> int:
        return self.data.height

    @property
    def glyph_name(self) -> str:
        if self.code_point == -1:
            return '.notdef'

        name = f'u{self.code_point:04X}'
        if len(self.flavors) > 0:
            name = f'{name}-{self.flavors[0].upper()}'
        return name

    def save(self):
        self.data.save_png(self.file_path)


class GlyphFlavorGroup(UserDict[str | None, GlyphFile]):
    def __getitem__(self, flavor: Any) -> GlyphFile:
        if isinstance(flavor, str):
            flavor = flavor.lower()
        return super().__getitem__(flavor)

    def __setitem__(self, flavor: Any, glyph_file: Any):
        if glyph_file is None:
            self.pop(flavor, None)
            return

        if isinstance(flavor, str):
            flavor = flavor.lower()
        elif flavor is not None:
            raise KeyError(flavor)

        if not isinstance(glyph_file, GlyphFile):
            raise ValueError(f"illegal value type: '{type(glyph_file).__name__}'")

        super().__setitem__(flavor, glyph_file)

    def __delitem__(self, flavor: Any):
        if isinstance(flavor, str):
            flavor = flavor.lower()
        super().__delitem__(flavor)

    def __contains__(self, flavor: Any) -> bool:
        if isinstance(flavor, str):
            flavor = flavor.lower()
        return super().__contains__(flavor)

    def get_file(self, flavor: str | None = None) -> GlyphFile:
        if flavor in self:
            return self[flavor]
        if None in self:
            return self[None]
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
                flavor_group = GlyphFlavorGroup()
                context[glyph_file.code_point] = flavor_group
            else:
                flavor_group = context[glyph_file.code_point]

            if len(glyph_file.flavors) > 0:
                for flavor in glyph_file.flavors:
                    if flavor in flavor_group:
                        raise RuntimeError(f"flavor {repr(flavor)} already exists:\n'{glyph_file.file_path}'\n'{flavor_group[flavor].file_path}'")
                    flavor_group[flavor] = glyph_file
            else:
                if None in flavor_group:
                    raise RuntimeError(f"default flavor already exists:\n'{glyph_file.file_path}'\n'{flavor_group[None].file_path}'")
                flavor_group[None] = glyph_file
    return context


def normalize_context(
        context: dict[int, GlyphFlavorGroup],
        root_dir: str | PathLike[str],
        flavors_order: list[str] | None = None,
):
    if isinstance(root_dir, str):
        root_dir = Path(root_dir)

    for code_point, flavor_group in context.items():
        if code_point == -1:
            code_name = 'notdef'
            file_dir = root_dir
        else:
            code_name = f'{code_point:04X}'
            block = unidata_blocks.get_block_by_code_point(code_point)
            file_dir = root_dir.joinpath(f'{block.code_start:04X}-{block.code_end:04X} {block.name}')
            if block.name == 'CJK Unified Ideographs':
                file_dir = file_dir.joinpath(f'{code_name[0:-2]}-')

        for glyph_file in set(flavor_group.values()):
            if len(glyph_file.flavors) > 0:
                if flavors_order is None:
                    flavors = sorted(glyph_file.flavors)
                else:
                    flavors = sorted(glyph_file.flavors, key=lambda x: flavors_order.index(x))
                file_name = f'{code_name} {",".join(flavors)}.png'
            else:
                file_name = f'{code_name}.png'
            file_path = file_dir.joinpath(file_name)
            if glyph_file.file_path != file_path:
                if file_path.exists():
                    raise RuntimeError(f"duplicate glyph files:\n'{glyph_file.file_path}'\n'{file_path}'")
                file_dir.mkdir(parents=True, exist_ok=True)
                glyph_file.file_path.rename(file_path)
                glyph_file.file_path = file_path

            glyph_file.save()


def get_character_mapping(context: dict[int, GlyphFlavorGroup], flavor: str | None = None) -> dict[int, str]:
    character_mapping = {}
    for code_point, flavor_group in context.items():
        if code_point < 0:
            continue
        glyph_file = flavor_group.get_file(flavor)
        character_mapping[code_point] = glyph_file.glyph_name
    return character_mapping


def get_glyph_sequence(context: dict[int, GlyphFlavorGroup], flavors: list[str] | None = None) -> list[GlyphFile]:
    if -1 in context:
        flavor_group = context[-1]
        if None not in flavor_group:
            raise ValueError("missing default flavor in '.notdef' group")
        glyph_name = flavor_group[None].glyph_name
        if glyph_name != '.notdef':
            raise ValueError(f"illegal glyph name for '.notdef': {repr(glyph_name)}")

    if flavors is None:
        flavors = [None]
    context = sorted(context.items())

    glyph_sequence = []
    glyph_names = set()
    for flavor in flavors:
        for code_point, flavor_group in context:
            if code_point < -1:
                continue
            if code_point == -1:
                glyph_file = flavor_group[None]
            else:
                glyph_file = flavor_group.get_file(flavor)
            glyph_name = glyph_file.glyph_name
            if glyph_name not in glyph_names:
                glyph_names.add(glyph_name)
                glyph_sequence.append(glyph_file)
    return glyph_sequence
