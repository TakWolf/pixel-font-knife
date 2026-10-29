import re
from pathlib import Path

import pytest

from pixel_font_knife.cmap.context import CmapContext
from pixel_font_knife.cmap.file import CmapGlyphFile
from pixel_font_knife.cmap.mapping.entry import CmapMappingEntry
from pixel_font_knife.cmap.mapping.mapping import CmapMapping
from pixel_font_knife.cmap.mapping.reference import CmapGlyphReference
from pixel_font_knife.cmap.variants import CmapGlyphVariants


def _create_mapping(target_code_point: int, reference_code_point: int) -> CmapMapping:
    entry = CmapMappingEntry({None: CmapGlyphReference(reference_code_point)})
    return CmapMapping({target_code_point: entry})


def test_entry_rejects_none_value_for_default_flavor() -> None:
    entry = CmapMappingEntry()

    with pytest.raises(TypeError, match=re.escape("illegal value type: 'NoneType'")):
        entry[None] = None


def test_mapping_rejects_none_value() -> None:
    mapping = CmapMapping()

    with pytest.raises(TypeError, match=re.escape("illegal value type: 'NoneType'")):
        mapping[0x41] = None


@pytest.mark.parametrize(
    'method_name',
    [
        'apply_mapping_by_code_point',
        'apply_mapping_by_flavor',
    ],
)
def test_apply_mappings_are_order_independent(method_name: str) -> None:
    first_glyph_file = CmapGlyphFile('0041.png', 0x41)
    second_glyph_file = CmapGlyphFile('0042.png', 0x42)
    context = CmapContext({
        0x41: CmapGlyphVariants({None: first_glyph_file}),
        0x42: CmapGlyphVariants({None: second_glyph_file}),
    })
    first_mapping = _create_mapping(0x51, 0x41)
    second_mapping = _create_mapping(0x52, 0x42)

    apply_mapping = getattr(context, method_name)
    forward = apply_mapping(first_mapping, second_mapping)
    reverse = apply_mapping(second_mapping, first_mapping)

    assert forward[0x51][None] is first_glyph_file
    assert forward[0x52][None] is second_glyph_file
    assert reverse[0x51][None] is first_glyph_file
    assert reverse[0x52][None] is second_glyph_file


@pytest.mark.parametrize(
    'method_name',
    [
        'apply_mapping_by_code_point',
        'apply_mapping_by_flavor',
    ],
)
def test_mapping_cannot_resolve_another_reference(method_name: str) -> None:
    glyph_file = CmapGlyphFile('0043.png', 0x43)
    context = CmapContext({
        0x43: CmapGlyphVariants({None: glyph_file}),
    })
    referenced_mapping = _create_mapping(0x42, 0x43)
    referencing_mapping = _create_mapping(0x41, 0x42)

    result = getattr(context, method_name)(
        referenced_mapping,
        referencing_mapping,
    )

    assert result[0x42][None] is glyph_file
    assert 0x41 not in result


@pytest.mark.parametrize(
    'method_name',
    [
        'apply_mapping_by_code_point',
        'apply_mapping_by_flavor',
    ],
)
@pytest.mark.parametrize('target_flavor', ['*', None, 'zh_cn'])
def test_apply_mapping_allows_missing_code_point(method_name: str, target_flavor: str | None) -> None:
    context = CmapContext()
    entry = CmapMappingEntry({target_flavor: CmapGlyphReference(0x9999)})
    mapping = CmapMapping({0x41: entry})

    result = getattr(context, method_name)(mapping)

    assert 0x41 not in result


@pytest.mark.parametrize(
    'method_name',
    [
        'apply_mapping_by_code_point',
        'apply_mapping_by_flavor',
    ],
)
@pytest.mark.parametrize('target_flavor', ['*', None, 'zh_cn'])
def test_apply_mapping_rejects_missing_code_point(method_name: str, target_flavor: str | None) -> None:
    context = CmapContext()
    entry = CmapMappingEntry({target_flavor: CmapGlyphReference(0x9999)})
    mapping = CmapMapping({0x41: entry})

    with pytest.raises(RuntimeError, match=re.escape('0x0041: missing reference code point 0x9999')):
        getattr(context, method_name)(mapping, allow_missing_code_point=False)


@pytest.mark.parametrize(
    'method_name',
    [
        'apply_mapping_by_code_point',
        'apply_mapping_by_flavor',
    ],
)
def test_apply_mapping_allows_partially_missing_code_point(method_name: str) -> None:
    glyph_file = CmapGlyphFile('0042.png', 0x42)
    context = CmapContext({
        0x42: CmapGlyphVariants({None: glyph_file}),
    })
    entry = CmapMappingEntry({
        None: CmapGlyphReference(0x42),
        'zh_cn': CmapGlyphReference(0x9999),
    })
    mapping = CmapMapping({0x41: entry})

    result = getattr(context, method_name)(mapping)

    assert result[0x41][None] is glyph_file
    assert 'zh_cn' not in result[0x41]


@pytest.mark.parametrize(
    'method_name',
    [
        'apply_mapping_by_code_point',
        'apply_mapping_by_flavor',
    ],
)
def test_apply_mapping_rejects_partially_missing_code_point(method_name: str) -> None:
    glyph_file = CmapGlyphFile('0042.png', 0x42)
    context = CmapContext({
        0x42: CmapGlyphVariants({None: glyph_file}),
    })
    entry = CmapMappingEntry({
        None: CmapGlyphReference(0x42),
        'zh_cn': CmapGlyphReference(0x9999),
    })
    mapping = CmapMapping({0x41: entry})

    with pytest.raises(RuntimeError, match=re.escape('0x0041: missing reference code point 0x9999')):
        getattr(context, method_name)(mapping, allow_missing_code_point=False)


@pytest.mark.parametrize(
    'method_name',
    [
        'apply_mapping_by_code_point',
        'apply_mapping_by_flavor',
    ],
)
def test_apply_mapping_reports_missing_reference_flavor(method_name: str) -> None:
    default_file = CmapGlyphFile('0042.png', 0x42)
    context = CmapContext({
        0x42: CmapGlyphVariants({None: default_file}),
    })
    entry = CmapMappingEntry({
        'zh_cn': CmapGlyphReference(0x42, 'zh_cn'),
    })
    mapping = CmapMapping({
        0x41: entry,
    })

    with pytest.raises(KeyError, match=re.escape(str(KeyError("0x0041: reference 0x0042: no flavor file: 'zh_cn'")))):
        getattr(context, method_name)(mapping, fallback_default=False)


def test_load_yaml_accepts_string_allowed_flavors(tmp_path: Path) -> None:
    yaml_path = tmp_path.joinpath('mapping.yaml')
    yaml_path.write_text('0x0041:\n  zh_cn: 0x0042 zh_cn\n', 'utf-8')

    mapping = CmapMapping.load_yaml(yaml_path, 'zh_cn')

    assert set(mapping[0x41]) == {'zh_cn'}
    assert mapping[0x41]['zh_cn'].flavor == 'zh_cn'


def test_load_yaml_rejects_disallowed_target_flavor(tmp_path: Path) -> None:
    yaml_path = tmp_path.joinpath('mapping.yaml')
    yaml_path.write_text('0x0041:\n  zh_tw: 0x0042\n', 'utf-8')

    with pytest.raises(RuntimeError, match=re.escape("0x0041: flavor 'zh_tw' not allowed")):
        CmapMapping.load_yaml(yaml_path, {'zh_cn'})


def test_load_yaml_rejects_disallowed_reference_flavor(tmp_path: Path) -> None:
    yaml_path = tmp_path.joinpath('mapping.yaml')
    yaml_path.write_text('0x0041:\n  zh_cn: 0x0042 zh_tw\n', 'utf-8')

    with pytest.raises(RuntimeError, match=re.escape("0x0041 -> 'zh_cn': reference flavor 'zh_tw' not allowed")):
        CmapMapping.load_yaml(yaml_path, {'zh_cn'})


@pytest.mark.parametrize(
    'flavor_order',
    [
        None,
        [None, 'ko', 'zh_cn', 'zh_hk'],
    ],
)
def test_load_and_save_yaml_preserves_mapping_semantics(
        assets_dir: Path,
        tmp_path: Path,
        flavor_order: list[str | None] | None,
) -> None:
    load_path = assets_dir.joinpath('mapping-example.yaml')
    save_path = tmp_path.joinpath('mapping-example.yaml')

    mapping = CmapMapping.load_yaml(load_path)
    mapping.save_yaml(save_path, flavor_order)

    assert load_path.read_text('utf-8') == save_path.read_text('utf-8')
    assert set(mapping) == {0x0004, 0x0005}
    assert set(mapping[0x0004]) == {'*'}
    assert mapping[0x0004]['*'].code_point == 0x6AA4
    assert mapping[0x0004]['*'].flavor is None
    assert set(mapping[0x0005]) == {None, 'ko', 'zh_cn', 'zh_hk'}
    assert mapping[0x0005][None].code_point == 0x6AA4
    assert mapping[0x0005][None].flavor is None
    assert mapping[0x0005]['ko'].code_point == 0x6AA4
    assert mapping[0x0005]['ko'].flavor == 'ko'
    assert mapping[0x0005]['zh_cn'] is mapping[0x0005]['zh_hk']
    assert mapping[0x0005]['zh_cn'].code_point == 0x6AA4
    assert mapping[0x0005]['zh_cn'].flavor == 'ja'


@pytest.mark.parametrize(
    ('code_point', 'display'),
    [
        (0x0000, '0x0000'),
        (0x0020, 'SPACE'),
        (0x0021, '!'),
        (0x0301, '\u0301'),
        (0x0378, '0x0378'),
        (0x2028, 'LINE SEPARATOR'),
        (0xD800, '0xD800'),
        (0x1F600, '😀'),
        (0x10FFFF, '0x10FFFF'),
    ],
)
def test_save_code_point_display(code_point: int, display: str, tmp_path: Path) -> None:
    entry = CmapMappingEntry()
    entry['*'] = CmapGlyphReference(code_point, None)
    mapping = CmapMapping({code_point: entry})

    save_path = tmp_path.joinpath('mapping.yaml')
    mapping.save_yaml(save_path)
    assert save_path.read_text('utf-8') == (
        f'\n# {display}\n'
        f'0x{code_point:04X}:\n'
        f'  # {display}\n'
        f'  "*": 0x{code_point:04X}\n'
    )

    loaded_mapping = CmapMapping.load_yaml(save_path)
    assert loaded_mapping[code_point]['*'].code_point == code_point
    assert loaded_mapping[code_point]['*'].flavor is None
