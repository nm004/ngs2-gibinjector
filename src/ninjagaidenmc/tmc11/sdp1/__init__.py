# NGMC Script by Nozomi Miyamori is marked with CC0 1.0.
# This file is a part of NGMC Script.

from __future__ import annotations
from dataclasses import dataclass, field, InitVar
from typing import NamedTuple
from array import array
from itertools import chain

@dataclass
class PackParser:
    data: memoryview
    unknown1: int
    param_info_table: tuple[ParamInfo]
    pack_table: tuple[memoryview]

    def __init__(self, magic, data):
        if (x1 := bytes(data[0x0:0x8])) != (x2 := magic.ljust(8, b'\x00')):
            raise ValueError('data has wrong magic bytes'
                             f' ("{x1.decode()}" != "{x2.decode()}")')
        if (x1 := bytes(data[0x8:0xc])) != b'1PDS':
            raise ValueError(f'not supported SDP version "{x1.decode()}"')
        container_size = int.from_bytes(data[0xc:0x10], 'little')
        self.data = data = data[:container_size].toreadonly()

        param_count = int.from_bytes(data[0x10:0x14], 'little')
        self.unknown1 = int.from_bytes(data[0x14:0x18], 'little')
        pack_count = int.from_bytes(data[0x18:0x1c], 'little')
        pack_size = int.from_bytes(data[0x1c:0x20], 'little')
        param_info_table_ofs = int.from_bytes(data[0x20:0x24], 'little')
        pack_table_ofs = int.from_bytes(data[0x24:0x28], 'little')
        # array_table_ofs = int.from_bytes(data[0x28:0x2c], 'little')
        # blob_table_ofs =  int.from_bytes(data[0x2c:0x30], 'little')

        o1 = param_info_table_ofs
        o2 = o1 + pack_table_ofs
        self.param_info_table = tuple(
            PackParser._gen_param_info_table(data[o1:o2], param_count)
        )

        n = 4*pack_size
        o1 = pack_table_ofs
        o2 = o1 + pack_count * n
        self.pack_table = tuple( data[o:o+n] for o in range(o1, o2, n) )

    # Param info table could be a hash table with separate chaining,
    # but I have no idea about the hash function used for this table.
    @staticmethod
    def _gen_param_info_table(data, param_count):
        for o in range(0, 0x10*param_count, 0x10):
            array_size = int.from_bytes(data[o:o+0x3], 'little') & 0x00ffffff
            value_type = data[0x3]
            param_index = int.from_bytes(data[o+0x4:o+0x8], 'little')
            param_id_ofs = int.from_bytes(data[o+0x8:o+0xc], 'little')
            next_node = int.from_bytes(data[o+0xc:o+0x10], 'little')

            o1 = 4*param_id_ofs
            o2 = o1 + 4*data[o1+3]
            param_id = data[o1:o2]

            # MSB of next_node is 1 if this is the first node of a bucket. Otherwise, it is 0.
            # next_node is -1 (0x7FFFFFFF) when next node is null.
            yield ParamInfo(array_size, value_type, param_index, param_id, next_node)

class ParamInfo(NamedTuple):
    array_size: int
    value_type: int
    param_index: int
    param_id: memoryview
    next_node: int
            
class EPM1Parser(PackParser):
    def __init__(self, data):
        super().__init__(b'EPM1', data)

class WorkPackParser(PackParser):
    def __init__(self, data):
        super().__init__(b'WorkPack', data)

class BankPackParser(PackParser):
    def __init__(self, data):
        super().__init__(b'BankPack', data)

@dataclass
class TexIndexParser:
    data: memoryview
    
    def __init__(self, data):
        if (x1 := bytes(data[0x0:0x8])) != b'TexIndex'):
            raise ValueError('data has wrong magic bytes'
                             f' ("{x1.decode()}" != "TexIndex")')
        if (x1 := bytes(data[0x8:0xc])) != b'1DIN'):
            raise ValueError(f'not supported TexIndex version "{x1.decode()}"')
        container_size = int.from_bytes(data[0xc:0x10], 'little')
        self.data = data = data[:container_size].toreadonly()

        count = int.from_bytes(data[0x10:0x14], 'little')
        unknown1 = int.from_bytes(data[0x14:0x18], 'little')

@dataclass
class EffectPackWrapperParser:
    data: memoryview
    name: bytes
    effect_pack_wrapper_id: int
    data_count: int
    unknown1: int
    unknown2: int
    packs: tuple

    def __init__(self, data):
        self.data = data.toreadonly()
        self.name = bytes(data[0:0x10]).partition(b'\x00')[0]
        self.pack_id = int.from_bytes(data[0x10:0x14], 'little')
        self.data_count = int.from_bytes(data[0x14:0x18], 'little')
        # They seem to relate to TexIndex.
        self.unknown1 = int.from_bytes(data[0x18:0x1c], 'little', signed=True)
        self.unknown2 = int.from_bytes(data[0x1c:0x20], 'little', signed=True)

class Pack:
    packs: list[tuple[Param]]
    unknown1: int

    def __init__(self):
        self.packs = []
        self.unknown1 = 0

    @classmethod
    def from_bytes(cls, data, /, parser):
        parser = parser(memoryview(data))
        instance = cls()
        instance.packs = list( tuple(Pack._gen_params(parser, p)) for p in parser.pack_table )
        instance.unknown1 = parser.unknown1
        return instance

    @staticmethod
    def _gen_params(parser, pack):
        data = parser.data
        for pi in parser.param_info_table:
            o = 4*pi.param_index
            enabled = int.from_bytes(pack[o:o+4], 'little')
            match pi.value_type:
                case 0x01:
                    value = pack[o+4]
                case 0x02:
                    value = int.from_bytes(pack[o+4:o+8], 'little')
                case 0x04:
                    value = pack[o+4:o+8].cast('f')[0]
                case 0x12 | 0x14:
                    x = { 0x12: 'I', 0x14: 'f' }[pi.value_type]
                    o1 = enabled
                    o2 = o1 + 4*pi.array_size
                    value = ( (o1 and array(x, bytes(data[o1:o2])))
                              or array(x, (0 for _ in range(pi.array_size))) )
                case 0x40:
                    o = enabled
                    value = ( (o and BankPack.from_bytes(data[o:]))
                              or BankPack() )
                case 0x80:
                    o1 = enabled
                    o2 = o1 + int.from_bytes(pack[o+4:o+8], 'little')
                    value = ( (o1 and EffectPackWrapper.from_bytes(data[o1:o2]))
                              or EffectPackWrapper() )
                case _:
                    raise ValueError(f"unknown value type {pi.value_type}")

            yield Param(bool(enabled), value, pi.param_id, pi.next_node)

    def serialize(self, magic):
        (param_info_table_size, pack_size, pack_table_size,
         array_table_size, blob_table_size, total_size) = self._sizes()

        # This writes the header
        B = bytearray(total_size)
        B[0x0:0x8] = magic.ljust(0x8, b'\x00')
        B[0x8:0xc] = b'1PDS'
        B[0xc:0x10] = len(B).to_bytes(4, 'little')
        B[0x10:0x14] = len(self.packs[0]).to_bytes(4, 'little')
        B[0x14:0x18] = self.unknown1.to_bytes(4, 'little')
        B[0x18:0x1c] = len(self.packs).to_bytes(4, 'little')
        B[0x1c:0x20] = pack_size.to_bytes(4, 'little')
        x = 0x30
        param_info_table_ofs = bool(param_info_table_size) * x
        B[0x20:0x24] = param_info_table_ofs.to_bytes(4, 'little')
        x += param_info_table_size
        pack_table_ofs = bool(pack_table_size) * x
        B[0x24:0x28] = pack_table_ofs.to_bytes(4, 'little')
        x += pack_table_size
        array_table_ofs = bool(array_table_size) * x
        B[0x28:0x2c] = array_table_ofs.to_bytes(4, 'little')
        x += array_table_size
        blob_table_ofs = bool(blob_table_size) * x
        B[0x2c:0x30] = blob_table_ofs.to_bytes(4, 'little')

        # This writes param info table
        x1 = 0
        o_p = 0x30 + 0x10 * len(self.packs[0])
        for i, p in enumerate(self.packs[0]):
            o = 0x30 + 0x10*i
            match p.value:
                case bool():
                    B[o+3] = 0x1
                    x = 2
                case int():
                    B[o+3] = 0x2
                    x = 2
                case float():
                    B[o+3] = 0x4
                    x = 2
                case array():
                    B[o:o+0x3] = len(p.value).to_bytes(3, 'little')
                    try:
                        t = {'I': 0x12, 'L': 0x12, 'f': 0x14}[p.value.typecode]
                    except KeyError as e:
                        raise ValueError(f"invalid array type '{p.value.typecode}'") from e
                    B[o+3] = t
                    x = 1
                case BankPack():
                    B[o+3] = 0x40
                    x = 1
                case EffectPackWrapper():
                    B[o+3] = 0x80
                    x = 2
                case _:
                    raise ValueError(f"invalid value type {p.value}")
            B[o+0x4:o+0x8] = x1.to_bytes(4, 'little')
            x1 += x
            B[o+0x8:o+0xc] = ((o_p-0x30)//4).to_bytes(4, 'little')
            B[o_p:o_p+len(p.param_id)] = p.param_id
            o_p += len(p.param_id)
            B[o+0xc:o+0x10] = p.next_node.to_bytes(4, 'little')

        # This writes pack table, array table and blob table
        o1 = pack_table_ofs
        o2 = array_table_ofs
        o3 = blob_table_ofs
        for p in self.packs:
            for j, q in enumerate(p):
                match q.value:
                    case bool() | int() | float():
                        B[o1] = q.enabled
                        if q.enabled:
                            match q.value:
                                case bool():
                                    B[o1+4] = q.value
                                case int():
                                    B[o1+4:o1+8] = q.value.to_bytes(4, 'little')
                                case float():
                                    B[o1+4:o1+8] = bytes(array('f', (q.value,)))
                        o1 += 8
                    case array():
                        v = bytes(q.value)
                        if q.enabled:
                            B[o1:o1+4] = o2.to_bytes(4, 'little')
                            B[o2:o2+len(v)] = v
                        o1 += 4
                        o2 += len(v)
                    case BankPack():
                        if q.enabled:
                            v = bytes(q.value)
                            B[o1:o1+4] = o3.to_bytes(4, 'little')
                            B[o3:o3+len(v)] = v
                            o3 += len(v)
                        o1 += 4
                    case EffectPackWrapper():
                        if q.enabled:
                            v = bytes(q.value)
                            B[o1:o1+4] = o3.to_bytes(4, 'little')
                            B[o1+4:o1+8] = len(v).to_bytes(4, 'little')
                            B[o3:o3+len(v)] = v
                            o3 += len(v)
                        o1 += 8
                    case _:
                        raise ValueError("invalid value type")

        return bytes(B)

    @property
    def _nbytes(self):
        return self._sizes()[-1]

    def _sizes(self):
        if not len(self.packs):
            return (0,0,0,0,0,0x30)

        param_info_table_size = 0x10 * len(self.packs[0]) + sum(len(p.param_id) for p in self.packs[0])
        param_info_table_size += -param_info_table_size % 0x10

        pack_size = sum( isinstance(p.value, array) or 2 for p in self.packs[0] )
        pack_table_size = 4*pack_size * len(self.packs)
        pack_table_size += -pack_table_size % 0x10

        array_table_size = sum( p.value.itemsize * len(p.value)
                                for p in chain.from_iterable(self.packs)
                                if isinstance(p.value, array) )
        array_table_size += -array_table_size % 0x10

        P = ( p for p in chain.from_iterable(self.packs)
              if ( isinstance(p.value, BankPack | EffectPackWrapper) ))
        blob_table_size = sum( bool(p.enabled) * p.value._nbytes for p in P )
        blob_table_size += -blob_table_size % 0x10

        total_size = (0x30 + param_info_table_size + pack_table_size
                      + array_table_size + blob_table_size)

        return (param_info_table_size, pack_size, pack_table_size,
                array_table_size, blob_table_size, total_size)

class EPM1(Pack):
    @classmethod
    def from_bytes(cls, data):
        return super().from_bytes(data, EPM1Parser)

    def __bytes__(self):
        return self.serialize(b'EPM1')

class WorkPack(Pack):
    @classmethod
    def from_bytes(cls, data):
        return super().from_bytes(data, WorkPackParser)

    def __bytes__(self):
        return self.serialize(b'WorkPack')

class BankPack(Pack):
    @classmethod
    def from_bytes(cls, data):
        return super().from_bytes(data, BankPackParser)

    def __bytes__(self):
        return self.serialize(b'BankPack')

class EffectPackWrapper:
    name: bytes = b''
    effect_pack_wrapper_id: int = -1
    unknown1: int = -1
    unknown2: int = -1
    packs: tuple[TexIndex] | tuple[WorkPack] | tuple[WorkPack,TexIndex] = ()

    @classmethod
    def from_bytes(cls, data):
        parser = EffectPackWrapperParser(memoryview(data))
        instance = cls()
        instance.name = parser.name
        instance.effect_pack_wrapper_id = parser.effect_pack_wrapper_id
        instance.unknown1 = parser.unknown1
        instance.unknown2 = parser.unknown2
        instance.packs = tuple(parser.data)
        match parser.data_count:
            case 1:
                d = data[0x20:]
                v1 = self.unknown1 == -1 and WorkPack.from_bytes(d) or TexIndex.from_bytes(d)
                instance.packs = (parser(),)
            case 2:
                d = data[0x20:]
                v1 = WorkPack.from_bytes(data[0x20:])
                d = data[0x20 + v1.data.nbytes:]
                v2 = TexIndex.from_bytes(d)
                instance.packs = (v1, v2)
            case _:
                raise ValueError(f'unknown data count {data_count}')

        return instance

    @property
    def _nbytes(self):
        return sum( p._nbytes for p in self.packs )

    def __bytes__(self):
        B = bytearray(0x20)
        B[0x0:0x10] = self.name[:0xf].ljust(0x10, b'\x00')
        B[0x10:0x14] = self.effect_pack_wrapper_id.to_bytes(4, 'little')
        B[0x14:0x18] = len(self.packs).to_bytes(4, 'little')
        B[0x18:0x1c] = self.unknown1.to_bytes(4, 'little', signed=True)
        B[0x1c:0x20] = self.unknown2.to_bytes(4, 'little', signed=True)
        for p in self.packs:
            B += bytes(p)
        return bytes(B)

@dataclass
class Param:
    enabled: bool = False
    value: EffectPackWrapper | BankPack | bool | int | float | array = False
    param_id: bytes = b''
    next_node: int = -1

@dataclass
class TexIndex:
    @classmethod
    def from_bytes(cls, data):
        instance = cls()
        instance._data = memoryview(bytes(data))
        return instance

    @property
    def _nbytes(self):
        return self._data.nbytes

    def __bytes__(self):
        return bytes(self._data)
