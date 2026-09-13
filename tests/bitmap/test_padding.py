from copy import copy, deepcopy

from pixel_font_knife.bitmap.padding import Padding


def test_copy() -> None:
    padding_1 = Padding(
        left=1,
        right=2,
        top=3,
        bottom=4,
    )
    padding_2 = copy(padding_1)
    padding_3 = deepcopy(padding_1)

    assert padding_1 == padding_2
    assert padding_1 == padding_3
    assert padding_1 is not padding_2
    assert padding_1 is not padding_3


def test_eq() -> None:
    padding_1 = Padding(
        left=1,
        right=2,
        top=3,
        bottom=4,
    )
    padding_2 = Padding(
        left=1,
        right=2,
        top=3,
        bottom=4,
    )
    assert padding_1 == padding_2
