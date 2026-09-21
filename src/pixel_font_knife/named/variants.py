from __future__ import annotations

from collections import UserDict
from typing import Any

from pixel_font_knife.glyph.common import check_glyph_name_key, check_flavor
from pixel_font_knife.named.file import NamedGlyphFile


class NamedGlyphVariants(UserDict[str | None, NamedGlyphFile]):
    """同一个 name key 下按 flavor 选择字形文件的使用映射。

    ``name_key`` 是该变体集合唯一对应的名称键，集合中的所有 ``NamedGlyphFile.name_key`` 必须与其
    一致，不允许把字形文件再次映射到其他 name key。映射键是请求时使用的 flavor，``None`` 表示默认
    变体；flavor 键与 ``NamedGlyphFile.flavors`` 的本地存储信息相互独立，不要求一致。多个 flavor
    可以引用同一个 ``NamedGlyphFile`` 对象，映射修改不会改变字形文件属性。

    ``check()`` 用于在字形属性被动态修改后重新检查 name key 一致性。``select()`` 优先返回指定
    flavor，缺失时回退到默认变体。``copy()`` 只复制映射容器，保留相同的 ``name_key``，并始终共享
    原有的 ``NamedGlyphFile`` 对象及其画布缓存。
    """

    name_key: str

    def __init__(self, name_key: str) -> None:
        check_glyph_name_key(name_key)
        super().__init__()
        self.name_key = name_key

    def __setitem__(self, flavor: Any, glyph_file: Any) -> None:
        if flavor is not None:
            check_flavor(flavor)

        if not isinstance(glyph_file, NamedGlyphFile):
            raise TypeError(f'illegal value type: {type(glyph_file).__name__!r}')

        if glyph_file.name_key != self.name_key:
            raise ValueError(f'name key mismatch: {self.name_key!r} != {glyph_file.name_key!r}')

        super().__setitem__(flavor, glyph_file)

    def __copy__(self) -> NamedGlyphVariants:
        return self.copy()

    def check(self) -> None:
        check_glyph_name_key(self.name_key)
        for glyph_file in self.values():
            if glyph_file.name_key != self.name_key:
                raise ValueError(f'name key mismatch: {self.name_key!r} != {glyph_file.name_key!r}')

    def select(
            self,
            flavor: str | None = None,
            fallback_default: bool = True,
    ) -> NamedGlyphFile:
        if flavor is not None:
            check_flavor(flavor)

        self.check()

        if flavor in self:
            return self[flavor]

        if None in self and fallback_default:
            return self[None]

        raise KeyError(f'no flavor file: {flavor!r}')

    def copy(self) -> NamedGlyphVariants:
        self.check()

        result = NamedGlyphVariants(self.name_key)
        result.update(self)
        return result
