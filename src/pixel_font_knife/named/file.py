from __future__ import annotations

from collections.abc import Sequence
from os import PathLike
from pathlib import Path

from pixel_font_knife.glyph.common import check_glyph_name_key, check_flavors, normalize_flavor_order
from pixel_font_knife.glyph.file import GlyphFile


class NamedGlyphFile(GlyphFile):
    """采用固定名称 PNG 文件命名范式的字形文件实体。

    ``name_key`` 和 ``flavors`` 表示字形身份及本地存储信息，并共同决定规范文件名。``name_key`` 必须
    与所属 ``NamedGlyphVariants`` 及 ``NamedContext`` 的名称键一致，不允许再次映射；若需修改，必须先
    将字形文件脱离原变体集合，再按新的 name key 建立映射。属性修改后应立即调用 ``normalize()``，
    将本地文件重命名为由当前属性确定的规范文件名。

    glyph name 由 name key 和第一个 flavor 生成；只使用第一个 flavor 是为了控制字体内 glyph name
    的长度。无 flavor 时 glyph name 等于 name key。``load()`` 从文件名解析属性并验证 name key 与
    flavor，不会修改它们的大小写或其他字符。``normalize()`` 只在原目录内规范文件名，不会更新任何
    上下文映射，也不会校验所在目录能否被 ``NamedContext`` 无冲突地重新加载。

    ``load_notdef()`` 创建 glyph name 为 ``.notdef`` 的独立字形文件实体；该实体类型可以复用于
    ``.notdef``，但不因此属于 ``NamedContext`` 的使用映射。
    """

    @staticmethod
    def load(file_path: str | PathLike[str]) -> NamedGlyphFile:
        if not isinstance(file_path, Path):
            file_path = Path(file_path)

        if file_path.suffix != '.png':
            raise ValueError(f'illegal glyph file extension: {str(file_path)!r}')

        name_key, separator, flavors_text = file_path.stem.partition(' ')
        flavors = flavors_text.split(',') if separator else []
        return NamedGlyphFile(file_path, name_key, flavors)

    @staticmethod
    def load_notdef(file_path: str | PathLike[str]) -> NamedGlyphFile:
        if not isinstance(file_path, Path):
            file_path = Path(file_path)

        if file_path.suffix != '.png':
            raise ValueError(f'illegal glyph file extension: {str(file_path)!r}')

        return NamedGlyphFile(file_path, '.notdef')

    name_key: str
    flavors: list[str]

    def __init__(
            self,
            file_path: str | PathLike[str],
            name_key: str,
            flavors: list[str] | None = None,
    ):
        check_glyph_name_key(name_key)
        if flavors is not None:
            check_flavors(flavors)

        super().__init__(file_path)
        self.name_key = name_key
        self.flavors = flavors if flavors is not None else []

    @property
    def glyph_name(self) -> str:
        name = self.name_key
        if len(self.flavors) > 0:
            name = f'{name}.{self.flavors[0]}'
        return name

    def normalize(self, flavor_order: str | Sequence[str | None] | None = None) -> None:
        if not self.file_path.exists():
            raise FileNotFoundError(f'missing glyph file:\n{str(self.file_path)!r}')

        check_glyph_name_key(self.name_key)
        check_flavors(self.flavors)

        flavor_order = normalize_flavor_order(flavor_order)

        if len(self.flavors) > 0:
            if flavor_order is None:
                flavors = self.flavors
            else:
                flavors = sorted(self.flavors, key=lambda x: flavor_order.index(x))
            file_name = f'{self.name_key} {",".join(flavors)}.png'
        else:
            file_name = f'{self.name_key}.png'

        if self.file_path.name != file_name:
            file_path = self.file_path.with_name(file_name)
            if file_path.exists():
                raise FileExistsError(f'duplicate glyph files:\n{str(self.file_path)!r}\n{str(file_path)!r}')
            else:
                self.file_path.rename(file_path)
                self.file_path = file_path
