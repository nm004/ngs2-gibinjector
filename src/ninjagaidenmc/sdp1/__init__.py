from dataclasses import dataclass
from array import array
from abc import ABC, abstractmethod
from itertools import chain

class Pack(ABC):
    def __init__(self):
        self._packs = []
        self.unknown1 = 0

    @classmethod
    @abstractmethod
    def magic(cls):
        pass

    @classmethod
    def from_bytes(cls, data):
        instance = cls()

        data = memoryview(data)
        pack_parser = PackParser(data)

        if pack_parser.magic != cls.magic:
            raise ValueError(f"data has no magic bytes {cls.magic}")

        data = memoryview(data[:pack_parser.size])

        def f():
            o1 = pack_parser.param_info_table_ofs
            o2 = pack_parser.pack_table_ofs

            n = 4*pack_parser.pack_size
            for j in range(pack_parser.pack_count):
                o = o2+j*n
                yield tuple(g(data[o1:o2], data[o:o+n]))

        def g(I, P):
            J = tuple(h(I))
            for j in J:
                o = 4*j.param_index
                enabled = int.from_bytes(P[o:o+4], 'little')
                match j.value_type:
                    case 0x01:
                        value = P[o+4]
                    case 0x02:
                        value = int.from_bytes(P[o+4:o+8], 'little')
                    case 0x04:
                        value = P[o+4:o+8].cast('f')[0]
                    case 0x12 | 0x14:
                        x = { 0x12: 'I', 0x14: 'f' }[j.value_type]
                        n = j.array_size
                        o = enabled
                        value = ( array(x, bytes(data[o:o+4*n]))
                                  if enabled else array(x, (0 for _ in range(n))) )
                    case 0x40:
                        o = enabled
                        value = ( BankPack.from_bytes(data[o:])
                                  if enabled else BankPack() )
                    case 0x80:
                        n = int.from_bytes(P[o+4:o+8], 'little')
                        o = enabled
                        value = ( EffectPack.from_bytes(data[o:o+n])
                                  if enabled else EffectPack() )
                    case _:
                        raise ValueError(f"unknown value type {pi.value_type}")

                o = 4*j.param_id_ofs
                yield Param(bool(enabled), value, j.linked_param, bytes(I[o:o+4*I[o+3]]))

        def h(I):
            for i in range(pack_parser.param_count):
                o = 0x10*i
                yield ParamInfoParser(I[o:o+0x10])

        instance.packs.extend(f())
        instance.unknown1 = pack_parser.unknown1
        return instance

    @property
    def packs(self):
        return self._packs

    @property
    def nbytes(self):
        return self._size()[-1]

    def _size(self):
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
              if ( isinstance(p.value, BankPack)
                   or isinstance(p.value, EffectPack) ))
        blob_table_size = sum( bool(p.enabled) * p.value.nbytes for p in P )
        blob_table_size += -blob_table_size % 0x10

        total_size = (0x30 + param_info_table_size + pack_table_size
                      + array_table_size + blob_table_size)

        return (param_info_table_size, pack_size, pack_table_size,
                array_table_size, blob_table_size, total_size)

    def __bytes__(self):
        (param_info_table_size, pack_size, pack_table_size,
         array_table_size, blob_table_size, total_size) = self._size()

        B = bytearray(total_size)
        B[0x0:0x8] = self.magic
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

        o1 = 0
        o2 = 0x30 + 0x10 * len(self.packs[0]) 
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
                case EffectPack():
                    B[o+3] = 0x80
                    x = 2
                case _:
                    raise ValueError(f"invalid value type {p.value}")

            B[o+0x4:o+0x8] = o1.to_bytes(4, 'little')
            o1 += x
            B[o+0x8:o+0xc] = ((o2-0x30)//4).to_bytes(4, 'little')
            B[o2:o2+len(p.param_id)] = p.param_id
            o2 += len(p.param_id)
            B[o+0xc:o+0x10] = p.linked_param.to_bytes(4, 'little')

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
                    case EffectPack():
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

class PackParser:
    def __init__(self, data):
        self._data = memoryview(data)

    @property
    def raw_magic(self):
        return bytes(self._data[0:8])

    @property
    def magic(self):
        return self.raw_magic.partition(b'\x00')[0]

    @property
    def version(self):
        return bytes(self._data[0x8:0xc])

    @property
    def size(self):
        return self._data[0xc:0x10].cast('I')[0]

    @property
    def param_count(self):
        return self._data[0x10:0x14].cast('I')[0]

    @property
    def unknown1(self):
        return self._data[0x14:0x18].cast('I')[0]

    @property
    def pack_count(self):
        return self._data[0x18:0x1c].cast('I')[0]

    @property
    def pack_size(self):
        return self._data[0x1c:0x20].cast('I')[0]

    @property
    def param_info_table_ofs(self):
        return self._data[0x20:0x24].cast('I')[0]

    @property
    def pack_table_ofs(self):
        return self._data[0x24:0x28].cast('I')[0]

    @property
    def array_table_ofs(self):
        return self._data[0x28:0x2c].cast('I')[0]

    @property
    def blob_table_ofs(self):
        return self._data[0x2c:0x30].cast('I')[0]

class ParamInfoParser:
    def __init__(self, data):
        self._data = memoryview(data)

    @property
    def array_size(self):
        return self._data[0x0:0x4].cast('I')[0] & 0x00ffffff

    @property
    def value_type(self):
        return self._data[0x3]

    @property
    def param_index(self):
        return self._data[0x4:0x8].cast('I')[0]

    @property
    def param_id_ofs(self):
        return self._data[0x8:0xc].cast('I')[0]

    @property
    def linked_param(self):
        return self._data[0xc:0x10].cast('I')[0]

class EPM1(Pack):
    @classmethod
    @property
    def magic(cls):
        return b'EPM1'

class WorkPack(Pack):
    @classmethod
    @property
    def magic(cls):
        return b'WorkPack'

class BankPack(Pack):
    @classmethod
    @property
    def magic(cls):
        return b'BankPack'

class TexIndex:
    @classmethod
    def from_bytes(cls, data):
        instance = cls()
        instance._data = memoryview(bytes(data))
        return instance

    @property
    def nbytes(self):
        return self._data.nbytes

    def __bytes__(self):
        return bytes(self._data)

@dataclass
class EffectPack:
    name: bytes = b''
    pack_id: int = 0
    packs: tuple[TexIndex] | tuple[WorkPack] | tuple[WorkPack,TexIndex] = ()
    unknown1: int = -1
    unknown2: int = -1

    @classmethod
    def from_bytes(cls, data):
        data = memoryview(data)
        effect_pack_parser = EffectPackParser(data)
        unknown1 = effect_pack_parser.unknown1
        unknown2 = effect_pack_parser.unknown2

        match effect_pack_parser.data_count:
            case 1:
                x = WorkPack if unknown1 == -1 else TexIndex
                packs = (x.from_bytes(data[0x20:]),)
            case 2:
                o = PackParser(data[0x20:]).size
                packs = (WorkPack.from_bytes(data[0x20:]),
                         TexIndex.from_bytes(data[0x20+o:]))
            case x:
                raise ValueError(f'unknown value count {x}')

        return cls(effect_pack_parser.name, effect_pack_parser.pack_id, packs,
                   unknown1, unknown2)

    @property
    def nbytes(self):
        return sum( p.nbytes for p in self.packs )

    def __bytes__(self):
        B = bytearray(0x20)
        B[0x0:0x10] = self.name[:0xf].ljust(0x10, b'\x00')
        B[0x10:0x14] = self.pack_id.to_bytes(4, 'little')
        B[0x14:0x18] = len(self.packs).to_bytes(4, 'little')
        B[0x18:0x1c] = self.unknown1.to_bytes(4, 'little', signed=True)
        B[0x1c:0x20] = self.unknown2.to_bytes(4, 'little', signed=True)
        for p in self.packs:
            B += bytes(p)
        return bytes(B)

class EffectPackParser:
    def __init__(self, data):
        self._data = memoryview(data)

    @property
    def name(self):
        return bytes(self._data[0:0x10])

    @property
    def pack_id(self):
        return self._data[0x10:0x14].cast('I')[0]

    @property
    def data_count(self):
        return self._data[0x14:0x18].cast('I')[0]
        
    @property
    def unknown1(self):
        return self._data[0x18:0x1c].cast('i')[0]
        
    @property
    def unknown2(self):
        return self._data[0x1c:0x20].cast('i')[0]

@dataclass
class Param:
    enabled: bool = False
    value: EffectPack | BankPack | bool | int | float | array = False
    linked_param: int = -1
    param_id: bytes = b''

