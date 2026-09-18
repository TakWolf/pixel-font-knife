from __future__ import annotations

from collections import UserDict
from collections.abc import Collection, Sequence
from os import PathLike
from pathlib import Path
from typing import Any

from pixel_font_knife.glyph.common import MergeConflictStrategy, check_merge_conflict_strategy, check_glyph_name_key, normalize_allowed_flavors, normalize_flavor_order
from pixel_font_knife.named.file import NamedGlyphFile
from pixel_font_knife.named.variants import NamedGlyphVariants


class NamedContext(UserDict[str, NamedGlyphVariants]):
    """固定名称字形文件的使用映射上下文。

    数据结构为 ``name_key -> flavor -> NamedGlyphFile``。上下文的 name key、变体集合的 name key
    与集合内所有 ``NamedGlyphFile.name_key`` 必须一致，不允许将字形文件再次映射到其他 name key。
    flavor 键是构建时的使用映射，与 ``NamedGlyphFile.flavors`` 的本地存储信息相互独立，不要求
    保持一致；同一个字形文件仍可被同一 name key 下的多个 flavor 引用。

    ``load()`` 根据本地文件名建立初始使用映射，并确保同一 name key 下的每个 flavor 只对应一个文件。
    字形文件的 flavors 允许在素材设计阶段修改，修改后应立即调用 ``normalize()`` 规范文件名；若需
    修改 name key，则必须先将字形文件脱离原变体集合，再按新的 name key 建立映射。``normalize()``
    不会重建或改变当前使用映射，也不保证规范化后的目录能够再次无冲突地加载。

    ``check()`` 用于在字形属性被动态修改后重新检查 name key 一致性。``copy()`` 和合并操作只复制
    ``NamedContext`` 与 ``NamedGlyphVariants`` 容器，始终共享原有的 ``NamedGlyphFile`` 对象及其
    画布缓存。按 name key 合并时以整组变体为单位处理冲突；按 flavor
    合并时只处理同一 name key 下发生冲突的 flavor。对合并结果中字形文件属性的修改，会被所有共享
    该对象的上下文观察到。

    ``get_glyph_sequence()`` 按 name key 顺序和 flavor 顺序生成字形序列，并按 glyph name 保留首次
    出现的字形，以满足固定名称字形的构建排序约定。``.notdef`` 不属于该上下文，应作为独立的
    ``NamedGlyphFile`` 实体加载。
    """

    @staticmethod
    def load(
            root_dir: str | PathLike[str],
            allowed_flavors: Collection[str] | None = None,
    ) -> NamedContext:
        allowed_flavors = normalize_allowed_flavors(allowed_flavors)

        if not isinstance(root_dir, Path):
            root_dir = Path(root_dir)

        context = NamedContext()
        for file_dir, _, file_names in root_dir.walk():
            for file_name in file_names:
                if not file_name.endswith('.png'):
                    continue

                file_path = file_dir.joinpath(file_name)
                glyph_file = NamedGlyphFile.load(file_path)

                if glyph_file.name_key not in context:
                    glyph_variants = NamedGlyphVariants(glyph_file.name_key)
                    context[glyph_file.name_key] = glyph_variants
                else:
                    glyph_variants = context[glyph_file.name_key]

                if len(glyph_file.flavors) > 0:
                    for flavor in glyph_file.flavors:
                        if allowed_flavors is not None and flavor not in allowed_flavors:
                            raise RuntimeError(f"flavor {flavor!r} not allowed:\n'{file_path}'")

                        if flavor in glyph_variants:
                            raise RuntimeError(f"flavor {flavor!r} already exists:\n'{file_path}'\n'{glyph_variants[flavor].file_path}'")

                        glyph_variants[flavor] = glyph_file
                else:
                    if None in glyph_variants:
                        raise RuntimeError(f"default flavor already exists:\n'{file_path}'\n'{glyph_variants[None].file_path}'")

                    glyph_variants[None] = glyph_file
        return context

    def __setitem__(self, name_key: Any, glyph_variants: Any) -> None:
        check_glyph_name_key(name_key)

        if glyph_variants is None:
            self.pop(name_key, None)
            return

        if not isinstance(glyph_variants, NamedGlyphVariants):
            raise ValueError(f'illegal value type: {type(glyph_variants).__name__!r}')

        if glyph_variants.name_key != name_key:
            raise ValueError(f'name key mismatch: {name_key!r} != {glyph_variants.name_key!r}')

        glyph_variants.check()

        super().__setitem__(name_key, glyph_variants)

    def __copy__(self) -> NamedContext:
        return self.copy()

    def check(self) -> None:
        for name_key, glyph_variants in self.items():
            if glyph_variants.name_key != name_key:
                raise ValueError(f'name key mismatch: {name_key!r} != {glyph_variants.name_key!r}')
            glyph_variants.check()

    def normalize(self, flavor_order: Sequence[str | None] | None = None) -> None:
        self.check()

        flavor_order = normalize_flavor_order(flavor_order)

        for glyph_variants in self.values():
            for glyph_file in glyph_variants.values():
                glyph_file.normalize(flavor_order)

    def merge_by_name_key(
            self,
            *contexts: NamedContext,
            conflict: MergeConflictStrategy = 'error',
    ) -> NamedContext:
        check_merge_conflict_strategy(conflict)

        result = self.copy()
        for context in contexts:
            context.check()
            for name_key, glyph_variants in context.items():
                if name_key not in result:
                    result[name_key] = glyph_variants.copy()
                    continue

                match conflict:
                    case 'keep':
                        pass
                    case 'replace':
                        result[name_key] = glyph_variants.copy()
                    case _:
                        raise RuntimeError(f'duplicate name key: {name_key!r}')
        return result

    def merge_by_flavor(
            self,
            *contexts: NamedContext,
            conflict: MergeConflictStrategy = 'error',
    ) -> NamedContext:
        check_merge_conflict_strategy(conflict)

        result = self.copy()
        for context in contexts:
            context.check()
            for name_key, source_variants in context.items():
                if name_key not in result:
                    result[name_key] = source_variants.copy()
                    continue

                target_variants = result[name_key]

                for flavor, glyph_file in source_variants.items():
                    if flavor not in target_variants:
                        target_variants[flavor] = glyph_file
                        continue

                    match conflict:
                        case 'keep':
                            pass
                        case 'replace':
                            target_variants[flavor] = glyph_file
                        case _:
                            raise RuntimeError(f'duplicate flavor: {name_key!r} {flavor!r}')
        return result

    def with_default_flavor(self, flavor_order: Sequence[str | None] | None = None) -> NamedContext:
        flavor_order = normalize_flavor_order(flavor_order)

        result = self.copy()
        for name_key, glyph_variants in result.items():
            if None not in glyph_variants:
                if len(glyph_variants) == 0:
                    raise RuntimeError(f'empty glyph variants: {name_key!r}')

                if flavor_order is None:
                    for flavor in glyph_variants.keys():
                        glyph_variants[None] = glyph_variants[flavor]
                        break
                else:
                    for flavor in flavor_order:
                        if flavor in glyph_variants:
                            glyph_variants[None] = glyph_variants[flavor]
                            break
                    if None not in glyph_variants:
                        raise RuntimeError(f'cannot fallback default with flavors: {flavor_order!r}')
        return result

    def get_glyph_sequence(self, flavor_order: Sequence[str | None] | None = None) -> list[NamedGlyphFile]:
        flavor_order = normalize_flavor_order(flavor_order)
        if flavor_order is None:
            flavor_order = [None]

        sequence = []
        glyph_names = set()
        for name_key, glyph_variants in sorted(self.items()):
            for flavor in flavor_order:
                glyph_file = glyph_variants.select(flavor)
                glyph_name = glyph_file.glyph_name
                if glyph_name not in glyph_names:
                    glyph_names.add(glyph_name)
                    sequence.append(glyph_file)
        return sequence

    def copy(self) -> NamedContext:
        result = NamedContext()
        for name_key, glyph_variants in self.items():
            result[name_key] = glyph_variants.copy()
        return result
