import pytest

from pixel_font_knife.cmap.context import CmapContext
from pixel_font_knife.cmap.file import CmapGlyphFile
from pixel_font_knife.cmap.mapping.entry import CmapMappingEntry
from pixel_font_knife.cmap.mapping.mapping import CmapMapping
from pixel_font_knife.cmap.mapping.reference import CmapGlyphReference
from pixel_font_knife.cmap.variants import CmapGlyphVariants


def _create_mapping(target_code_point: int, reference_code_point: int) -> CmapMapping:
    entry = CmapMappingEntry({None: CmapGlyphReference(reference_code_point)})
    return CmapMapping({target_code_point: entry})


@pytest.mark.parametrize(
    'method_name',
    [
        'apply_mapping_by_code_point',
        'apply_mapping_by_flavor',
    ],
)
def test_apply_mappings_are_order_independent(method_name: str) -> None:
    first_glyph_file = CmapGlyphFile('0041.png', 0x41)
    second_glyph_file = CmapGlyphFile('0042.png', 0x42)
    context = CmapContext({
        0x41: CmapGlyphVariants({None: first_glyph_file}),
        0x42: CmapGlyphVariants({None: second_glyph_file}),
    })
    first_mapping = _create_mapping(0x51, 0x41)
    second_mapping = _create_mapping(0x52, 0x42)

    apply_mapping = getattr(context, method_name)
    forward = apply_mapping(first_mapping, second_mapping)
    reverse = apply_mapping(second_mapping, first_mapping)

    assert forward[0x51][None] is first_glyph_file
    assert forward[0x52][None] is second_glyph_file
    assert reverse[0x51][None] is first_glyph_file
    assert reverse[0x52][None] is second_glyph_file


@pytest.mark.parametrize(
    'method_name',
    [
        'apply_mapping_by_code_point',
        'apply_mapping_by_flavor',
    ],
)
def test_mapping_cannot_resolve_another_reference(method_name: str) -> None:
    glyph_file = CmapGlyphFile('0043.png', 0x43)
    context = CmapContext({
        0x43: CmapGlyphVariants({None: glyph_file}),
    })
    referenced_mapping = _create_mapping(0x42, 0x43)
    referencing_mapping = _create_mapping(0x41, 0x42)

    result = getattr(context, method_name)(
        referenced_mapping,
        referencing_mapping,
    )

    assert result[0x42][None] is glyph_file
    assert 0x41 not in result
