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


class MonoBitmap(Bitmap[int]):
    """尺寸固定的 0/1 单色位图。

    0 表示空白，1 表示墨迹。构造输入和 ``solid()`` 的显式填充值会将所有非零值归一化为 1；
    ``blank()`` 默认填入 0，``solid()`` 默认填入 1。矩阵坐标、尺寸、复制和裁边约定见 ``Bitmap``。
    调用方原地修改像素时应保持 0/1 取值和矩阵尺寸，直接修改不会触发归一化。

    PNG 读写继承自 ``Bitmap``，本类通过 ``_rgba_to_pixel()`` 和 ``_pixel_to_rgba()`` 定义转换规则。
    ``load_png()`` 先将图像转换为 8bit RGBA，再将 Alpha 大于等于 128 的像素视为墨迹，
    其余视为空白；RGB 颜色不参与判断。``dump_png()`` 和 ``save_png()`` 写出 8bit RGBA PNG，
    墨迹为不透明黑色，空白为透明黑色。宽或高为 0 的位图可参与内存操作，但不能编码为 PNG。

    ``scale_to()`` 按最近邻采样缩放至指定尺寸，``scale()`` 按比例计算目标尺寸并四舍五入，
    两者均不修改原位图。目标宽或高为 0 时得到对应尺寸的空位图，零尺寸源图不能放大为非零尺寸。

    集合运算将另一位图的左上角放在指定偏移处，结果保持自身画布尺寸，超出画布的内容被裁去。
    ``dilate()`` 按指定半径和邻域形状扩张墨迹，同样不扩大画布。集合运算和膨胀均返回新位图；
    ``overlaps()`` 只判断墨迹是否相交，不修改任一输入。
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
