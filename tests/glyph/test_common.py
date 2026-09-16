import re

import pytest

from pixel_font_knife.glyph.common import check_flavor


def test_validate_flavor() -> None:
    check_flavor('ZH-CN')


@pytest.mark.parametrize(
    'flavor',
    [
        'zh cn',
        'zh\tcn',
        'zh\ncn',
        'zh\u3000cn',
        'zh.cn',
        'zh,cn',
        'zh_cn*',
    ],
)
def test_validate_flavor_with_illegal_character(flavor: str) -> None:
    with pytest.raises(KeyError, match=re.escape(str(KeyError(f'illegal flavor: {flavor!r}')))):
        check_flavor(flavor)
