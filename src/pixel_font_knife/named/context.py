from __future__ import annotations

from collections import UserDict
from collections.abc import Collection, Sequence
from os import PathLike
from pathlib import Path
from typing import Any

from pixel_font_knife.glyph.common import MergeConflictStrategy, check_merge_conflict_strategy, check_glyph_name_key
from pixel_font_knife.named.file import NamedGlyphFile
from pixel_font_knife.named.variants import NamedGlyphVariants


class NamedContext(UserDict[str, NamedGlyphVariants]):
    @staticmethod
    def load(
            root_dir: str | PathLike[str],
            allowed_flavors: Collection[str] | None = None,
    ) -> NamedContext:
        if allowed_flavors is not None:
            allowed_flavors = set(allowed_flavors)

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
                    glyph_variants = NamedGlyphVariants()
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
        if not isinstance(name_key, str):
            raise KeyError(f'illegal name key type: {type(name_key).__name__!r}')

        check_glyph_name_key(name_key)

        if not isinstance(glyph_variants, NamedGlyphVariants):
            raise ValueError(f'illegal value type: {type(glyph_variants).__name__!r}')

        super().__setitem__(name_key, glyph_variants)

    def __copy__(self) -> NamedContext:
        return self.copy()

    def normalize(self, flavor_order: Sequence[str] | None = None) -> None:
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
                            raise RuntimeError(f'duplicate named flavor: {name_key!r} {flavor!r}')
        return result

    def with_default_flavor(self, flavor_order: Sequence[str] | None = None) -> NamedContext:
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
