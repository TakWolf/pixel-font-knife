from __future__ import annotations

from collections import UserDict
from typing import Any

from pixel_font_knife.cmap.mapping.reference import CmapGlyphReference
from pixel_font_knife.glyph.common import check_flavor


class CmapMappingEntry(UserDict[str | None, CmapGlyphReference]):
    """一个目标码点下，目标 flavor 到实体字形引用的配置映射。

    ``None`` 表示默认目标 flavor，``'*'`` 表示复制源字形的完整变体集合；通配符的结构约束由
    ``CmapMapping`` 的加载、保存和 ``CmapContext`` 的应用入口检查。
    """

    def __setitem__(self, flavor: Any, glyph_reference: Any) -> None:
        if flavor is not None and flavor != '*':
            check_flavor(flavor)

        if not isinstance(glyph_reference, CmapGlyphReference):
            raise TypeError(f'illegal value type: {type(glyph_reference).__name__!r}')

        super().__setitem__(flavor, glyph_reference)
