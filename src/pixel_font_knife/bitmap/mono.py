from __future__ import annotations

from io import StringIO
from typing import Literal

from pixel_font_knife.bitmap.bitmap import Bitmap, ColorRgba

type _SetOperation = Literal[
    'union',
    'intersection',
    'difference',
    'symmetric_difference',
]


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


class MonoBitmap(Bitmap[int]):
    """Monochrome bitmap with fixed dimensions and 0/1 pixels.

    Zero denotes blank pixels and one denotes ink. Construction and explicit
    ``solid()`` values normalize all nonzero values to one. ``blank()`` defaults
    to zero and ``solid()`` to one. See ``Bitmap`` for coordinates, dimensions,
    copying, and trimming. In-place edits must preserve 0/1 values and matrix
    dimensions; direct edits do not trigger normalization.

    PNG I/O is inherited from ``Bitmap``, with conversion rules defined by
    ``_rgba_to_pixel()`` and ``_pixel_to_rgba()``. ``load_png()`` converts images to
    8-bit RGBA and treats alpha values of at least 128 as ink, ignoring RGB.
    ``dump_png()`` and ``save_png()`` write 8-bit RGBA PNGs with opaque black ink
    and transparent black blanks. Zero width or height is allowed in memory but
    cannot be encoded as PNG.

    ``scale_to()`` uses nearest-neighbor sampling; ``scale()`` computes target
    dimensions from scale factors and rounds half up. Both leave the source
    unchanged. Zero target width or height produces an empty bitmap of that size.
    A source with zero width or height cannot be scaled to a target with both
    dimensions nonzero.

    Set operations place the other bitmap's top left at the given offset, retain
    this bitmap's canvas dimensions, and clip content outside the canvas.
    ``dilate()`` expands ink using the specified radius and neighborhood shape
    without expanding the canvas. Set operations and dilation return new bitmaps.
    ``overlaps()`` only checks for intersecting ink and leaves both inputs unchanged.
    """

    @staticmethod
    def _blank_value() -> int:
        return 0

    @staticmethod
    def _solid_value() -> int:
        return 1

    @staticmethod
    def _is_blank(pixel: int) -> bool:
        return pixel == 0

    @staticmethod
    def _normalize_pixel(pixel: int) -> int:
        return 0 if pixel == 0 else 1

    @staticmethod
    def _rgba_to_pixel(color: ColorRgba) -> int:
        return 1 if color[3] >= 128 else 0

    @staticmethod
    def _pixel_to_rgba(pixel: int) -> ColorRgba:
        return (0, 0, 0, 255) if pixel != 0 else (0, 0, 0, 0)

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
                bitmap_row[target_x] = _set_pixel(
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
