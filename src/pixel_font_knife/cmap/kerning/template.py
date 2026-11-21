from __future__ import annotations

from collections.abc import Sequence
from os import PathLike
from pathlib import Path

import yaml

from pixel_font_knife.cmap.context import CmapContext
from pixel_font_knife.glyph.common import normalize_flavor_order


class CmapKerningTemplate:
    """Derive glyph kerning from character groups resolved through a cmap context.

    ``groups`` defines left and right glyph groups as lists of characters.
    ``values`` maps group name pairs to requested horizontal offsets.
    ``calculate_kerning_values()`` resolves characters to ``CmapGlyphFile`` objects
    through ``CmapContext``. Only negative presets are processed. For each pair,
    the left bitmap is dilated by one pixel within its canvas, and the requested
    offset is moved toward zero until this mask no longer overlaps the right
    bitmap, or zero is reached. Only negative results are returned, in the
    pixel-font-builder format ``(left_glyph_name, right_glyph_name) -> offset``.

    Kerning is keyed by glyph name, so characters sharing a glyph also share its
    kerning. Use separate glyph entities when kerning must differ across scripts
    or languages. For example, sharing a glyph between Latin A (U+0041) and
    Cyrillic A (U+0410) may cause unintended kerning across scripts. Conflicting
    negative presets for the same glyph name pair raise ``ValueError``.
    """

    @staticmethod
    def load(file_path: str | PathLike[str]) -> CmapKerningTemplate:
        if not isinstance(file_path, Path):
            file_path = Path(file_path)

        data = yaml.safe_load(file_path.read_bytes())

        groups = {}
        for group_name, alphabet in data['groups'].items():
            groups[group_name] = list(alphabet)

        values = {}
        for group_names, offset in data['values'].items():
            group_names = group_names.split(',')
            left_group_name = group_names[0]
            right_group_name = group_names[1]
            values[(left_group_name, right_group_name)] = offset

        return CmapKerningTemplate(groups, values)

    groups: dict[str, list[str]]
    values: dict[tuple[str, str], int]

    def __init__(
            self,
            groups: dict[str, list[str]],
            values: dict[tuple[str, str], int],
    ) -> None:
        self.groups = groups
        self.values = values

    def calculate_kerning_values(
            self,
            context: CmapContext,
            flavor_order: str | Sequence[str | None] | None = None,
            fallback_default: bool = True,
            allow_missing_glyph: bool = False,
    ) -> dict[tuple[str, str], int]:
        flavor_order = normalize_flavor_order(flavor_order)
        if flavor_order is None:
            flavor_order = [None]

        kerning_presets = {}
        kerning_values = {}
        for (left_group_name, right_group_name), offset in self.values.items():
            if offset >= 0:
                continue

            left_group = self.groups[left_group_name]
            right_group = self.groups[right_group_name]

            for flavor in flavor_order:
                for left_c in left_group:
                    left_code_point = ord(left_c)
                    if left_code_point not in context:
                        continue

                    try:
                        left_file = context[left_code_point].select(flavor, fallback_default, allow_missing_glyph)
                    except KeyError as error:
                        raise KeyError(f'left group {left_group_name!r} character {left_c!r}: {error.args[0]}') from error

                    if left_file is None:
                        continue

                    left_bitmap_mask = left_file.canvas.bitmap.dilate(1)

                    for right_c in right_group:
                        right_code_point = ord(right_c)
                        if right_code_point not in context:
                            continue

                        try:
                            right_file = context[right_code_point].select(flavor, fallback_default, allow_missing_glyph)
                        except KeyError as error:
                            raise KeyError(f'right group {right_group_name!r} character {right_c!r}: {error.args[0]}') from error

                        if right_file is None:
                            continue

                        left_glyph_name = left_file.glyph_name
                        right_glyph_name = right_file.glyph_name
                        glyph_name_pair = left_glyph_name, right_glyph_name
                        source = left_group_name, right_group_name, left_c, right_c, flavor

                        if glyph_name_pair in kerning_presets:
                            preset_offset, preset_source = kerning_presets[glyph_name_pair]
                            if preset_offset != offset:
                                preset_left_group, preset_right_group, preset_left_c, preset_right_c, preset_flavor = preset_source
                                raise ValueError(
                                    f'kerning preset mismatch for glyph pair {glyph_name_pair!r}: '
                                    f'{preset_offset} from groups {(preset_left_group, preset_right_group)!r}, '
                                    f'characters {(preset_left_c, preset_right_c)!r}, requested flavor {preset_flavor!r} != '
                                    f'{offset} from groups {(left_group_name, right_group_name)!r}, '
                                    f'characters {(left_c, right_c)!r}, requested flavor {flavor!r}',
                                )
                        else:
                            kerning_presets[glyph_name_pair] = (offset, source)

                            actual_offset = offset
                            while actual_offset < 0:
                                if not left_bitmap_mask.overlaps(right_file.canvas.bitmap, x=left_bitmap_mask.width + actual_offset):
                                    break
                                actual_offset += 1

                            if actual_offset < 0:
                                kerning_values[(left_glyph_name, right_glyph_name)] = actual_offset
        return kerning_values
