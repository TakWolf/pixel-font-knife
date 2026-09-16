from collections.abc import Iterable
from typing import Literal, Any

MergeConflictStrategy = Literal[
    'error',
    'keep',
    'replace',
]


def check_merge_conflict_strategy(conflict: MergeConflictStrategy) -> None:
    if conflict not in ('error', 'keep', 'replace'):
        raise ValueError(f'illegal merge conflict strategy: {conflict!r}')


def check_glyph_name_key(glyph_name: str) -> None:
    if glyph_name == '':
        raise KeyError('glyph name cannot be empty')

    if any(character.isspace() for character in glyph_name):
        raise KeyError(f'illegal glyph name: {glyph_name!r}')


def check_flavor(flavor: Any) -> None:
    if flavor is None:
        raise KeyError('flavor cannot be None')

    if not isinstance(flavor, str):
        raise KeyError(f'illegal flavor type: {type(flavor).__name__!r}')

    if len(flavor) == 0:
        raise KeyError('flavor cannot be empty')

    if any(character.isspace() for character in flavor) or '.' in flavor or ',' in flavor or '*' in flavor:
        raise KeyError(f'illegal flavor: {flavor!r}')


def check_flavors(flavors: Iterable[Any]) -> None:
    validated_flavors = set()
    for flavor in flavors:
        check_flavor(flavor)
        if flavor in validated_flavors:
            raise KeyError(f'duplicate flavor: {flavor!r}')
        validated_flavors.add(flavor)
