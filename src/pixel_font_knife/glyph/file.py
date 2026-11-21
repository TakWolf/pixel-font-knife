from abc import ABC, abstractmethod
from os import PathLike
from pathlib import Path
from typing import Literal

from pixel_font_knife.bitmap.mono import MonoBitmap
from pixel_font_knife.glyph.canvas import GlyphCanvas


class GlyphFile(ABC):
    """File entity that can be included directly in a glyph sequence during a build.

    Each entity binds a subclass-defined glyph name, a local PNG path, and a lazily
    loaded, cached ``GlyphCanvas``. Multiple context mappings may reference the
    same entity, sharing its attributes and canvas cache.

    ``file_path`` is the current storage location. Changing it neither reloads nor
    clears an already cached canvas. ``save()`` always writes the current canvas
    to the current path. Subclasses may expose mutable attributes affecting glyph
    identity or the canonical path. After editing them, callers should promptly
    normalize local files according to the subclass's conventions.
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

    def suggest_horizontal_offset(
            self,
            em_size: int,
            baseline_from_em_top: int,
            vertical_bias: Literal['top', 'bottom'] | None = None,
    ) -> tuple[int, int]:
        return self.canvas.horizontal_offset_for_trimmed(em_size, baseline_from_em_top, vertical_bias)

    def suggest_advance_width(self) -> int:
        return self.canvas.advance_width()

    def suggest_vertical_offset(
            self,
            em_size: int,
            horizontal_bias: Literal['left', 'right'] | None = 'left',
            vertical_bias: Literal['top', 'bottom'] | None = None,
    ) -> tuple[int, int]:
        return self.canvas.vertical_offset_for_trimmed(em_size, horizontal_bias, vertical_bias)

    def suggest_advance_height(self, em_size: int) -> int:
        return self.canvas.advance_height(em_size)

    def suggest_bitmap(self) -> list[list[int]]:
        return self.canvas.trimmed_bitmap.data

    def save(self) -> None:
        self.canvas.bitmap.save_png(self.file_path)
