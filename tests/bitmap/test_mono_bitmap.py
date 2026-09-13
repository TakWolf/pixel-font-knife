import sys
from copy import copy, deepcopy
from io import BytesIO
from pathlib import Path

import pytest

from pixel_font_knife.bitmap.mono_bitmap import Paddings, MonoBitmap


def test_init() -> None:
    bitmap = MonoBitmap([])
    assert bitmap.width == 0
    assert bitmap.height == 0
    assert bitmap == MonoBitmap()
    assert bitmap[:] == MonoBitmap()

    bitmap = MonoBitmap([
        [0, 1, 2, 3],
        [1, 0, 0, 1],
    ])
    assert bitmap.width == 4
    assert bitmap.height == 2
    assert bitmap == MonoBitmap([
        [0, 1, 1, 1],
        [1, 0, 0, 1],
    ])

    with pytest.raises(ValueError):
        MonoBitmap([
            [0, 1, 1],
            [1],
        ])


def test_create() -> None:
    bitmap = MonoBitmap.create(3, 4)
    assert bitmap.width == 3
    assert bitmap.height == 4
    assert bitmap == MonoBitmap([
        [0, 0, 0],
        [0, 0, 0],
        [0, 0, 0],
        [0, 0, 0],
    ])

    bitmap = MonoBitmap.create(2, 3, filled=True)
    assert bitmap.width == 2
    assert bitmap.height == 3
    assert bitmap == MonoBitmap([
        [1, 1],
        [1, 1],
        [1, 1],
    ])


def test_inside() -> None:
    bitmap = MonoBitmap.create(50, 50)
    assert bitmap.is_x_inside(10)
    assert not bitmap.is_x_inside(-1)
    assert not bitmap.is_x_inside(60)
    assert bitmap.is_y_inside(25)
    assert not bitmap.is_y_inside(-5)
    assert not bitmap.is_y_inside(90)
    assert bitmap.is_inside(20, 40)
    assert not bitmap.is_inside(-6, 10)
    assert not bitmap.is_inside(15, 90)


def test_calculate_padding() -> None:
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
    assert bitmap.calculate_paddings() == Paddings(1, 2, 3, 1)
    assert bitmap.calculate_left_padding() == 1
    assert bitmap.calculate_right_padding() == 2
    assert bitmap.calculate_top_padding() == 3
    assert bitmap.calculate_bottom_padding() == 1


def test_calculate_paddings_inconsistent_dimensions() -> None:
    bitmap = MonoBitmap.create(7, 10)
    bitmap.data = [[0] * 7 for _ in range(5)]
    with pytest.raises(ValueError, match='inconsistent bitmap height'):
        bitmap.calculate_paddings()

    bitmap = MonoBitmap.create(7, 5)
    bitmap[2] = [0] * 5
    with pytest.raises(ValueError, match='inconsistent row widths'):
        bitmap.calculate_paddings()


def test_optimize() -> None:
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
    optimized_bitmap, paddings = bitmap.optimize()
    assert optimized_bitmap == MonoBitmap([
        [0, 1, 0, 1],
        [1, 1, 0, 0],
        [0, 1, 1, 1],
        [0, 1, 0, 1],
        [0, 0, 1, 0],
    ])
    assert paddings == Paddings(1, 2, 3, 1)
    assert optimized_bitmap is not bitmap
    for optimized_row in optimized_bitmap:
        assert all(optimized_row is not bitmap_row for bitmap_row in bitmap)


def test_optimize_empty() -> None:
    bitmap = MonoBitmap.create(7, 10)
    optimized_bitmap, paddings = bitmap.optimize()
    assert optimized_bitmap == MonoBitmap.create(0, 0)
    assert paddings == Paddings(7, 0, 10, 0)

    bitmap = MonoBitmap()
    optimized_bitmap, paddings = bitmap.optimize()
    assert optimized_bitmap == MonoBitmap.create(0, 0)
    assert paddings == Paddings(0, 0, 0, 0)


def test_optimize_inconsistent_dimensions() -> None:
    bitmap = MonoBitmap.create(7, 10)
    bitmap.data = [[0] * 7 for _ in range(5)]
    with pytest.raises(ValueError, match='inconsistent bitmap height'):
        bitmap.optimize()

    bitmap = MonoBitmap.create(7, 5)
    bitmap[2] = [0] * 5
    with pytest.raises(ValueError, match='inconsistent row widths'):
        bitmap.optimize()


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


def test_scale(glyphs_dir: Path) -> None:
    for file_path in glyphs_dir.joinpath('black').iterdir():
        if file_path.suffix != '.png':
            continue

        x1_bitmap = MonoBitmap.load_png(file_path)
        x3_bitmap = MonoBitmap.load_png(glyphs_dir.joinpath('x3', file_path.name))
        x1_5_bitmap = MonoBitmap.load_png(glyphs_dir.joinpath('x1.5', file_path.name))
        assert x1_bitmap.scale(3, 3) == x3_bitmap
        assert x1_bitmap.scale(1.5, 1.5) == x1_5_bitmap
        assert x3_bitmap.scale(1 / 3, 1 / 3) == x1_bitmap
        assert x3_bitmap.scale(0.5, 0.5) == x1_5_bitmap


def test_plus_minus() -> None:
    bitmap = MonoBitmap([
        [1, 1, 1, 1],
        [1, 0, 0, 1],
        [1, 0, 0, 1],
        [1, 1, 1, 1],
    ])
    assert bitmap.plus(MonoBitmap([
        [1, 1, 1],
        [1, 1, 1],
    ]), x=-1, y=1) == MonoBitmap([
        [1, 1, 1, 1],
        [1, 1, 0, 1],
        [1, 1, 0, 1],
        [1, 1, 1, 1],
    ])
    assert bitmap.minus(MonoBitmap([
        [1, 1, 1],
        [1, 1, 1],
    ]), x=-1, y=1) == MonoBitmap([
        [1, 1, 1, 1],
        [0, 0, 0, 1],
        [0, 0, 0, 1],
        [1, 1, 1, 1],
    ])


def test_is_overlapped() -> None:
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
    assert bitmap_1.is_overlapped(bitmap_2)
    assert not bitmap_1.is_overlapped(bitmap_2, x=3, y=3)
    assert not bitmap_1.is_overlapped(bitmap_2, x=2, y=2)
    assert bitmap_1.is_overlapped(bitmap_2, x=1, y=1)


def test_pixel_expand() -> None:
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
    assert bitmap.pixel_expand(1) == MonoBitmap([
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


def test_draw() -> None:
    bitmap = MonoBitmap([
        [1, 1, 0, 0],
        [0, 0, 1, 1],
    ])
    text = ('████    *\n'
            '    ████*\n')
    assert bitmap.draw(end='*') == text


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


def test_dump_save_empty(tmp_path: Path) -> None:
    for bitmap in [MonoBitmap(), MonoBitmap([[], []]), MonoBitmap.create(2, 0)]:
        with pytest.raises(ValueError, match='cannot encode empty bitmap as PNG'):
            bitmap.dump_png(BytesIO())
        with pytest.raises(ValueError, match='cannot encode empty bitmap as PNG'):
            bitmap.save_png(tmp_path.joinpath('empty.png'))


@pytest.mark.skipif(sys.platform == 'win32', reason='PNG compression output differs on Windows')
def test_load_dump_save(glyphs_dir: Path, tmp_path: Path) -> None:
    black_load_dir = glyphs_dir.joinpath('black')
    black_save_dir = tmp_path.joinpath('black')
    black_save_dir.mkdir()

    red_load_dir = glyphs_dir.joinpath('red')
    red_save_dir = tmp_path.joinpath('red')
    red_save_dir.mkdir()

    for black_load_path in black_load_dir.iterdir():
        if black_load_path.suffix != '.png':
            continue
        red_load_path = red_load_dir.joinpath(black_load_path.name)

        assert black_load_path.name == red_load_path.name
        black_bitmap = MonoBitmap.load_png(black_load_path)
        red_bitmap = MonoBitmap.load_png(red_load_path)
        assert black_bitmap == red_bitmap
        assert black_bitmap.width == red_bitmap.width == 12
        assert black_bitmap.height == red_bitmap.height == 12

        black_save_path = black_save_dir.joinpath(black_load_path.name)
        black_bitmap.save_png(black_save_path)
        black_stream = BytesIO()
        black_bitmap.dump_png(black_stream)
        assert black_load_path.read_bytes() == black_save_path.read_bytes() == black_stream.getvalue()

        red_save_path = red_save_dir.joinpath(red_load_path.name)
        red_bitmap.save_png(red_save_path, color=(255, 0, 0))
        red_stream = BytesIO()
        red_bitmap.dump_png(red_stream, color=(255, 0, 0))
        assert red_load_path.read_bytes() == red_save_path.read_bytes() == red_stream.getvalue()


def test_move_right_and_overlap_bolding(glyphs_dir: Path) -> None:
    for file_path in glyphs_dir.joinpath('black').iterdir():
        if file_path.suffix != '.png':
            continue

        bitmap = MonoBitmap.load_png(file_path)
        solid_bitmap = bitmap.resize(left=1).plus(bitmap)
        shadow_bitmap = solid_bitmap.minus(bitmap).resize(left=1)
        result_bitmap = solid_bitmap.minus(shadow_bitmap)
        bold_bitmap = MonoBitmap.load_png(glyphs_dir.joinpath('move-right-and-overlap-bolding', file_path.name))
        assert result_bitmap == bold_bitmap


def test_move_left_and_overlap_bolding(glyphs_dir: Path) -> None:
    for file_path in glyphs_dir.joinpath('black').iterdir():
        if file_path.suffix != '.png':
            continue

        bitmap = MonoBitmap.load_png(file_path)
        solid_bitmap = bitmap.resize(right=1).plus(bitmap, x=1)
        shadow_bitmap = solid_bitmap.minus(bitmap, x=1).resize(left=-1)
        result_bitmap = solid_bitmap.minus(shadow_bitmap)
        bold_bitmap = MonoBitmap.load_png(glyphs_dir.joinpath('move-left-and-overlap-bolding', file_path.name))
        assert result_bitmap == bold_bitmap


def test_inflation_bolding(glyphs_dir: Path) -> None:
    for file_path in glyphs_dir.joinpath('black').iterdir():
        if file_path.suffix != '.png':
            continue

        bitmap = MonoBitmap.load_png(file_path)
        result_bitmap = bitmap.scale(scale_x=4, scale_y=4).resize(left=1, right=1, top=1, bottom=1).pixel_expand(1)
        result_bitmap = result_bitmap.scale(scale_x=0.5, scale_y=0.5)
        result_bitmap = result_bitmap.resize(left=1, right=-1, top=-1, bottom=1)
        bold_bitmap = MonoBitmap.load_png(glyphs_dir.joinpath('inflation-bolding', file_path.name))
        assert result_bitmap == bold_bitmap
