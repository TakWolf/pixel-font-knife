from __future__ import annotations

from typing import Literal

from pixel_font_knife.bitmap.mono_bitmap import MonoBitmap
from pixel_font_knife.bitmap.padding import Padding


class GlyphCanvas:
    """保留字形原始画布尺寸及其布局含义的位图容器。

    ``bitmap`` 表示未裁边的 PNG 画布，其宽高参与 advance 和相对 em box 的偏移计算；
    ``trimmed_bitmap`` 与 ``trimmed_padding`` 仅表示墨迹裁边结果，不能替代原始画布参与布局计算。
    trimmed 数据按需计算并缓存，替换 ``bitmap`` 时会自动失效。

    横排和竖排偏移先根据原始画布计算，再由 ``*_for_trimmed()`` 使用裁边 padding 补偿墨迹位置。
    奇偶尺寸无法对称居中时，必须通过 bias 明确离散方向；该 bias 与裁边 padding 是相互独立的概念。
    """

    _bitmap: MonoBitmap
    _trimmed_bitmap: MonoBitmap | None
    _trimmed_padding: Padding | None

    def __init__(self, bitmap: MonoBitmap) -> None:
        self._bitmap = bitmap
        self._trimmed_bitmap = None
        self._trimmed_padding = None

    @property
    def bitmap(self) -> MonoBitmap:
        return self._bitmap

    @bitmap.setter
    def bitmap(self, bitmap: MonoBitmap) -> None:
        self._bitmap = bitmap
        self._trimmed_bitmap = None
        self._trimmed_padding = None

    @property
    def width(self) -> int:
        return self.bitmap.width

    @property
    def height(self) -> int:
        return self.bitmap.height

    @property
    def dimensions(self) -> tuple[int, int]:
        return self.bitmap.dimensions

    @property
    def trimmed_bitmap(self) -> MonoBitmap:
        if self._trimmed_bitmap is None:
            self._trimmed_bitmap, self._trimmed_padding = self.bitmap.trim()
        return self._trimmed_bitmap

    @property
    def trimmed_padding(self) -> Padding:
        if self._trimmed_padding is None:
            self._trimmed_bitmap, self._trimmed_padding = self.bitmap.trim()
        return self._trimmed_padding

    @property
    def is_blank(self) -> bool:
        return self.trimmed_bitmap.width == 0 or self.trimmed_bitmap.height == 0

    def horizontal_offset(
            self,
            em_size: int,
            baseline_from_em_top: int,
            vertical_bias: Literal['top', 'bottom'] | None = None,
    ) -> tuple[int, int]:
        height_difference = self.height - em_size

        if height_difference % 2 == 0:
            bottom_space = height_difference // 2
        elif vertical_bias == 'top':
            bottom_space = (height_difference - 1) // 2
        elif vertical_bias == 'bottom':
            bottom_space = (height_difference + 1) // 2
        else:
            raise ValueError('canvas height and em size must have the same parity unless vertical_bias is specified')

        horizontal_offset_x = 0
        horizontal_offset_y = baseline_from_em_top - em_size - bottom_space
        return horizontal_offset_x, horizontal_offset_y

    def vertical_offset(
            self,
            em_size: int,
            horizontal_bias: Literal['left', 'right'] | None = 'left',
            vertical_bias: Literal['top', 'bottom'] | None = None,
    ) -> tuple[int, int]:
        if self.width % 2 == 0:
            vertical_offset_x = -(self.width // 2)
        elif horizontal_bias == 'left':
            vertical_offset_x = -((self.width + 1) // 2)
        elif horizontal_bias == 'right':
            vertical_offset_x = -((self.width - 1) // 2)
        else:
            raise ValueError('canvas width must be even unless horizontal_bias is specified')

        height_difference = em_size - self.height

        if height_difference % 2 == 0:
            vertical_offset_y = height_difference // 2
        elif vertical_bias == 'top':
            vertical_offset_y = (height_difference - 1) // 2
        elif vertical_bias == 'bottom':
            vertical_offset_y = (height_difference + 1) // 2
        else:
            raise ValueError('canvas height and em size must have the same parity unless vertical_bias is specified')

        return vertical_offset_x, vertical_offset_y

    def horizontal_offset_for_trimmed(
            self,
            em_size: int,
            baseline_from_em_top: int,
            vertical_bias: Literal['top', 'bottom'] | None = None,
    ) -> tuple[int, int]:
        if self.is_blank:
            return 0, 0
        else:
            horizontal_offset_x, horizontal_offset_y = self.horizontal_offset(
                em_size,
                baseline_from_em_top,
                vertical_bias,
            )
            horizontal_offset_x += self.trimmed_padding.left
            horizontal_offset_y += self.trimmed_padding.bottom
            return horizontal_offset_x, horizontal_offset_y

    def vertical_offset_for_trimmed(
            self,
            em_size: int,
            horizontal_bias: Literal['left', 'right'] | None = 'left',
            vertical_bias: Literal['top', 'bottom'] | None = None,
    ) -> tuple[int, int]:
        if self.is_blank:
            return 0, 0
        else:
            vertical_offset_x, vertical_offset_y = self.vertical_offset(
                em_size,
                horizontal_bias,
                vertical_bias,
            )
            vertical_offset_x += self.trimmed_padding.left
            vertical_offset_y += self.trimmed_padding.top
            return vertical_offset_x, vertical_offset_y

    def advance_width(self) -> int:
        return self.width

    def advance_height(self, em_size: int) -> int:
        return em_size
