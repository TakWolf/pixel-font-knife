from collections.abc import Iterable, Collection, Sequence
from typing import Any, Literal

MergeConflictStrategy = Literal[
    'error',
    'keep',
    'replace',
]


def check_merge_conflict_strategy(conflict: MergeConflictStrategy) -> None:
    if conflict not in ('error', 'keep', 'replace'):
        raise ValueError(f'illegal merge conflict strategy: {conflict!r}')


def check_code_point(code_point: Any) -> None:
    if not isinstance(code_point, int):
        raise TypeError(f'illegal code point type: {type(code_point).__name__!r}')

    if code_point < 0:
        raise ValueError(f'illegal code point: {code_point}')


def check_glyph_name_key(name_key: Any) -> None:
    if not isinstance(name_key, str):
        raise TypeError(f'illegal name key type: {type(name_key).__name__!r}')

    if name_key == '':
        raise ValueError('name key cannot be empty')

    if any(character.isspace() for character in name_key):
        raise ValueError(f'illegal name key: {name_key!r}')


def check_flavor(flavor: Any) -> None:
    if flavor is None:
        raise TypeError('flavor cannot be None')

    if not isinstance(flavor, str):
        raise TypeError(f'illegal flavor type: {type(flavor).__name__!r}')

    if len(flavor) == 0:
        raise ValueError('flavor cannot be empty')

    if any(character.isspace() for character in flavor) or '.' in flavor or ',' in flavor or '*' in flavor:
        raise ValueError(f'illegal flavor: {flavor!r}')


def check_flavors(flavors: Iterable[Any]) -> None:
    validated_flavors = set()
    for flavor in flavors:
        check_flavor(flavor)
        if flavor in validated_flavors:
            raise ValueError(f'duplicate flavor: {flavor!r}')
        validated_flavors.add(flavor)


def normalize_allowed_flavors(allowed_flavors: Collection[str] | None) -> set[str] | None:
    if allowed_flavors is not None:
        if isinstance(allowed_flavors, str):
            allowed_flavors = {allowed_flavors}
        else:
            if not isinstance(allowed_flavors, set):
                allowed_flavors = set(allowed_flavors)
    return allowed_flavors


def normalize_flavor_order(flavor_order: str | Sequence[str | None] | None) -> Sequence[str | None] | None:
    if isinstance(flavor_order, str):
        flavor_order = [flavor_order]
    return flavor_order
