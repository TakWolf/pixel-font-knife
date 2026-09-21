from __future__ import annotations

from collections.abc import Sequence
from os import PathLike
from pathlib import Path

import yaml

from pixel_font_knife.cmap.context import CmapContext
from pixel_font_knife.glyph.common import normalize_flavor_order


class CmapKerningTemplate:
    """通过 cmap 字母表反向推导字形 kerning 的专用工具。

    ``groups`` 使用字符组成的字母表描述左右字形组，``values`` 使用组名对描述期望的水平间距。
    ``calculate_kerning_values()`` 通过 ``CmapContext`` 将字符反向解析为实际 ``CmapGlyphFile``，
    再根据字形位图碰撞结果收缩配置值，最终生成符合 pixel-font-builder 格式的
    ``(left_glyph_name, right_glyph_name) -> offset`` 数据。

    pixel-font-builder 会将顶级 kerning 配置编译到默认脚本和默认语言系统中。通常不应让不同语言或
    不同文字系统的字形参与彼此的 kerning，因此参与 kerning 的字符应尽量避免共享同一个字形实体。
    例如，不应将拉丁字母 A 和西里尔字母 А 映射到同一个字形，否则根据 glyph name 生成的 kerning
    可能跨文字系统生效。
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
                        left_file = context[left_code_point].select(flavor, fallback_default)
                    except KeyError as error:
                        raise KeyError(f'left group {left_group_name!r} character {left_c!r}: {error.args[0]}') from error

                    left_bitmap_mask = left_file.canvas.bitmap.dilate(1)

                    for right_c in right_group:
                        right_code_point = ord(right_c)
                        if right_code_point not in context:
                            continue

                        try:
                            right_file = context[right_code_point].select(flavor, fallback_default)
                        except KeyError as error:
                            raise KeyError(f'right group {right_group_name!r} character {right_c!r}: {error.args[0]}') from error

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
                                    f'characters {(left_c, right_c)!r}, requested flavor {flavor!r}'
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
