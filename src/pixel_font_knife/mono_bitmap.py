from collections import UserList
from os import PathLike

import png


class MonoBitmap(UserList[list[int]]):
    @staticmethod
    def cost(source: list[list[int]]) -> 'MonoBitmap':
        bitmap = MonoBitmap(0, 0)
        bitmap.width = len(source[0])
        bitmap.height = len(source)
        for source_row in source:
            if bitmap.width != len(source_row):
                raise ValueError('Rows widths unequal')
            bitmap.append([0 if alpha == 0 else 1 for alpha in source_row])
        return bitmap

    @staticmethod
    def load_png(file_path: str | bytes | PathLike[str] | PathLike[bytes]) -> 'MonoBitmap':
        width, height, pixels, _ = png.Reader(filename=file_path).read()
        bitmap = MonoBitmap(0, 0)
        bitmap.width = width
        bitmap.height = height
        for pixels_row in pixels:
            bitmap.append([1 if pixels_row[i + 3] > 127 else 0 for i in range(0, width * 4, 4)])
        return bitmap

    width: int
    height: int

    def __init__(self, width: int, height: int, alpha: int = 0):
        super().__init__()
        self.width = width
        self.height = height
        for _ in range(height):
            self.append([alpha] * width)

    def copy(self) -> 'MonoBitmap':
        bitmap = MonoBitmap(0, 0)
        bitmap.width = self.width
        bitmap.height = self.height
        for bitmap_row in self:
            bitmap.append(bitmap_row[:])
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
