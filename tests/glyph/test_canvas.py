import re

import pytest

from pixel_font_knife.bitmap.mono_bitmap import MonoBitmap
from pixel_font_knife.bitmap.padding import Padding
from pixel_font_knife.glyph.canvas import GlyphCanvas


def test_init() -> None:
    canvas = GlyphCanvas(MonoBitmap.blank(7, 15))
    assert canvas.width == 7
    assert canvas.height == 15
    assert canvas.dimensions == (7, 15)


def test_trim() -> None:
    canvas = GlyphCanvas(MonoBitmap([
        [0, 0, 0, 0, 0, 0, 0],
        [0, 0, 0, 0, 0, 0, 0],
        [0, 1, 1, 1, 1, 0, 0],
        [0, 1, 0, 0, 1, 0, 0],
        [0, 1, 1, 1, 1, 0, 0],
        [0, 1, 0, 0, 1, 0, 0],
        [0, 1, 0, 0, 1, 0, 0],
        [0, 1, 0, 0, 1, 0, 0],
        [0, 1, 0, 0, 1, 0, 0],
        [0, 1, 0, 0, 1, 0, 0],
        [0, 1, 0, 0, 1, 0, 0],
        [0, 1, 0, 0, 1, 0, 0],
        [0, 1, 0, 0, 1, 0, 0],
        [0, 1, 1, 1, 1, 0, 0],
        [0, 0, 0, 0, 0, 0, 0],
    ]))
    assert canvas.trimmed_bitmap == MonoBitmap([
        [1, 1, 1, 1],
        [1, 0, 0, 1],
        [1, 1, 1, 1],
        [1, 0, 0, 1],
        [1, 0, 0, 1],
        [1, 0, 0, 1],
        [1, 0, 0, 1],
        [1, 0, 0, 1],
        [1, 0, 0, 1],
        [1, 0, 0, 1],
        [1, 0, 0, 1],
        [1, 1, 1, 1],
    ])
    assert canvas.trimmed_padding == Padding(left=1, right=2, top=2, bottom=1)
    assert not canvas.is_blank


def test_set_bitmap() -> None:
    canvas = GlyphCanvas(MonoBitmap.solid(3, 3))
    assert canvas.trimmed_bitmap.dimensions == (3, 3)
    assert canvas.trimmed_padding == Padding(0, 0, 0, 0)

    bitmap = MonoBitmap.blank(5, 7)
    canvas.bitmap = bitmap
    assert canvas.bitmap is bitmap
    assert canvas.dimensions == (5, 7)
    assert canvas.trimmed_bitmap.dimensions == (0, 0)
    assert canvas.trimmed_padding == Padding(5, 0, 7, 0)
    assert canvas.is_blank


def test_horizontal_offset() -> None:
    canvas = GlyphCanvas(MonoBitmap.solid(10, 16))
    assert canvas.horizontal_offset(12, 10) == (0, -4)
    assert canvas.advance_width() == 10


def test_horizontal_offset_with_vertical_bias() -> None:
    canvas = GlyphCanvas(MonoBitmap.solid(10, 15))

    with pytest.raises(ValueError, match=re.escape('canvas height and em size must have the same parity unless vertical_bias is specified')):
        canvas.horizontal_offset(12, 10)

    assert canvas.horizontal_offset(12, 10, 'top') == (0, -3)
    assert canvas.horizontal_offset(12, 10, 'bottom') == (0, -4)


def test_horizontal_offset_with_smaller_canvas() -> None:
    canvas = GlyphCanvas(MonoBitmap.solid(10, 9))
    assert canvas.horizontal_offset(12, 10, 'top') == (0, 0)
    assert canvas.horizontal_offset(12, 10, 'bottom') == (0, -1)


def test_vertical_offset() -> None:
    canvas = GlyphCanvas(MonoBitmap.solid(10, 16))
    assert canvas.vertical_offset(12) == (-5, -2)
    assert canvas.advance_height(12) == 12
    assert canvas.vertical_offset(24) == (-5, 4)
    assert canvas.advance_height(24) == 24


def test_vertical_offset_with_horizontal_bias() -> None:
    canvas = GlyphCanvas(MonoBitmap.solid(7, 12))
    assert canvas.vertical_offset(12) == (-4, 0)
    assert canvas.vertical_offset(12, 'left') == (-4, 0)
    assert canvas.vertical_offset(12, 'right') == (-3, 0)

    with pytest.raises(ValueError, match=re.escape('canvas width must be even unless horizontal_bias is specified')):
        canvas.vertical_offset(12, None)


def test_vertical_offset_with_vertical_bias() -> None:
    canvas = GlyphCanvas(MonoBitmap.solid(10, 15))

    with pytest.raises(ValueError, match=re.escape('canvas height and em size must have the same parity unless vertical_bias is specified')):
        canvas.vertical_offset(12)

    assert canvas.vertical_offset(12, vertical_bias='top') == (-5, -2)
    assert canvas.vertical_offset(12, vertical_bias='bottom') == (-5, -1)


def test_vertical_offset_with_smaller_canvas() -> None:
    canvas = GlyphCanvas(MonoBitmap.solid(10, 9))
    assert canvas.vertical_offset(12, vertical_bias='top') == (-5, 1)
    assert canvas.vertical_offset(12, vertical_bias='bottom') == (-5, 2)


def test_offsets_for_trimmed() -> None:
    canvas = GlyphCanvas(MonoBitmap.solid(7, 12).resize(left=1, right=2, top=2, bottom=2))
    assert canvas.horizontal_offset_for_trimmed(12, 10) == (1, -2)
    assert canvas.vertical_offset_for_trimmed(12) == (-4, 0)
    assert canvas.advance_width() == 10
    assert canvas.advance_height(12) == 12


def test_offsets_for_blank() -> None:
    canvas = GlyphCanvas(MonoBitmap.blank(7, 15))
    assert canvas.is_blank
    assert canvas.horizontal_offset_for_trimmed(12, 10) == (0, 0)
    assert canvas.vertical_offset_for_trimmed(12) == (0, 0)
    assert canvas.advance_width() == 7
    assert canvas.advance_height(12) == 12
