import os
from pathlib import Path

import pytest

from pixel_font_knife import glyph_file_util
from pixel_font_knife.glyph_file_util import GlyphFile, GlyphFlavorGroup
from pixel_font_knife.mono_bitmap import MonoBitmap


def test_glyph_file_1():
    glyph_file = GlyphFile.load(Path('notdef.png'))
    assert glyph_file.code_point == -1
    assert len(glyph_file.flavors) == 0
    assert glyph_file.glyph_name == '.notdef'


def test_glyph_file_2():
    with pytest.raises(ValueError) as info:
        GlyphFile.load(Path('notdef a,b.png'))
    assert info.value.args[0] == "'notdef' can't have flavors: 'notdef a,b.png'"


def test_glyph_file_3():
    glyph_file = GlyphFile.load(Path('4E00.png'))
    assert glyph_file.code_point == 0x4E00
    assert len(glyph_file.flavors) == 0
    assert glyph_file.glyph_name == '4E00'


def test_glyph_file_4():
    glyph_file = GlyphFile.load(Path('4E00 A,b,C,b,a.png'))
    assert glyph_file.code_point == 0x4E00
    assert glyph_file.flavors == ['a', 'b', 'c']
    assert glyph_file.glyph_name == '4E00-A'


def test_glyph_file_5(glyphs_dir: Path):
    file_path = glyphs_dir.joinpath('black', '6A1E.png')
    glyph_file = GlyphFile.load(file_path)
    assert glyph_file.bitmap == MonoBitmap.load_png(file_path)
    assert glyph_file.width == 12
    assert glyph_file.height == 12


def test_glyph_file_6():
    with pytest.raises(ValueError) as info:
        GlyphFile.load(Path('4E00.txt'))
    assert info.value.args[0] == "not '.png' file: '4E00.txt'"


def test_flavor_group():
    flavor_group = GlyphFlavorGroup()

    glyph_file_default = GlyphFile.load(Path('6000.png'))
    flavor_group[None] = glyph_file_default

    glyph_file_ab = GlyphFile.load(Path('6000 a,b.png'))
    flavor_group['a'] = glyph_file_ab
    flavor_group['b'] = glyph_file_ab

    assert flavor_group.get_file() == flavor_group.get_file('c') == glyph_file_default
    assert flavor_group.get_file('a') == flavor_group.get_file('b') == glyph_file_ab
    assert flavor_group.get_file('A') == flavor_group.get_file('a') == glyph_file_ab
    assert flavor_group.get_file('B') == flavor_group.get_file('b') == glyph_file_ab


def test_context(glyphs_dir: Path):
    context = glyph_file_util.load_context(os.fspath(glyphs_dir.joinpath('context')))

    assert len(context) == 3
    assert -1 in context
    assert 0x4E11 in context
    assert 0x6AA4 in context
    assert 0x4E10 not in context

    group_notdef = context[-1]
    assert len(group_notdef) == 1

    group_4e11 = context[0x4E11]
    assert len(group_4e11) == 2
    assert None in group_4e11
    assert 'zh_cn' in group_4e11
    assert group_4e11.get_file('zh_hk') is group_4e11.get_file()

    group_6aa4 = context[0x6AA4]
    assert len(group_6aa4) == 5
    assert None in group_6aa4
    assert group_6aa4.get_file('zh_hk') is group_6aa4.get_file('zh_tw')
    assert group_6aa4.get_file('zh_tr') is group_6aa4.get_file('ko')

    assert glyph_file_util.get_character_mapping(context) == {
        0x4E11: '4E11',
        0x6AA4: '6AA4',
    }
    assert glyph_file_util.get_character_mapping(context, 'zh_cn') == {
        0x4E11: '4E11-ZH_CN',
        0x6AA4: '6AA4',
    }

    assert [glyph_file.file_path for glyph_file in glyph_file_util.get_glyph_sequence(context, [None, 'zh_cn', 'zh_hk'])] == [
        glyphs_dir.joinpath('context', 'notdef.png'),
        glyphs_dir.joinpath('context', '4E11.png'),
        glyphs_dir.joinpath('context', '6AA4.png'),
        glyphs_dir.joinpath('context', '4E11 zh_cn.png'),
        glyphs_dir.joinpath('context', '6AA4 zh_hk,zh_tw.png'),
    ]
