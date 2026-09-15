from __future__ import annotations

from collections import UserList
from io import StringIO
from os import PathLike
from typing import Any, BinaryIO

from pixel_font_knife.bitmap.padding import Padding
from pixel_font_knife.internal import png


class MonoBitmap(UserList[list[int]]):
    @staticmethod
    def blank(width: int, height: int) -> MonoBitmap:
        bitmap = MonoBitmap()
        bitmap.width = width
        bitmap.height = height
        for _ in range(height):
            bitmap.append([0] * width)
        return bitmap

    @staticmethod
    def solid(width: int, height: int) -> MonoBitmap:
        bitmap = MonoBitmap()
        bitmap.width = width
        bitmap.height = height
        for _ in range(height):
            bitmap.append([1] * width)
        return bitmap

    @staticmethod
    def load_png(file_path: str | PathLike[str]) -> MonoBitmap:
        width, height, rows, _ = png.Reader(filename=file_path).read()
        bitmap = MonoBitmap()
        bitmap.width = width
        bitmap.height = height
        for row in rows:
            bitmap_row = []
            for i in range(0, width * 4, 4):
                bitmap_row.append(1 if row[i + 3] > 127 else 0)
            bitmap.append(bitmap_row)
        return bitmap

    width: int
    height: int

    def __init__(self, bitmap: list[list[int]] | None = None) -> None:
        super().__init__()
        if bitmap is None or len(bitmap) == 0:
            self.width = 0
            self.height = 0
        else:
            self.width = len(bitmap[0])
            self.height = len(bitmap)
            for bitmap_row in bitmap:
                if self.width != len(bitmap_row):
                    raise ValueError('inconsistent row widths')
                self.append([0 if pixel == 0 else 1 for pixel in bitmap_row])

    def __copy__(self) -> MonoBitmap:
        return self.copy()

    def __deepcopy__(self, memo: dict[int, Any]) -> MonoBitmap:
        return self.deepcopy()

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, MonoBitmap):
            return NotImplemented
        return (self.width == other.width and
                self.height == other.height and
                super().__eq__(other))

    @property
    def dimensions(self) -> tuple[int, int]:
        return self.width, self.height

    def is_x_inside(self, x: int) -> bool:
        return 0 <= x < self.width

    def is_y_inside(self, y: int) -> bool:
        return 0 <= y < self.height

    def is_inside(self, x: int, y: int) -> bool:
        return self.is_x_inside(x) and self.is_y_inside(y)

    def measure_padding(self) -> Padding:
        if self.height != len(self):
            raise ValueError('inconsistent bitmap height')

        first_row = self.height
        last_row = -1
        first_col = self.width
        last_col = -1

        for y, bitmap_row in enumerate(self):
            if self.width != len(bitmap_row):
                raise ValueError('inconsistent row widths')
            for x, pixel in enumerate(bitmap_row):
                if pixel != 0:
                    if y < first_row:
                        first_row = y
                    if y > last_row:
                        last_row = y
                    if x < first_col:
                        first_col = x
                    if x > last_col:
                        last_col = x

        if first_row == self.height:
            return Padding(self.width, 0, self.height, 0)

        return Padding(
            first_col,
            self.width - 1 - last_col,
            first_row,
            self.height - 1 - last_row,
        )

    def measure_left_padding(self) -> int:
        padding = 0
        for i in range(self.width):
            if any(bitmap_row[i] != 0 for bitmap_row in self):
                break
            padding += 1
        return padding

    def measure_right_padding(self) -> int:
        padding = 0
        for i in range(self.width):
            if any(bitmap_row[-1 - i] != 0 for bitmap_row in self):
                break
            padding += 1
        return padding

    def measure_top_padding(self) -> int:
        padding = 0
        for bitmap_row in self:
            if any(pixel != 0 for pixel in bitmap_row):
                break
            padding += 1
        return padding

    def measure_bottom_padding(self) -> int:
        padding = 0
        for bitmap_row in reversed(self):
            if any(pixel != 0 for pixel in bitmap_row):
                break
            padding += 1
        return padding

    def trim(self) -> tuple[MonoBitmap, Padding]:
        padding = self.measure_padding()
        bitmap = MonoBitmap()
        bitmap.width = self.width - padding.left - padding.right
        bitmap.height = self.height - padding.top - padding.bottom
        end_x = self.width - padding.right
        end_y = self.height - padding.bottom
        for bitmap_row in self.data[padding.top:end_y]:
            bitmap.append(bitmap_row[padding.left:end_x])
        return bitmap, padding

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
            for ox, pixel in enumerate(other_row):
                tx = ox + x
                if not bitmap.is_x_inside(tx):
                    continue
                if pixel != 0:
                    bitmap[ty][tx] = 1
        return bitmap

    def minus(self, other: MonoBitmap, x: int = 0, y: int = 0) -> MonoBitmap:
        bitmap = self.copy()
        for oy, other_row in enumerate(other):
            ty = oy + y
            if not bitmap.is_y_inside(ty):
                continue
            for ox, pixel in enumerate(other_row):
                tx = ox + x
                if not bitmap.is_x_inside(tx):
                    continue
                if pixel != 0:
                    bitmap[ty][tx] = 0
        return bitmap

    def overlaps(self, other: MonoBitmap, x: int = 0, y: int = 0) -> bool:
        for oy, other_row in enumerate(other):
            ty = oy + y
            if not self.is_y_inside(ty):
                continue
            for ox, pixel in enumerate(other_row):
                tx = ox + x
                if not self.is_x_inside(tx):
                    continue
                if pixel != 0 and self[ty][tx] != 0:
                    return True
        return False

    def dilate(self, size: int) -> MonoBitmap:
        if size <= 0:
            raise ValueError(f'stroke size must be positive: {size}')

        bitmap = self.copy()
        for y, source_row in enumerate(self):
            for x, pixel in enumerate(source_row):
                if pixel == 0:
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

    def to_text(self, off: str = '  ', on: str = '██', line_suffix: str | None = None) -> str:
        text = StringIO()
        for bitmap_row in self:
            for pixel in bitmap_row:
                text.write(off if pixel == 0 else on)
            if line_suffix is not None:
                text.write(line_suffix)
            text.write('\n')
        return text.getvalue()

    def _build_png(self) -> png.Image:
        if self.width == 0 or self.height == 0:
            raise ValueError('cannot encode empty bitmap as PNG')

        rows = []
        for bitmap_row in self:
            row = []
            for pixel in bitmap_row:
                row.extend((0, 0, 0, 255 if pixel != 0 else 0))
            rows.append(row)
        return png.from_array(rows, 'RGBA')

    def dump_png(self, stream: BinaryIO) -> None:
        self._build_png().write(stream)

    def save_png(self, file_path: str | PathLike[str]) -> None:
        self._build_png().save(file_path)

    def copy(self) -> MonoBitmap:
        bitmap = MonoBitmap()
        for bitmap_row in self:
            bitmap.append(bitmap_row.copy())
        bitmap.width = self.width
        bitmap.height = self.height
        return bitmap

    def deepcopy(self) -> MonoBitmap:
        return self.copy()
