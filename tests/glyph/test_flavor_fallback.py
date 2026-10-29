import re

import pytest

from pixel_font_knife.cmap.context import CmapContext
from pixel_font_knife.cmap.file import CmapGlyphFile
from pixel_font_knife.cmap.variants import CmapGlyphVariants
from pixel_font_knife.named.context import NamedContext
from pixel_font_knife.named.file import NamedGlyphFile
from pixel_font_knife.named.variants import NamedGlyphVariants


@pytest.fixture(params=['cmap', 'named'])
def variants(request: pytest.FixtureRequest) -> CmapGlyphVariants | NamedGlyphVariants:
    if request.param == 'cmap':
        return CmapGlyphVariants({
            None: CmapGlyphFile('0041.png', 0x41),
            'alt': CmapGlyphFile('0041 alt.png', 0x41, ['alt']),
        })

    result = NamedGlyphVariants('foo')
    result[None] = NamedGlyphFile('foo.png', 'foo')
    result['alt'] = NamedGlyphFile('foo alt.png', 'foo', ['alt'])
    return result


@pytest.fixture
def context(variants: CmapGlyphVariants | NamedGlyphVariants) -> CmapContext | NamedContext:
    if isinstance(variants, CmapGlyphVariants):
        return CmapContext({0x41: variants})
    return NamedContext({'foo': variants})


@pytest.mark.parametrize('fallback_default', [False, True])
@pytest.mark.parametrize('allow_missing_glyph', [False, True])
@pytest.mark.parametrize('flavor', [None, 'alt'])
def test_select_existing_flavor_ignores_fallback(
        variants: CmapGlyphVariants | NamedGlyphVariants,
        fallback_default: bool,
        allow_missing_glyph: bool,
        flavor: str | None,
) -> None:
    assert variants.select(flavor, fallback_default, allow_missing_glyph) is variants[flavor]


def test_select_missing_flavor_with_default(variants: CmapGlyphVariants | NamedGlyphVariants) -> None:
    assert variants.select('missing', fallback_default=True) is variants[None]
    assert variants.select('missing', fallback_default=True, allow_missing_glyph=True) is variants[None]
    assert variants.select('missing', fallback_default=False, allow_missing_glyph=True) is None
    with pytest.raises(KeyError, match=re.escape("no flavor file: 'missing'")):
        variants.select('missing', fallback_default=False)


@pytest.mark.parametrize('empty', [False, True])
@pytest.mark.parametrize('flavor', [None, 'missing'])
def test_select_missing_flavor_without_default(
        variants: CmapGlyphVariants | NamedGlyphVariants,
        empty: bool,
        flavor: str | None,
) -> None:
    del variants[None]
    if empty:
        variants.clear()

    for fallback_default in (False, True):
        assert variants.select(flavor, fallback_default, allow_missing_glyph=True) is None
        with pytest.raises(KeyError, match=re.escape(f'no flavor file: {flavor!r}')):
            variants.select(flavor, fallback_default)


def test_sequence_skips_missing_flavor_even_with_default(context: CmapContext | NamedContext) -> None:
    assert context.get_glyph_sequence('missing', fallback_default=False, allow_missing_glyph=True) == []


def test_sequence_skip_continues_other_flavors_and_deduplicates(
        context: CmapContext | NamedContext,
        variants: CmapGlyphVariants | NamedGlyphVariants,
) -> None:
    variants['alias'] = variants['alt']

    assert context.get_glyph_sequence(['missing', None, 'alt', 'alias'], fallback_default=False, allow_missing_glyph=True) == [
        variants[None], variants['alt'],
    ]
    assert set(variants) == {None, 'alt', 'alias'}


def test_sequence_skip_handles_missing_default(
        context: CmapContext | NamedContext,
        variants: CmapGlyphVariants | NamedGlyphVariants,
) -> None:
    del variants[None]

    assert context.get_glyph_sequence(fallback_default=False, allow_missing_glyph=True) == []
    assert context.get_glyph_sequence([None, 'alt'], fallback_default=False, allow_missing_glyph=True) == [variants['alt']]
    with pytest.raises(KeyError, match='no flavor file: None'):
        context.get_glyph_sequence()


def test_sequence_default_requires_default_when_flavor_missing(
        context: CmapContext | NamedContext,
        variants: CmapGlyphVariants | NamedGlyphVariants,
) -> None:
    del variants[None]

    with pytest.raises(KeyError, match=re.escape("no flavor file: 'missing'")):
        context.get_glyph_sequence('missing', fallback_default=True)


def test_sequence_falls_back_then_skips_when_default_missing(
        context: CmapContext | NamedContext,
        variants: CmapGlyphVariants | NamedGlyphVariants,
) -> None:
    assert context.get_glyph_sequence('missing', allow_missing_glyph=True) == [variants[None]]

    del variants[None]

    assert context.get_glyph_sequence('missing', allow_missing_glyph=True) == []
    assert context.get_glyph_sequence(allow_missing_glyph=True) == []
    assert context.get_glyph_sequence(['missing', 'alt'], allow_missing_glyph=True) == [variants['alt']]
