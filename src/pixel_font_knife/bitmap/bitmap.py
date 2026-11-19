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
    """提供矩形像素矩阵和公共位图操作的抽象基类。

    ``PixelT`` 为单色整数或 RGBA 元组，具体像素语义由子类定义。矩阵按从上到下的行顺序存储，
    行内像素从左到右排列；坐标原点位于左上角，x 向右、y 向下，``dimensions`` 为 ``(width, height)``。
    构造时复制输入矩阵及各行，逐像素归一化，并检查行宽一致；``None`` 或空序列表示 0×0 位图。

    子类通过 ``_blank_value()``、``_solid_value()`` 和 ``_is_blank()`` 定义默认空白值、填充值和
    空白判断，并必须实现 ``_normalize_pixel()``，以规范构造输入和 ``solid()`` 的显式填充值。
    空白判断不要求像素与默认空白值完全相等。

    PNG 读写由基类统一完成，子类必须通过 ``_rgba_to_pixel()`` 和 ``_pixel_to_rgba()`` 定义
    内部像素与 8bit RGBA 的转换规则。``load_png()`` 先将图像转换为 8bit RGBA，再逐像素转换，
    保留画布尺寸并返回调用类的实例。``_build_png()`` 通过相反的转换构造图像，供 ``dump_png()``
    和 ``save_png()`` 写出；宽或高为 0 的位图不能编码为 PNG。

    ``blank()`` 和 ``solid()`` 允许宽或高为 0。调用方可原地修改像素或以等宽行替换现有行，
    但应维持矩阵尺寸和子类的像素约定；直接修改列表不会自动维护宽高或重新归一化像素。
    ``resize()`` 按四条边扩展或裁减画布，新增区域填入空白值；``crop()`` 的矩形必须位于画布内。
    这些操作与 ``trim()`` 均返回新位图，不修改原矩阵。

    ``scale_to()`` 按最近邻采样缩放至指定尺寸，``scale()`` 按比例计算目标尺寸并四舍五入，
    两者均保留具体类型且不修改原位图。目标宽或高为 0 时得到对应尺寸的空位图，
    零尺寸源图不能放大为非零尺寸。PNG 编码前会检查矩阵高度和各行宽度是否与记录尺寸一致。

    边距测量、裁边和碰撞检测均使用子类的空白判断。``overlaps()`` 将另一位图的左上角放在
    ``(x, y)``，只检查两幅画布交集内是否存在同时非空的像素。全空位图的 ``measure_padding()``
    返回 ``Padding(width, 0, height, 0)``，``trim()`` 得到 0×0 位图并返回对应边距。

    相等比较要求具体类型、尺寸和像素内容均相同。``copy()`` 与 ``deepcopy()`` 都复制矩阵及各行，
    保留具体类型；整数和 RGBA 元组不可变，无需额外复制像素值。
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
