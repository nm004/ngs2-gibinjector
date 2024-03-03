# TCMLib by Nozomi Miyamori is marked with CC0 1.0.
# This file is a part of TCMLib.

from abc import ABC, abstractmethod
from collections.abc import MutableSequence

class AbstractChunk(ABC):
    @abstractmethod
    def __init__(self):
        pass

    # This updates the underlying data.
    @abstractmethod
    def commit(self):
        pass

    # data must return an object that can be passed to memoryview.
    @property
    @abstractmethod
    def data(self):
        pass

    def __bool__(self):
        return bool(memoryview(self.data))

class AbstractContainer(AbstractChunk, MutableSequence):
    @property
    @abstractmethod
    def chunks(self):
        pass

    @property
    def mview(self):
        return memoryview(self.data)[:self.container_size]

    @property
    def magic(self):
        return memoryview(self.data)[0:8].tobytes().partition(b'\x00')[0]

    @magic.setter
    def magic(self, val):
        memoryview(self.data)[0:8] = val.ljust(0x8, b'\x00')

    @property
    def version(self):
        return memoryview(self.data)[0x8:0xc].tobytes()

    @version.setter
    def version(self, val):
        memoryview(self.data)[0x8:0xc] = val

    @property
    def info_size(self):
        return memoryview(self.data)[0xc:0x10].cast('I')[0]

    @info_size.setter
    def info_size(self, val):
        memoryview(self.data)[0xc:0x10].cast('I')[0] = val

    @property
    def container_size(self):
        return memoryview(self.data)[0x10:0x14].cast('I')[0]

    @container_size.setter
    def container_size(self, val):
        memoryview(self.data)[0x10:0x14].cast('I')[0] = val

    @property
    def chunk_count(self):
        return memoryview(self.data)[0x14:0x18].cast('I')[0]

    @chunk_count.setter
    def chunk_count(self, val):
        memoryview(self.data)[0x14:0x18].cast('I')[0] = val

    @property
    def valid_chunk_count(self):
        return memoryview(self.data)[0x18:0x1c].cast('I')[0]

    @valid_chunk_count.setter
    def valid_chunk_count(self, val):
        memoryview(self.data)[0x18:0x1c].cast('I')[0] = val

    @property
    def chunk_ofs_table_ofs(self):
        return memoryview(self.data)[0x20:0x24].cast('I')[0]

    @chunk_ofs_table_ofs.setter
    def chunk_ofs_table_ofs(self, val):
        memoryview(self.data)[0x20:0x24].cast('I')[0] = val

    @property
    def chunk_size_table_ofs(self):
        return memoryview(self.data)[0x24:0x28].cast('I')[0]

    @chunk_size_table_ofs.setter
    def chunk_size_table_ofs(self, val):
        memoryview(self.data)[0x24:0x28].cast('I')[0] = val

    @property
    def optional_chunk_ofs(self):
        return memoryview(self.data)[0x28:0x2c].cast('I')[0]

    @optional_chunk_ofs.setter
    def optional_chunk_ofs(self, val):
        memoryview(self.data)[0x28:0x2c].cast('I')[0] = val

    @property
    def meta_info_buf(self):
        n = self.info_size
        o = ( self.chunk_ofs_table_ofs
              or self.chunk_size_table_ofs
              or self.optional_chunk_ofs
              or None )
        return memoryview(self.data)[n:o]

    @property
    def chunk_ofs_table_buf(self): 
        o = self.chunk_ofs_table_ofs or self.container_size
        n = self.chunk_count
        return memoryview(self.data)[o:o+4*n].cast('I')

    @property
    def chunk_size_table_buf(self): 
        o = self.chunk_size_table_ofs or self.container_size
        n = self.chunk_count
        return memoryview(self.data)[o:o+4*n].cast('I')

    @property
    def optional_chunk_buf(self):
        o = self.optional_chunk_ofs or self.container_size
        try:
            p = self.chunk_ofs_table_buf[0]
        except IndexError:
            p = None
        return memoryview(self.data)[o:p]

    def count(self, val):
        return self.chunks.count(val)

    def index(self, val):
        return self.chunks.index(val)

    def insert(self, key, val):
        self.chunks.insert(key, val)

    def append(self, val):
        self.chunks.append(val)

    def clear(self):
        self.chunks.clear()

    def extend(self, other):
        self.chunks.extend(other)

    def pop(self, key=0):
        self.chunks.pop(key)

    def remove(self, val):
        self.chunks.remove(val)

    def reverse(self):
        self.chunks.reverse()

    def __len__(self):
        return len(self.chunks)

    def __getitem__(self, key):
        return self.chunks[key]

    def __setitem__(self, key, val):
        self.chunks[key] = val

    def __delitem__(self, key):
        del self.chunks[key]

    def __iter__(self):
        return iter(self.chunks)

    def __reversed__(self):
        return reversed(self.chunks)

    def __add__(self, other):
        return self.chunks + other

    def __radd__(self, other):
        return other + self.chunks

    def __iadd__(self, other):
        self.chunks += other

    def __mul__(self, other):
        return self.chunks * other

    def __rmul__(self, other):
        return other * self.chunks

    def __imul__(self, other):
        self.chunks *= other
