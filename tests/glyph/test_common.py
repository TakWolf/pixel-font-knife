import re

import pytest

from pixel_font_knife.glyph.common import check_flavor, normalize_allowed_flavors, normalize_flavor_order


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


def test_normalize_allowed_flavors() -> None:
    assert normalize_allowed_flavors(None) is None
    assert normalize_allowed_flavors('zh_cn') == {'zh_cn'}
    assert normalize_allowed_flavors(['zh_cn', 'zh_tw']) == {'zh_cn', 'zh_tw'}


def test_normalize_flavor_order() -> None:
    assert normalize_flavor_order(None) is None
    assert normalize_flavor_order('zh_cn') == ['zh_cn']
    assert normalize_flavor_order([None, 'zh_cn']) == [None, 'zh_cn']
