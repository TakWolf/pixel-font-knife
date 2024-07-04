from collections import UserList
from os import PathLike

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

    def copy(self) -> 'MonoBitmap':
        bitmap = MonoBitmap()
        for bitmap_row in self:
            bitmap.append(bitmap_row[:])
        bitmap.width = self.width
        bitmap.height = self.height
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
