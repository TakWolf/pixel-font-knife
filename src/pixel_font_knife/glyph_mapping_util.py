import re
from collections import UserDict
from io import StringIO
from os import PathLike
from pathlib import Path
from typing import Any

import yaml

from pixel_font_knife.glyph_file_util import GlyphFlavorGroup


class SourceGlyph:
    code_point: int
    flavor: str | None

    def __init__(self, code_point: int, flavor: str | None):
        self.code_point = code_point
        self.flavor = flavor

    def __str__(self) -> str:
        if self.flavor is None:
            return f'0x{self.code_point:04X}'
        else:
            return f'0x{self.code_point:04X} {self.flavor}'


class SourceFlavorGroup(UserDict[str | None, SourceGlyph]):
    def __contains__(self, flavor: Any) -> bool:
        if isinstance(flavor, str):
            flavor = flavor.lower()
        return super().__contains__(flavor)

    def __getitem__(self, flavor: Any) -> SourceGlyph:
        if isinstance(flavor, str):
            flavor = flavor.lower()
        return super().__getitem__(flavor)

    def __setitem__(self, flavor: Any, source_glyph: Any):
        if isinstance(flavor, str):
            flavor = flavor.lower()
        elif flavor is not None:
            raise KeyError(flavor)

        if source_glyph is None:
            self.pop(flavor, None)
            return

        if not isinstance(source_glyph, SourceGlyph):
            raise ValueError(f"illegal value type: '{type(source_glyph).__name__}'")

        super().__setitem__(flavor, source_glyph)

    def get_source(self, flavor: str | None = None) -> SourceGlyph:
        if flavor in self:
            return self[flavor]
        if None in self:
            return self[None]
        raise KeyError(flavor)


def load_mapping(file_path: str | PathLike[str]) -> dict[int, SourceFlavorGroup]:
    if isinstance(file_path, str):
        file_path = Path(file_path)

    mapping = {}
    raw_mapping = yaml.safe_load(file_path.read_bytes())
    if raw_mapping is not None:
        for code_point, raw_source_group in raw_mapping.items():
            if raw_source_group is not None:
                source_group = SourceFlavorGroup()
                for key, value in raw_source_group.items():
                    if key is None:
                        flavors = []
                    else:
                        flavors = key.lower().split(',')
                    if isinstance(value, int):
                        source_glyph = SourceGlyph(value, None)
                    else:
                        tokens = re.split(r'\s+', value, 1)
                        source_glyph = SourceGlyph(int(tokens[0], 0), tokens[1].lower())

                    if len(flavors) > 0:
                        for flavor in flavors:
                            if flavor in source_group:
                                raise RuntimeError(f'0x{code_point:04X} duplicate flavor {repr(flavor)}')
                            source_group[flavor] = source_glyph
                    else:
                        if None in source_group:
                            raise RuntimeError(f'0x{code_point:04X} duplicate default flavor')
                        source_group[None] = source_glyph
                mapping[code_point] = source_group
    return mapping


def save_mapping(
        mapping: dict[int, SourceFlavorGroup],
        file_path: str | PathLike[str],
        flavors_order: list[str] | None = None,
):
    buffer = StringIO()
    for code_point, source_group in sorted(mapping.items()):
        buffer.write('\n')
        c = chr(code_point)
        if c.isprintable():
            buffer.write(f'# {c}\n')
        else:
            buffer.write(f'# 0x{code_point:04X}\n')
        buffer.write(f'0x{code_point:04X}:\n')

        source_pending = {}
        for flavor, source_glyph in source_group.items():
            source_str = str(source_glyph)
            if source_str in source_pending:
                flavors = source_pending[source_str]
            else:
                flavors = []
                source_pending[source_str] = flavors
            flavors.append(flavor)

        flavor_pending = []
        default_source_str = None
        for source_str, flavors in source_pending.items():
            if None in flavors:
                default_source_str = source_str
                continue
            if flavors_order is None:
                flavors.sort()
            else:
                flavors.sort(key=lambda x: flavors_order.index(x))
            flavor_pending.append((flavors[0], ','.join(flavors), source_str))
        if flavors_order is None:
            flavor_pending.sort()
        else:
            flavor_pending.sort(key=lambda x: flavors_order.index(x[0]))

        if default_source_str is not None:
            buffer.write(f'  ~: {default_source_str}\n')
        for _, flavors_str, source_str in flavor_pending:
            buffer.write(f'  {flavors_str}: {source_str}\n')

    if isinstance(file_path, str):
        file_path = Path(file_path)
    file_path.write_text(buffer.getvalue(), 'utf-8')


def apply_mapping(context: dict[int, GlyphFlavorGroup], mapping: dict[int, SourceFlavorGroup]):
    context_patch = {}
    for code_point, source_group in mapping.items():
        if len(source_group) == 0:
            continue
        flavor_group = context_patch.get(code_point, None)
        for flavor, source_glyph in source_group.items():
            if source_glyph.code_point not in context:
                continue
            if flavor_group is None:
                flavor_group = GlyphFlavorGroup()
                context_patch[code_point] = flavor_group
            flavor_group[flavor] = context[source_glyph.code_point].get_file(source_glyph.flavor)

    for code_point, flavor_group in context_patch.items():
        if code_point in context:
            context[code_point].update(flavor_group)
        else:
            context[code_point] = flavor_group
