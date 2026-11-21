from abc import ABC, abstractmethod
from collections import UserList
from collections.abc import Sequence
from copy import copy, deepcopy
from math import floor, isfinite
from os import PathLike
from typing import Any, Self, BinaryIO, cast

from png import PngImage, PngHeader, PngColorType, PngFilterType

from pixel_font_knife.bitmap.padding import Padding

type ColorRgba = tuple[int, int, int, int]


class Bitmap[PixelT: (int, ColorRgba)](UserList[list[PixelT]], ABC):
    """Abstract base class for rectangular pixel matrices and shared bitmap operations.

    ``PixelT`` is a monochrome integer or an RGBA tuple; subclasses define its
    meaning. Rows run from top to bottom and pixels from left to right. The origin
    is at the top left, x increases rightward, y increases downward, and
    ``dimensions`` is ``(width, height)``. Construction copies the matrix and each
    row, normalizes every pixel, and checks for equal row widths. ``None`` or an
    empty sequence produces a 0-by-0 bitmap.

    Subclasses define blank and solid defaults and blank detection through
    ``_blank_value()``, ``_solid_value()``, and ``_is_blank()``. They must implement
    ``_normalize_pixel()`` for constructor input and explicit ``solid()`` values.
    A blank pixel need not equal the default blank value.

    PNG I/O is shared by this base class. Subclasses implement ``_rgba_to_pixel()``
    and ``_pixel_to_rgba()`` to convert between internal pixels and 8-bit RGBA.
    ``load_png()`` converts the image to 8-bit RGBA and then converts each pixel,
    preserving canvas dimensions and returning an instance of the calling class.
    ``_build_png()`` performs the reverse conversion for ``dump_png()`` and
    ``save_png()``. PNG encoding requires nonzero width and height.

    ``blank()`` and ``solid()`` allow zero width or height. Callers may edit pixels
    in place or replace rows with rows of equal width, but must preserve dimensions
    and subclass pixel conventions. Direct list edits do not update dimensions or
    normalize pixels. ``resize()`` expands or crops the canvas at its four edges,
    filling new areas with blank pixels. The rectangle passed to ``crop()`` must
    lie inside the canvas. These operations and ``trim()`` return new bitmaps.

    ``scale_to()`` uses nearest-neighbor sampling. ``scale()`` computes target
    dimensions from scale factors and rounds half up. Both preserve the concrete
    type and leave the source unchanged. A zero target width or height produces
    an empty bitmap of the requested dimensions. A source with zero width or
    height cannot be scaled to a target with both dimensions nonzero. PNG encoding
    checks that the matrix height and row widths match the recorded dimensions.

    Padding measurement, trimming, and overlap detection use subclass blank
    detection. ``overlaps()`` places the other bitmap's top left at ``(x, y)`` and
    checks for pixels that are nonblank in both canvases within their intersection.
    For an entirely blank bitmap, ``measure_padding()`` returns
    ``Padding(width, 0, height, 0)``; ``trim()`` returns a 0-by-0 bitmap and that
    padding.

    Equality requires the same concrete type, dimensions, and pixel contents.
    ``copy()`` and ``deepcopy()`` copy the matrix and each row while preserving the
    concrete type. Integers and RGBA tuples are immutable and need no further copy.
    """

    @staticmethod
    @abstractmethod
    def _blank_value() -> PixelT:
        raise NotImplementedError()

    @staticmethod
    @abstractmethod
    def _solid_value() -> PixelT:
        raise NotImplementedError()

    @staticmethod
    @abstractmethod
    def _is_blank(pixel: PixelT) -> bool:
        raise NotImplementedError()

    @staticmethod
    @abstractmethod
    def _normalize_pixel(pixel: PixelT) -> PixelT:
        raise NotImplementedError()

    @staticmethod
    @abstractmethod
    def _rgba_to_pixel(color: ColorRgba) -> PixelT:
        raise NotImplementedError()

    @staticmethod
    @abstractmethod
    def _pixel_to_rgba(pixel: PixelT) -> ColorRgba:
        raise NotImplementedError()

    @classmethod
    def blank(cls, width: int, height: int) -> Self:
        if width < 0 or height < 0:
            raise ValueError(f'bitmap dimensions must be non-negative: ({width}, {height})')

        bitmap = cls()
        bitmap.width = width
        bitmap.height = height
        for _ in range(height):
            bitmap.append([cls._blank_value()] * width)
        return bitmap

    @classmethod
    def solid(cls, width: int, height: int, pixel: PixelT | None = None) -> Self:
        if width < 0 or height < 0:
            raise ValueError(f'bitmap dimensions must be non-negative: ({width}, {height})')

        if pixel is None:
            pixel = cls._solid_value()
        else:
            pixel = cls._normalize_pixel(pixel)

        bitmap = cls()
        bitmap.width = width
        bitmap.height = height
        for _ in range(height):
            bitmap.append([pixel] * width)
        return bitmap

    @classmethod
    def load_png(cls, file_path: str | PathLike[str]) -> Self:
        image = PngImage.load(file_path)
        if image.header.color_type != PngColorType.TRUECOLOR_ALPHA or image.header.bit_depth != 8:
            image = image.to_rgba(bit_depth=8)

        bitmap = cls()
        bitmap.width = image.header.width
        bitmap.height = image.header.height
        for row in image.bitmap:
            bitmap.append([
                cls._rgba_to_pixel((row[x], row[x + 1], row[x + 2], row[x + 3]))
                for x in range(0, len(row), 4)
            ])
        return bitmap

    width: int
    height: int

    def __init__(self, bitmap: Sequence[Sequence[PixelT]] | None = None) -> None:
        super().__init__()
        if not bitmap:
            self.width = 0
            self.height = 0
        else:
            self.width = len(bitmap[0])
            self.height = len(bitmap)
            normalize_pixel = type(self)._normalize_pixel
            for bitmap_row in bitmap:
                if self.width != len(bitmap_row):
                    raise ValueError('inconsistent row widths')
                self.append([normalize_pixel(pixel) for pixel in bitmap_row])

    def __copy__(self) -> Self:
        bitmap = cast(type[Self], type(self))()
        bitmap.width = self.width
        bitmap.height = self.height
        for bitmap_row in self:
            bitmap.append([pixel for pixel in bitmap_row])
        return bitmap

    def __deepcopy__(self, memo: dict[int, Any]) -> Self:
        return copy(self)

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Bitmap) or type(self) is not type(other):
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

        is_blank = type(self)._is_blank

        for y, bitmap_row in enumerate(self):
            if self.width != len(bitmap_row):
                raise ValueError('inconsistent row widths')
            for x, pixel in enumerate(bitmap_row):
                if not is_blank(pixel):
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
        is_blank = type(self)._is_blank

        padding = 0
        for x in range(self.width):
            if any(not is_blank(bitmap_row[x]) for bitmap_row in self):
                break
            padding += 1
        return padding

    def measure_right_padding(self) -> int:
        is_blank = type(self)._is_blank

        padding = 0
        for x in range(self.width):
            if any(not is_blank(bitmap_row[-1 - x]) for bitmap_row in self):
                break
            padding += 1
        return padding

    def measure_top_padding(self) -> int:
        is_blank = type(self)._is_blank

        padding = 0
        for bitmap_row in self:
            if any(not is_blank(pixel) for pixel in bitmap_row):
                break
            padding += 1
        return padding

    def measure_bottom_padding(self) -> int:
        is_blank = type(self)._is_blank

        padding = 0
        for bitmap_row in reversed(self):
            if any(not is_blank(pixel) for pixel in bitmap_row):
                break
            padding += 1
        return padding

    def is_x_inside(self, x: int) -> bool:
        return 0 <= x < self.width

    def is_y_inside(self, y: int) -> bool:
        return 0 <= y < self.height

    def is_inside(self, x: int, y: int) -> bool:
        return self.is_x_inside(x) and self.is_y_inside(y)

    def overlaps(self, other: Self, x: int = 0, y: int = 0) -> bool:
        left = max(x, 0)
        right = min(x + other.width, self.width)
        top = max(y, 0)
        bottom = min(y + other.height, self.height)

        if left >= right or top >= bottom:
            return False

        is_blank = type(self)._is_blank
        other_is_blank = type(other)._is_blank

        for target_y in range(top, bottom):
            self_row = self[target_y]
            other_row = other[target_y - y]

            for target_x in range(left, right):
                if not is_blank(self_row[target_x]) and not other_is_blank(other_row[target_x - x]):
                    return True

        return False

    def resize(self, left: int = 0, right: int = 0, top: int = 0, bottom: int = 0) -> Self:
        width = self.width + left + right
        height = self.height + top + bottom

        bitmap = cast(Self, type(self).blank(width, height))

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

    def crop(self, x: int, y: int, width: int, height: int) -> Self:
        if width < 0 or height < 0:
            raise ValueError(f'bitmap dimensions must be non-negative: ({width}, {height})')
        if x < 0 or y < 0 or x + width > self.width or y + height > self.height:
            raise ValueError(f'crop rectangle must be inside bitmap bounds: ({x}, {y}, {width}, {height})')

        bitmap = cast(type[Self], type(self))()
        bitmap.width = width
        bitmap.height = height
        for bitmap_row in self.data[y:y + height]:
            bitmap.append(bitmap_row[x:x + width])
        return bitmap

    def trim(self) -> tuple[Self, Padding]:
        padding = self.measure_padding()
        bitmap = self.crop(
            padding.left,
            padding.top,
            self.width - padding.left - padding.right,
            self.height - padding.top - padding.bottom,
        )
        return bitmap, padding

    def scale_to(self, width: int, height: int) -> Self:
        if width < 0 or height < 0:
            raise ValueError(f'bitmap dimensions must be non-negative: ({width}, {height})')
        if width == 0 or height == 0:
            return cast(Self, type(self).blank(width, height))
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

        bitmap = cast(type[Self], type(self))()
        bitmap.width = width
        bitmap.height = height
        for y in source_y:
            bitmap.append([self[y][x] for x in source_x])
        return bitmap

    def scale(self, scale_x: float = 1, scale_y: float = 1) -> Self:
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

    def _build_png(self) -> PngImage:
        if self.width == 0 or self.height == 0:
            raise ValueError('cannot encode empty bitmap as PNG')

        if self.height != len(self):
            raise ValueError('inconsistent bitmap height')

        pixel_to_rgba = type(self)._pixel_to_rgba

        rows = []
        for bitmap_row in self:
            if self.width != len(bitmap_row):
                raise ValueError('inconsistent row widths')

            row = []
            for pixel in bitmap_row:
                row.extend(pixel_to_rgba(pixel))
            rows.append(row)

        return PngImage(
            header=PngHeader((self.width, self.height)),
            bitmap=rows,
        )

    def dump_png(self, stream: BinaryIO) -> None:
        self._build_png().dump(stream, filter_type=PngFilterType.NONE)

    def save_png(self, file_path: str | PathLike[str]) -> None:
        self._build_png().save(file_path, filter_type=PngFilterType.NONE)

    def copy(self) -> Self:
        return copy(self)

    def deepcopy(self) -> Self:
        return deepcopy(self)
