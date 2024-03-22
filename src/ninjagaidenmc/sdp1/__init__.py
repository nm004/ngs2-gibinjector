from dataclasses import dataclass
from array import array
from abc import ABC, abstractmethod

class Pack(ABC):
    _packs = []

    @abstractmethod
    def magic(self):
        pass

    @property
    def packs(self):
        return self._packs

    @classmethod
    def from_bytes(cls, data):
        instance = cls()

        data = memoryview(data)
        pack_parser = PackParser(data)
        o1 = pack_parser.param_info_table_ofs or None
        o2 = pack_parser.param_table_ofs or None
        o3 = pack_parser.array_table_ofs or None
        o4 = pack_parser.blob_ofs or None
        def f(PI):
            for i in range(pack_parser.param_count):
                o = 0x10*i
                yield ParamInfoParser(PI[o:o+0x10])
        I = tuple(f(data[o1:o2]))

        def f(I, P):
            for i in I:
                o = 4*i.param_index
                match i.value_type:
                    case 0x01:
                        enabled = P[o]
                        value = P[o+4]
                    case 0x02:
                        enabled = P[o]
                        value = P[o+4:o+8].cast('I')[0]
                    case 0x04:
                        enabled = P[o]
                        value = P[o+4:o+8].cast('f')[0]
                    case 0x12 | 0x14:
                        t = { 0x12: 'L', 0x14: 'f' }[i.value_type]
                        o1 = enabled = P[o]
                        value = array(t, data[o1:o1+4*i.array_size].cast('I')
                                      if enabled else (0,) * i.array_size)
                    case 0x40 | 0x80:
                        m = P[o:o+8].cast('I')
                        enabled = m[0]
                        t = { 0x40: BankPack, 0x80: EffPack }[i.value_type]
                        value = t.from_bytes( data[m[0]:m[0] + m[1]] if m[0] else b'' )
                    case _:
                        raise ValueError(f"unknown value type {pi.value_type}")

                o = p.param_id_ofs
                yield Param(enabled, value, i.linked_param, data[o:o+4*data[o+4]])

        s = pack_parser.param_table_size
        for j in range(pack_parser.pack_count):
            instance.packs.append( f(I, data[o2+4*j*s:o3]) )
        return instance

    def __bytes__(self):
        param_info_table_size = 0x10 * len(self.packs) + sum(len(p.param_id) for p in self.packs)
        param_info_table_size += -param_info_table_size % 0x10

        param_table_size = sum( 2 * isinstance(p.value, array) or 1 for p in self.packs )
        param_table_size = param_table_size * len(self.packs)
        param_table_size += -param_table_size % 0x10

        array_table_size = sum( p.value.itemsize * len(p.value)
                                for p in self.packs if isinstance(p.value, array) )

        blob_size = sum( len(p.value) for p in self.packs if ( isinstance(p.value, BankPack)
                                                               or isinstance(p.value, EffectPack) ))

        B = bytearray(0x30 + param_info_table_size + param_table_size + array_table_size + blob_size)
        B[0x0:0x8] = self.magic
        B[0x8:0xc] = b'1PDS'
        B[0x10:0x14] = len(B).to_bytes(4, 'little')
        B[0x14:0x18] = unknown_count1.to_bytes(4, 'little')
        B[0x18:0x1c] = len(self.packs).to_bytes(4, 'little')
        B[0x1c:0x20] = len(self.packs[0]).to_bytes(4, 'little')
        B[0x20:0x24] = 0x30.to_bytes(4, 'little')
        o1 = (0x30 + param_info_table_size) * bool(param_table_size)
        B[0x24:0x28] = o1.to_bytes(4, 'little')
        o2 = (o1 + param_table_size) * bool(array_table_size)
        B[0x28:0x2c] = o2.to_bytes(4, 'little')
        o3 = (o2 + array_table_size) * bool(blob_size)
        B[0x2c:0x30] = o3.to_bytes(4, 'little')

        o1 = 0
        o2 = 0x30 + 0x10 * len(self.packs[0]) 
        for i, p in enumerate(self.packs[0]):
            o = 0x30 + 0x10*i
            match p.value:
                case bool():
                    B[o+4] = 0x1
                    x = 2
                case int():
                    B[o+4] = 0x2
                    x = 2
                case float():
                    B[o+4] = 0x4
                    x = 2
                case array():
                    B[o:o+0x3] = p.to_bytes(3, 'little')
                    B[o+0x3:o+0x4] = p.value_type.to_bytes(1)
                    match p.value.typecode:
                        case 'f':
                            B[o+4] = 0x12
                        case 'L':
                            B[o+4] = 0x14
                        case _:
                            raise ValueError("invalid array type")
                    x = 1
                case BankPack():
                    B[o+4] = 0x40
                    x = 2
                case EffectPack():
                    B[o+4] = 0x80
                    x = 2
                case _:
                    raise ValueError("invalid value type")

            B[o+0x4:o+0x8] = o1.to_bytes(4, 'little')
            o1 += x
            B[o+0x8:o+0xc] = p.linked_param.to_bytes(4, 'little')

            B[o:o+len(p.param_id)] = p.param_id
            o2 += len(p.param_id)

        o1 = int.from_bytes(B[0x24:0x28]) 
        o2 = int.from_bytes(B[0x28:0x2c])
        o3 = int.from_bytes(B[0x2c:0x30])
        for p in self.packs:
            for j, q in enumerate(p):
                match q.value:
                    case bool() | int() | float():
                        B[o1] = q.enabled
                        if q.enabled:
                            B[o1+4] = q.value
                        o1 += 8
                    case array():
                        if q.enabled:
                            B[o1] = o2
                            o1 += 4
                            v = q.value.tobytes()
                            B[o2:o2+len(v)] = v
                            o2 += len(v)
                    case EffectPack() | BankPack():
                        v = bytes(q.value)
                        B[o1] = o3
                        B[o1+4] = len(v)
                        o1 += 8
                        B[o3:o3+len(v)] = v
                        o3 += len(v)
                    case _:
                        raise ValueError("invalid value type")

        return bytes(B)

class PackParser:
    def __init__(self, data):
        self._mview = memoryview(data)

    @property
    def mview(self):
        return self._mview

    @property
    def magic(self):
        return self.mview[0:8].tobytes()

    @property
    def version(self):
        return self.mview[0x8:0xc].tobytes()

    @property
    def container_size(self):
        return self.mview[0xc:0x10].cast('I')[0]

    @property
    def param_count(self):
        return self.mview[0x10:0x14].cast('I')[0]

    @property
    def unknown1_count(self):
        return self.mview[0x14:0x18].cast('I')[0]

    @property
    def pack_count(self):
        return self.mview[0x18:0x1c].cast('I')[0]

    @property
    def param_table_size(self):
        return self.mview[0x1c:0x20].cast('I')[0]

    @property
    def param_info_table_ofs(self):
        return self.mview[0x20:0x24].cast('I')[0]

    @property
    def param_table_ofs(self):
        return self.mview[0x24:0x28].cast('I')[0]

    @property
    def array_table_ofs(self):
        return self.mview[0x28:0x2c].cast('I')[0]

    @property
    def blob_ofs(self):
        return self.mview[0x2c:0x30].cast('I')[0]

class ParamInfoParser:
    def __init__(self, data):
        self._mview = memoryview(data)

    @property
    def mview(self):
        return self._mview

    @property
    def array_size(self):
        return self.mview[0x0:0x4].cast('I')[0] & 0x00ffffff

    @property
    def value_type(self):
        return self.mview[0x3] & 0xff

    @property
    def param_index(self):
        return self.mview[0x4:0x8].cast('I')[0]

    @property
    def param_id_ofs(self):
        return self.mview[0x8:0xc].cast('I')[0] * 4

    @property
    def linked_param(self):
        return self.mview[0xc:0x10].cast('I')[0] & 0x7fffffff

class EPM1(Pack):
    @property
    def magic(self):
        return b'EPM1'

class WorkPack(Pack):
    @property
    def magic(self):
        return b'WorkPack'

class BankPack(Pack):
    @property
    def magic(self):
        return b'BankPack'

class EffectPack:
    def from_bytes(self):
        pass

@dataclass(frozen=True)
class Param:
    enabled: bool = False
    value: EffectPack | BankPack | bool | int | float | array = False
    linked_param: int = -1
    param_id: bytes = b''

