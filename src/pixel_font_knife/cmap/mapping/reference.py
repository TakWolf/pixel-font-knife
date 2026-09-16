from pixel_font_knife.glyph.common import check_flavor


class CmapGlyphReference:
    code_point: int
    flavor: str | None

    def __init__(
            self,
            code_point: int,
            flavor: str | None = None,
    ) -> None:
        if code_point < 0:
            raise KeyError(f'illegal code point: {code_point}')
        if flavor is not None:
            check_flavor(flavor)

        self.code_point = code_point
        self.flavor = flavor
