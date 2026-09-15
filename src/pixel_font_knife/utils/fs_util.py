import os
from os import PathLike
from pathlib import Path

from pixel_font_knife.bitmap.mono_bitmap import MonoBitmap


def is_empty_dir(path: str | PathLike[str]) -> bool:
    items = os.listdir(path)
    if '.DS_Store' in items:
        items.remove('.DS_Store')
    return len(items) == 0


def format_glyph_files(root_dir: str | PathLike[str]) -> None:
    if not isinstance(root_dir, Path):
        root_dir = Path(root_dir)

    for file_dir, _, file_names in root_dir.walk():
        for file_name in file_names:
            if not file_name.endswith('.png'):
                continue

            file_path = file_dir.joinpath(file_name)
            bitmap = MonoBitmap.load_png(file_path)
            bitmap.save_png(file_path)
