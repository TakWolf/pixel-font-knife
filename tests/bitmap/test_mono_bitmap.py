import re
from pathlib import Path

import pytest

from pixel_font_knife.bitmap.mono import MonoBitmap


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
