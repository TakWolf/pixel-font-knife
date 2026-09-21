import re
from pathlib import Path

import pytest

from pixel_font_knife.cmap.context import CmapContext
from pixel_font_knife.cmap.file import CmapGlyphFile
from pixel_font_knife.cmap.variants import CmapGlyphVariants


def _touch(root_dir: Path, *file_names: str) -> None:
    for file_name in file_names:
        file_path = root_dir.joinpath(file_name)
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.touch()


def _create_variants(code_point: int, flavor: str | None, file_name: str) -> CmapGlyphVariants:
    glyph_variants = CmapGlyphVariants()
    glyph_variants[flavor] = CmapGlyphFile(file_name, code_point)
    return glyph_variants


def test_file_load_preserves_code_point_and_flavors() -> None:
    glyph_file = CmapGlyphFile.load('4E00 A,b.png')

    assert glyph_file.file_path == Path('4E00 A,b.png')
    assert glyph_file.code_point == 0x4E00
    assert glyph_file.flavors == ['A', 'b']
    assert glyph_file.glyph_name == 'u4E00.A'


def test_file_load_without_flavors() -> None:
    glyph_file = CmapGlyphFile.load('4E00.png')

    assert glyph_file.code_point == 0x4E00
    assert glyph_file.flavors == []
    assert glyph_file.glyph_name == 'u4E00'


def test_file_load_rejects_non_png_file() -> None:
    with pytest.raises(ValueError, match=re.escape("illegal glyph file extension: '4E00.txt'")):
        CmapGlyphFile.load('4E00.txt')


@pytest.mark.parametrize(
    'flavor_order',
    [
        ['zh_cn', 'zh_tw'],
        [None, 'zh_cn', 'zh_tw'],
    ],
)
def test_file_normalize_uses_code_point_directory_and_flavor_order(
        tmp_path: Path,
        flavor_order: list[str | None],
) -> None:
    file_path = tmp_path.joinpath('source.png')
    file_path.touch()
    glyph_file = CmapGlyphFile(file_path, 0x4E00, ['zh_tw', 'zh_cn'])

    glyph_file.normalize(tmp_path, flavor_order)

    assert glyph_file.file_path == tmp_path.joinpath(
        '4E00-9FFF CJK Unified Ideographs',
        '4E-',
        '4E00 zh_cn,zh_tw.png',
    )
    assert glyph_file.file_path.exists()
    assert not file_path.exists()
    assert glyph_file.flavors == ['zh_tw', 'zh_cn']
    assert glyph_file.glyph_name == 'u4E00.zh_tw'


def test_file_normalize_accepts_string_flavor_order(tmp_path: Path) -> None:
    file_path = tmp_path.joinpath('source.png')
    file_path.touch()
    glyph_file = CmapGlyphFile(file_path, 0x4E00, ['zh_cn'])

    glyph_file.normalize(tmp_path, 'zh_cn')

    assert glyph_file.file_path.name == '4E00 zh_cn.png'


def test_variants_reject_none_value_for_default_flavor() -> None:
    glyph_variants = CmapGlyphVariants()

    with pytest.raises(TypeError, match=re.escape("illegal value type: 'NoneType'")):
        glyph_variants[None] = None


def test_context_rejects_none_value() -> None:
    context = CmapContext()

    with pytest.raises(TypeError, match=re.escape("illegal value type: 'NoneType'")):
        context[0x4E00] = None


def test_variants_select_exact_flavor_then_default() -> None:
    default_file = CmapGlyphFile('4E00.png', 0x4E00)
    flavored_file = CmapGlyphFile('4E00 zh_cn.png', 0x4E00, ['zh_cn'])
    glyph_variants = CmapGlyphVariants()
    glyph_variants[None] = default_file
    glyph_variants['zh_cn'] = flavored_file

    assert glyph_variants.select() is default_file
    assert glyph_variants.select('zh_cn') is flavored_file
    assert glyph_variants.select('zh_tw') is default_file


def test_context_load_builds_flavor_usage_mapping(tmp_path: Path) -> None:
    _touch(tmp_path, 'default/4E00.png', 'variants/4E00 zh_cn,zh_tw.png', '0041 ja.png')

    context = CmapContext.load(tmp_path, {'zh_cn', 'zh_tw', 'ja'})

    assert set(context) == {0x4E00, 0x41}
    assert context[0x4E00][None].file_path == tmp_path.joinpath('default/4E00.png')
    assert context[0x4E00]['zh_cn'] is context[0x4E00]['zh_tw']
    assert context[0x4E00]['zh_cn'].file_path == tmp_path.joinpath('variants/4E00 zh_cn,zh_tw.png')
    assert context[0x41]['ja'].file_path == tmp_path.joinpath('0041 ja.png')


def test_context_load_accepts_string_allowed_flavors(tmp_path: Path) -> None:
    _touch(tmp_path, '4E00 zh_cn.png')

    context = CmapContext.load(tmp_path, 'zh_cn')

    assert set(context[0x4E00]) == {'zh_cn'}


def test_context_load_rejects_disallowed_flavor(tmp_path: Path) -> None:
    _touch(tmp_path, '4E00 zh_tw.png')

    with pytest.raises(RuntimeError, match=re.escape("flavor 'zh_tw' not allowed:")):
        CmapContext.load(tmp_path, {'zh_cn'})


def test_copy_shares_glyph_file() -> None:
    glyph_file = CmapGlyphFile('4E00.png', 0x4E00)
    context = CmapContext({
        0x4E00: CmapGlyphVariants({
            None: glyph_file,
        }),
    })

    result = context.copy()

    assert result is not context
    assert result[0x4E00] is not context[0x4E00]
    assert result[0x4E00][None] is glyph_file


def test_merge_by_code_point_replaces_whole_variants_group() -> None:
    default_variants = _create_variants(0x4E00, None, '4E00.png')
    flavored_variants = _create_variants(0x4E00, 'zh_cn', '4E00 zh_cn.png')

    result = CmapContext({
        0x4E00: default_variants,
    }).merge_by_code_point(
        CmapContext({
            0x4E00: flavored_variants,
        }),
        conflict='replace',
    )

    assert None not in result[0x4E00]
    assert result[0x4E00]['zh_cn'] is flavored_variants['zh_cn']


def test_merge_by_flavor_replaces_only_conflicting_flavor() -> None:
    default_file = CmapGlyphFile('4E00.png', 0x4E00)
    old_file = CmapGlyphFile('4E00 old.png', 0x4E00)
    new_file = CmapGlyphFile('4E00 new.png', 0x4E00)
    target_variants = CmapGlyphVariants({
        None: default_file,
        'zh_cn': old_file,
    })
    source_variants = CmapGlyphVariants({
        'zh_cn': new_file,
    })

    result = CmapContext({
        0x4E00: target_variants,
    }).merge_by_flavor(
        CmapContext({
            0x4E00: source_variants,
        }),
        conflict='replace',
    )

    assert result[0x4E00][None] is default_file
    assert result[0x4E00]['zh_cn'] is new_file


@pytest.mark.parametrize(
    'flavor_order',
    [
        ['zh_tw', 'zh_cn'],
        'zh_tw',
    ],
)
def test_with_default_flavor_uses_priority_without_mutating_source(
        flavor_order: list[str] | str,
) -> None:
    zh_cn_file = CmapGlyphFile('4E00 zh_cn.png', 0x4E00)
    zh_tw_file = CmapGlyphFile('4E00 zh_tw.png', 0x4E00)
    glyph_variants = CmapGlyphVariants({
        'zh_cn': zh_cn_file,
        'zh_tw': zh_tw_file,
    })
    context = CmapContext({
        0x4E00: glyph_variants,
    })

    result = context.with_default_flavor(flavor_order)

    assert None not in context[0x4E00]
    assert result[0x4E00][None] is zh_tw_file


def test_get_glyph_sequence_sorts_by_flavor_then_code_point_and_deduplicates() -> None:
    default_file = CmapGlyphFile('0042.png', 0x42)
    shared_file = CmapGlyphFile('0041 zh_cn.png', 0x41, ['zh_cn'])
    first_variants = CmapGlyphVariants({
        None: shared_file,
        'zh_cn': shared_file,
    })
    second_variants = CmapGlyphVariants({
        None: default_file,
        'zh_cn': shared_file,
    })

    sequence = CmapContext({
        0x42: second_variants,
        0x41: first_variants,
    }).get_glyph_sequence([None, 'zh_cn'])

    assert sequence == [shared_file, default_file]


def test_get_glyph_sequence_accepts_string_flavor_order() -> None:
    default_file = CmapGlyphFile('0041.png', 0x41)
    flavored_file = CmapGlyphFile('0041 zh_cn.png', 0x41, ['zh_cn'])
    context = CmapContext({
        0x41: CmapGlyphVariants({
            None: default_file,
            'zh_cn': flavored_file,
        }),
    })

    assert context.get_glyph_sequence('zh_cn') == [flavored_file]
    assert context.get_glyph_sequence('default') == [default_file]


def test_get_glyph_sequence_reports_code_point_for_missing_flavor() -> None:
    default_file = CmapGlyphFile('0041.png', 0x41)
    context = CmapContext({
        0x41: CmapGlyphVariants({
            None: default_file,
        }),
    })

    with pytest.raises(KeyError, match=re.escape(str(KeyError("0x0041: no flavor file: 'zh_cn'")))):
        context.get_glyph_sequence('zh_cn', fallback_default=False)


def test_get_character_mapping_uses_context_code_points() -> None:
    glyph_file = CmapGlyphFile('0041.png', 0x41)
    context = CmapContext({
        0x42: CmapGlyphVariants({
            None: glyph_file,
        }),
    })

    assert context.get_character_mapping() == {
        0x42: 'u0041',
    }


def test_get_character_mapping_reports_code_point_for_missing_flavor() -> None:
    default_file = CmapGlyphFile('0041.png', 0x41)
    context = CmapContext({
        0x42: CmapGlyphVariants({
            None: default_file,
        }),
    })

    with pytest.raises(KeyError, match=re.escape(str(KeyError("0x0042: no flavor file: 'zh_cn'")))):
        context.get_character_mapping('zh_cn', fallback_default=False)
