# NGMC Script by Nozomi Miyamori is marked with CC0 1.0.
# This file is a part of NGMC Script.

from __future__ import annotations
from typing import NamedTuple
from array import array
from itertools import chain

class PackParser:
    param_table: tuple[Param]
    packs: tuple[memoryview]
    _data: memoryview

    def __init__(self, magic, data):
        if (x1 := bytes(data[0x0:0x8])) != (x2 := magic.ljust(8, b'\x00')):
            raise ValueError('data has wrong magic bytes'
                             f' ("{x1.decode()}" != "{x2.decode()}")')
        if (x1 := bytes(data[0x8:0xc])) != b'1PDS':
            raise ValueError(f'not supported SDP version "{x1.decode()}"')
        container_size = int.from_bytes(data[0xc:0x10], 'little')
        data = data[:container_size].toreadonly()
        self._data = data

        param_count = int.from_bytes(data[0x10:0x14], 'little')
        # unknown1 = int.from_bytes(data[0x14:0x18], 'little')
        packs_count = int.from_bytes(data[0x18:0x1c], 'little')
        pack_size = int.from_bytes(data[0x1c:0x20], 'little')
        param_table_ofs = int.from_bytes(data[0x20:0x24], 'little')
        pack_table_ofs = int.from_bytes(data[0x24:0x28], 'little')
        # array_table_ofs = int.from_bytes(data[0x28:0x2c], 'little')
        # blob_table_ofs =  int.from_bytes(data[0x2c:0x30], 'little')

        o1 = param_table_ofs
        o2 = param_table_ofs + pack_table_ofs
        self.param_table = tuple(
            PackParser.__gen_param_table(data[o1:o2], param_count)
        )

        n = 4*pack_size
        o1 = pack_table_ofs
        o2 = pack_table_ofs + packs_count * n
        # print(magic, pack_count * n, n)
        self.packs = tuple( tuple(PackParser.__gen_packs(
            data[o:o+n], self.param_table, data
        )) for o in range(o1, o2, n) )

    # Param table could be a hash table with separate chaining,
    # but I have no idea about the hash function used for this table.
    @staticmethod
    def __gen_param_table(data, param_count):
        for o in range(0, 0x10*param_count, 0x10):
            array_size = int.from_bytes(data[o:o+0x3], 'little')
            value_type = data[o+0x3]
            param_index = int.from_bytes(data[o+0x4:o+0x8], 'little')
            param_id_ofs = int.from_bytes(data[o+0x8:o+0xc], 'little')
            # MSB of next_node is 1 if this is the first node of a bucket. Otherwise, it is 0.
            # next_node is -1 (0x7FFFFFFF) when next node is null.
            next_node = int.from_bytes(data[o+0xc:o+0x10], 'little') & 0x7fffffff
            is_first_node = bool(data[o+0xf] & 0x80)

            o1 = 4*param_id_ofs
            o2 = o1 + 4*data[o1+3]
            param_id = data[o1:o2]

            yield Param(array_size, value_type, param_index, param_id, next_node, is_first_node)

    @staticmethod
    def __gen_packs(pack_table, param_table, data):
        for i, p in enumerate(param_table):
            o = 4*p.index
            enabled = int.from_bytes(pack_table[o:o+4], 'little')
            if not enabled:
                yield None
                continue

            match p.value_type:
                case 0x01:
                    yield bool(pack_table[o+4])
                case 0x02:
                    yield int.from_bytes(pack_table[o+4:o+8], 'little')
                case 0x04:
                    yield pack_table[o+4:o+8].cast('f')[0]
                case 0x12 | 0x14:
                    x = { 0x12: 'I', 0x14: 'f' }[p.value_type]
                    o1 = enabled
                    o2 = bool(enabled) * o1 + 4*p.array_size
                    yield data[o1:o2].cast(x)
                case 0x40:
                    o = enabled
                    yield BankPackParser(data[o:])
                case 0x80:
                    o1 = enabled
                    o2 = o1 + int.from_bytes(pack_table[o+4:o+8], 'little')
                    yield PackParser.__make_effectpack(data[o1:o2])
                case x:
                    raise ValueError(f"unknown value type {x}")

    def __make_effectpack(data):
        data = data.toreadonly()
        name = bytes(data[0:0x10]).partition(b'\x00')[0]
        _id = int.from_bytes(data[0x10:0x14], 'little')
        packs_count = int.from_bytes(data[0x14:0x18], 'little')
        # They seem to relate to TexIndex.
        unknown1 = int.from_bytes(data[0x18:0x1c], 'little', signed=True)
        unknown2 = int.from_bytes(data[0x1c:0x20], 'little', signed=True)
        packs = tuple(PackParser.__gen_effectpack_packs(data, packs_count))
        return EffectPackWrapper(name, _id, unknown1, unknown2, packs)

    @staticmethod
    def __gen_effectpack_packs(data, packs_count):
        o = 0x20
        for i in range(packs_count):
            d = data[o:]
            match d[0:0x8]:
                case b'WorkPack':
                    yield WorkPackParser(d)
                case b'TexIndex':
                    yield TexIndexParser(d)
                case _:
                    raise ValueError('unknown data in EffectPackWrapper')
            o += int.from_bytes(d[0xc:0x10], 'little')

class Param(NamedTuple):
    array_size: int
    value_type: int
    index: int
    id: memoryview
    next_node: int
    is_first_node: bool

class EffectPackWrapper(NamedTuple):
    name: bytes
    id: int
    unknown1: int
    unknown2: int
    packs: tuple[WorkPackParser | TexIndexParser]

class EPM1Parser(PackParser):
    def __init__(self, data):
        super().__init__(b'EPM1', data)

class WorkPackParser(PackParser):
    def __init__(self, data):
        super().__init__(b'WorkPack', data)

class BankPackParser(PackParser):
    def __init__(self, data):
        super().__init__(b'BankPack', data)

class TexIndexParser:
    _data: memoryview
    
    def __init__(self, data):
        if (x1 := bytes(data[0x0:0x8])) != b'TexIndex':
            raise ValueError('data has wrong magic bytes'
                             f' ("{x1.decode()}" != "TexIndex")')
        if (x1 := bytes(data[0x8:0xc])) != b'1DIN':
            raise ValueError(f'not supported TexIndex version "{x1.decode()}"')
        container_size = int.from_bytes(data[0xc:0x10], 'little')
        self._data = data[:container_size].toreadonly()

        # unknown_count1 = int.from_bytes(data[0x10:0x14], 'little')
        # unknown2 = int.from_bytes(data[0x14:0x18], 'little')
