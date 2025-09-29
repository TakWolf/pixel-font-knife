from __future__ import annotations

from collections import UserList
from io import StringIO
from os import PathLike
from typing import Any, BinaryIO

import png


class MonoBitmap(UserList[list[int]]):
    @staticmethod
    def create(width: int, height: int, filled: bool = False) -> MonoBitmap:
        bitmap = MonoBitmap()
        bitmap.width = width
        bitmap.height = height
        for _ in range(height):
            bitmap.append([1 if filled else 0] * width)
        return bitmap

    @staticmethod
    def load_png(file_path: str | PathLike[str]) -> MonoBitmap:
        width, height, pixels, _ = png.Reader(filename=file_path).read()
        bitmap = MonoBitmap()
        bitmap.width = width
        bitmap.height = height
        for pixels_row in pixels:
            bitmap_row = []
            for i in range(0, width * 4, 4):
                bitmap_row.append(1 if pixels_row[i + 3] > 127 else 0)
            bitmap.append(bitmap_row)
        return bitmap

    width: int
    height: int

    def __init__(self, bitmap: list[list[int]] | None = None):
        super().__init__()
        if bitmap is None:
            self.width = 0
            self.height = 0
        else:
            self.width = len(bitmap[0])
            self.height = len(bitmap)
            for bitmap_row in bitmap:
                if self.width != len(bitmap_row):
                    raise ValueError('rows with and widths are not equal')
                self.append([0 if color == 0 else 1 for color in bitmap_row])

    def __eq__(self, other: Any) -> bool:
        if not isinstance(other, MonoBitmap):
            return NotImplemented
        return (self.width == other.width and
                self.height == other.height and
                super().__eq__(other))

    def is_x_inside(self, x: int) -> bool:
        return 0 <= x < self.width

    def is_y_inside(self, y: int) -> bool:
        return 0 <= y < self.height

    def is_inside(self, x: int, y: int) -> bool:
        return self.is_x_inside(x) and self.is_y_inside(y)

    def calculate_left_padding(self) -> int:
        padding = 0
        for i in range(self.width):
            if any(bitmap_row[i] != 0 for bitmap_row in self):
                break
            padding += 1
        return padding

    def calculate_right_padding(self) -> int:
        padding = 0
        for i in range(self.width):
            if any(bitmap_row[-1 - i] != 0 for bitmap_row in self):
                break
            padding += 1
        return padding

    def calculate_top_padding(self) -> int:
        padding = 0
        for bitmap_row in self:
            if any(color != 0 for color in bitmap_row):
                break
            padding += 1
        return padding

    def calculate_bottom_padding(self) -> int:
        padding = 0
        for bitmap_row in reversed(self):
            if any(color != 0 for color in bitmap_row):
                break
            padding += 1
        return padding

    def copy(self) -> MonoBitmap:
        bitmap = MonoBitmap()
        for bitmap_row in self:
            bitmap.append(bitmap_row[:])
        bitmap.width = self.width
        bitmap.height = self.height
        return bitmap

    def resize(self, left: int = 0, right: int = 0, top: int = 0, bottom: int = 0) -> MonoBitmap:
        bitmap = MonoBitmap()
        bitmap.width = self.width + left + right
        bitmap.height = self.height + top + bottom
        for y in range(bitmap.height):
            sy = y - top
            bitmap_row = []
            for x in range(bitmap.width):
                sx = x - left
                bitmap_row.append(self[sy][sx] if self.is_inside(sx, sy) else 0)
            bitmap.append(bitmap_row)
        return bitmap

    def scale(self, scale_x: float = 1, scale_y: float = 1) -> MonoBitmap:
        bitmap = MonoBitmap()
        bitmap.width = int(self.width * scale_x)
        bitmap.height = int(self.height * scale_y)
        for y in range(bitmap.height):
            sy = int(y / scale_y)
            bitmap_row = []
            for x in range(bitmap.width):
                sx = int(x / scale_x)
                bitmap_row.append(self[sy][sx])
            bitmap.append(bitmap_row)
        return bitmap

    def plus(self, other: MonoBitmap, x: int = 0, y: int = 0) -> MonoBitmap:
        bitmap = self.copy()
        for oy, other_row in enumerate(other):
            ty = oy + y
            if not bitmap.is_y_inside(ty):
                continue
            for ox, color in enumerate(other_row):
                tx = ox + x
                if not bitmap.is_x_inside(tx):
                    continue
                if color != 0:
                    bitmap[ty][tx] = 1
        return bitmap

    def minus(self, other: MonoBitmap, x: int = 0, y: int = 0) -> MonoBitmap:
        bitmap = self.copy()
        for oy, other_row in enumerate(other):
            ty = oy + y
            if not bitmap.is_y_inside(ty):
                continue
            for ox, color in enumerate(other_row):
                tx = ox + x
                if not bitmap.is_x_inside(tx):
                    continue
                if color != 0:
                    bitmap[ty][tx] = 0
        return bitmap

    def is_overlapped(self, other: MonoBitmap, x: int = 0, y: int = 0) -> bool:
        for oy, other_row in enumerate(other):
            ty = oy + y
            if not self.is_y_inside(ty):
                continue
            for ox, color in enumerate(other_row):
                tx = ox + x
                if not self.is_x_inside(tx):
                    continue
                if color != 0 and self[ty][tx] != 0:
                    return True
        return False

    def pixel_expand(self, size: int) -> MonoBitmap:
        if size <= 0:
            raise ValueError(f'the stroke size must be a positive number: {size}')

        bitmap = self.copy()
        for y, source_row in enumerate(self):
            for x, color in enumerate(source_row):
                if color == 0:
                    continue
                for ty in range(y - size, y + size + 1):
                    if not bitmap.is_y_inside(ty):
                        continue
                    for tx in range(x - size, x + size + 1):
                        if not bitmap.is_x_inside(tx):
                            continue
                        bitmap[ty][tx] = 1
        return bitmap

    def crop(self, x: int, y: int, width: int, height: int) -> MonoBitmap:
        bitmap = MonoBitmap()
        bitmap.width = width
        bitmap.height = height
        for ny in range(height):
            sy = ny + y
            bitmap_row = []
            for nx in range(width):
                sx = nx + x
                bitmap_row.append(self[sy][sx])
            bitmap.append(bitmap_row)
        return bitmap

    def draw(self, white: str = '  ', black: str = '██', end: str | None = None) -> str:
        text = StringIO()
        for bitmap_row in self:
            for color in bitmap_row:
                text.write(white if color == 0 else black)
            if end is not None:
                text.write(end)
            text.write('\n')
        return text.getvalue()

    def _build_png(self, color: tuple[int, int, int]) -> png.Image:
        red, green, blue = color
        pixels = []
        for bitmap_row in self:
            pixels_row = []
            for color in bitmap_row:
                pixels_row.append(red)
                pixels_row.append(green)
                pixels_row.append(blue)
                pixels_row.append(255 if color != 0 else 0)
            pixels.append(pixels_row)
        return png.from_array(pixels, 'RGBA')

    def dump_png(self, stream: BinaryIO, color: tuple[int, int, int] = (0, 0, 0)):
        self._build_png(color).write(stream)

    def save_png(self, file_path: str | PathLike[str], color: tuple[int, int, int] = (0, 0, 0)):
        self._build_png(color).save(file_path)
