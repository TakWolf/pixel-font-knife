from abc import ABC, abstractmethod
from os import PathLike
from pathlib import Path

from pixel_font_knife.bitmap.mono_bitmap import MonoBitmap
from pixel_font_knife.glyph.canvas import GlyphCanvas


class GlyphFile(ABC):
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
