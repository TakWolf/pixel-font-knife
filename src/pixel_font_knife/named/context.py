from __future__ import annotations

from collections import UserDict
from collections.abc import Collection, Sequence
from copy import copy
from os import PathLike
from pathlib import Path
from typing import Any

from pixel_font_knife.glyph.common import MergeConflictStrategy, check_merge_conflict_strategy, check_glyph_name_key, normalize_allowed_flavors, normalize_flavor_order
from pixel_font_knife.named.file import NamedGlyphFile
from pixel_font_knife.named.variants import NamedGlyphVariants


class NamedContext(UserDict[str, NamedGlyphVariants]):
    """Context mapping fixed glyph names and requested flavors to glyph files.

    The structure is ``name_key -> flavor -> NamedGlyphFile``. The context key,
    variant set's name key, and every contained ``NamedGlyphFile.name_key`` must
    match; remapping a file to a different name key is not allowed. Flavor keys
    describe usage during a build and are independent of local storage metadata
    in ``NamedGlyphFile.flavors``. They need not match it, and multiple flavors
    under the same name key may reference the same file.

    ``load()`` builds the initial usage mapping from local filenames, ensuring
    each flavor under a name key resolves to just one file. A glyph file's flavors
    may be edited while designing assets; call ``normalize()`` promptly afterward
    to normalize filenames. Before changing a name key, detach the file from its
    original variant set, then map it under the new key. ``normalize()`` neither
    rebuilds nor changes usage mappings and does not guarantee the normalized
    directory can be reloaded without conflicts.

    ``check()`` rechecks name key consistency after glyph attributes are edited.
    ``copy()`` and merge operations copy only the ``NamedContext`` and
    ``NamedGlyphVariants`` containers, sharing glyph file objects and canvas caches.
    Merging by name key resolves conflicts for entire variant sets; merging by
    flavor resolves only colliding flavors under the same name key. Changes to
    shared glyph file attributes are visible in every context referencing them.

    ``get_glyph_sequence()`` iterates in name key order, then flavor order, keeping
    the first glyph for each glyph name to meet fixed-name glyph build ordering
    conventions. ``.notdef`` is not part of this context and should be loaded as a
    standalone ``NamedGlyphFile`` entity.
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
        for file_path in root_dir.rglob('*.png'):
            if not file_path.is_file():
                continue

            glyph_file = NamedGlyphFile.load(file_path)

            if glyph_file.name_key not in context:
                glyph_variants = NamedGlyphVariants(glyph_file.name_key)
                context[glyph_file.name_key] = glyph_variants
            else:
                glyph_variants = context[glyph_file.name_key]

            if glyph_file.flavors:
                for flavor in glyph_file.flavors:
                    if allowed_flavors is not None and flavor not in allowed_flavors:
                        raise RuntimeError(f'flavor {flavor!r} not allowed:\n{str(file_path)!r}')

                    if flavor in glyph_variants:
                        raise RuntimeError(f'flavor {flavor!r} already exists:\n{str(file_path)!r}\n{str(glyph_variants[flavor].file_path)!r}')

                    glyph_variants[flavor] = glyph_file
            else:
                if None in glyph_variants:
                    raise RuntimeError(f'default flavor already exists:\n{str(file_path)!r}\n{str(glyph_variants[None].file_path)!r}')

                glyph_variants[None] = glyph_file
        return context

    def __setitem__(self, name_key: Any, glyph_variants: Any) -> None:
        check_glyph_name_key(name_key)

        if not isinstance(glyph_variants, NamedGlyphVariants):
            raise TypeError(f'illegal value type: {type(glyph_variants).__name__!r}')

        if glyph_variants.name_key != name_key:
            raise ValueError(f'name key mismatch: {name_key!r} != {glyph_variants.name_key!r}')

        glyph_variants.check()

        super().__setitem__(name_key, glyph_variants)

    def __copy__(self) -> NamedContext:
        result = NamedContext()
        for name_key, glyph_variants in self.items():
            result[name_key] = glyph_variants.copy()
        return result

    def check(self) -> None:
        for name_key, glyph_variants in self.items():
            if glyph_variants.name_key != name_key:
                raise ValueError(f'name key mismatch: {name_key!r} != {glyph_variants.name_key!r}')
            glyph_variants.check()

    def normalize(self, flavor_order: str | Sequence[str | None] | None = None) -> None:
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

    def with_default_flavor(self, flavor_order: str | Sequence[str | None] | None = None) -> NamedContext:
        flavor_order = normalize_flavor_order(flavor_order)

        result = self.copy()
        for name_key, glyph_variants in result.items():
            if None not in glyph_variants:
                if not glyph_variants:
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

    def get_glyph_sequence(
            self,
            flavor_order: str | Sequence[str | None] | None = None,
            fallback_default: bool = True,
            allow_missing_glyph: bool = False,
    ) -> list[NamedGlyphFile]:
        flavor_order = normalize_flavor_order(flavor_order)
        if flavor_order is None:
            flavor_order = [None]

        sequence = []
        glyph_names = set()
        for name_key, glyph_variants in sorted(self.items()):
            for flavor in flavor_order:
                try:
                    glyph_file = glyph_variants.select(flavor, fallback_default, allow_missing_glyph)
                except KeyError as error:
                    raise KeyError(f'{name_key!r}: {error.args[0]}') from error

                if glyph_file is None:
                    continue

                glyph_name = glyph_file.glyph_name
                if glyph_name not in glyph_names:
                    glyph_names.add(glyph_name)
                    sequence.append(glyph_file)
        return sequence

    def copy(self) -> NamedContext:
        return copy(self)
