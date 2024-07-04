from collections import UserList
from os import PathLike
from typing import Any

import png


class MonoBitmap(UserList[list[int]]):
    @staticmethod
    def create(width: int, height: int, alpha: int = 0) -> 'MonoBitmap':
        bitmap = MonoBitmap()
        bitmap.width = width
        bitmap.height = height
        for _ in range(height):
            bitmap.append([0 if alpha == 0 else 1] * width)
        return bitmap

    @staticmethod
    def load_png(file_path: str | bytes | PathLike[str] | PathLike[bytes]) -> 'MonoBitmap':
        width, height, pixels, _ = png.Reader(filename=file_path).read()
        bitmap = MonoBitmap()
        bitmap.width = width
        bitmap.height = height
        for pixels_row in pixels:
            bitmap.append([1 if pixels_row[i + 3] > 127 else 0 for i in range(0, width * 4, 4)])
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
                    raise ValueError('Rows widths unequal')
                self.append([0 if alpha == 0 else 1 for alpha in bitmap_row])

    def __eq__(self, other: Any) -> bool:
        if isinstance(other, MonoBitmap):
            return (self.width == other.width and
                    self.height == other.height and
                    super().__eq__(other))
        return super().__eq__(other)

    def copy(self) -> 'MonoBitmap':
        bitmap = MonoBitmap()
        for bitmap_row in self:
            bitmap.append(bitmap_row[:])
        bitmap.width = self.width
        bitmap.height = self.height
        return bitmap

    def resize(self, left: int = 0, right: int = 0, top: int = 0, bottom: int = 0) -> 'MonoBitmap':
        bitmap = MonoBitmap()
        bitmap.width = self.width + left + right
        bitmap.height = self.height + top + bottom
        for y in range(bitmap.height):
            sy = y - top
            bitmap_row = []
            for x in range(bitmap.width):
                sx = x - left
                bitmap_row.append(self[sy][sx] if 0 <= sy < self.height and 0 <= sx < self.width else 0)
            bitmap.append(bitmap_row)
        return bitmap

    def save_png(
            self,
            file_path: str | bytes | PathLike[str] | PathLike[bytes],
            color: tuple[int, int, int] = (0, 0, 0),
    ):
        red, green, blue = color
        pixels = []
        for bitmap_row in self:
            pixels_row = []
            for alpha in bitmap_row:
                pixels_row.append(red)
                pixels_row.append(green)
                pixels_row.append(blue)
                pixels_row.append(255 if alpha != 0 else 0)
            pixels.append(pixels_row)
        png.from_array(pixels, 'RGBA').save(file_path)
