import re

import pytest

from pixel_font_knife.named.context import NamedContext
from pixel_font_knife.named.file import NamedGlyphFile
from pixel_font_knife.named.variants import NamedGlyphVariants


def test_variants_require_matching_name_key() -> None:
    glyph_file = NamedGlyphFile('foo.png', 'foo')
    glyph_variants = NamedGlyphVariants('bar')

    with pytest.raises(ValueError, match=re.escape("name key mismatch: 'bar' != 'foo'")):
        glyph_variants[None] = glyph_file


def test_context_requires_matching_name_key() -> None:
    glyph_variants = NamedGlyphVariants('foo')

    with pytest.raises(ValueError, match=re.escape("name key mismatch: 'bar' != 'foo'")):
        NamedContext({'bar': glyph_variants})


def test_check_after_name_key_modified() -> None:
    glyph_file = NamedGlyphFile('foo.png', 'foo')
    glyph_variants = NamedGlyphVariants('foo')
    glyph_variants[None] = glyph_file
    context = NamedContext({'foo': glyph_variants})

    glyph_file.name_key = 'bar'

    with pytest.raises(ValueError, match=re.escape("name key mismatch: 'foo' != 'bar'")):
        context.check()


def test_copy_shares_matching_glyph_file() -> None:
    glyph_file = NamedGlyphFile('foo.png', 'foo')
    glyph_variants = NamedGlyphVariants('foo')
    glyph_variants[None] = glyph_file
    context = NamedContext({'foo': glyph_variants})

    result = context.copy()

    assert result is not context
    assert result['foo'] is not context['foo']
    assert result['foo'].name_key == 'foo'
    assert result['foo'][None] is glyph_file
