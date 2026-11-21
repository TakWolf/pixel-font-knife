from __future__ import annotations

import shutil
from collections import UserDict
from collections.abc import Collection, Sequence
from copy import copy
from os import PathLike
from pathlib import Path
from typing import Any

from pixel_font_knife.cmap.file import CmapGlyphFile
from pixel_font_knife.cmap.mapping.mapping import CmapMapping
from pixel_font_knife.cmap.variants import CmapGlyphVariants
from pixel_font_knife.glyph.common import MergeConflictStrategy, check_merge_conflict_strategy, check_code_point, normalize_allowed_flavors, normalize_flavor_order
from pixel_font_knife.utils import fs_util


class CmapContext(UserDict[int, CmapGlyphVariants]):
    """Context mapping code points and requested flavors to cmap glyph files.

    The structure is ``code_point -> flavor -> CmapGlyphFile``. Context and variant
    keys describe usage during a build, while ``CmapGlyphFile.code_point``,
    ``CmapGlyphFile.flavors``, and ``CmapGlyphFile.file_path`` describe glyph
    identity and local storage. These are independent and need not match. A glyph
    file may be referenced by multiple code points or flavors; editing usage
    mappings does not change its local metadata.

    ``load()`` builds the initial usage mapping from local filenames, ensuring
    each flavor under a code point resolves to just one file. Glyph attributes may
    be edited while designing assets; call ``normalize()`` promptly afterward.
    Normalization uses each file's current attributes to determine its local path.
    It neither updates context or variant keys nor rebuilds usage mappings, and
    does not guarantee the directory can be reloaded without conflicts. It is not
    transactional: if a file fails to normalize, earlier moves are not rolled back.
    After moving files, empty subdirectories under ``root_dir`` are removed, but
    ``root_dir`` itself is retained.

    ``copy()`` and merge operations copy only the ``CmapContext`` and
    ``CmapGlyphVariants`` containers, sharing glyph file objects and canvas caches.
    Merging by code point resolves conflicts for entire variant sets; merging by
    flavor resolves only colliding flavors under the same code point. Changes to
    shared glyph file attributes are visible in every context referencing them.

    Mapping references should point directly to concrete glyphs in the original
    context, rather than to targets introduced by other mappings.
    ``apply_mapping_by_code_point()`` and ``apply_mapping_by_flavor()`` resolve all
    references from this context, so reference resolution does not depend on
    mapping or entry order. Conflicting targets are handled by ``conflict``;
    ``keep`` and ``replace`` can produce different results when mappings are
    reordered. The library does not verify whether references point to concrete
    glyphs; callers must follow this convention and handle missing references or
    conflicts resulting from violations.

    ``get_glyph_sequence()`` iterates in flavor order, then code point order,
    keeping the first glyph for each glyph name to meet font build ordering
    conventions. ``get_character_mapping()`` maps this context's code point keys
    to glyph names.
    """

    @staticmethod
    def load(
            root_dir: str | PathLike[str],
            allowed_flavors: Collection[str] | None = None,
    ) -> CmapContext:
        allowed_flavors = normalize_allowed_flavors(allowed_flavors)

        if not isinstance(root_dir, Path):
            root_dir = Path(root_dir)

        context = CmapContext()
        for file_path in root_dir.rglob('*.png'):
            if not file_path.is_file():
                continue

            glyph_file = CmapGlyphFile.load(file_path)

            if glyph_file.code_point not in context:
                glyph_variants = CmapGlyphVariants()
                context[glyph_file.code_point] = glyph_variants
            else:
                glyph_variants = context[glyph_file.code_point]

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

    def __setitem__(self, code_point: Any, glyph_variants: Any) -> None:
        check_code_point(code_point)

        if not isinstance(glyph_variants, CmapGlyphVariants):
            raise TypeError(f'illegal value type: {type(glyph_variants).__name__!r}')

        super().__setitem__(code_point, glyph_variants)

    def __copy__(self) -> CmapContext:
        result = CmapContext()
        for code_point, glyph_variants in self.items():
            result[code_point] = glyph_variants.copy()
        return result

    def normalize(
            self,
            root_dir: str | PathLike[str],
            flavor_order: str | Sequence[str | None] | None = None,
    ) -> None:
        flavor_order = normalize_flavor_order(flavor_order)

        if not isinstance(root_dir, Path):
            root_dir = Path(root_dir)

        for glyph_variants in self.values():
            for glyph_file in glyph_variants.values():
                glyph_file.normalize(root_dir, flavor_order)

        for file_dir, _, _ in root_dir.walk(top_down=False):
            if file_dir != root_dir and fs_util.is_empty_dir(file_dir):
                shutil.rmtree(file_dir)

    def merge_by_code_point(
            self,
            *contexts: CmapContext,
            conflict: MergeConflictStrategy = 'error',
    ) -> CmapContext:
        check_merge_conflict_strategy(conflict)

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
                        raise RuntimeError(f'duplicate code point: 0x{code_point:04X}')
        return result

    def merge_by_flavor(
            self,
            *contexts: CmapContext,
            conflict: MergeConflictStrategy = 'error',
    ) -> CmapContext:
        check_merge_conflict_strategy(conflict)

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
                            raise RuntimeError(f'duplicate flavor: 0x{code_point:04X} {flavor!r}')
        return result

    def apply_mapping_by_code_point(
            self,
            *mappings: CmapMapping,
            allow_missing_code_point: bool = True,
            fallback_default: bool = True,
            allow_missing_glyph: bool = False,
            conflict: MergeConflictStrategy = 'error',
    ) -> CmapContext:
        check_merge_conflict_strategy(conflict)

        result = self.copy()
        for mapping in mappings:
            for code_point, entry in mapping.items():
                if not entry:
                    continue

                if '*' in entry:
                    if len(entry) > 1:
                        raise RuntimeError(f'0x{code_point:04X}: wildcard flavor cannot be mixed with explicit flavors')

                    glyph_reference = entry['*']
                    if glyph_reference.flavor is not None:
                        raise RuntimeError(f'0x{code_point:04X}: wildcard flavor reference must be a code point')

                    if glyph_reference.code_point not in self:
                        if allow_missing_code_point:
                            continue
                        else:
                            raise RuntimeError(f'0x{code_point:04X}: missing reference code point 0x{glyph_reference.code_point:04X}')

                    glyph_variants = self[glyph_reference.code_point].copy()
                else:
                    glyph_variants = None

                    for flavor, glyph_reference in entry.items():
                        if glyph_reference.code_point not in self:
                            if allow_missing_code_point:
                                continue
                            else:
                                raise RuntimeError(f'0x{code_point:04X}: missing reference code point 0x{glyph_reference.code_point:04X}')

                        try:
                            glyph_file = self[glyph_reference.code_point].select(glyph_reference.flavor, fallback_default, allow_missing_glyph)
                        except KeyError as error:
                            raise KeyError(f'0x{code_point:04X}: reference 0x{glyph_reference.code_point:04X}: {error.args[0]}') from error

                        if glyph_file is None:
                            continue

                        if glyph_variants is None:
                            glyph_variants = CmapGlyphVariants()
                        glyph_variants[flavor] = glyph_file

                    if glyph_variants is None:
                        continue

                if code_point not in result:
                    result[code_point] = glyph_variants
                    continue

                match conflict:
                    case 'keep':
                        pass
                    case 'replace':
                        result[code_point] = glyph_variants
                    case _:
                        raise RuntimeError(f'duplicate code point: 0x{code_point:04X}')
        return result

    def apply_mapping_by_flavor(
            self,
            *mappings: CmapMapping,
            allow_missing_code_point: bool = True,
            fallback_default: bool = True,
            allow_missing_glyph: bool = False,
            conflict: MergeConflictStrategy = 'error',
    ) -> CmapContext:
        check_merge_conflict_strategy(conflict)

        result = self.copy()
        for mapping in mappings:
            for code_point, entry in mapping.items():
                if not entry:
                    continue

                if '*' in entry:
                    if len(entry) > 1:
                        raise RuntimeError(f'0x{code_point:04X}: wildcard flavor cannot be mixed with explicit flavors')

                    glyph_reference = entry['*']
                    if glyph_reference.flavor is not None:
                        raise RuntimeError(f'0x{code_point:04X}: wildcard flavor reference must be a code point')

                    if glyph_reference.code_point not in self:
                        if allow_missing_code_point:
                            continue
                        else:
                            raise RuntimeError(f'0x{code_point:04X}: missing reference code point 0x{glyph_reference.code_point:04X}')

                    source_variants = self[glyph_reference.code_point].copy()
                else:
                    source_variants = None

                    for flavor, glyph_reference in entry.items():
                        if glyph_reference.code_point not in self:
                            if allow_missing_code_point:
                                continue
                            else:
                                raise RuntimeError(f'0x{code_point:04X}: missing reference code point 0x{glyph_reference.code_point:04X}')

                        try:
                            glyph_file = self[glyph_reference.code_point].select(glyph_reference.flavor, fallback_default, allow_missing_glyph)
                        except KeyError as error:
                            raise KeyError(f'0x{code_point:04X}: reference 0x{glyph_reference.code_point:04X}: {error.args[0]}') from error

                        if glyph_file is None:
                            continue

                        if source_variants is None:
                            source_variants = CmapGlyphVariants()
                        source_variants[flavor] = glyph_file

                    if source_variants is None:
                        continue

                if code_point not in result:
                    result[code_point] = source_variants
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
                            raise RuntimeError(f'duplicate flavor: 0x{code_point:04X} {flavor!r}')
        return result

    def with_default_flavor(self, flavor_order: str | Sequence[str | None] | None = None) -> CmapContext:
        flavor_order = normalize_flavor_order(flavor_order)

        result = self.copy()
        for code_point, glyph_variants in result.items():
            if None not in glyph_variants:
                if not glyph_variants:
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

    def get_glyph_sequence(
            self,
            flavor_order: str | Sequence[str | None] | None = None,
            fallback_default: bool = True,
            allow_missing_glyph: bool = False,
    ) -> list[CmapGlyphFile]:
        flavor_order = normalize_flavor_order(flavor_order)
        if flavor_order is None:
            flavor_order = [None]

        context = sorted(self.items())

        sequence = []
        glyph_names = set()
        for flavor in flavor_order:
            for code_point, glyph_variants in context:
                try:
                    glyph_file = glyph_variants.select(flavor, fallback_default, allow_missing_glyph)
                except KeyError as error:
                    raise KeyError(f'0x{code_point:04X}: {error.args[0]}') from error

                if glyph_file is None:
                    continue

                glyph_name = glyph_file.glyph_name
                if glyph_name not in glyph_names:
                    glyph_names.add(glyph_name)
                    sequence.append(glyph_file)
        return sequence

    def get_character_mapping(
            self,
            flavor: str | None = None,
            fallback_default: bool = True,
            allow_missing_glyph: bool = False,
    ) -> dict[int, str]:
        character_mapping = {}
        for code_point, glyph_variants in self.items():
            try:
                glyph_file = glyph_variants.select(flavor, fallback_default, allow_missing_glyph)
            except KeyError as error:
                raise KeyError(f'0x{code_point:04X}: {error.args[0]}') from error

            if glyph_file is None:
                continue

            character_mapping[code_point] = glyph_file.glyph_name
        return character_mapping

    def copy(self) -> CmapContext:
        return copy(self)
