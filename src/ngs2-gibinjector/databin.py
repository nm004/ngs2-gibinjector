# NGS2 Gib Injector by Nozomi Miyamori is marked with CC0 1.0.
# This file is a part of NGS2 Gib Injector.
#
# This module is for parsing databin bundled with NINJA GAIDEN
# Master Collection.
from collections import namedtuple
from enum import IntEnum
import zlib

class Databin:
    def __init__(self, data):
        self._data = data = memoryview(data)
        chunkbin = self._get_chunkbin(data)
        self._chunks = { i: Chunk(info, chunkbin) for i, info in self._generate_chunk_info(data) }

    @property
    def chunks(self):
        return self._chunks

    @staticmethod
    def _get_head(data):
        return data[0:0x20].cast('I')

    @staticmethod
    def _get_directory(data):
        H = Databin._get_head(data)
        return data[H[4]:H[5]]

    @staticmethod
    def _get_chunkbin(data):
        H = Databin._get_head(data)
        return data[H[4]+H[5]:]

    @staticmethod
    def _generate_chunk_info(data):
        D = Databin._get_directory(data)
        chunk_info_ofs_table = D[0x10:].cast('I')
        chunk_id_index_map_ofs = D[0x4:].cast('I')[0]
        chunk_id_index_map_item_count = D[0x8:].cast('I')[0]
        chunk_id_index_map = D[chunk_id_index_map_ofs:].cast('I')
        # chunk_info_ofs_table_item_count = D[0x0:].cast('I')[0]
        for i in range(chunk_id_index_map_item_count):
            chunk_id = chunk_id_index_map[2*i]
            chunk_index = chunk_id_index_map[2*i+1]
            chunk_info_ofs = chunk_info_ofs_table[chunk_index]
            yield ( chunk_id, D[chunk_info_ofs:chunk_info_ofs+0x18] )

class Chunk:
    def __init__(self, info, chunkbin):
        self._info = info
        o = self._offset
        self._data = chunkbin[o:o+self.compressed_size]

    def decompress(self):
        return zlib.decompress(self._data)

    @property
    def type(self):
        return ChunkType(self._info[0x17:].cast('B')[0])

    @property
    def _offset(self):
        return self._info.cast('Q')[0]

    @property
    def size(self):
        return self._info[0x8:].cast('I')[0]

    @property
    def compressed_size(self):
        return self._info[0xc:].cast('I')[0]

class ChunkType(IntEnum):
    LANG = 0
    UNKNOWN1 = 1
    UNKNOWN2 = 2
    TDP4ACT = 3
    TDP4CLD = 4
    UNKNOWN5 = 5
    UNKNOWN6 = 6
    UNKNOWN7 = 7
    TMC_EFF = 8
    UNKNOWN9 = 9
    UNKNOWN10 = 10
    TMC = 11
    UNKNOWN12 = 12
    itm_dat2 = 13
    UNKNOWN14 = 14
    TMCL1 = 15
    UNKNOWN16 = 16
    chr_dat = 17
    rtm_dat = 18
    tdpack = 19
    TDP4SOB = 20
    TDP4SOC = 21
    sprpack = 22
    STAGEETC = 23
    TDP4STY = 24
    TNF = 25
    TMCL2 = 26
    TMCL3 = 27
    XWSFILE = 28
    PNG = 29
    WMV = 30
