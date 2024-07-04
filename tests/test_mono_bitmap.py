from pixel_font_knife.mono_bitmap import MonoBitmap


def test_create():
    bitmap = MonoBitmap(3, 4)
    assert bitmap.width == 3
    assert bitmap.height == 4
    assert bitmap == [
        [0, 0, 0],
        [0, 0, 0],
        [0, 0, 0],
        [0, 0, 0],
    ]

    bitmap = MonoBitmap(2, 3, alpha=1)
    assert bitmap.width == 2
    assert bitmap.height == 3
    assert bitmap == [
        [1, 1],
        [1, 1],
        [1, 1],
    ]
