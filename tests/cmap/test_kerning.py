from pathlib import Path

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
