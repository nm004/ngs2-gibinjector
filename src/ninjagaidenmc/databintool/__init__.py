# NINJA GAIDEN Mater Collection scripts by Nozomi Miyamori
# is marked with CC0 1.0. This file is a part of NINJA GAIDEN
# Master Collection Scripts.
#
# This module is for parsing databin bundled with NINJA GAIDEN
# Master Collection.

from __future__ import annotations
from typing import NamedTuple
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

        # we don't use these because chunk_id == chunk_index
        # id_index_map_ofs = int.from_bytes(directory[0x4:0x8], 'little')
        # id_index_map_count = int.from_bytes(directory[0x8:0xc], 'little')

        # chunk_id = int.from_bytes(id_index_map[o:o+4], 'little')
        # chunk_index = int.from_bytes(id_index_map[o+4:o+8], 'little')

        o1 = 0x10
        o2 = 0x10 + 4*chunks_count
        chunk_info_ofs_table = directory[o1:o2].cast('I')

        n = chunk_info_size
        chunk_info = tuple( directory[o:o+n] for o in chunk_info_ofs_table )

        o = head_size + directory_size
        self.chunks = tuple(self._gen_chunks(chunk_info, data[o:]) )

    @staticmethod
    def _gen_chunks(chunk_info, chunkbin):
        for i in chunk_info:
            offset = int.from_bytes(i[:0x8], 'little')
            decompressed_size = int.from_bytes(i[0x8:0xc], 'little')
            compressed_size = int.from_bytes(i[0xc:0x10], 'little')
            linked_chunk_id = int.from_bytes(i[0x14:0x16], 'little')
            chunk_category1 = i[0x16]
            chunk_category2 = i[0x17]

            o1 = offset
            o2 = offset + compressed_size
            data = chunkbin[o1:o2]

            yield Chunk( decompressed_size, compressed_size,
                         linked_chunk_id, chunk_category1, chunk_category2,
                         data )

    def get_linked_chunks(self, key):
        c = self.chunks[i]
        D = {}
        while (i := c.linked_chunk_id) != -1 and c not in D:
            D[i] = c
            c = self.chunks[i]
        return D

class Chunk(NamedTuple):
    decompressed_size: int
    compressed_size: int
    linked_chunk_id: int
    chunk_category1: int
    chunk_category2: int
    data: memoryview

def decompress(chunk):
    return zlib.decompress(chunk.data)
