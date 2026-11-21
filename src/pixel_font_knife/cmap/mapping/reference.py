from pixel_font_knife.glyph.common import check_code_point, check_flavor


class CmapGlyphReference:
    """Source code point and optional flavor of a concrete glyph in ``CmapContext``.

    This object describes a reference location without holding a glyph file.
    When applying mappings, references should point directly to concrete glyphs
    in the original context, rather than to targets introduced by other mappings.
    """

    code_point: int
    flavor: str | None

    def __init__(
            self,
            code_point: int,
            flavor: str | None = None,
    ) -> None:
        check_code_point(code_point)
        if flavor is not None:
            check_flavor(flavor)

        self.code_point = code_point
        self.flavor = flavor
