from copy import copy, deepcopy

from pixel_font_knife.mono_bitmap import Paddings


def test_copy():
    paddings_1 = Paddings(
        left=1,
        right=2,
        top=3,
        bottom=4,
    )
    paddings_2 = copy(paddings_1)
    paddings_3 = deepcopy(paddings_1)

    assert paddings_1 == paddings_2
    assert paddings_1 == paddings_3
    assert paddings_1 is not paddings_2
    assert paddings_1 is not paddings_3


def test_eq():
    paddings_1 = Paddings(
        left=1,
        right=2,
        top=3,
        bottom=4,
    )
    paddings_2 = Paddings(
        left=1,
        right=2,
        top=3,
        bottom=4,
    )
    assert paddings_1 == paddings_2
