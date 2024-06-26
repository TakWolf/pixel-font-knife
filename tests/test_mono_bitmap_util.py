import hashlib
from pathlib import Path

from pixel_font_knife import mono_bitmap_util


def _file_sha256(file_path: Path) -> str:
    return hashlib.sha256(file_path.read_bytes()).hexdigest()


def test_load_save(assets_dir: Path, tmp_path: Path):
    load_file_path = assets_dir.joinpath('4E2D.png')
    save_file_path = tmp_path.joinpath('4E2D.png')

    bitmap, width, height = mono_bitmap_util.load_png(load_file_path)
    assert bitmap == [
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
    assert width == height == 12

    mono_bitmap_util.save_png(bitmap, save_file_path)
    assert _file_sha256(load_file_path) == _file_sha256(save_file_path)
