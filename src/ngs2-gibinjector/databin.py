# NGS2 Gib Injector by Nozomi Miyamori is marked with CC0 1.0.
# This file is a part of NGS2 Gib Injector.
#
# This module is for parsing databin bundled with NINJA GAIDEN
# Master Collection.
from collections.abc import Mapping
import zlib

class Databin(Mapping):
    def __init__(self, data):
        self._data = data = memoryview(data)
        chunkbin = self._get_chunkbin(data)
        self._chunks = { i: Chunk(info, chunkbin) for i, info in self._generate_chunk_info(data) }

    def __getitem__(self, key):
        return self._chunks[key]

    def __iter__(self):
        return iter(self._chunks)

    def __len__(self):
        return len(self._chunks)

    def __contains__(self, val):
        return key in self._chunks

    def keys(self):
        return self._chunks.keys()

    def items(self):
        return self._chunks.items()

    def values(self):
        return self._chunks.values()

    def get(self, key, default):
        return self._chunks.get(key, default)

    @staticmethod
    def _get_head(data):
        return data[0:0x20].cast('I')

    @staticmethod
    def _get_directory(data):
        H = Databin._get_head(data)
        return data[H[4]:H[4]+H[5]]

    @staticmethod
    def _get_chunkbin(data):
        H = Databin._get_head(data)
        return data[H[4]+H[5]:]

    @staticmethod
    def _generate_chunk_info(data):
        H = Databin._get_head(data)
        D = Databin._get_directory(data)
        chunk_info_ofs_table_item_count = D[0x0:0x4].cast('I')[0]
        chunk_info_ofs_table = D[0x10:0x10 + 4*chunk_info_ofs_table_item_count].cast('I')
        chunk_id_index_map_ofs = D[0x4:0x8].cast('I')[0]
        chunk_id_index_map_item_count = D[0x8:0xc].cast('I')[0]
        chunk_id_index_map = D[chunk_id_index_map_ofs:]
        for i in range(chunk_id_index_map_item_count):
            i = chunk_id_index_map[8*i:8*(i+1)]
            chunk_id = i.cast('I')[0]
            chunk_index = i.cast('I')[1]
            chunk_info_ofs = chunk_info_ofs_table[chunk_index]
            yield ( chunk_id, D[chunk_info_ofs:chunk_info_ofs+H[1]] )

class Chunk:
    def __init__(self, info, chunkbin):
        self._info = info
        o = self._offset
        self._data = chunkbin[o:o+self.compressed_size]

    def decompress(self):
        return zlib.decompress(self._data)

    @property
    def _offset(self):
        return self._info.cast('Q')[0]

    @property
    def size(self):
        return self._info[0x8:0xc].cast('I')[0]

    @property
    def compressed_size(self):
        return self._info[0xc:0x10].cast('I')[0]

    @property
    def linked_chunk_id(self):
        return self._info[0x14:0x16].cast('h')[0]

    @property
    def chunk_group_id(self):
        return self._info[0x16]

    @property
    def chunk_category_id(self):
        return self._info[0x17]
