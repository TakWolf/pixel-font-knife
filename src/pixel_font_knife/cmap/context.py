from __future__ import annotations

import shutil
from collections import UserDict
from collections.abc import Sequence
from os import PathLike
from pathlib import Path
from typing import Any

from pixel_font_knife.cmap.file import CmapGlyphFile
from pixel_font_knife.cmap.variants import CmapGlyphVariants
from pixel_font_knife.glyph.common import MergeConflictStrategy, validate_merge_conflict_strategy
from pixel_font_knife.utils import fs_util


class CmapContext(UserDict[int, CmapGlyphVariants]):
    """cmap 字形文件的使用映射上下文。

    数据结构为 ``code_point -> flavor -> CmapGlyphFile``。上下文和变体的键表示构建时的使用映射，
    ``CmapGlyphFile.code_point``、``CmapGlyphFile.flavors`` 和 ``CmapGlyphFile.file_path``
    则表示字形身份及本地存储信息；两者相互独立，不要求保持一致。因此，同一个字形文件可以被多个码点
    或 flavor 引用，修改使用映射不会修改字形文件的本地信息。

    ``load()`` 根据本地文件名建立初始使用映射，并确保同一码点下的每个 flavor 只对应一个文件。
    字形文件属性允许在素材设计阶段修改；修改后应立即调用 ``normalize()``，根据字形文件自身的
    ``code_point`` 和 ``flavors`` 将文件移动到规范路径。该操作不会重建或改变当前使用映射，
    也不保证规范化后的目录能够再次无冲突地加载。

    ``copy()`` 和合并操作只复制 ``CmapContext`` 与 ``CmapGlyphVariants`` 容器，始终共享原有的
    ``CmapGlyphFile`` 对象及其画布缓存。按码点合并时以整组变体为单位处理冲突；按 flavor 合并时
    只处理同一码点下发生冲突的 flavor。对合并结果中字形文件属性的修改，会被所有共享该对象的
    上下文观察到。

    ``get_glyph_sequence()`` 按 flavor 顺序和码点顺序生成字形序列，并按 glyph name 保留首次出现的
    字形，以满足字体构建的字形排序约定。``get_character_mapping()`` 则以当前上下文的码点键生成
    码点到 glyph name 的映射。
    """

    @staticmethod
    def load(root_dir: str | PathLike[str]) -> CmapContext:
        if not isinstance(root_dir, Path):
            root_dir = Path(root_dir)

        context = CmapContext()
        for file_dir, _, file_names in root_dir.walk():
            for file_name in file_names:
                if not file_name.endswith('.png'):
                    continue

                file_path = file_dir.joinpath(file_name)
                glyph_file = CmapGlyphFile.load(file_path)

                if glyph_file.code_point not in context:
                    glyph_variants = CmapGlyphVariants()
                    context[glyph_file.code_point] = glyph_variants
                else:
                    glyph_variants = context[glyph_file.code_point]

                if len(glyph_file.flavors) > 0:
                    for flavor in glyph_file.flavors:
                        if flavor in glyph_variants:
                            raise RuntimeError(f"flavor {flavor!r} already exists:\n'{file_path}'\n'{glyph_variants[flavor].file_path}'")
                        glyph_variants[flavor] = glyph_file
                else:
                    if None in glyph_variants:
                        raise RuntimeError(f"default flavor already exists:\n'{file_path}'\n'{glyph_variants[None].file_path}'")
                    glyph_variants[None] = glyph_file
        return context

    def __setitem__(self, code_point: Any, glyph_variants: Any) -> None:
        if not isinstance(code_point, int):
            raise KeyError(f'illegal code point type: {type(code_point).__name__!r}')

        if code_point < 0:
            raise KeyError(f'illegal code point: {code_point}')

        if not isinstance(glyph_variants, CmapGlyphVariants):
            raise ValueError(f'illegal value type: {type(glyph_variants).__name__!r}')

        super().__setitem__(code_point, glyph_variants)

    def __copy__(self) -> CmapContext:
        return self.copy()

    def normalize(
            self,
            root_dir: str | PathLike[str],
            flavor_order: Sequence[str] | None = None,
    ) -> None:
        if not isinstance(root_dir, Path):
            root_dir = Path(root_dir)

        for glyph_variants in self.values():
            for glyph_file in glyph_variants.values():
                glyph_file.normalize(root_dir, flavor_order)

        for file_dir, _, _ in root_dir.walk(top_down=False):
            if fs_util.is_empty_dir(file_dir):
                shutil.rmtree(file_dir)

    def merge_by_code_point(
            self,
            *contexts: CmapContext,
            conflict: MergeConflictStrategy = 'error',
    ) -> CmapContext:
        validate_merge_conflict_strategy(conflict)

        result = self.copy()
        for context in contexts:
            for code_point, glyph_variants in context.items():
                if code_point not in result:
                    result[code_point] = glyph_variants.copy()
                    continue

                match conflict:
                    case 'keep':
                        pass
                    case 'replace':
                        result[code_point] = glyph_variants.copy()
                    case _:
                        raise RuntimeError(f'duplicate cmap code point: 0x{code_point:04X}')
        return result

    def merge_by_flavor(
            self,
            *contexts: CmapContext,
            conflict: MergeConflictStrategy = 'error',
    ) -> CmapContext:
        validate_merge_conflict_strategy(conflict)

        result = self.copy()
        for context in contexts:
            for code_point, source_variants in context.items():
                if code_point not in result:
                    result[code_point] = source_variants.copy()
                    continue

                target_variants = result[code_point]

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
                            raise RuntimeError(f'duplicate cmap flavor: 0x{code_point:04X} {flavor!r}')
        return result

    def with_default_flavor(self, flavor_order: Sequence[str] | None = None) -> CmapContext:
        result = self.copy()
        for code_point, glyph_variants in result.items():
            if None not in glyph_variants:
                if len(glyph_variants) == 0:
                    raise RuntimeError(f'empty glyph variants: 0x{code_point:04X}')

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

    def get_glyph_sequence(self, flavor_order: Sequence[str | None] | None = None) -> list[CmapGlyphFile]:
        if flavor_order is None:
            flavor_order = [None]

        context = sorted(self.items())

        sequence = []
        glyph_names = set()
        for flavor in flavor_order:
            for code_point, glyph_variants in context:
                glyph_file = glyph_variants.select(flavor)
                glyph_name = glyph_file.glyph_name
                if glyph_name not in glyph_names:
                    glyph_names.add(glyph_name)
                    sequence.append(glyph_file)
        return sequence

    def get_character_mapping(self, flavor: str | None = None) -> dict[int, str]:
        character_mapping = {}
        for code_point, glyph_variants in self.items():
            glyph_file = glyph_variants.select(flavor)
            character_mapping[code_point] = glyph_file.glyph_name
        return character_mapping

    def copy(self) -> CmapContext:
        result = CmapContext()
        for code_point, glyph_variants in self.items():
            result[code_point] = glyph_variants.copy()
        return result
