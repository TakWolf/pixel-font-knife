from io import BytesIO
from pathlib import Path

import pytest

from pixel_font_knife.mono_bitmap import MonoBitmap


def test_init():
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


def test_create():
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


def test_eq():
    assert MonoBitmap([
        [0, 1],
        [1, 0],
    ]) == MonoBitmap([
        [0, 1],
        [1, 0],
    ])

    bitmap_1 = MonoBitmap([
        [1, 1, 1],
        [0, 0, 0],
    ])
    bitmap_2 = bitmap_1.copy()
    bitmap_2.width = 2
    bitmap_2.height = 3
    assert bitmap_1 != bitmap_2


def test_inside():
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


def test_calculate_padding():
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
    assert bitmap.calculate_left_padding() == 1
    assert bitmap.calculate_right_padding() == 2
    assert bitmap.calculate_top_padding() == 3
    assert bitmap.calculate_bottom_padding() == 1


def test_copy():
    bitmap = MonoBitmap([
        [0, 0, 0],
        [1, 0, 1],
        [0, 1, 0],
    ])
    copy_bitmap = bitmap.copy()
    assert bitmap == copy_bitmap
    assert bitmap is not copy_bitmap


def test_resize():
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


def test_scale(glyphs_dir: Path):
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


def test_plus_minus():
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


def test_pixel_expand():
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


def test_crop():
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


def test_draw():
    bitmap = MonoBitmap([
        [1, 1, 0, 0],
        [0, 0, 1, 1],
    ])
    text = ('████    *\n'
            '    ████*\n')
    assert bitmap.draw(end='*') == text


def test_load_dump_save(glyphs_dir: Path, tmp_path: Path):
    black_load_dir = glyphs_dir.joinpath('black')
    black_save_dir = tmp_path.joinpath('black')
    black_save_dir.mkdir()

    red_load_dir = glyphs_dir.joinpath('red')
    red_save_dir = tmp_path.joinpath('red')
    red_save_dir.mkdir()

    for black_load_path, red_load_path in zip(sorted(black_load_dir.iterdir()), sorted(red_load_dir.iterdir())):
        if black_load_path.suffix != '.png' or red_load_path.suffix != '.png':
            continue

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


def test_move_right_and_overlap_bolding(glyphs_dir: Path):
    for file_path in glyphs_dir.joinpath('black').iterdir():
        if file_path.suffix != '.png':
            continue

        bitmap = MonoBitmap.load_png(file_path)
        solid_bitmap = bitmap.resize(left=1).plus(bitmap)
        shadow_bitmap = solid_bitmap.minus(bitmap).resize(left=1)
        result_bitmap = solid_bitmap.minus(shadow_bitmap)
        bold_bitmap = MonoBitmap.load_png(glyphs_dir.joinpath('move-right-and-overlap-bolding', file_path.name))
        assert result_bitmap == bold_bitmap


def test_move_left_and_overlap_bolding(glyphs_dir: Path):
    for file_path in glyphs_dir.joinpath('black').iterdir():
        if file_path.suffix != '.png':
            continue

        bitmap = MonoBitmap.load_png(file_path)
        solid_bitmap = bitmap.resize(right=1).plus(bitmap, x=1)
        shadow_bitmap = solid_bitmap.minus(bitmap, x=1).resize(left=-1)
        result_bitmap = solid_bitmap.minus(shadow_bitmap)
        bold_bitmap = MonoBitmap.load_png(glyphs_dir.joinpath('move-left-and-overlap-bolding', file_path.name))
        assert result_bitmap == bold_bitmap


def test_inflation_bolding(glyphs_dir: Path):
    for file_path in glyphs_dir.joinpath('black').iterdir():
        if file_path.suffix != '.png':
            continue

        bitmap = MonoBitmap.load_png(file_path)
        result_bitmap = bitmap.scale(scale_x=4, scale_y=4).resize(left=1, right=1, top=1, bottom=1).pixel_expand(1)
        result_bitmap = result_bitmap.scale(scale_x=0.5, scale_y=0.5)
        result_bitmap = result_bitmap.resize(left=1, right=-1, top=-1, bottom=1)
        bold_bitmap = MonoBitmap.load_png(glyphs_dir.joinpath('inflation-bolding', file_path.name))
        assert result_bitmap == bold_bitmap
