import hashlib
from pathlib import Path

import pytest

from pixel_font_knife.mono_bitmap import MonoBitmap


def _file_sha256(file_path: Path) -> str:
    return hashlib.sha256(file_path.read_bytes()).hexdigest()


def test_init():
    bitmap = MonoBitmap([
        [0, 1, 2, 3],
        [1, 0, 0, 1],
    ])
    assert bitmap.width == 4
    assert bitmap.height == 2
    assert bitmap == [
        [0, 1, 1, 1],
        [1, 0, 0, 1],
    ]

    with pytest.raises(ValueError):
        MonoBitmap([
            [0, 1, 2],
            [],
        ])


def test_create():
    bitmap = MonoBitmap.create(3, 4)
    assert bitmap.width == 3
    assert bitmap.height == 4
    assert bitmap == [
        [0, 0, 0],
        [0, 0, 0],
        [0, 0, 0],
        [0, 0, 0],
    ]

    bitmap = MonoBitmap.create(2, 3, alpha=2)
    assert bitmap.width == 2
    assert bitmap.height == 3
    assert bitmap == [
        [1, 1],
        [1, 1],
        [1, 1],
    ]


def test_copy():
    bitmap = MonoBitmap([
        [0, 0, 0],
        [1, 0, 1],
        [0, 1, 0],
    ])
    copy_bitmap = bitmap.copy()
    assert bitmap == copy_bitmap
    assert bitmap is not copy_bitmap


def test_load_save(glyphs_dir: Path, tmp_path: Path):
    black_load_dir = glyphs_dir.joinpath('black')
    black_save_dir = tmp_path.joinpath('black')
    black_save_dir.mkdir()

    red_load_dir = glyphs_dir.joinpath('red')
    red_save_dir = tmp_path.joinpath('red')
    red_save_dir.mkdir()

    for black_load_path, red_load_path in zip(sorted(black_load_dir.iterdir()), sorted(red_load_dir.iterdir())):
        assert black_load_path.name == red_load_path.name
        black_bitmap = MonoBitmap.load_png(black_load_path)
        red_bitmap = MonoBitmap.load_png(red_load_path)
        assert black_bitmap == red_bitmap
        assert black_bitmap.width == red_bitmap.width == 12
        assert black_bitmap.height == red_bitmap.height == 12

        black_save_path = black_save_dir.joinpath(black_load_path.name)
        black_bitmap.save_png(black_save_path)
        assert _file_sha256(black_load_path) == _file_sha256(black_save_path)

        red_save_path = red_save_dir.joinpath(red_load_path.name)
        red_bitmap.save_png(red_save_path, color=(255, 0, 0))
        assert _file_sha256(red_load_path) == _file_sha256(red_save_path)