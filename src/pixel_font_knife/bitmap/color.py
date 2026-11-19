from __future__ import annotations

from pixel_font_knife.bitmap.bitmap import Bitmap, ColorRgba
from pixel_font_knife.bitmap.mono import MonoBitmap


class ColorBitmap(Bitmap[ColorRgba]):
    """以 8bit RGBA 像素表示的彩色位图。

    每个像素为 ``(red, green, blue, alpha)`` 元组，各通道应为 0～255 的整数，RGB 不预乘 Alpha。
    Alpha 为 0 表示空白，任何大于 0 的 Alpha 都表示墨迹，包括半透明像素；RGB 颜色不影响空白判断。
    矩阵坐标、尺寸、复制和裁边约定见 ``Bitmap``。

    构造输入和 ``solid()`` 的显式填充值会检查通道数量、整数类型和取值范围，
    并将完全透明的像素统一为 ``(0, 0, 0, 0)``，
    因此透明像素原有的 RGB 值不会保留；其余像素保持原值。``blank()`` 默认填入透明黑色，
    ``solid()`` 默认填入不透明黑色。调用方原地修改像素时应维持通道范围和矩阵尺寸，
    直接修改不会触发归一化。

    PNG 读写继承自 ``Bitmap``，本类通过 ``_rgba_to_pixel()`` 和 ``_pixel_to_rgba()`` 定义转换规则。
    ``load_png()`` 将图像转换为 8bit RGBA，保留画布尺寸和可见像素的颜色、透明度，
    并将完全透明的像素归零。``dump_png()`` 和 ``save_png()`` 按相同规则写出 8bit RGBA PNG，
    保留半透明 Alpha，不进行单色阈值转换。宽或高为 0 的位图可参与内存操作，但不能编码为 PNG。
    写出前会重新检查可变像素的通道是否合法，非法值抛出 ``ValueError``。

    边距测量和 ``trim()`` 以包含墨迹的最小矩形为准；``overlaps()`` 检查是否有位置同时包含墨迹，
    不进行颜色混合，也不按 Alpha 大小设置额外阈值。
    ``to_mono_mask()`` 将 Alpha 大于 0 的像素转为 1，其余转为 0；该掩码用于表示墨迹范围，
    与 ``MonoBitmap.load_png()`` 使用的 Alpha 大于等于 128 的二值化规则不同。
    """

    @staticmethod
    def _blank_value() -> ColorRgba:
        return 0, 0, 0, 0

    @staticmethod
    def _solid_value() -> ColorRgba:
        return 0, 0, 0, 255

    @staticmethod
    def _is_blank(pixel: ColorRgba) -> bool:
        return pixel[3] == 0

    @staticmethod
    def _normalize_pixel(pixel: ColorRgba) -> ColorRgba:
        if not isinstance(pixel, (tuple, list)) or len(pixel) != 4 or any(not isinstance(channel, int) or not 0 <= channel <= 255 for channel in pixel):
            raise ValueError(f'expected four RGBA integers in [0, 255], got {pixel!r}')
        return tuple(pixel) if pixel[3] != 0 else (0, 0, 0, 0)

    @staticmethod
    def _rgba_to_pixel(color: ColorRgba) -> ColorRgba:
        return color if color[3] != 0 else (0, 0, 0, 0)

    @staticmethod
    def _pixel_to_rgba(pixel: ColorRgba) -> ColorRgba:
        return ColorBitmap._normalize_pixel(pixel)

    def to_mono_mask(self) -> MonoBitmap:
        bitmap = MonoBitmap.blank(self.width, self.height)
        for y, bitmap_row in enumerate(self):
            bitmap[y] = [0 if self._is_blank(pixel) else 1 for pixel in bitmap_row]
        return bitmap
