from pathlib import Path

from pixel_font_knife import glyph_file_util, kerning_util
from pixel_font_knife.kerning_util import KerningConfig


def test_calculate_kerning_values(assets_dir: Path, glyphs_dir: Path):
    context = glyph_file_util.load_context(glyphs_dir.joinpath('kerning'))
    kerning_config = KerningConfig.load(assets_dir.joinpath('kerning-example.yml'))
    kerning_values = kerning_util.calculate_kerning_values(kerning_config, context)
    assert len(kerning_values) == 1
    assert kerning_values[('u0054', 'u006F')] == -1
