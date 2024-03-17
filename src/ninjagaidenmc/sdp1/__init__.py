from container import AbstractChunk
from dataclasses import dataclass
from typing import Any
from array import array
from abc import ABC

class PackContainer(ABC):
    @abstractmethod
    def magic(self):
        pass

    def from_bytes(self, data):
        pack = PackContainerParser(data)
        o1 = self.param_info_table_ofs or None
        o2 = self.scalar_table_ofs or None
        o3 = self.array_table_ofs or None
        o4 = self.blob_table_ofs or None
        PI = self.mview[o1:o2]
        S = self.mview[o2:o3]
        A = self.mview[o3:o4]

        PI = tuple(g())
        P = tuple( tuple(f())
                   for i in range(self.pack_count) )

    def __bytes__(self):
        param_info_table_size = 0x10 * len(P) + sum(len(p.param_id) for p in P)
        param_info_table_size += -param_info_table_size % 0x10

        scalar_table_size = sum( ( 1 if p.value_type & 0x10 else 2 ) for p in P )
        total_scalar_table_size = scalar_table_size * len()
        total_scalar_table_size += -scalar_table_size % 0x10

        array_table_size =

        b = bytearray()
        b[0x0:0x8] = self.magic
        b[0x8:0xc] = b'1PDS'
        b[0x10:0x14] = ( 0x30
                         + param_info_table_size
                         + total_scalar_table_size
                         + array_table_size
                         + blob_table_size).to_bytes(4, 'little')
        b[0x14:0x18] = unknown_count1.to_bytes(4, 'little')
        b[0x18:0x1c] = len().to_bytes(4, 'little')
        b[0x1c:0x20] = len().to_bytes(4, 'little')
        b[0x20:0x24] = 0x30.to_bytes(4, 'little')
        b[0x24:0x28] = (0x30
                        + param_info_table_size).to_bytes(4, 'little')
        b[0x28:0x2c] = (0x30
                        + param_info_table_size
                        + total_scalar_table_size).to_bytes(4, 'little')
        b[0x2c:0x30] = (0x30
                        + param_info_table_size
                        + total_scalar_table_size
                        + array_table_size).to_bytes(4, 'little')

        for i, p in enumerate(P):
            o = 0x30 + 0x10*i
            b[o:o+0x3] = p.array_size.to_bytes(3, 'little')
            b[o+0x3:o+0x4] = p.value_type.to_bytes(1)
            b[o+0x4:o+0x8] = x.to_bytes(4, 'little')
            b[o+0x8:o+0xc] = p.linked_param.to_bytes(4, 'little')

            o = 0x30 + 0x10 * len(P) + sum(len(q.param_id) for q in P[i:])
            b[o:o+len(p.param_id)] = p.param_id

        for i in X:
            for j, p in enumerate(P):
                o1 = 0x30+param_info_table_size+i*scalar_table_size+4
                o2 = 0x30+param_info_table_size+total_scalar_table_size
                match p.value:
                    case bool():
                        b[o+] = p.enabled
                        b[o+] = p.value
                    case int():
                        b[o+] = p.enabled
                        b[o+] = p.value
                    case float():
                        b[o+] = p.enabled
                        b[o+] = p.value
                    case array():
                        b[o+] = if p.enabled else 0
                    case bytes():
                        if p.enabled:
                            b[o+] = 
                            b[o+] = len(p.value)

        return bytes(b)

class EPM1(PackContainer):
    @property
    def magic(self):
        return b'EPM1'

class WorkPackContainer(PackContainer):
    @property
    def magic(self):
        return b'WorkPack'

class BankPackContainer(PackContainer):
    @property
    def magic(self):
        return b'BankPack'

def g():
    for i in range(self.param_count):
        o = 0x10*i
        p = ParamInfoParser(PI[o:o+0x10])
        yield ParamInfo(p.array_size,
                        p.value_type,
                        p.linked_param,
                        p.param_id)

def f():
    i * self.pack_size
    for pi in P:
        o = 4*pi.param_index
        match pi.value_type:
            case 0x01:
                yield (S[o], S[o+4])
            case 0x02:
                yield (S[o], S[o+4:o+8].cast('I')[0])
            case 0x04:
                yield (S[o], S[o+4:o+8].cast('f')[0])
            case 0x12:
                a = array('L', A[S[o]:S[o]+4*PI.array_size].cast('I')
                          if S[o] else tuple(0) * PI.array_size)
                yield (S[o], a)
            case 0x14:
                a = array('f', A[S[o]:S[o]+4*PI.array_size].cast('I')
                          if S[o] else tuple(0) * PI.array_size)
                yield (S[o], a)
            case 0x40:
                yield (S[o:o+4].cast('I'))
            case 0x80:
                yield (S[o:o+4].cast('I'))
            case _:
                raise ValueError(f"unknown value type {pi.value_type}")

@dataclass(frozen=True)
class Param:
    value: Any
    enabled: bool = True
    linked_param: int = -1
    param_id: bytes = b''

class PackContainerParser:
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
        return self.mview[8:0xc].tobytes()

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
    def pack_size(self):
        return self.mview[0x1c:0x20].cast('I')[0] * 4

    @property
    def param_info_table_ofs(self):
        return self.mview[0x20:0x24].cast('I')[0]

    @property
    def scalar_table_ofs(self):
        return self.mview[0x24:0x28].cast('I')[0]

    @property
    def array_table_ofs(self):
        return self.mview[0x28:0x2c].cast('I')[0]

    @property
    def blob_table_ofs(self):
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

    @property
    def param_id(self):
        m = self.mview
        o = self.param_id_ofs
        n = m[o:o+4].cast('I')[0] >> 24
        return m[o:o+4*n]
