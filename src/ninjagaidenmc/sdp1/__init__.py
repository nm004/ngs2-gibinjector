from __future__ import annotations
from dataclasses import dataclass, field, InitVar
from typing import ClassVar
from array import array
from itertools import chain

@dataclass
class PackParser:
    _MAGIC: ClassVar[bytes]
    data: memoryview
    magic: bytes = field(init=False)
    version: bytes = field(init=False)
    size: int = field(init=False)
    param_count: int = field(init=False)
    unknown1: int = field(init=False)
    pack_count: int = field(init=False)
    pack_size: int = field(init=False)
    param_info_table_ofs: int = field(init=False)
    pack_table_ofs: int = field(init=False)
    array_table_ofs: int = field(init=False)
    blob_table_ofs: int = field(init=False)
    param_info: tuple[ParamInfoParser] = field(init=False)
    pack_table: tuple[memoryview] = field(init=False)
    def __post_init__(self):
        self.magic = bytes(self.data[0x0:0x8])
        if self.magic != self._MAGIC.ljust(8, b'\x00'):
            raise ValueError(f"data has no magic bytes {self._MAGIC.decode()}")
        self.version = bytes(self.data[0x8:0xc])
        self.size = int.from_bytes(self.data[0xc:0x10], 'little')
        self.param_count = int.from_bytes(self.data[0x10:0x14], 'little')
        self.unknown1 = int.from_bytes(self.data[0x14:0x18], 'little')
        self.pack_count = int.from_bytes(self.data[0x18:0x1c], 'little')
        self.pack_size = int.from_bytes(self.data[0x1c:0x20], 'little')
        self.param_info_table_ofs = int.from_bytes(self.data[0x20:0x24], 'little')
        self.pack_table_ofs = int.from_bytes(self.data[0x24:0x28], 'little')
        self.array_table_ofs = int.from_bytes(self.data[0x28:0x2c], 'little')
        self.blob_table_ofs =  int.from_bytes(self.data[0x2c:0x30], 'little')

        o1 = self.param_info_table_ofs
        o2 = self.pack_table_ofs
        T = self.data[o1:o2]
        o = self.param_info_table_ofs
        self.param_info = tuple( ParamInfoParser(self.data[o+0x10*i:o+0x10*(i+1)], T)
                                 for i in range(self.param_count) )

        n = 4*self.pack_size
        o = self.pack_table_ofs
        self.pack_table = tuple( self.data[o+i*n:o+(i+1)*n]
                                 for i in range(self.pack_count) )

        self.data = self.data[:self.size]

    def to_list(self):
        def f(P):
            for pi in self.param_info:
                o = 4*pi.param_index
                enabled = int.from_bytes(P[o:o+4], 'little')
                match pi.value_type:
                    case 0x01:
                        value = P[o+4]
                    case 0x02:
                        value = int.from_bytes(P[o+4:o+8], 'little')
                    case 0x04:
                        value = P[o+4:o+8].cast('f')[0]
                    case 0x12 | 0x14:
                        x = { 0x12: 'I', 0x14: 'f' }[pi.value_type]
                        o1 = enabled
                        o2 = o1 + 4*pi.array_size
                        value = ( array(x, bytes(self.data[o1:o2]))
                                  if enabled else array(x, (0 for _ in range(pi.array_size))) )
                    case 0x40:
                        o = enabled
                        value = ( BankPack.from_bytes(self.data[o:])
                                  if enabled else BankPack() )
                    case 0x80:
                        o1 = enabled
                        o2 = o1 + int.from_bytes(P[o+4:o+8], 'little')
                        value = ( EffectPackWrapper.from_bytes(self.data[o1:o2])
                                  if enabled else EffectPackWrapper() )
                    case _:
                        raise ValueError(f"unknown value type {pi.value_type}")

                yield Param(bool(enabled), value, pi.param_id, pi._next_param)

        return list( tuple(f(p)) for p in self.pack_table )

class EPM1Parser(PackParser):
    _MAGIC: ClassVar[bytes] = b'EPM1'

class WorkPackParser(PackParser):
    _MAGIC: ClassVar[bytes] = b'WorkPack'

class BankPackParser(PackParser):
    _MAGIC: ClassVar[bytes] = b'BankPack'

# This could be a hash table with separate chaining,
# but I have no idea about the hash function used for this table.
@dataclass
class ParamInfoParser:
    data: memoryview
    param_info_table: InitVar[memoryview]
    array_size: int = field(init=False)
    value_type: int = field(init=False)
    param_index: int = field(init=False)
    param_id_ofs: int = field(init=False)
    param_id: memoryview = field(init=False)

    # MSB is high if this is the first node of a bucket. Otherwise, it is low.
    # It is -1 (0x7FFFFFFF) when next node is null.
    _next_param: int = field(init=False)

    def __post_init__(self, param_info_table):
        self.array_size = int.from_bytes(self.data[0x0:0x3], 'little') & 0x00ffffff
        self.value_type = self.data[0x3]
        self.param_index = int.from_bytes(self.data[0x4:0x8], 'little')
        self.param_id_ofs = int.from_bytes(self.data[0x8:0xc], 'little')
        o = 4*self.param_id_ofs
        T = param_info_table
        self.param_id = T[o:o+4*T[o+3]]
        self._next_param = int.from_bytes(self.data[0xc:0x10], 'little')

@dataclass
class EffectPackWrapperParser:
    data: memoryview
    name: bytes = field(init=False)
    pack_id: int = field(init=False)
    data_count: int = field(init=False)
    # It looks like these are the first indices of something
    unknown1: int = field(init=False)
    unknown2: int = field(init=False)

    def __post_init__(self):
        self.name = bytes(self.data[0:0x10])
        self.pack_id = int.from_bytes(self.data[0x10:0x14], 'little')
        self.data_count = int.from_bytes(self.data[0x14:0x18], 'little')
        self.unknown1 = int.from_bytes(self.data[0x18:0x1c], 'little', signed=True)
        self.unknown2 = int.from_bytes(self.data[0x1c:0x20], 'little', signed=True)

    def to_tuple(self):
        match self.data_count:
            case 1:
                x = WorkPack if self.unknown1 == -1 else TexIndex
                return (x.from_bytes(self.data[0x20:]),)
            case 2:
                o = WorkPackParser(self.data[0x20:]).size
                return (WorkPack.from_bytes(self.data[0x20:]),
                        TexIndex.from_bytes(self.data[o+0x20:]))
            case x:
                raise ValueError(f'unknown value count {x}')

class Pack:
    packs: list[tuple[Param]]
    unknown1: int

    def __init__(self):
        self.packs = []
        self.unknown1 = 0

    @classmethod
    def from_bytes(cls, data, /, parser):
        parser = parser(memoryview(data).toreadonly())
        instance = cls()
        instance.packs = parser.to_list()
        instance.unknown1 = parser.unknown1
        return instance

    def serialize(self, magic_bytes):
        (param_info_table_size, pack_size, pack_table_size,
         array_table_size, blob_table_size, total_size) = self._sizes()

        # This writes the header
        B = bytearray(total_size)
        B[0x0:0x8] = magic_bytes.ljust(0x8, b'\x00')
        B[0x8:0xc] = b'1PDS'
        B[0xc:0x10] = len(B).to_bytes(4, 'little')
        B[0x10:0x14] = len(self.packs[0]).to_bytes(4, 'little')
        B[0x14:0x18] = self.unknown1.to_bytes(4, 'little')
        B[0x18:0x1c] = len(self.packs).to_bytes(4, 'little')
        B[0x1c:0x20] = pack_size.to_bytes(4, 'little')
        B[0x20:0x24] = 0x30.to_bytes(4, 'little')
        o = 0x30 + param_info_table_size
        pack_table_ofs = bool(pack_table_size) * o
        B[0x24:0x28] = pack_table_ofs.to_bytes(4, 'little')
        o += pack_table_size
        array_table_ofs = bool(array_table_size) * o
        B[0x28:0x2c] = array_table_ofs.to_bytes(4, 'little')
        o += array_table_size
        blob_table_ofs = bool(blob_table_size) * o
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
            B[o_p:o_p+len(p._param_id)] = p._param_id
            o_p += len(p._param_id)
            B[o+0xc:o+0x10] = p._next_param.to_bytes(4, 'little')

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

        param_info_table_size = 0x10 * len(self.packs[0]) + sum(len(p._param_id) for p in self.packs[0])
        param_info_table_size += -param_info_table_size % 0x10

        pack_size = sum( isinstance(p.value, array) or 2 for p in self.packs[0] )
        pack_table_size = 4*pack_size * len(self.packs)
        pack_table_size += -pack_table_size % 0x10

        array_table_size = sum( p.value.itemsize * len(p.value)
                                for p in chain.from_iterable(self.packs)
                                if isinstance(p.value, array) )
        array_table_size += -array_table_size % 0x10

        P = ( p for p in chain.from_iterable(self.packs)
              if ( isinstance(p.value, BankPack)
                   or isinstance(p.value, EffectPackWrapper) ))
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
        return self.serialize(EPM1Parser._MAGIC)

class WorkPack(Pack):
    @classmethod
    def from_bytes(cls, data):
        return super().from_bytes(data, WorkPackParser)

    def __bytes__(self):
        return self.serialize(WorkPackParser._MAGIC)

class BankPack(Pack):
    @classmethod
    def from_bytes(cls, data):
        return super().from_bytes(data, BankPackParser)

    def __bytes__(self):
        return self.serialize(BankPackParser._MAGIC)

class EffectPackWrapper:
    name: bytes = b''
    pack_id: int = -1
    data: tuple[TexIndex] | tuple[WorkPack] | tuple[WorkPack,TexIndex] = ()
    unknown1: int = -1
    unknown2: int = -1

    @classmethod
    def from_bytes(cls, data):
        parser = EffectPackWrapperParser(memoryview(data).toreadonly())
        instance = cls()
        instance.name = parser.name
        instance.pack_id = parser.pack_id
        instance.data = parser.to_tuple()
        instance.unknown1 = parser.unknown1
        instance.unknown2 = parser.unknown2
        return instance

    @property
    def _nbytes(self):
        return sum( p._nbytes for p in self.data )

    def __bytes__(self):
        B = bytearray(0x20)
        B[0x0:0x10] = self.name[:0xf].ljust(0x10, b'\x00')
        B[0x10:0x14] = self.pack_id.to_bytes(4, 'little')
        B[0x14:0x18] = len(self.data).to_bytes(4, 'little')
        B[0x18:0x1c] = self.unknown1.to_bytes(4, 'little', signed=True)
        B[0x1c:0x20] = self.unknown2.to_bytes(4, 'little', signed=True)
        for d in self.data:
            B += bytes(d)
        return bytes(B)

@dataclass
class Param:
    enabled: bool = False
    value: EffectPackWrapper | BankPack | bool | int | float | array = False
    _param_id: bytes = b''
    _next_param: int = -1

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
