import re
from pathlib import Path

import pytest

from pixel_font_knife.named.context import NamedContext
from pixel_font_knife.named.file import NamedGlyphFile
from pixel_font_knife.named.variants import NamedGlyphVariants


def _touch(root_dir: Path, *file_names: str) -> None:
    for file_name in file_names:
        root_dir.joinpath(file_name).touch()


def _create_variants(name_key: str, flavor: str | None, file_name: str) -> NamedGlyphVariants:
    glyph_variants = NamedGlyphVariants(name_key)
    glyph_variants[flavor] = NamedGlyphFile(file_name, name_key)
    return glyph_variants


def test_file_load_preserves_name_key_and_flavors() -> None:
    glyph_file = NamedGlyphFile.load('foo A,b.png')

    assert glyph_file.file_path == Path('foo A,b.png')
    assert glyph_file.name_key == 'foo'
    assert glyph_file.flavors == ['A', 'b']
    assert glyph_file.glyph_name == 'foo.A'


def test_file_load_without_flavors() -> None:
    glyph_file = NamedGlyphFile.load('foo.png')

    assert glyph_file.name_key == 'foo'
    assert glyph_file.flavors == []
    assert glyph_file.glyph_name == 'foo'


def test_load_notdef_uses_special_glyph_name() -> None:
    glyph_file = NamedGlyphFile.load_notdef('notdef.png')

    assert glyph_file.file_path == Path('notdef.png')
    assert glyph_file.name_key == '.notdef'
    assert glyph_file.flavors == []
    assert glyph_file.glyph_name == '.notdef'


@pytest.mark.parametrize(
    'flavor_order',
    [
        ['zh_cn', 'zh_tw'],
        [None, 'zh_cn', 'zh_tw'],
    ],
)
def test_file_normalize_uses_requested_flavor_order(
        tmp_path: Path,
        flavor_order: list[str | None],
) -> None:
    file_path = tmp_path.joinpath('source.png')
    file_path.touch()
    glyph_file = NamedGlyphFile(file_path, 'foo', ['zh_tw', 'zh_cn'])

    glyph_file.normalize(flavor_order)

    assert glyph_file.file_path == tmp_path.joinpath('foo zh_cn,zh_tw.png')
    assert glyph_file.file_path.exists()
    assert not file_path.exists()
    assert glyph_file.flavors == ['zh_tw', 'zh_cn']
    assert glyph_file.glyph_name == 'foo.zh_tw'


def test_file_normalize_accepts_string_flavor_order(tmp_path: Path) -> None:
    file_path = tmp_path.joinpath('source.png')
    file_path.touch()
    glyph_file = NamedGlyphFile(file_path, 'foo', ['zh_cn'])

    glyph_file.normalize('zh_cn')

    assert glyph_file.file_path.name == 'foo zh_cn.png'


def test_variants_select_exact_flavor_then_default() -> None:
    default_file = NamedGlyphFile('foo.png', 'foo')
    flavored_file = NamedGlyphFile('foo zh_cn.png', 'foo', ['zh_cn'])
    glyph_variants = NamedGlyphVariants('foo')
    glyph_variants[None] = default_file
    glyph_variants['zh_cn'] = flavored_file

    assert glyph_variants.select() is default_file
    assert glyph_variants.select('zh_cn') is flavored_file
    assert glyph_variants.select('zh_tw') is default_file


def test_variants_require_matching_name_key() -> None:
    glyph_file = NamedGlyphFile('foo.png', 'foo')
    glyph_variants = NamedGlyphVariants('bar')

    with pytest.raises(ValueError, match=re.escape("name key mismatch: 'bar' != 'foo'")):
        glyph_variants[None] = glyph_file


def test_context_load_builds_flavor_usage_mapping(tmp_path: Path) -> None:
    _touch(tmp_path, 'foo.png', 'foo zh_cn,zh_tw.png', 'bar ja.png')

    context = NamedContext.load(tmp_path, {'zh_cn', 'zh_tw', 'ja'})

    assert set(context) == {'foo', 'bar'}
    assert context['foo'][None].file_path == tmp_path.joinpath('foo.png')
    assert context['foo']['zh_cn'] is context['foo']['zh_tw']
    assert context['foo']['zh_cn'].file_path == tmp_path.joinpath('foo zh_cn,zh_tw.png')
    assert context['bar']['ja'].file_path == tmp_path.joinpath('bar ja.png')


def test_context_load_accepts_string_allowed_flavors(tmp_path: Path) -> None:
    _touch(tmp_path, 'foo zh_cn.png')

    context = NamedContext.load(tmp_path, 'zh_cn')

    assert set(context['foo']) == {'zh_cn'}


def test_context_load_rejects_disallowed_flavor(tmp_path: Path) -> None:
    _touch(tmp_path, 'foo zh_tw.png')

    with pytest.raises(RuntimeError, match=re.escape("flavor 'zh_tw' not allowed:")):
        NamedContext.load(tmp_path, {'zh_cn'})


def test_context_requires_matching_name_key() -> None:
    glyph_variants = NamedGlyphVariants('foo')

    with pytest.raises(ValueError, match=re.escape("name key mismatch: 'bar' != 'foo'")):
        NamedContext({
            'bar': glyph_variants,
        })


def test_check_after_name_key_modified() -> None:
    glyph_file = NamedGlyphFile('foo.png', 'foo')
    glyph_variants = NamedGlyphVariants('foo')
    glyph_variants[None] = glyph_file
    context = NamedContext({
        'foo': glyph_variants,
    })

    glyph_file.name_key = 'bar'

    with pytest.raises(ValueError, match=re.escape("name key mismatch: 'foo' != 'bar'")):
        context.check()


def test_copy_shares_matching_glyph_file() -> None:
    glyph_file = NamedGlyphFile('foo.png', 'foo')
    glyph_variants = NamedGlyphVariants('foo')
    glyph_variants[None] = glyph_file
    context = NamedContext({
        'foo': glyph_variants,
    })

    result = context.copy()

    assert result is not context
    assert result['foo'] is not context['foo']
    assert result['foo'].name_key == 'foo'
    assert result['foo'][None] is glyph_file


def test_merge_by_name_key_replaces_whole_variants_group() -> None:
    default_variants = _create_variants('foo', None, 'foo.png')
    flavored_variants = _create_variants('foo', 'zh_cn', 'foo zh_cn.png')

    result = NamedContext({
        'foo': default_variants,
    }).merge_by_name_key(
        NamedContext({
            'foo': flavored_variants,
        }),
        conflict='replace',
    )

    assert None not in result['foo']
    assert result['foo']['zh_cn'] is flavored_variants['zh_cn']


def test_merge_by_flavor_replaces_only_conflicting_flavor() -> None:
    default_file = NamedGlyphFile('foo.png', 'foo')
    old_file = NamedGlyphFile('foo old.png', 'foo')
    new_file = NamedGlyphFile('foo new.png', 'foo')
    target_variants = NamedGlyphVariants('foo')
    target_variants[None] = default_file
    target_variants['zh_cn'] = old_file
    source_variants = NamedGlyphVariants('foo')
    source_variants['zh_cn'] = new_file

    result = NamedContext({
        'foo': target_variants,
    }).merge_by_flavor(
        NamedContext({
            'foo': source_variants,
        }),
        conflict='replace',
    )

    assert result['foo'][None] is default_file
    assert result['foo']['zh_cn'] is new_file


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
    zh_cn_file = NamedGlyphFile('foo zh_cn.png', 'foo')
    zh_tw_file = NamedGlyphFile('foo zh_tw.png', 'foo')
    glyph_variants = NamedGlyphVariants('foo')
    glyph_variants['zh_cn'] = zh_cn_file
    glyph_variants['zh_tw'] = zh_tw_file
    context = NamedContext({
        'foo': glyph_variants,
    })

    result = context.with_default_flavor(flavor_order)

    assert None not in context['foo']
    assert result['foo'][None] is zh_tw_file


def test_get_glyph_sequence_sorts_by_name_key_then_flavor_and_deduplicates() -> None:
    foo_default = NamedGlyphFile('foo.png', 'foo')
    foo_flavored = NamedGlyphFile('foo zh_cn.png', 'foo', ['zh_cn'])
    foo_variants = NamedGlyphVariants('foo')
    foo_variants[None] = foo_default
    foo_variants['zh_cn'] = foo_flavored
    foo_variants['zh_tw'] = foo_flavored
    bar_default = NamedGlyphFile('bar.png', 'bar')
    bar_variants = NamedGlyphVariants('bar')
    bar_variants[None] = bar_default

    sequence = NamedContext({
        'foo': foo_variants,
        'bar': bar_variants,
    }).get_glyph_sequence([None, 'zh_cn', 'zh_tw'])

    assert sequence == [bar_default, foo_default, foo_flavored]


def test_get_glyph_sequence_accepts_string_flavor_order() -> None:
    default_file = NamedGlyphFile('foo.png', 'foo')
    flavored_file = NamedGlyphFile('foo zh_cn.png', 'foo', ['zh_cn'])
    variants = NamedGlyphVariants('foo')
    variants[None] = default_file
    variants['zh_cn'] = flavored_file
    context = NamedContext({
        'foo': variants,
    })

    assert context.get_glyph_sequence('zh_cn') == [flavored_file]
    assert context.get_glyph_sequence('default') == [default_file]


def test_get_glyph_sequence_reports_name_key_for_missing_flavor() -> None:
    default_file = NamedGlyphFile('foo.png', 'foo')
    variants = NamedGlyphVariants('foo')
    variants[None] = default_file
    context = NamedContext({
        'foo': variants,
    })

    with pytest.raises(KeyError, match=re.escape(str(KeyError("'foo': no flavor file: 'zh_cn'")))):
        context.get_glyph_sequence('zh_cn', fallback_default=False)
