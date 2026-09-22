import re
import sys
from collections.abc import Callable
from copy import copy, deepcopy
from io import BytesIO
from pathlib import Path

import pytest

from pixel_font_knife.bitmap.mono_bitmap import MonoBitmap
from pixel_font_knife.bitmap.padding import Padding


def test_init() -> None:
    bitmap = MonoBitmap([])
    assert bitmap.width == 0
    assert bitmap.height == 0
    assert bitmap.dimensions == (0, 0)
    assert bitmap == MonoBitmap()
    assert bitmap[:] == MonoBitmap()

    bitmap = MonoBitmap([
        [0, 1, 2, 3],
        [1, 0, 0, 1],
    ])
    assert bitmap.width == 4
    assert bitmap.height == 2
    assert bitmap.dimensions == (4, 2)
    assert bitmap == MonoBitmap([
        [0, 1, 1, 1],
        [1, 0, 0, 1],
    ])

    with pytest.raises(ValueError):
        MonoBitmap([
            [0, 1, 1],
            [1],
        ])


def test_blank() -> None:
    bitmap = MonoBitmap.blank(3, 4)
    assert bitmap.width == 3
    assert bitmap.height == 4
    assert bitmap.dimensions == (3, 4)
    assert bitmap == MonoBitmap([
        [0, 0, 0],
        [0, 0, 0],
        [0, 0, 0],
        [0, 0, 0],
    ])


def test_solid() -> None:
    bitmap = MonoBitmap.solid(3, 4)
    assert bitmap.width == 3
    assert bitmap.height == 4
    assert bitmap.dimensions == (3, 4)
    assert bitmap == MonoBitmap([
        [1, 1, 1],
        [1, 1, 1],
        [1, 1, 1],
        [1, 1, 1],
    ])


@pytest.mark.parametrize('factory', [MonoBitmap.blank, MonoBitmap.solid])
@pytest.mark.parametrize(('width', 'height'), [(-1, 0), (0, -1), (-1, -1)])
def test_factory_invalid_dimensions(factory: Callable[[int, int], MonoBitmap], width: int, height: int) -> None:
    with pytest.raises(ValueError, match=re.escape('bitmap dimensions must be non-negative')):
        factory(width, height)


@pytest.mark.parametrize('factory', [MonoBitmap.blank, MonoBitmap.solid])
def test_factory_zero_dimensions(factory: Callable[[int, int], MonoBitmap]) -> None:
    assert factory(0, 2).dimensions == (0, 2)
    assert factory(2, 0).dimensions == (2, 0)


def test_measure_padding() -> None:
    bitmap = MonoBitmap([
        [0, 0, 0, 0, 0, 0, 0],
        [0, 0, 0, 0, 0, 0, 0],
        [0, 0, 0, 0, 0, 0, 0],
        [0, 0, 1, 0, 1, 0, 0],
        [0, 1, 1, 0, 0, 0, 0],
        [0, 0, 1, 1, 1, 0, 0],
        [0, 0, 1, 0, 1, 0, 0],
        [0, 0, 0, 1, 0, 0, 0],
        [0, 0, 0, 0, 0, 0, 0],
    ])
    assert bitmap.measure_padding() == Padding(1, 2, 3, 1)
    assert bitmap.measure_left_padding() == 1
    assert bitmap.measure_right_padding() == 2
    assert bitmap.measure_top_padding() == 3
    assert bitmap.measure_bottom_padding() == 1


def test_measure_padding_inconsistent_dimensions() -> None:
    bitmap = MonoBitmap.blank(7, 10)
    bitmap.data = [[0] * 7 for _ in range(5)]
    with pytest.raises(ValueError, match=re.escape('inconsistent bitmap height')):
        bitmap.measure_padding()

    bitmap = MonoBitmap.blank(7, 5)
    bitmap[2] = [0] * 5
    with pytest.raises(ValueError, match=re.escape('inconsistent row widths')):
        bitmap.measure_padding()


def test_inside() -> None:
    bitmap = MonoBitmap.blank(50, 50)
    assert bitmap.is_x_inside(10)
    assert not bitmap.is_x_inside(-1)
    assert not bitmap.is_x_inside(60)
    assert bitmap.is_y_inside(25)
    assert not bitmap.is_y_inside(-5)
    assert not bitmap.is_y_inside(90)
    assert bitmap.is_inside(20, 40)
    assert not bitmap.is_inside(-6, 10)
    assert not bitmap.is_inside(15, 90)


def test_overlaps() -> None:
    bitmap_1 = MonoBitmap([
        [1, 1, 1, 0],
        [1, 1, 1, 0],
        [1, 1, 1, 0],
        [0, 0, 0, 0],
    ])
    bitmap_2 = MonoBitmap([
        [0, 0, 0, 0],
        [0, 1, 1, 1],
        [0, 1, 1, 1],
        [0, 1, 1, 1],
    ])
    assert bitmap_1.overlaps(bitmap_2)
    assert not bitmap_1.overlaps(bitmap_2, x=3, y=3)
    assert not bitmap_1.overlaps(bitmap_2, x=2, y=2)
    assert bitmap_1.overlaps(bitmap_2, x=1, y=1)
    assert bitmap_1.overlaps(bitmap_2, x=-1, y=-1)
    assert not bitmap_1.overlaps(bitmap_2, x=bitmap_1.width)
    assert not bitmap_1.overlaps(bitmap_2, y=bitmap_1.height)
    assert not bitmap_1.overlaps(bitmap_2, x=-bitmap_2.width)
    assert not bitmap_1.overlaps(bitmap_2, y=-bitmap_2.height)


def test_resize() -> None:
    bitmap = MonoBitmap([
        [1, 0, 1, 0],
        [1, 0, 0, 0],
        [1, 1, 1, 0],
        [0, 0, 1, 0],
    ])
    assert bitmap.resize(left=2, right=1, top=3, bottom=2) == MonoBitmap([
        [0, 0, 0, 0, 0, 0, 0],
        [0, 0, 0, 0, 0, 0, 0],
        [0, 0, 0, 0, 0, 0, 0],
        [0, 0, 1, 0, 1, 0, 0],
        [0, 0, 1, 0, 0, 0, 0],
        [0, 0, 1, 1, 1, 0, 0],
        [0, 0, 0, 0, 1, 0, 0],
        [0, 0, 0, 0, 0, 0, 0],
        [0, 0, 0, 0, 0, 0, 0],
    ])
    assert bitmap.resize(left=-1, right=-1, top=-1, bottom=-1) == MonoBitmap([
        [0, 0],
        [1, 1],
    ])
    assert bitmap.resize(left=-4).dimensions == (0, 4)
    assert bitmap.resize(top=-4).dimensions == (4, 0)


@pytest.mark.parametrize(
    'resize',
    [
        {'left': -5},
        {'right': -3, 'left': -2},
        {'top': -5},
        {'bottom': -3, 'top': -2},
    ],
)
def test_resize_invalid_dimensions(resize: dict[str, int]) -> None:
    with pytest.raises(ValueError, match=re.escape('bitmap dimensions must be non-negative')):
        MonoBitmap.blank(4, 4).resize(**resize)


def test_trim() -> None:
    bitmap = MonoBitmap([
        [0, 0, 0, 0, 0, 0, 0],
        [0, 0, 0, 0, 0, 0, 0],
        [0, 0, 0, 0, 0, 0, 0],
        [0, 0, 1, 0, 1, 0, 0],
        [0, 1, 1, 0, 0, 0, 0],
        [0, 0, 1, 1, 1, 0, 0],
        [0, 0, 1, 0, 1, 0, 0],
        [0, 0, 0, 1, 0, 0, 0],
        [0, 0, 0, 0, 0, 0, 0],
    ])
    trimmed_bitmap, padding = bitmap.trim()
    assert trimmed_bitmap == MonoBitmap([
        [0, 1, 0, 1],
        [1, 1, 0, 0],
        [0, 1, 1, 1],
        [0, 1, 0, 1],
        [0, 0, 1, 0],
    ])
    assert padding == Padding(1, 2, 3, 1)
    assert trimmed_bitmap is not bitmap
    for trimmed_row in trimmed_bitmap:
        assert all(trimmed_row is not bitmap_row for bitmap_row in bitmap)


def test_trim_empty() -> None:
    bitmap = MonoBitmap.blank(7, 10)
    trimmed_bitmap, padding = bitmap.trim()
    assert trimmed_bitmap == MonoBitmap.blank(0, 0)
    assert padding == Padding(7, 0, 10, 0)

    bitmap = MonoBitmap()
    trimmed_bitmap, padding = bitmap.trim()
    assert trimmed_bitmap == MonoBitmap.blank(0, 0)
    assert padding == Padding(0, 0, 0, 0)


def test_trim_inconsistent_dimensions() -> None:
    bitmap = MonoBitmap.blank(7, 10)
    bitmap.data = [[0] * 7 for _ in range(5)]
    with pytest.raises(ValueError, match=re.escape('inconsistent bitmap height')):
        bitmap.trim()

    bitmap = MonoBitmap.blank(7, 5)
    bitmap[2] = [0] * 5
    with pytest.raises(ValueError, match=re.escape('inconsistent row widths')):
        bitmap.trim()


def test_crop() -> None:
    bitmap = MonoBitmap([
        [0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
        [0, 0, 0, 0, 1, 0, 0, 0, 0, 0],
        [0, 0, 0, 0, 1, 0, 0, 0, 0, 0],
        [0, 0, 0, 0, 1, 0, 0, 0, 0, 0],
        [0, 0, 1, 1, 1, 1, 1, 1, 0, 0],
        [0, 0, 0, 0, 1, 0, 0, 0, 0, 0],
        [0, 0, 0, 0, 1, 0, 0, 0, 0, 0],
        [0, 0, 0, 0, 1, 0, 0, 0, 0, 0],
        [0, 0, 0, 0, 1, 0, 0, 0, 0, 0],
        [0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
    ])
    assert bitmap.crop(x=1, y=2, width=6, height=4) == MonoBitmap([
        [0, 0, 0, 1, 0, 0],
        [0, 0, 0, 1, 0, 0],
        [0, 1, 1, 1, 1, 1],
        [0, 0, 0, 1, 0, 0],
    ])
    assert bitmap.crop(x=10, y=2, width=0, height=4).dimensions == (0, 4)
    assert bitmap.crop(x=2, y=10, width=4, height=0).dimensions == (4, 0)


@pytest.mark.parametrize(
    ('x', 'y', 'width', 'height'),
    [
        (-1, 0, 1, 1),
        (0, -1, 1, 1),
        (0, 0, -1, 1),
        (0, 0, 1, -1),
        (9, 0, 2, 1),
        (0, 9, 1, 2),
    ],
)
def test_crop_invalid_rectangle(x: int, y: int, width: int, height: int) -> None:
    with pytest.raises(ValueError):
        MonoBitmap.blank(10, 10).crop(x, y, width, height)


def test_scale_to() -> None:
    bitmap = MonoBitmap([
        [1, 0, 1],
        [0, 1, 0],
    ])
    assert bitmap.scale_to(5, 3) == MonoBitmap([
        [1, 1, 0, 0, 1],
        [1, 1, 0, 0, 1],
        [0, 0, 1, 1, 0],
    ])
    assert bitmap.scale_to(2, 1) == MonoBitmap([
        [1, 0],
    ])


def test_scale(bitmaps_dir: Path) -> None:
    for file_path in bitmaps_dir.joinpath('x1').glob('*.png'):
        if not file_path.is_file():
            continue

        x1_bitmap = MonoBitmap.load_png(file_path)
        x3_bitmap = MonoBitmap.load_png(bitmaps_dir.joinpath('x3', file_path.name))
        x1_5_bitmap = MonoBitmap.load_png(bitmaps_dir.joinpath('x1.5', file_path.name))
        assert x1_bitmap.scale(3, 3) == x3_bitmap
        assert x1_bitmap.scale(1.5, 1.5) == x1_5_bitmap
        assert x3_bitmap.scale(1 / 3, 1 / 3) == x1_bitmap
        assert x3_bitmap.scale(0.5, 0.5) == x1_5_bitmap


def test_scale_rounds_dimensions() -> None:
    bitmap = MonoBitmap.solid(3, 3)
    assert bitmap.scale(0.5, 0.5).dimensions == (2, 2)
    assert bitmap.scale(1.5, 1.5).dimensions == (5, 5)


def test_scale_invalid_arguments() -> None:
    bitmap = MonoBitmap([[1]])

    for scale in (0, -1, float('inf'), float('-inf'), float('nan')):
        with pytest.raises(ValueError):
            bitmap.scale(scale_x=scale)
        with pytest.raises(ValueError):
            bitmap.scale(scale_y=scale)

    with pytest.raises(ValueError, match=re.escape('bitmap dimensions must be non-negative')):
        bitmap.scale_to(-1, 1)
    with pytest.raises(ValueError, match=re.escape('bitmap dimensions must be non-negative')):
        bitmap.scale_to(1, -1)
    with pytest.raises(ValueError, match=re.escape('scaled bitmap dimensions must be finite')):
        MonoBitmap.solid(2, 1).scale(sys.float_info.max)

    assert bitmap.scale_to(0, 1).dimensions == (0, 1)
    assert bitmap.scale_to(1, 0).dimensions == (1, 0)

    with pytest.raises(ValueError, match=re.escape('cannot scale a zero-sized bitmap')):
        MonoBitmap.blank(0, 0).scale_to(1, 1)


def test_set_operations() -> None:
    bitmap = MonoBitmap([
        [1, 1, 0],
        [1, 0, 0],
    ])
    other = MonoBitmap([
        [1, 0],
        [1, 1],
    ])

    assert bitmap.union(other, x=1) == MonoBitmap([
        [1, 1, 0],
        [1, 1, 1],
    ])
    assert bitmap.intersection(other, x=1) == MonoBitmap([
        [0, 1, 0],
        [0, 0, 0],
    ])
    assert bitmap.difference(other, x=1) == MonoBitmap([
        [1, 0, 0],
        [1, 0, 0],
    ])
    assert bitmap.symmetric_difference(other, x=1) == MonoBitmap([
        [1, 0, 0],
        [1, 1, 1],
    ])
    assert bitmap.intersection(other, x=3) == MonoBitmap.blank(3, 2)
    assert bitmap.union(other, x=-1, y=-1) == MonoBitmap([
        [1, 1, 0],
        [1, 0, 0],
    ])
    assert bitmap.intersection(other, x=-1, y=-1) == MonoBitmap([
        [1, 0, 0],
        [0, 0, 0],
    ])
    assert bitmap.difference(other, x=-1, y=-1) == MonoBitmap([
        [0, 1, 0],
        [1, 0, 0],
    ])
    assert bitmap.symmetric_difference(other, x=-1, y=-1) == MonoBitmap([
        [0, 1, 0],
        [1, 0, 0],
    ])


def test_dilate() -> None:
    bitmap = MonoBitmap([
        [0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
        [0, 0, 0, 0, 1, 0, 0, 0, 0, 0],
        [0, 0, 0, 0, 1, 0, 0, 0, 0, 0],
        [0, 0, 0, 0, 1, 0, 0, 0, 0, 0],
        [0, 0, 1, 1, 1, 1, 1, 1, 0, 0],
        [0, 0, 0, 0, 1, 0, 0, 0, 0, 0],
        [0, 0, 0, 0, 1, 0, 0, 0, 0, 0],
        [0, 0, 0, 0, 1, 0, 0, 0, 0, 0],
        [0, 0, 0, 0, 1, 0, 0, 0, 0, 0],
        [0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
    ])
    assert bitmap.dilate(1) == MonoBitmap([
        [0, 0, 0, 1, 1, 1, 0, 0, 0, 0],
        [0, 0, 0, 1, 1, 1, 0, 0, 0, 0],
        [0, 0, 0, 1, 1, 1, 0, 0, 0, 0],
        [0, 1, 1, 1, 1, 1, 1, 1, 1, 0],
        [0, 1, 1, 1, 1, 1, 1, 1, 1, 0],
        [0, 1, 1, 1, 1, 1, 1, 1, 1, 0],
        [0, 0, 0, 1, 1, 1, 0, 0, 0, 0],
        [0, 0, 0, 1, 1, 1, 0, 0, 0, 0],
        [0, 0, 0, 1, 1, 1, 0, 0, 0, 0],
        [0, 0, 0, 1, 1, 1, 0, 0, 0, 0],
    ])


def test_dilate_shapes() -> None:
    bitmap = MonoBitmap([
        [0, 0, 0, 0, 0],
        [0, 0, 0, 0, 0],
        [0, 0, 1, 0, 0],
        [0, 0, 0, 0, 0],
        [0, 0, 0, 0, 0],
    ])
    assert bitmap.dilate(1, 'orthogonal') == MonoBitmap([
        [0, 0, 0, 0, 0],
        [0, 0, 1, 0, 0],
        [0, 1, 1, 1, 0],
        [0, 0, 1, 0, 0],
        [0, 0, 0, 0, 0],
    ])
    assert bitmap.dilate(1, 'diagonal') == MonoBitmap([
        [0, 0, 0, 0, 0],
        [0, 1, 0, 1, 0],
        [0, 0, 1, 0, 0],
        [0, 1, 0, 1, 0],
        [0, 0, 0, 0, 0],
    ])
    assert bitmap.dilate(1, 'surrounding') == MonoBitmap([
        [0, 0, 0, 0, 0],
        [0, 1, 1, 1, 0],
        [0, 1, 1, 1, 0],
        [0, 1, 1, 1, 0],
        [0, 0, 0, 0, 0],
    ])
    assert bitmap.dilate(1) == bitmap.dilate(1, 'surrounding')


def test_dilate_radius() -> None:
    bitmap = MonoBitmap([
        [0, 0, 0, 0, 0],
        [0, 0, 0, 0, 0],
        [0, 0, 1, 0, 0],
        [0, 0, 0, 0, 0],
        [0, 0, 0, 0, 0],
    ])
    assert bitmap.dilate(2, 'orthogonal') == MonoBitmap([
        [0, 0, 1, 0, 0],
        [0, 0, 1, 0, 0],
        [1, 1, 1, 1, 1],
        [0, 0, 1, 0, 0],
        [0, 0, 1, 0, 0],
    ])
    assert bitmap.dilate(2, 'diagonal') == MonoBitmap([
        [1, 0, 0, 0, 1],
        [0, 1, 0, 1, 0],
        [0, 0, 1, 0, 0],
        [0, 1, 0, 1, 0],
        [1, 0, 0, 0, 1],
    ])


def test_dilate_invalid_arguments() -> None:
    bitmap = MonoBitmap([[1]])
    assert bitmap.dilate(0) == bitmap
    assert bitmap.dilate(0) is not bitmap

    with pytest.raises(ValueError, match=re.escape('dilation radius must be non-negative')):
        bitmap.dilate(-1)
    with pytest.raises(ValueError, match=re.escape('unsupported dilation shape')):
        bitmap.dilate(1, 'invalid')


def test_to_text() -> None:
    bitmap = MonoBitmap([
        [1, 1, 0, 0],
        [0, 0, 1, 1],
    ])
    text = ('████    *\n'
            '    ████*\n')
    assert bitmap.to_text(line_suffix='*') == text


@pytest.mark.skipif(sys.platform == 'win32', reason='PNG compression output differs on Windows')
def test_load_dump_save(bitmaps_dir: Path, tmp_path: Path) -> None:
    load_dir = bitmaps_dir.joinpath('x1')
    save_dir = tmp_path.joinpath('x1')
    save_dir.mkdir()

    for load_path in load_dir.glob('*.png'):
        if not load_path.is_file():
            continue

        bitmap = MonoBitmap.load_png(load_path)
        assert bitmap.width == 12
        assert bitmap.height == 12
        assert bitmap.dimensions == (12, 12)

        save_path = save_dir.joinpath(load_path.name)
        bitmap.save_png(save_path)
        stream = BytesIO()
        bitmap.dump_png(stream)
        assert load_path.read_bytes() == save_path.read_bytes() == stream.getvalue()


def test_dump_save_empty(tmp_path: Path) -> None:
    for bitmap in [MonoBitmap(), MonoBitmap([[], []]), MonoBitmap.blank(2, 0)]:
        with pytest.raises(ValueError, match=re.escape('cannot encode empty bitmap as PNG')):
            bitmap.dump_png(BytesIO())
        with pytest.raises(ValueError, match=re.escape('cannot encode empty bitmap as PNG')):
            bitmap.save_png(tmp_path.joinpath('empty.png'))


def test_copy() -> None:
    bitmap_1 = MonoBitmap([
        [0, 1],
        [1, 0],
    ])
    bitmap_2 = copy(bitmap_1)
    bitmap_3 = deepcopy(bitmap_1)

    assert bitmap_1 == bitmap_2
    assert bitmap_1 == bitmap_3
    assert bitmap_1 is not bitmap_2
    assert bitmap_1 is not bitmap_3

    for bitmap_row_1, bitmap_row_2, bitmap_row_3 in zip(bitmap_1, bitmap_2, bitmap_3):
        assert bitmap_row_1 is not bitmap_row_2
        assert bitmap_row_1 is not bitmap_row_3


def test_eq() -> None:
    bitmap_1 = MonoBitmap([
        [0, 1],
        [1, 0],
    ])
    bitmap_2 = MonoBitmap([
        [0, 1],
        [1, 0],
    ])
    assert bitmap_1 == bitmap_2


def test_move_right_and_overlap_bolding(bitmaps_dir: Path) -> None:
    for file_path in bitmaps_dir.joinpath('x1').glob('*.png'):
        if not file_path.is_file():
            continue

        bitmap = MonoBitmap.load_png(file_path)
        solid_bitmap = bitmap.resize(left=1).union(bitmap)
        shadow_bitmap = solid_bitmap.difference(bitmap).resize(left=1)
        result_bitmap = solid_bitmap.difference(shadow_bitmap)
        bold_bitmap = MonoBitmap.load_png(bitmaps_dir.joinpath('move-right-and-overlap-bolding', file_path.name))
        assert result_bitmap == bold_bitmap


def test_move_left_and_overlap_bolding(bitmaps_dir: Path) -> None:
    for file_path in bitmaps_dir.joinpath('x1').glob('*.png'):
        if not file_path.is_file():
            continue

        bitmap = MonoBitmap.load_png(file_path)
        solid_bitmap = bitmap.resize(right=1).union(bitmap, x=1)
        shadow_bitmap = solid_bitmap.difference(bitmap, x=1).resize(left=-1)
        result_bitmap = solid_bitmap.difference(shadow_bitmap)
        bold_bitmap = MonoBitmap.load_png(bitmaps_dir.joinpath('move-left-and-overlap-bolding', file_path.name))
        assert result_bitmap == bold_bitmap


def test_inflation_bolding(bitmaps_dir: Path) -> None:
    for file_path in bitmaps_dir.joinpath('x1').glob('*.png'):
        if not file_path.is_file():
            continue

        bitmap = MonoBitmap.load_png(file_path)
        result_bitmap = bitmap.scale(scale_x=4, scale_y=4).resize(left=1, right=1, top=1, bottom=1).dilate(1)
        result_bitmap = result_bitmap.scale(scale_x=0.5, scale_y=0.5)
        result_bitmap = result_bitmap.resize(left=1, right=-1, top=-1, bottom=1)
        bold_bitmap = MonoBitmap.load_png(bitmaps_dir.joinpath('inflation-bolding', file_path.name))
        assert result_bitmap == bold_bitmap
