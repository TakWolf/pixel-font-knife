from os import PathLike

import png


def load_png(
        file_path: str | bytes | PathLike[str] | PathLike[bytes],
) -> tuple[list[list[int]], int, int]:
    width, height, pixels, _ = png.Reader(filename=file_path).read()
    bitmap = []
    for pixels_row in pixels:
        bitmap_row = []
        for i in range(0, width * 4, 4):
            alpha = pixels_row[i + 3]
            bitmap_row.append(1 if alpha > 127 else 0)
        bitmap.append(bitmap_row)
    return bitmap, width, height


def save_png(
        bitmap: list[list[int]],
        file_path: str | bytes | PathLike[str] | PathLike[bytes],
        color: tuple[int, int, int] = (0, 0, 0),
):
    red, green, blue = color
    pixels = []
    for bitmap_row in bitmap:
        pixels_row = []
        for alpha in bitmap_row:
            pixels_row.append(red)
            pixels_row.append(green)
            pixels_row.append(blue)
            pixels_row.append(255 if alpha != 0 else 0)
        pixels.append(pixels_row)
    png.from_array(pixels, 'RGBA').save(file_path)
