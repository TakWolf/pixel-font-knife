import hashlib
from pathlib import Path

from pixel_font_knife import mono_bitmap_util


def _file_sha256(file_path: Path) -> str:
    return hashlib.sha256(file_path.read_bytes()).hexdigest()


def test_load_save(assets_dir: Path, tmp_path: Path):
    black_load_path = assets_dir.joinpath('png', '4E2D-black.png')
    black_save_path = tmp_path.joinpath('4E2D-black.png')
    black_bitmap, black_width, black_height = mono_bitmap_util.load_png(black_load_path)
    mono_bitmap_util.save_png(black_bitmap, black_save_path)

    red_load_path = assets_dir.joinpath('png', '4E2D-red.png')
    red_save_path = tmp_path.joinpath('4E2D-red.png')
    red_bitmap, red_width, red_height = mono_bitmap_util.load_png(red_load_path)
    mono_bitmap_util.save_png(red_bitmap, red_save_path, color=(255, 0, 0))

    assert black_bitmap == red_bitmap == [
        [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
        [0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0],
        [0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0],
        [1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 0],
        [1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0],
        [1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0],
        [1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0],
        [1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 0],
        [0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0],
        [0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0],
        [0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0],
        [0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0]
    ]
    assert black_width == red_width == 12
    assert black_height == red_height == 12
    assert _file_sha256(black_load_path) == _file_sha256(black_save_path)
    assert _file_sha256(red_load_path) == _file_sha256(red_save_path)
