import struct
import zlib
from io import BytesIO

_PNG_SIGNATURE = b'\x89PNG\r\n\x1a\n'


class MiniPNGReader:
    def __init__(self, data: bytes):
        self.data = data
        self.pos = 8
        self.width = 0
        self.height = 0
        self.pixels: list[list[int]] = []

    def read_chunk(self) -> tuple[bytes, bytes]:
        if self.pos + 8 > len(self.data):
            raise ValueError("unexpected end of png data")
        length = struct.unpack('>I', self.data[self.pos:self.pos+4])[0]
        self.pos += 4
        chunk_type = self.data[self.pos:self.pos+4]
        self.pos += 4
        chunk_data = self.data[self.pos:self.pos+length]
        self.pos += length
        _crc = self.data[self.pos:self.pos+4]
        self.pos += 4
        return chunk_type, chunk_data

    def _parse_ihdr(self, data: bytes):
        if len(data) != 13:
            raise ValueError("invalid ihdr length")
        self.width, self.height, bit_depth, color_type, compression, filter_method, interlace = struct.unpack('>IIBBBBB', data)

        if bit_depth != 8:
            raise ValueError(f"unsupported bit depth: {bit_depth}")
        if color_type != 6:  # RGBA
            raise ValueError(f"unsupported color type: {color_type}")
        if compression != 0:
            raise ValueError("unsupported compression method")
        if filter_method != 0:
            raise ValueError("unsupported filter method")
        if interlace != 0:
            raise ValueError("interlaced images not supported")

    def _decode_scanlines(self, raw_data: bytes) -> list[list[int]]:
        stride = self.width * 4 + 1
        if len(raw_data) != stride * self.height:
            raise ValueError("decompressed data size mismatch")

        rows = []
        for y in range(self.height):
            start = y * stride
            filter_type = raw_data[start]
            if filter_type != 0:
                raise ValueError(f"unsupported filter type: {filter_type}")
            scanline = raw_data[start+1:start+stride]
            rows.append(list(scanline))
        return rows

    def parse(self) -> tuple[int, int, list[list[int]]]:
        if self.data[:8] != _PNG_SIGNATURE:
            raise ValueError("invalid png signature")

        idat_parts = []
        while self.pos < len(self.data):
            chunk_type, chunk_data = self.read_chunk()
            if chunk_type == b'IHDR':
                self._parse_ihdr(chunk_data)
            elif chunk_type == b'IDAT':
                idat_parts.append(chunk_data)
            elif chunk_type == b'IEND':
                break

        if not idat_parts:
            raise ValueError("no idat chunks found")

        compressed = b''.join(idat_parts)
        raw_data = zlib.decompress(compressed)
        rows = self._decode_scanlines(raw_data)
        return self.width, self.height, rows


class MiniPNGWriter:
    def __init__(self, width: int, height: int):
        self.width = width
        self.height = height
        self._chunks: list[bytes] = []

    def add_chunk(self, chunk_type: bytes, data: bytes):
        length = struct.pack('>I', len(data))
        chunk = length + chunk_type + data
        crc = struct.pack('>I', zlib.crc32(chunk_type + data) & 0xFFFFFFFF)
        self._chunks.append(chunk + crc)

    def build_ihdr(self):
        data = struct.pack(
            '>IIBBBBB',
            self.width,
            self.height,
            8,  # bit depth
            6,  # color type: RGBA
            0,  # compression method
            0,  # filter method
            0   # interlace
        )
        self.add_chunk(b'IHDR', data)

    def build_idat(self, rows: list[list[int]]):
        raw_data = bytearray()
        for row in rows:
            raw_data.append(0)  # filter type 0
            raw_data.extend(bytes(row))
        compressed = zlib.compress(raw_data, level=6)
        self.add_chunk(b'IDAT', compressed)

    def build_iend(self):
        self.add_chunk(b'IEND', b'')

    def dump(self) -> bytes:
        buf = BytesIO()
        buf.write(_PNG_SIGNATURE)
        for chunk in self._chunks:
            buf.write(chunk)
        return buf.getvalue()
