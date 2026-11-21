from __future__ import annotations

from collections.abc import Sequence
from os import PathLike
from pathlib import Path

from pixel_font_knife.glyph.common import check_glyph_name_key, check_flavors, normalize_flavor_order
from pixel_font_knife.glyph.file import GlyphFile


class NamedGlyphFile(GlyphFile):
    """Glyph file entity following the fixed-name PNG naming convention.

    ``name_key`` and ``flavors`` describe glyph identity and local storage, and
    together determine the canonical filename. ``name_key`` must match the keys
    in its ``NamedGlyphVariants`` and ``NamedContext``; remapping to a different
    name key is not allowed. Before changing it, detach the file from its original
    variant set, then map it under the new key. After editing attributes, call
    ``normalize()`` promptly to rename the local file to its canonical filename.

    The glyph name is derived from the name key and the first flavor only, to
    limit its length within the font. Without flavors, it equals the name key.
    ``load()`` parses attributes from the filename and validates the name key and
    flavors without changing their case or other characters. ``normalize()`` only
    normalizes the filename within its current directory; it neither updates
    context mappings nor checks whether ``NamedContext`` can reload the directory
    without conflicts.

    ``load_notdef()`` creates a standalone entity with the glyph name ``.notdef``.
    Reusing this entity type for ``.notdef`` does not make it part of a
    ``NamedContext`` usage mapping.
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
        if self.flavors:
            name = f'{name}.{self.flavors[0]}'
        return name

    def normalize(self, flavor_order: str | Sequence[str | None] | None = None) -> None:
        if not self.file_path.exists():
            raise FileNotFoundError(f'missing glyph file:\n{str(self.file_path)!r}')

        check_glyph_name_key(self.name_key)
        check_flavors(self.flavors)

        flavor_order = normalize_flavor_order(flavor_order)

        if self.flavors:
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
