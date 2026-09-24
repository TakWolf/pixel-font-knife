from __future__ import annotations

from collections.abc import Sequence
from os import PathLike
from pathlib import Path

import unidata_blocks

from pixel_font_knife.glyph.common import check_code_point, check_flavors, normalize_flavor_order
from pixel_font_knife.glyph.file import GlyphFile


class CmapGlyphFile(GlyphFile):
    """采用 cmap PNG 文件命名范式的字形文件实体。

    ``code_point`` 和 ``flavors`` 表示字形身份及本地存储信息，并共同决定规范文件路径；它们不表示
    ``CmapContext`` 中的使用映射键。属性在素材设计阶段允许修改，修改后应立即调用 ``normalize()``
    将本地文件移动到由当前属性确定的规范路径。

    glyph name 由 code point 和第一个 flavor 生成；只使用第一个 flavor 是为了控制字体内 glyph name
    的长度。无 flavor 时名称仅由 code point 生成。``load()`` 从文件名解析属性并验证 flavor，
    不会修改 flavor 的大小写或其他字符。``normalize()`` 只规范本地路径，不会更新任何上下文映射，
    也不会校验整个目录能否无冲突地重新加载。
    """

    @staticmethod
    def get_normalized_dir(
            code_point: int,
            root_dir: str | PathLike[str],
    ) -> Path:
        if not isinstance(root_dir, Path):
            root_dir = Path(root_dir)

        block = unidata_blocks.get_block_by_code_point(code_point)
        file_dir = root_dir.joinpath(f'{block.code_start:04X}-{block.code_end:04X} {block.name}')
        if block.name == 'CJK Unified Ideographs':
            code_name = f'{code_point:04X}'
            file_dir = file_dir.joinpath(f'{code_name[0:-2]}-')
        return file_dir

    @staticmethod
    def load(file_path: str | PathLike[str]) -> CmapGlyphFile:
        if not isinstance(file_path, Path):
            file_path = Path(file_path)

        if file_path.suffix != '.png':
            raise ValueError(f'illegal glyph file extension: {str(file_path)!r}')

        code_point_text, separator, flavors_text = file_path.stem.partition(' ')
        code_point = int(code_point_text, 16)
        flavors = flavors_text.split(',') if separator else []
        return CmapGlyphFile(file_path, code_point, flavors)

    code_point: int
    flavors: list[str]

    def __init__(
            self,
            file_path: str | PathLike[str],
            code_point: int,
            flavors: list[str] | None = None,
    ):
        check_code_point(code_point)
        if flavors is not None:
            check_flavors(flavors)

        super().__init__(file_path)
        self.code_point = code_point
        self.flavors = flavors if flavors is not None else []

    @property
    def glyph_name(self) -> str:
        name = f'u{self.code_point:04X}'
        if len(self.flavors) > 0:
            name = f'{name}.{self.flavors[0]}'
        return name

    def normalize(
            self,
            root_dir: str | PathLike[str],
            flavor_order: str | Sequence[str | None] | None = None,
    ) -> None:
        if not self.file_path.exists():
            raise FileNotFoundError(f'missing glyph file:\n{str(self.file_path)!r}')

        check_code_point(self.code_point)
        check_flavors(self.flavors)

        flavor_order = normalize_flavor_order(flavor_order)

        file_dir = CmapGlyphFile.get_normalized_dir(self.code_point, root_dir)

        if len(self.flavors) > 0:
            if flavor_order is None:
                flavors = self.flavors
            else:
                flavors = sorted(self.flavors, key=lambda x: flavor_order.index(x))
            file_name = f'{self.code_point:04X} {",".join(flavors)}.png'
        else:
            file_name = f'{self.code_point:04X}.png'

        file_path = file_dir.joinpath(file_name)
        if self.file_path != file_path:
            if file_path.exists():
                raise FileExistsError(f'duplicate glyph files:\n{str(self.file_path)!r}\n{str(file_path)!r}')
            else:
                file_dir.mkdir(parents=True, exist_ok=True)
                self.file_path.rename(file_path)
                self.file_path = file_path
