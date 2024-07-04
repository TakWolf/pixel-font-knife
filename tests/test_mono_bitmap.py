import pytest

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


def test_cost():
    bitmap = MonoBitmap.cost([
        [0, 1, 2, 3],
        [1, 0, 0, 1],
    ])
    assert bitmap.width == 4
    assert bitmap.height == 2
    assert bitmap == [
        [0, 1, 1, 1],
        [1, 0, 0, 1],
    ]

    with pytest.raises(ValueError):
        MonoBitmap.cost([
            [0, 1, 2],
            [],
        ])
