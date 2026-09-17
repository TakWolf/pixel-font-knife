from pixel_font_knife.glyph.common import check_flavor


class CmapGlyphReference:
    """指向 ``CmapContext`` 中实体字形的源码点与可选 flavor。

    该对象只描述引用位置，不持有字形文件。应用 mapping 时，引用必须直接指向原始上下文中的实体字形，
    不应指向其他 mapping 创建的目标映射。
    """

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
