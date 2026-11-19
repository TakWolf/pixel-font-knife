from pixel_font_knife.bitmap.color import ColorBitmap
from pixel_font_knife.bitmap.mono import MonoBitmap


def test_to_mono_mask() -> None:
    pixels = [
        [(255, 0, 0, 0), (0, 0, 0, 1), (255, 255, 255, 127)],
        [(0, 255, 0, 128), (0, 0, 255, 255), (255, 255, 255, 0)],
    ]
    bitmap = ColorBitmap(pixels)

    mask = bitmap.to_mono_mask()

    assert mask == MonoBitmap([
        [0, 1, 1],
        [1, 1, 0],
    ])
    assert bitmap == ColorBitmap(pixels)
