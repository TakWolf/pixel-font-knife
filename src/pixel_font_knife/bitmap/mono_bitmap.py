from __future__ import annotations

from collections import UserList
from io import StringIO
from math import floor, isfinite
from os import PathLike
from typing import Any, BinaryIO, Literal

from pixel_font_knife.bitmap.padding import Padding
from pixel_font_knife.internal import png

_SetOperation = Literal[
    'union',
    'intersection',
    'difference',
    'symmetric_difference',
]


class MonoBitmap(UserList[list[int]]):
    @staticmethod
    def blank(width: int, height: int) -> MonoBitmap:
        if width < 0 or height < 0:
            raise ValueError(f'bitmap dimensions must be non-negative: ({width}, {height})')

        bitmap = MonoBitmap()
        bitmap.width = width
        bitmap.height = height
        for _ in range(height):
            bitmap.append([0] * width)
        return bitmap

    @staticmethod
    def solid(width: int, height: int) -> MonoBitmap:
        if width < 0 or height < 0:
            raise ValueError(f'bitmap dimensions must be non-negative: ({width}, {height})')

        bitmap = MonoBitmap()
        bitmap.width = width
        bitmap.height = height
        for _ in range(height):
            bitmap.append([1] * width)
        return bitmap

    @staticmethod
    def load_png(file_path: str | PathLike[str]) -> MonoBitmap:
        with open(file_path, 'rb') as file:
            width, height, rows, info = png.Reader(file=file).asRGBA()
            alpha_threshold = 1 << (info['bitdepth'] - 1)

            bitmap = MonoBitmap()
            bitmap.width = width
            bitmap.height = height
            for row in rows:
                bitmap.append([
                    1 if row[x * 4 + 3] >= alpha_threshold else 0
                    for x in range(width)
                ])
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
                    first_row = min(first_row, y)
                    last_row = max(last_row, y)
                    first_col = min(first_col, x)
                    last_col = max(last_col, x)

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
        for x in range(self.width):
            if any(bitmap_row[x] != 0 for bitmap_row in self):
                break
            padding += 1
        return padding

    def measure_right_padding(self) -> int:
        padding = 0
        for x in range(self.width):
            if any(bitmap_row[-1 - x] != 0 for bitmap_row in self):
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

    def is_x_inside(self, x: int) -> bool:
        return 0 <= x < self.width

    def is_y_inside(self, y: int) -> bool:
        return 0 <= y < self.height

    def is_inside(self, x: int, y: int) -> bool:
        return self.is_x_inside(x) and self.is_y_inside(y)

    def overlaps(self, other: MonoBitmap, x: int = 0, y: int = 0) -> bool:
        left = max(x, 0)
        right = min(x + other.width, self.width)
        top = max(y, 0)
        bottom = min(y + other.height, self.height)

        if left >= right or top >= bottom:
            return False

        for target_y in range(top, bottom):
            self_row = self[target_y]
            other_row = other[target_y - y]

            for target_x in range(left, right):
                if self_row[target_x] != 0 and other_row[target_x - x] != 0:
                    return True

        return False

    def resize(self, left: int = 0, right: int = 0, top: int = 0, bottom: int = 0) -> MonoBitmap:
        width = self.width + left + right
        height = self.height + top + bottom

        bitmap = MonoBitmap.blank(width, height)

        source_left = max(-left, 0)
        source_right = min(self.width, width - left)
        source_top = max(-top, 0)
        source_bottom = min(self.height, height - top)

        if source_left >= source_right or source_top >= source_bottom:
            return bitmap

        target_left = source_left + left
        target_right = source_right + left

        for source_y in range(source_top, source_bottom):
            target_y = source_y + top
            bitmap[target_y][target_left:target_right] = self[source_y][source_left:source_right]

        return bitmap

    def trim(self) -> tuple[MonoBitmap, Padding]:
        padding = self.measure_padding()
        bitmap = self.crop(
            padding.left,
            padding.top,
            self.width - padding.left - padding.right,
            self.height - padding.top - padding.bottom,
        )
        return bitmap, padding

    def crop(self, x: int, y: int, width: int, height: int) -> MonoBitmap:
        if width < 0 or height < 0:
            raise ValueError(f'bitmap dimensions must be non-negative: ({width}, {height})')
        if x < 0 or y < 0 or x + width > self.width or y + height > self.height:
            raise ValueError(f'crop rectangle must be inside bitmap bounds: ({x}, {y}, {width}, {height})')

        bitmap = MonoBitmap()
        bitmap.width = width
        bitmap.height = height
        for bitmap_row in self.data[y:y + height]:
            bitmap.append(bitmap_row[x:x + width])
        return bitmap

    def scale_to(self, width: int, height: int) -> MonoBitmap:
        if width < 0 or height < 0:
            raise ValueError(f'bitmap dimensions must be non-negative: ({width}, {height})')
        if width == 0 or height == 0:
            return MonoBitmap.blank(width, height)
        if self.width == 0 or self.height == 0:
            raise ValueError('cannot scale a zero-sized bitmap to non-zero dimensions')

        source_x = [
            min(floor(target_x * self.width / width), self.width - 1)
            for target_x in range(width)
        ]
        source_y = [
            min(floor(target_y * self.height / height), self.height - 1)
            for target_y in range(height)
        ]

        bitmap = MonoBitmap()
        bitmap.width = width
        bitmap.height = height
        for y in source_y:
            bitmap.append([self[y][x] for x in source_x])
        return bitmap

    def scale(self, scale_x: float = 1, scale_y: float = 1) -> MonoBitmap:
        if not isfinite(scale_x) or scale_x <= 0:
            raise ValueError(f'scale_x must be positive and finite: {scale_x}')
        if not isfinite(scale_y) or scale_y <= 0:
            raise ValueError(f'scale_y must be positive and finite: {scale_y}')

        scaled_width = self.width * scale_x
        scaled_height = self.height * scale_y
        if not isfinite(scaled_width) or not isfinite(scaled_height):
            raise ValueError('scaled bitmap dimensions must be finite')

        width = floor(scaled_width + 0.5)
        height = floor(scaled_height + 0.5)
        return self.scale_to(width, height)

    @staticmethod
    def _set_pixel(left: int, right: int, operation: _SetOperation) -> int:
        if operation == 'union':
            return left | right
        if operation == 'intersection':
            return left & right
        if operation == 'difference':
            return left & (1 - right)
        if operation == 'symmetric_difference':
            return left ^ right
        raise ValueError(f'unsupported set operation: {operation!r}')

    def _set_operation(
            self,
            other: MonoBitmap,
            operation: _SetOperation,
            x: int,
            y: int,
    ) -> MonoBitmap:
        bitmap = self.copy()
        left = max(x, 0)
        right = min(x + other.width, self.width)
        top = max(y, 0)
        bottom = min(y + other.height, self.height)

        if operation == 'intersection':
            bitmap = MonoBitmap.blank(self.width, self.height)

        for target_y in range(top, bottom):
            bitmap_row = bitmap[target_y]
            self_row = self[target_y]
            other_row = other[target_y - y]
            for target_x in range(left, right):
                bitmap_row[target_x] = self._set_pixel(
                    self_row[target_x],
                    other_row[target_x - x],
                    operation,
                )
        return bitmap

    def union(self, other: MonoBitmap, x: int = 0, y: int = 0) -> MonoBitmap:
        return self._set_operation(other, 'union', x, y)

    def intersection(self, other: MonoBitmap, x: int = 0, y: int = 0) -> MonoBitmap:
        return self._set_operation(other, 'intersection', x, y)

    def difference(self, other: MonoBitmap, x: int = 0, y: int = 0) -> MonoBitmap:
        return self._set_operation(other, 'difference', x, y)

    def symmetric_difference(self, other: MonoBitmap, x: int = 0, y: int = 0) -> MonoBitmap:
        return self._set_operation(other, 'symmetric_difference', x, y)

    def dilate(
            self,
            radius: int,
            shape: Literal['orthogonal', 'diagonal', 'surrounding'] = 'surrounding',
    ) -> MonoBitmap:
        if radius < 0:
            raise ValueError(f'dilation radius must be non-negative: {radius}')
        if shape not in ('orthogonal', 'diagonal', 'surrounding'):
            raise ValueError(f'unsupported dilation shape: {shape!r}')
        if radius == 0:
            return self.copy()

        bitmap = self.copy()
        for y, source_row in enumerate(self):
            for x, pixel in enumerate(source_row):
                if pixel == 0:
                    continue
                for offset_y in range(-radius, radius + 1):
                    for offset_x in range(-radius, radius + 1):
                        if shape == 'orthogonal' and offset_x != 0 and offset_y != 0:
                            continue
                        if shape == 'diagonal' and abs(offset_x) != abs(offset_y):
                            continue
                        target_x = x + offset_x
                        target_y = y + offset_y
                        if bitmap.is_inside(target_x, target_y):
                            bitmap[target_y][target_x] = 1
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
        bitmap.width = self.width
        bitmap.height = self.height
        for bitmap_row in self:
            bitmap.append(bitmap_row.copy())
        return bitmap

    def deepcopy(self) -> MonoBitmap:
        return self.copy()
