from __future__ import annotations

from collections import UserDict
from typing import Any

from pixel_font_knife.cmap.file import CmapGlyphFile
from pixel_font_knife.glyph.common import normalize_flavor


class CmapGlyphVariants(UserDict[str | None, CmapGlyphFile]):
    """同一个上下文码点下按 flavor 选择字形文件的使用映射。

    键是请求时使用的 flavor，``None`` 表示默认变体；键与 ``CmapGlyphFile.flavors`` 的本地存储信息
    相互独立，不要求一致。多个 flavor 可以引用同一个 ``CmapGlyphFile`` 对象，映射修改不会改变
    字形文件属性。

    ``select()`` 优先返回指定 flavor，缺失时回退到默认变体。``copy()`` 只复制映射容器，始终共享
    原有的 ``CmapGlyphFile`` 对象及其画布缓存。
    """

    def __getitem__(self, flavor: Any) -> CmapGlyphFile:
        flavor = normalize_flavor(flavor)
        return super().__getitem__(flavor)

    def __setitem__(self, flavor: Any, glyph_file: Any) -> None:
        flavor = normalize_flavor(flavor)

        if glyph_file is None:
            self.pop(flavor, None)
            return

        if not isinstance(glyph_file, CmapGlyphFile):
            raise ValueError(f'illegal value type: {type(glyph_file).__name__!r}')

        super().__setitem__(flavor, glyph_file)

    def __delitem__(self, flavor: Any) -> None:
        flavor = normalize_flavor(flavor)
        super().__delitem__(flavor)

    def __contains__(self, flavor: Any) -> bool:
        flavor = normalize_flavor(flavor)
        return super().__contains__(flavor)

    def __copy__(self) -> CmapGlyphVariants:
        return self.copy()

    def select(self, flavor: str | None = None) -> CmapGlyphFile:
        if flavor in self:
            return self[flavor]
        if None in self:
            return self[None]
        raise KeyError(f'no flavor file: {flavor!r}')

    def copy(self) -> CmapGlyphVariants:
        return CmapGlyphVariants(self)
