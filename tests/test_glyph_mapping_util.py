from pathlib import Path

from pixel_font_knife import glyph_mapping_util, glyph_file_util


def test_load(assets_dir: Path, glyphs_dir: Path, tmp_path: Path):
    load_path = assets_dir.joinpath('mapping-example.yaml')
    save_path = tmp_path.joinpath('mapping-example.yaml')

    mapping = glyph_mapping_util.load_mapping(load_path)
    glyph_mapping_util.save_mapping(mapping, save_path)
    assert load_path.read_text('utf-8') == save_path.read_text('utf-8')

    assert len(mapping) == 2

    assert len(mapping[0x0004]) == 1
    assert mapping[0x0004]['*'].code_point == 0x6AA4
    assert mapping[0x0004]['*'].flavor is None

    assert len(mapping[0x0005]) == 4
    assert mapping[0x0005][None].code_point == 0x6AA4
    assert mapping[0x0005][None].flavor is None
    assert mapping[0x0005]['zh_cn'].code_point == 0x6AA4
    assert mapping[0x0005]['zh_cn'].flavor == 'ja'

    context = glyph_file_util.load_context(glyphs_dir.joinpath('context'))
    assert 0x0004 not in context
    assert 0x0005 not in context
    glyph_mapping_util.apply_mapping(context, mapping)
    assert 0x0005 in context
    assert 0x0004 in context

    assert len(context[0x0004]) == 5
    assert context[0x0004][None] == context[0x6AA4][None]
    assert context[0x0004]['zh_hk'] == context[0x6AA4]['zh_hk']
    assert context[0x0004]['zh_tw'] == context[0x6AA4]['zh_tw']
    assert context[0x0004]['zh_tr'] == context[0x6AA4]['zh_tr']
    assert context[0x0004]['ko'] == context[0x6AA4]['ko']

    assert len(context[0x0005]) == 4
    assert context[0x0005][None] == context[0x6AA4][None]
    assert context[0x0005]['ko'] == context[0x6AA4]['ko']
    assert context[0x0005]['zh_cn'] == context[0x6AA4][None]
