from __future__ import annotations

from os import PathLike
from pathlib import Path

import yaml

from pixel_font_knife.glyph_file_util import GlyphFlavorGroup


class KerningConfig:
    @staticmethod
    def load(file_path: str | PathLike[str]) -> KerningConfig:
        if isinstance(file_path, str):
            file_path = Path(file_path)

        data = yaml.safe_load(file_path.read_bytes())

        groups = {}
        for group_name, alphabet in data['groups'].items():
            groups[group_name] = list(alphabet)

        templates = {}
        for group_names, offset in data['templates'].items():
            group_names = group_names.split(',')
            left_group_name = group_names[0]
            right_group_name = group_names[1]
            templates[(left_group_name, right_group_name)] = offset

        return KerningConfig(
            groups,
            templates,
        )

    groups: dict[str, list[str]]
    templates: dict[tuple[str, str], int]

    def __init__(
            self,
            groups: dict[str, list[str]],
            templates: dict[tuple[str, str], int],
    ):
        self.groups = groups
        self.templates = templates


def calculate_kerning_values(
        kerning_config: KerningConfig,
        context: dict[int, GlyphFlavorGroup],
) -> dict[tuple[str, str], int]:
    kerning_values = {}
    for (left_group_name, right_group_name), offset in kerning_config.templates.items():
        if offset >= 0:
            continue

        left_group = kerning_config.groups[left_group_name]
        right_group = kerning_config.groups[right_group_name]

        for left_c in left_group:
            left_code_point = ord(left_c)
            if left_code_point not in context:
                continue
            left_file = context[left_code_point].get_file()
            left_bitmap_mask = left_file.bitmap.pixel_expand(1)

            for right_c in right_group:
                right_code_point = ord(right_c)
                if right_code_point not in context:
                    continue
                right_file = context[right_code_point].get_file()

                actual_offset = offset
                while actual_offset < 0:
                    if not left_bitmap_mask.is_overlapped(right_file.bitmap, x=left_bitmap_mask.width + actual_offset):
                        break
                    actual_offset += 1

                if actual_offset < 0:
                    kerning_values[(left_file.glyph_name, right_file.glyph_name)] = actual_offset
    return kerning_values
