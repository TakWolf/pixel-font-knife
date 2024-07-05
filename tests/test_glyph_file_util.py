import os
from pathlib import Path

import pytest

from pixel_font_knife import glyph_file_util
from pixel_font_knife.glyph_file_util import GlyphFile, GlyphFlavorGroup
from pixel_font_knife.mono_bitmap import MonoBitmap


def test_glyph_file_1(glyphs_dir: Path):
    glyph_file = GlyphFile.load(Path('notdef.png'))
    assert glyph_file.code_point == -1
    assert len(glyph_file.flavors) == 0

    glyph_file = GlyphFile.load(Path('40FF a,b,c,b,a.png'))
    assert glyph_file.code_point == 0x40FF
    assert glyph_file.flavors == ['a', 'b', 'c']

    file_path = glyphs_dir.joinpath('black', '6A1E.png')
    glyph_file = GlyphFile.load(file_path)
    assert glyph_file.bitmap == MonoBitmap.load_png(file_path)
    assert glyph_file.width == 12
    assert glyph_file.height == 12

    with pytest.raises(ValueError):
        GlyphFile.load(Path('5000.txt'))


def test_flavor_group():
    flavor_group = GlyphFlavorGroup(0x6000)
    flavor_group.add_file(GlyphFile.load(Path('6000.png')))
    flavor_group.add_file(GlyphFile.load(Path('6000 a,b.png')))
    assert len(flavor_group) == 3
    assert flavor_group.get_file().file_path == Path('6000.png')
    assert flavor_group.get_file('a').file_path == Path('6000 a,b.png')

    with pytest.raises(KeyError):
        flavor_group.get_file('c')
    assert flavor_group.get_file('c', fallback_default=True).file_path == Path('6000.png')
    assert flavor_group.get_file('c', fallback_any=True) is not None
    assert flavor_group.get_file('c', allow_none=True) is None

    with pytest.raises(ValueError):
        flavor_group.add_file(GlyphFile.load(Path('7000.png')))

    with pytest.raises(RuntimeError):
        flavor_group.add_file(GlyphFile.load(Path('6000.png')))

    with pytest.raises(RuntimeError):
        flavor_group.add_file(GlyphFile.load(Path('6000 b.png')))


def test_load_context(glyphs_dir: Path):
    context = glyph_file_util.load_context(os.fspath(glyphs_dir.joinpath('context')))
    assert len(context) == 3
    assert -1 in context
    group_4e11 = context[0x4E11]
    assert len(group_4e11) == 2
    assert '' in group_4e11
    assert 'zh_cn' in group_4e11
    group_6aa4 = context[0x6AA4]
    assert len(group_6aa4) == 5
    assert '' in group_6aa4
    assert group_6aa4['zh_hk'] is group_6aa4['zh_tw']
