from abc import ABC, abstractmethod
from os import PathLike
from pathlib import Path

from pixel_font_knife.bitmap.mono_bitmap import MonoBitmap
from pixel_font_knife.glyph.canvas import GlyphCanvas


class GlyphFile(ABC):
    """构建期间可直接加入字形序列的文件实体。

    每个实体绑定一个由子类定义的 glyph name、一个本地 PNG 文件路径，以及按需加载并缓存的
    ``GlyphCanvas``。同一个实体可以被多个上下文映射引用；这些引用共享对象属性和画布缓存。

    ``file_path`` 表示当前持久化位置。修改路径不会重新加载或清空已经缓存的画布；``save()`` 始终将
    当前画布写入当前路径。子类可以开放影响字形身份或规范路径的可变属性，调用方修改后应按照对应领域
    的约定及时规范化本地文件。
    """

    file_path: Path
    _canvas: GlyphCanvas | None

    def __init__(self, file_path: str | PathLike[str]) -> None:
        self.file_path = file_path if isinstance(file_path, Path) else Path(file_path)
        self._canvas = None

    @property
    @abstractmethod
    def glyph_name(self) -> str:
        raise NotImplementedError()

    @property
    def canvas(self) -> GlyphCanvas:
        if self._canvas is None:
            bitmap = MonoBitmap.load_png(self.file_path)
            self._canvas = GlyphCanvas(bitmap)
        return self._canvas

    @canvas.setter
    def canvas(self, canvas: GlyphCanvas) -> None:
        self._canvas = canvas

    def save(self) -> None:
        self.canvas.bitmap.save_png(self.file_path)
