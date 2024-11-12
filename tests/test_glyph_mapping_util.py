import os
from pathlib import Path

from pixel_font_knife import glyph_mapping_util, glyph_file_util


def test_load(assets_dir: Path, glyphs_dir: Path, tmp_path: Path):
    load_path = assets_dir.joinpath('example-mapping.yml')
    save_path = tmp_path.joinpath('example-mapping.yml')

    mapping = glyph_mapping_util.load_mapping(os.fspath(load_path))
    glyph_mapping_util.save_mapping(mapping, os.fspath(save_path))
    assert load_path.read_text('utf-8') == save_path.read_text('utf-8')

    assert len(mapping) == 1
    assert len(mapping[0x1000]) == 4
    assert mapping[0x1000].get_source().code_point == 0x6AA4
    assert mapping[0x1000].get_source('ja').flavor is None
    assert mapping[0x1000].get_source('zh_cn').flavor == 'ja'

    context = glyph_file_util.load_context(os.fspath(glyphs_dir.joinpath('context')))
    assert 0x1000 not in context
    glyph_mapping_util.apply_mapping(context, mapping)
    assert 0x1000 in context
    assert len(context[0x1000]) == 4
    assert context[0x1000][None] == context[0x6AA4][None]
    assert context[0x1000]['ko'] == context[0x6AA4]['ko']
    assert context[0x1000]['zh_cn'] == context[0x6AA4][None]
