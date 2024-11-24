# NINJA GAIDEN Mater Collection scripts by Nozomi Miyamori
# is marked with CC0 1.0. This file is a part of NINJA GAIDEN
# Master Collection Scripts.
#
# This module is for parsing databin bundled with NINJA GAIDEN
# Master Collection.

from __future__ import annotations
from typing import NamedTuple
from contextlib import contextmanager
import zlib

class DatabinParser:
    chunks: tuple[Chunk]

    def __init__(self, data):
        data = memoryview(data).toreadonly()

        # version = int.from_bytes(data[:4], 'little')
        chunk_info_size = int.from_bytes(data[0x4:0x8], 'little')
        # unknown_0x8 = int.from_bytes(data[0x8:0xc], 'little')

        head_size = int.from_bytes(data[0x10:0x14], 'little')
        directory_size = int.from_bytes(data[0x14:0x18], 'little')
        # unknown_0x18 = int.from_bytes(data[0x18:0x1c], 'little')
        
        o1 = head_size
        o2 = head_size + directory_size
        directory = data[o1:o2]

        chunks_count = int.from_bytes(directory[:4], 'little')

        # we don't use these but leave them for informational notes.
        #infoidx_map_ofs = int.from_bytes(directory[0x4:0x8], 'little')
        #infoidx_map_count = int.from_bytes(directory[0x8:0xc], 'little')

        #chunk_info_idx = int.from_bytes(infoidx_map[o:o+4], 'little')
        #chunk_idx = int.from_bytes(infoidx_map[o+4:o+8], 'little')

        o1 = 0x10
        o2 = 0x10 + 4*chunks_count
        chunk_info_ofs_table = directory[o1:o2].cast('I')

        n = chunk_info_size
        chunk_info = tuple( directory[o:o+n] for o in chunk_info_ofs_table )

        o = head_size + directory_size
        self.chunks = tuple(self._gen_chunks(chunk_info, data[o:]))

    @staticmethod
    def _gen_chunks(chunk_info, chunkbin):
        for k, i in enumerate(chunk_info):
            offset = int.from_bytes(i[:0x8], 'little')
            decompressed_size = int.from_bytes(i[0x8:0xc], 'little')
            compressed_size = int.from_bytes(i[0xc:0x10], 'little')
            linked_chunk_index = int.from_bytes(i[0x14:0x16], 'little', signed=True)
            tag1 = i[0x16]
            tag2 = i[0x17]

            o1 = offset
            o2 = offset + compressed_size
            data = chunkbin[o1:o2]

            yield Chunk( k, decompressed_size, compressed_size,
                         linked_chunk_index, tag1, tag2, data )

    def close(self):
        for c in self.chunks:
            c.data.release()

    def __enter__(self):
        return self

    def __exit__(self, ex_type, ex_value, trace):
        self.close()

class Chunk(NamedTuple):
    index: int
    decompressed_size: int
    compressed_size: int
    linked_chunk_index: int
    tag1: int
    tag2: int
    data: memoryview

def decompress(chunk):
    try:
        return zlib.decompress(chunk.data)
    except zlib.error:
        return b''
