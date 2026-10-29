import re
from pathlib import Path
from unittest.mock import Mock

import pytest

from pixel_font_knife.bitmap.mono_bitmap import MonoBitmap
from pixel_font_knife.cmap.context import CmapContext
from pixel_font_knife.cmap.file import CmapGlyphFile
from pixel_font_knife.cmap.kerning.template import CmapKerningTemplate
from pixel_font_knife.cmap.variants import CmapGlyphVariants


def test_load(assets_dir: Path) -> None:
    template = CmapKerningTemplate.load(assets_dir.joinpath('kerning-example.yaml'))

    assert template.groups == {
        'latin_T': ['T'],
        'latin_o': ['o'],
    }
    assert template.values == {
        ('latin_T', 'latin_o'): -1,
    }


def test_calculate_kerning_values(assets_dir: Path, glyphs_dir: Path) -> None:
    context = CmapContext.load(glyphs_dir.joinpath('kerning'))
    template = CmapKerningTemplate.load(assets_dir.joinpath('kerning-example.yaml'))

    assert template.calculate_kerning_values(context) == {
        ('u0054', 'u006F'): -1,
    }


def test_calculate_kerning_values_accepts_string_flavor_order(assets_dir: Path, glyphs_dir: Path) -> None:
    context = CmapContext.load(glyphs_dir.joinpath('kerning'))
    template = CmapKerningTemplate.load(assets_dir.joinpath('kerning-example.yaml'))

    assert template.calculate_kerning_values(context, 'default') == {
        ('u0054', 'u006F'): -1,
    }


def test_calculate_kerning_values_reduces_offset_to_avoid_overlap(glyphs_dir: Path) -> None:
    context = CmapContext.load(glyphs_dir.joinpath('kerning'))
    template = CmapKerningTemplate(
        groups={
            'left': ['T'],
            'right': ['o'],
        },
        values={
            ('left', 'right'): -8,
        },
    )

    assert template.calculate_kerning_values(context) == {
        ('u0054', 'u006F'): -3,
    }


def test_calculate_kerning_values_ignores_non_negative_and_missing_characters(glyphs_dir: Path) -> None:
    context = CmapContext.load(glyphs_dir.joinpath('kerning'))
    template = CmapKerningTemplate(
        groups={
            'left': ['T', 'X'],
            'right': ['o', 'Y'],
        },
        values={
            ('left', 'right'): -1,
            ('right', 'left'): 1,
        },
    )

    assert template.calculate_kerning_values(context) == {
        ('u0054', 'u006F'): -1,
    }


@pytest.mark.parametrize(
    ('missing_character', 'message'),
    [
        ('T', "left group 'left' character 'T': no flavor file: 'alt'"),
        ('o', "right group 'right' character 'o': no flavor file: 'alt'"),
    ],
)
def test_calculate_kerning_values_reports_missing_flavor_context(
        glyphs_dir: Path,
        missing_character: str,
        message: str,
) -> None:
    default_context = CmapContext.load(glyphs_dir.joinpath('kerning'))
    context = CmapContext()
    for character in ('T', 'o'):
        code_point = ord(character)
        default_file = default_context[code_point][None]
        variants = CmapGlyphVariants({None: default_file})
        if character != missing_character:
            variants['alt'] = CmapGlyphFile(default_file.file_path, code_point, ['alt'])
        context[code_point] = variants
    template = CmapKerningTemplate(
        groups={
            'left': ['T'],
            'right': ['o'],
        },
        values={
            ('left', 'right'): -1,
        },
    )

    with pytest.raises(KeyError, match=re.escape(str(KeyError(message)))):
        template.calculate_kerning_values(context, 'alt', fallback_default=False)


def test_calculate_kerning_values_uses_requested_flavors(glyphs_dir: Path) -> None:
    default_context = CmapContext.load(glyphs_dir.joinpath('kerning'))
    left_default = default_context[ord('T')][None]
    right_default = default_context[ord('o')][None]
    left_flavored = CmapGlyphFile(left_default.file_path, ord('T'), ['alt'])
    right_flavored = CmapGlyphFile(right_default.file_path, ord('o'), ['alt'])
    context = CmapContext({
        ord('T'): CmapGlyphVariants({
            None: left_default,
            'alt': left_flavored,
        }),
        ord('o'): CmapGlyphVariants({
            None: right_default,
            'alt': right_flavored,
        }),
    })
    template = CmapKerningTemplate(
        groups={
            'left': ['T'],
            'right': ['o'],
        },
        values={
            ('left', 'right'): -1,
        },
    )

    assert template.calculate_kerning_values(context, ['alt', None]) == {
        ('u0054.alt', 'u006F.alt'): -1,
        ('u0054', 'u006F'): -1,
    }


def test_calculate_kerning_values_deduplicates_fallback_default(
        glyphs_dir: Path,
        monkeypatch: pytest.MonkeyPatch,
) -> None:
    context = CmapContext.load(glyphs_dir.joinpath('kerning'))
    template = CmapKerningTemplate(
        groups={
            'left': ['T'],
            'right': ['o'],
        },
        values={
            ('left', 'right'): -8,
        },
    )
    overlaps = Mock(return_value=False)
    monkeypatch.setattr(MonoBitmap, 'overlaps', overlaps)

    assert template.calculate_kerning_values(context, ['alt', None]) == {
        ('u0054', 'u006F'): -8,
    }
    overlaps.assert_called_once()


def test_calculate_kerning_values_reports_preset_mismatch(glyphs_dir: Path) -> None:
    context = CmapContext.load(glyphs_dir.joinpath('kerning'))
    template = CmapKerningTemplate(
        groups={
            'left_1': ['T'],
            'right_1': ['o'],
            'left_2': ['T'],
            'right_2': ['o'],
        },
        values={
            ('left_1', 'right_1'): -1,
            ('left_2', 'right_2'): -8,
        },
    )

    message = (
        "kerning preset mismatch for glyph pair ('u0054', 'u006F'): "
        "-1 from groups ('left_1', 'right_1'), characters ('T', 'o'), requested flavor None != "
        "-8 from groups ('left_2', 'right_2'), characters ('T', 'o'), requested flavor None"
    )
    with pytest.raises(ValueError, match=re.escape(message)):
        template.calculate_kerning_values(context)
