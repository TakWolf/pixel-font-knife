from __future__ import annotations

from collections import UserDict
from collections.abc import Collection, Sequence
from io import StringIO
from os import PathLike
from pathlib import Path
from typing import Any

import unicodedata2
import yaml

from pixel_font_knife.cmap.mapping.entry import CmapMappingEntry
from pixel_font_knife.cmap.mapping.reference import CmapGlyphReference
from pixel_font_knife.glyph.common import check_code_point, normalize_allowed_flavors, normalize_flavor_order


def _display_code_point(code_point: int) -> str:
    c = chr(code_point)
    category = unicodedata2.category(c)
    if category.startswith(('L', 'M', 'N', 'P', 'S')):
        return c
    return unicodedata2.name(c, f'0x{code_point:04X}')


class CmapMapping(UserDict[int, CmapMappingEntry]):
    """目标码点到字形引用配置项的声明式映射。

    YAML 中的顶层键是目标码点；每个配置项再按目标 flavor 引用原始 ``CmapContext`` 中的实体字形。
    ``~`` 表示默认 flavor，``"*"`` 表示复制源字形的完整变体集合。加载和保存保持 flavor 大小写，
    并将多个指向同一引用的 flavor 合并为同一个 YAML 键。

    mapping 本身不解析引用关系。应用时所有引用都从调用方提供的原始上下文解析，因此合法配置的文件
    顺序和条目顺序不会影响结果；引用其他 mapping 创建的目标不属于受支持的用法。
    """

    @staticmethod
    def load_yaml(
            file_path: str | PathLike[str],
            allowed_flavors: Collection[str] | None = None,
    ) -> CmapMapping:
        allowed_flavors = normalize_allowed_flavors(allowed_flavors)

        if not isinstance(file_path, Path):
            file_path = Path(file_path)

        mapping = CmapMapping()
        raw_mapping = yaml.safe_load(file_path.read_bytes())
        if raw_mapping is not None:
            for code_point, raw_entry in raw_mapping.items():
                if raw_entry is not None:
                    entry = CmapMappingEntry()
                    if '*' in raw_entry:
                        if len(raw_entry) > 1:
                            raise RuntimeError(f'0x{code_point:04X} wildcard flavor cannot be mixed with explicit flavors')

                        value = raw_entry['*']
                        if not isinstance(value, int):
                            raise RuntimeError(f'0x{code_point:04X} wildcard flavor reference must be a code point')

                        entry['*'] = CmapGlyphReference(value)
                    else:
                        for key, value in raw_entry.items():
                            if key is None:
                                flavors = []
                            else:
                                flavors = key.split(',')

                            if isinstance(value, int):
                                glyph_reference = CmapGlyphReference(value)
                            else:
                                reference_code_point_text, separator, reference_flavor = value.partition(' ')
                                reference_code_point = int(reference_code_point_text, 0)

                                if allowed_flavors is not None and separator and reference_flavor not in allowed_flavors:
                                    raise RuntimeError(f'0x{code_point:04X} -> {key!r}: reference flavor {reference_flavor!r} not allowed')

                                glyph_reference = CmapGlyphReference(reference_code_point, reference_flavor if separator else None)

                            if len(flavors) > 0:
                                for flavor in flavors:
                                    if allowed_flavors is not None and flavor not in allowed_flavors:
                                        raise RuntimeError(f'0x{code_point:04X}: flavor {flavor!r} not allowed')

                                    if flavor in entry:
                                        raise RuntimeError(f'0x{code_point:04X}: duplicate flavor {flavor!r}')

                                    entry[flavor] = glyph_reference
                            else:
                                if None in entry:
                                    raise RuntimeError(f'0x{code_point:04X}: duplicate default flavor')

                                entry[None] = glyph_reference
                    mapping[code_point] = entry
        return mapping

    def __setitem__(self, code_point: Any, entry: Any) -> None:
        check_code_point(code_point)

        if entry is None:
            self.pop(code_point, None)
            return

        if not isinstance(entry, CmapMappingEntry):
            raise TypeError(f'illegal value type: {type(entry).__name__!r}')

        super().__setitem__(code_point, entry)

    def save_yaml(
            self,
            file_path: str | PathLike[str],
            flavor_order: str | Sequence[str | None] | None = None,
    ) -> None:
        flavor_order = normalize_flavor_order(flavor_order)

        buffer = StringIO()

        for code_point, entry in sorted(self.items()):
            buffer.write('\n')
            buffer.write(f'# {_display_code_point(code_point)}\n')
            buffer.write(f'0x{code_point:04X}:\n')

            if '*' in entry:
                if len(entry) > 1:
                    raise RuntimeError(f'0x{code_point:04X}: wildcard flavor cannot be mixed with explicit flavors')

                glyph_reference = entry['*']
                if glyph_reference.flavor is not None:
                    raise RuntimeError(f'0x{code_point:04X}: wildcard flavor reference must be a code point')

                buffer.write(f'  # {_display_code_point(glyph_reference.code_point)}\n')
                buffer.write(f'  "*": 0x{glyph_reference.code_point:04X}\n')
            else:
                pending_references = {}
                for flavor, glyph_reference in entry.items():
                    key = glyph_reference.code_point, glyph_reference.flavor
                    if key in pending_references:
                        flavors = pending_references[key]
                    else:
                        flavors = []
                        pending_references[key] = flavors
                    flavors.append(flavor)

                pending_flavors = []
                default_reference = None
                for (reference_code_point, reference_flavor), flavors in pending_references.items():
                    reference_str = f'0x{reference_code_point:04X}'
                    if reference_flavor is not None:
                        reference_str = f'{reference_str} {reference_flavor}'
                    reference_c = _display_code_point(reference_code_point)

                    if None in flavors:
                        default_reference = reference_str, reference_c
                        continue
                    if flavor_order is None:
                        flavors.sort()
                    else:
                        flavors.sort(key=lambda x: flavor_order.index(x))
                    pending_flavors.append((flavors[0], ','.join(flavors), (reference_str, reference_c)))

                if flavor_order is None:
                    pending_flavors.sort()
                else:
                    pending_flavors.sort(key=lambda x: flavor_order.index(x[0]))

                if default_reference is not None:
                    default_reference_str, default_reference_c = default_reference
                    buffer.write(f'  # {default_reference_c}\n')
                    buffer.write(f'  ~: {default_reference_str}\n')
                for _, flavors_text, (reference_str, reference_c) in pending_flavors:
                    buffer.write(f'  # {reference_c}\n')
                    buffer.write(f'  {flavors_text}: {reference_str}\n')

        if not isinstance(file_path, Path):
            file_path = Path(file_path)
        file_path.write_text(buffer.getvalue(), 'utf-8')
