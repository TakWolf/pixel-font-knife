from __future__ import annotations

from pixel_font_knife.bitmap.bitmap import Bitmap, ColorRgba
from pixel_font_knife.bitmap.mono import MonoBitmap


class ColorBitmap(Bitmap[ColorRgba]):
    """Color bitmap with 8-bit RGBA pixels.

    Each pixel is a ``(red, green, blue, alpha)`` tuple of integers from 0 to 255.
    RGB channels are not premultiplied by alpha. Zero alpha denotes a blank pixel;
    any positive alpha denotes ink, including translucent pixels, regardless of
    RGB values. See ``Bitmap`` for coordinates, dimensions, copying, and trimming.

    Construction and explicit ``solid()`` values validate the channel count,
    integer types, and ranges. Fully transparent pixels become ``(0, 0, 0, 0)``,
    discarding their original RGB values; other pixels retain their values.
    ``blank()`` defaults to transparent black and ``solid()`` to opaque black.
    In-place edits must preserve channel ranges and matrix dimensions; direct
    edits do not trigger normalization.

    PNG I/O is inherited from ``Bitmap``, with conversion rules defined by
    ``_rgba_to_pixel()`` and ``_pixel_to_rgba()``. ``load_png()`` converts images to
    8-bit RGBA, preserving canvas dimensions and visible pixels' color and alpha,
    and zeroing fully transparent pixels. ``dump_png()`` and ``save_png()`` use
    the same rules to write 8-bit RGBA PNGs, preserving translucent alpha without
    monochrome thresholding. Zero width or height is allowed in memory but cannot
    be encoded as PNG. Channels are validated again before writing; invalid values
    raise ``ValueError``.

    Padding measurement and ``trim()`` use the smallest rectangle containing ink.
    ``overlaps()`` checks for positions containing ink in both bitmaps, without
    color blending or an additional alpha threshold. ``to_mono_mask()`` converts
    positive alpha to one and zero alpha to zero to represent ink coverage. This
    differs from the alpha threshold of 128 used by ``MonoBitmap.load_png()``.
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
        return pixel if pixel[3] != 0 else (0, 0, 0, 0)

    @staticmethod
    def _rgba_to_pixel(color: ColorRgba) -> ColorRgba:
        return color if color[3] != 0 else (0, 0, 0, 0)

    @staticmethod
    def _pixel_to_rgba(pixel: ColorRgba) -> ColorRgba:
        return pixel if pixel[3] != 0 else (0, 0, 0, 0)

    def to_mono_mask(self) -> MonoBitmap:
        _is_blank = type(self)._is_blank

        bitmap = MonoBitmap.blank(self.width, self.height)
        for y, bitmap_row in enumerate(self):
            bitmap[y] = [0 if _is_blank(pixel) else 1 for pixel in bitmap_row]
        return bitmap
