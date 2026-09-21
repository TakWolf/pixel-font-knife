import re

import pytest

from pixel_font_knife.glyph.common import check_code_point, check_glyph_name_key, check_flavor, check_flavors, normalize_allowed_flavors, normalize_flavor_order


def test_check_code_point() -> None:
    check_code_point(0)


@pytest.mark.parametrize('code_point', [None, '0x0041', 65.0])
def test_check_code_point_with_illegal_type(code_point: object) -> None:
    with pytest.raises(TypeError, match=re.escape(f'illegal code point type: {type(code_point).__name__!r}')):
        check_code_point(code_point)


def test_check_code_point_with_illegal_value() -> None:
    with pytest.raises(ValueError, match=re.escape('illegal code point: -1')):
        check_code_point(-1)


def test_check_glyph_name_key() -> None:
    check_glyph_name_key('.notdef')


@pytest.mark.parametrize('name_key', [None, 1])
def test_check_glyph_name_key_with_illegal_type(name_key: object) -> None:
    with pytest.raises(TypeError, match=re.escape(f'illegal name key type: {type(name_key).__name__!r}')):
        check_glyph_name_key(name_key)


@pytest.mark.parametrize(
    ('name_key', 'message'),
    [
        ('', 'name key cannot be empty'),
        ('foo bar', "illegal name key: 'foo bar'"),
        ('foo\tbar', "illegal name key: 'foo\\tbar'"),
    ],
)
def test_check_glyph_name_key_with_illegal_value(name_key: str, message: str) -> None:
    with pytest.raises(ValueError, match=re.escape(message)):
        check_glyph_name_key(name_key)


def test_check_flavor() -> None:
    check_flavor('ZH-CN')


@pytest.mark.parametrize('flavor', [None, 1])
def test_check_flavor_with_illegal_type(flavor: object) -> None:
    with pytest.raises(TypeError, match=re.escape('flavor cannot be None' if flavor is None else f'illegal flavor type: {type(flavor).__name__!r}')):
        check_flavor(flavor)


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
def test_check_flavor_with_illegal_character(flavor: str) -> None:
    with pytest.raises(ValueError, match=re.escape(f'illegal flavor: {flavor!r}')):
        check_flavor(flavor)


def test_check_flavor_with_empty_value() -> None:
    with pytest.raises(ValueError, match=re.escape('flavor cannot be empty')):
        check_flavor('')


def test_check_flavors_with_duplicate_value() -> None:
    with pytest.raises(ValueError, match=re.escape("duplicate flavor: 'zh_cn'")):
        check_flavors(['zh_cn', 'zh_cn'])


def test_normalize_allowed_flavors() -> None:
    assert normalize_allowed_flavors(None) is None
    assert normalize_allowed_flavors('zh_cn') == {'zh_cn'}
    assert normalize_allowed_flavors(['zh_cn', 'zh_tw']) == {'zh_cn', 'zh_tw'}


def test_normalize_flavor_order() -> None:
    assert normalize_flavor_order(None) is None
    assert normalize_flavor_order('zh_cn') == ['zh_cn']
    assert normalize_flavor_order([None, 'zh_cn']) == [None, 'zh_cn']
