# NGS2 Gib Injector by Nozomi Miyamori is marked with CC0 1.0.
# This file is a part of NGS2 Gib Injector.
#
# This module is for reading/writing container format which is
# used by some Team Ninja's (Koei-Tecmo) games such as NINJA GAIDEN
# Master Collection and Dead or Alive 5 Last Round.

from __future__ import annotations
from operator import indexOf
from typing import ClassVar, Self
from array import array
from dataclasses import dataclass, field

class Container:
    _MAGIC: ClassVar[bytes]

    @classmethod
    def validate_magic(cls, parser):
        if parser.magic != cls._MAGIC:
            raise ValueError(f'data does not have magic bytes "{cls._MAGIC.decode()}".')

    def __bytes__(self):

        chunks = tuple( memoryview(c) for c in self.make_chunks() )

        optional_chunk = memoryview(self.make_optional_chunk())
        meta_info = memoryview(self.make_meta_info())
        
        # These calculate sizes of new data
        info_size = bool(self.enable_L) * 0x30 or 0x50

        meta_info_size = meta_info.nbytes + -meta_info.nbytes % 0x10
        chunk_ofs_table_size = 4*len(chunks)
        chunk_ofs_table_size += -4*len(chunks) % 0x10
        chunk_size_table_size = chunk_ofs_table_size * any( c.nbytes % 0x10 for c in C )
        optional_chunk_size = optional_chunk.nbytes + -optional_chunk.nbytes % 0x10
        total_chunk_size = sum( c.nbytes + -c.nbytes % 0x10 for c in chunks )
        total_size = ( info_size
                       + meta_info_size
                       + chunk_ofs_table_size
                       + chunk_size_table_size
                       + optional_chunk_size
                       + total_chunk_size )
        B = bytearray(total_size)
        B[0:8] = self._MAGIC
        B[0x8:0xc] = 0x00000101.to_bytes(4)
        B[0xc:0x10] = info_size.to_bytes(4, 'little')
        B[0x10:0x14] = total_size.to_bytes(4, 'little')
        B[0x14:0x18] = len(chunks).to_bytes(4, 'little')
        valid_chunk_count = sum( c.nbytes > 0 for c in chunks )
        B[0x18:0x1c] = valid_chunk_count.to_bytes(4, 'little')

        n = info_size + meta_info.nbytes
        chunk_ofs_table_ofs = n * bool(chunk_ofs_table_size)
        B[0x20:0x24] = chunk_ofs_table_ofs.to_bytes(4, 'little')
        n += chunk_ofs_table_size
        chunk_size_table_ofs = n * bool(chunk_size_table_size)
        B[0x24:0x28] = chunk_size_table_ofs.to_bytes(4, 'little')
        n += chunk_size_table_size
        optional_chunk_ofs = n * bool(optional_chunk)
        B[0x28:0x2c] = optional_chunk_ofs.to_bytes(4, 'little')

        if self.enable_L:
            B[0x40:0x44] = valid_chunk_count.to_bytes(4, 'little')
            B[0x44:0x48] = (0x10 + meta_info_size + total_chunk_size).to_bytes(4, 'little')
            B[0x48:0x4c] = (0x01234567).to_bytes(4, 'little')

        if meta_info:
            o1 = info_size
            o2 = o1 + meta_info.nbytes
            B[o1:o2] = meta_info

        # This writes the new chunk offset table
        if chunk_ofs_table_ofs:
            x = ( chunk_ofs_table_ofs
                  + chunk_ofs_table_size
                  + chunk_size_table_size
                  + optional_chunk_size )
            for i, c in enumerate(chunks):
                o = chunk_ofs_table_ofs + 4*i
                y = c.nbytes + -c.nbytes % 0x10
                B[o:o+4] = (x * bool(p)).to_bytes(4, 'little')
                x += p

        # This writes the chunk size table
        if chunk_size_table_ofs:
            for i, c in enumerate(chunks):
                o = chunk_size_table_ofs + 4*i
                B[o:o+4] = c.nbytes.to_bytes(4, 'little')

        # This writes the new optional data
        if optional_chunk:
            B[o1:o2] = optional_chunk


        # This writes the new chunks
        if chunks:
            o1 = chunk_ofs_table_ofs
            o2 = o1 + len(chunks)
            O = memoryview(B[o1:o2]).cast('I')
            for i, c in enumerate(chunks):
                o1 = O[i]
                o2 = o1 + c.nbytes
                B[o1:o2] = bytes(c).ljust(c.nbytes + -c.nbytes % 0x10, b'\x00')

        return bytes(B)

@dataclass
class ContainerParser:
    data: memoryview
    ldata: memoryview | None = None
    magic: bytes = field(init=False)
    version: bytes = field(init=False)
    info_size: int = field(init=False)
    container_size: int = field(init=False)
    chunk_conut: int = field(init=False)
    valid_chunk_count: int = field(init=False)
    chunk_ofs_table_ofs: int = field(init=False)
    chunk_size_table_ofs: int = field(init=False)
    optional_chunk_ofs: int = field(init=False)
    chunk_ofs_table: memoryview = field(init=False)
    chunk_size_table: memoryview = field(init=False)
    optional_chunk: memoryview = field(init=False)
    meta_info: memoryview = field(init=False)
    chunks: tuple = field(init=False)

    def __post_init__(self):
        self.magic = bytes(self.data[0:8])
        self.version = bytes(self.data[0x8:0xc])
        self.info_size = int.from_bytes(self.data[0xc:0x10], 'little')
        self.container_size = int.from_bytes(self.data[0x10:0x14], 'little')
        self.chunk_count = int.from_bytes(self.data[0x14:0x18], 'little')
        self.valid_chunk_count = int.from_bytes(self.data[0x18:0x1c], 'little')
        self.chunk_ofs_table_ofs = int.from_bytes(self.data[0x20:0x24], 'little')
        self.chunk_size_table_ofs = int.from_bytes(self.data[0x24:0x28], 'little')
        self.optional_chunk_ofs =  int.from_bytes(self.data[0x28:0x2c], 'little')

        o1 = self.chunk_ofs_table_ofs or -1
        o2 = bool(o1 != -1) * (o1 + 4*self.chunk_count)
        self.chunk_ofs_table = self.data[o1:o2].cast('I')

        o1 = self.chunk_size_table_ofs or -1
        o2 = bool(o1 != -1) * (o1 + 4*self.chunk_count)
        self.chunk_size_table = self.data[o1:o2].cast('I')
        
        o1 = self.optional_chunk_ofs or -1
        try:
            n = self.chunk_ofs_table[0]
        except IndexError:
            n = self.chunk_size
        o2 = bool(o1 != -1) * n
        self.optional_chunk = self.data[o1:o2]

        o1 = self.info_size
        o2 = ( self.chunk_ofs_table_ofs
               or self.chunk_size_table_ofs
               or self.optional_chunk_ofs
               or self.container_size )
        self.meta_info = self.data[o1:o2]

        def f():
            O = self.chunk_ofs_table
            if S := self.chunk_size_table:
                # Some chunks are empty
                yield from ( self.data[o:(o+s)*bool(s)] for o, s in zip(O, S) )
                return

            for i, o1 in enumerate(O):
                if not o1:
                    yield self.data[:0]
                    continue
                for o2 in O[i+1:]:
                    if o2:
                        yield self.data[o1:o2]
                        break
                else:
                    yield self.data[o1:]

        self.chunks = tuple(f())


        # ldata = ldata[:memoryview(ldata)[0x4:0x8].cast('I')[0]] if ldata else b''
        # self._lmview = memoryview(ldata)

        # if self.info_size == 0x50:
        #     if not self.ldata:
        #         raise ValueError(f'{magic} should have ldata, but no ldata was passed.')
        #     elif self.lcontainer_chunk_count != self.mview[0x40:0x44].cast('I')[0]:
        #         raise ValueError(f'{magic} chunk count of ldata read from data differs'
        #                          f'from chunk count read from ldata ({count} != {count1})')
        #     elif self.lcontainer_size != self.mview[0x44:0x48].cast('I')[0]:
        #         raise ValueError(f'{magic} size of ldata read from data differs from size'
        #                          f'read from ldata ({size} != {size1})')
        #     elif self.lcontainer_check_digits != self.mview[0x48:0x4c]:
        #         raise ValueError(f'{magic} check digits read from data differs from check'
        #                          f'digits read from ldata ({digits:08X} != {digits1:08X})')
        # elif self.ldata:
        #     raise ValueError(f'{magic} should NOT have ldata, but ldata was passed')

# @dataclass
# class LContainerParser:
#     data: memoryview

#     @property
#     def lcontainer_chunk_count(self):
#         return self._data[0x0:0x4].cast('I')[0]

#     @property
#     def lcontainer_size(self):
#         return self._data[0x4:0x8].cast('I')[0]

#     @property
#     def lcontainer_check_digits(self):
#         return bytes(self._data[0x8:0xc])

# class TMC(Container):
#     def __init__(self, data, ldata):
#         ldata = ldata or self.lheader.ldata
#         super().__init__(data)

#         tbl = tuple(self._chunk_typeid_table)
#         L = LHeader(self[tbl.index(0x8000_0020)], ldata)

#         for i, t in enumerate(tbl):
#             if not (c := self[i]):
#                 continue
#             match t:
#                 case 0x8000_0001:
#                     try:
#                         ldata = L.mdlgeo
#                     except AttributeError:
#                         ldata = None
#                     self[i] = MdlGeo(c, ldata)
#                     self._mdlgeo_cidx = i
#                 case 0x8000_0002:
#                     try:
#                         ldata = L.ttdl
#                     except AttributeError:
#                         ldata = None
#                     self[i] = TTDM(c, ldata)
#                     self._ttdm_cidx = i
#                 case 0x8000_0003:
#                     try:
#                         ldata = L.vtxlay
#                     except AttributeError:
#                         ldata = None
#                     self[i] = VtxLay(c, ldata)
#                     self._vtxlay_cidx = i
#                 case 0x8000_0004:
#                     try:
#                         ldata = L.idxlay
#                     except AttributeError:
#                         ldata = None
#                     self[i] = IdxLay(c, ldata)
#                     self._idxlay_cidx = i
#                 case 0x8000_0005:
#                     try:
#                         ldata = L.mtrcol
#                     except AttributeError:
#                         ldata = None
#                     self[i] = MtrCol(c, ldata)
#                     self._mtrcol_cidx = i
#                 case 0x8000_0006:
#                     try:
#                         ldata = L.mdlinfo
#                     except AttributeError:
#                         ldata = None
#                     self[i] = MdlInfo(c, ldata)
#                     self._mdlinfo_cidx = i
#                 case 0x8000_0010:
#                     self[i] = HieLay(c)
#                     self._hielay_cidx = i
#                 case 0x8000_0020:
#                     self[i] = L
#                     self._lheader_cidx = i
#                 case 0x8000_0030:
#                     self[i] = NodeLay(c)
#                     self._nodelay_cidx = i
#                 case 0x8000_0040:
#                     self[i] = GlblMtx(c)
#                     self._glblmtx_cidx = i
#                 case 0x8000_0050:
#                     self[i] = BnOfsMtx(c)
#                     self._bnofsmtx_cidx = i
#                 case 0x8000_0060:
#                     self[i] = cpf(c)
#                     self._cpf_cidx = i
#                 case 0x8000_0070:
#                     self[i] = MCAPACK(c)
#                     self._mcapack_cidx = i
#                 case 0x8000_0080:
#                     self[i] = RENPACK(c)
#                     self._renpack_cidx = i

#     def commit(self):
#         try:
#             _ = self.lheader.mdlgeo
#             self.mdlgeo.commit()
#             self.lheader.mdlgeo = Chunk(self.mdlgeo.ldata)
#         except AttributeError:
#             pass
#         try:
#             _ = self.lheader.ttdl
#             self.ttdm.commit()
#             self.lheader.ttdl = Chunk(self.ttdm.ttdl.ldata)
#         except AttributeError:
#             pass
#         try:
#             _ = self.lheader.vtxlay
#             self.vtxlay.commit()
#             self.lheader.vtxlay = Chunk(self.vtxlay.ldata)
#         except AttributeError:
#             pass
#         try:
#             _ = self.lheader.idxlay
#             self.idxlay.commit()
#             self.lheader.idxlay = Chunk(self.idxlay.ldata)
#         except AttributeError:
#             pass
#         try:
#             _ = self.lheader.mtrcol
#             self.mtrcol.commit()
#             self.lheader.mtrcol = Chunk(self.mtrcol.ldata)
#         except AttributeError:
#             pass
#         try:
#             _ = self.lheader.mdlinfo
#             self.mdlinfo.commit()
#             self.lheader.mdlinfo = Chunk(self.mdlinfo.ldata)
#         except AttributeError:
#             pass
#         super().commit()

#     @property
#     def name(self):
#         return bytes(self._meta_info.mview[0x20:]).partition(b'\x00')[0]

#     @property
#     def mdlgeo(self):
#         return self[self._mdlgeo_cidx]

#     @mdlgeo.setter
#     def mdlgeo(self, val):
#         self[self._mdlgeo_cidx] = val

#     @property
#     def ttdm(self):
#         return self[self._ttdm_cidx]

#     @ttdm.setter
#     def ttdm(self, val):
#         self[self._ttdm_cidx] = val

#     @property
#     def vtxlay(self):
#         return self[self._vtxlay_cidx]

#     @vtxlay.setter
#     def vtxlay(self, val):
#         self[self._vtxlay_cidx] = val

#     @property
#     def idxlay(self):
#         return self[self._idxlay_cidx]

#     @idxlay.setter
#     def idxlay(self, val):
#         self[self._idxlay_cidx] = val

#     @property
#     def mtrcol(self):
#         return self[self._mtrcol_cidx]

#     @mtrcol.setter
#     def mtrcol(self, val):
#         self[self._mtrcol_cidx] = val

#     @property
#     def mdlinfo(self):
#         return self[self._mdlinfo_cidx]

#     @mdlinfo.setter
#     def mdlinfo(self, val):
#         self[self._mdlinfo_cidx] = val

#     @property
#     def hielay(self):
#         return self[self._hielay_cidx]

#     @hielay.setter
#     def hielay(self, val):
#         self[self._hielay_cidx] = val

#     @property
#     def lheader(self):
#         return self[self._lheader_cidx]

#     @lheader.setter
#     def lheader(self, val):
#         self[self._lheader_cidx] = val

#     @property
#     def nodelay(self):
#         return self[self._nodelay_cidx]

#     @nodelay.setter
#     def nodelay(self, val):
#         self[self._nodelay_cidx] = val

#     @property
#     def glblmtx(self):
#         return self[self._glblmtx_cidx]

#     @glblmtx.setter
#     def glblmtx(self, val):
#         self[self._glblmtx_cidx] = val

#     @property
#     def bnofsmtx(self):
#         return self[self._bnofsmtx_cidx]

#     @bnofsmtx.setter
#     def bnofsmtx(self, val):
#         self[self._bnofsmtx_cidx] = val

#     @property
#     def _chunk_typeid_table(self):
#         c = self.chunk_count
#         return self._meta_info.mview[0xc0:0xc0+4*c].cast('I')

# class MdlGeo(Container):
#     def __init__(self, data, ldata = None):
#         super().__init__(data, ldata)
#         self.chunks[:] = map(ObjGeo, self.chunks)

#     def commit(self):
#         super().commit()
#         for i, objgeo in enumerate(self):
#             objgeo._id = i

# class ObjGeo(Container):
#     def __init__(self, data, ldata = None):
#         super().__init__(data, ldata)
#         self._optional_chunk = GeoDecl(self._optional_chunk)
#         self.chunks[:] = map(ObjGeoChunk, self.chunks)
#         for b in self:
#             T = ( ObjGeoChunk.Texture(b.mview[o:])
#                   for o in b._texture_offset_table )
#             b._textures = list(T)
#             b._info_size = self.geodecl[b.decl_index].info_size

#     def commit(self):
#         super().commit()
#         for i, b in enumerate(self):
#             b._id = i

#     @property
#     def geodecl(self):
#         return self._optional_chunk

#     @property
#     def name(self):
#         return bytes(self._meta_info.mview[0x20:]).partition(b'\x00')[0]

#     @property
#     def _id(self):
#         return self._meta_info.mview[0x4:0x8].cast('i')[0]

#     @_id.setter
#     def _id(self, val):
#         self._meta_info.mview[0x4:0x8].cast('i')[0] = val

# class ObjGeoChunk(Chunk):
#     @property
#     def textures(self):
#         return self._textures

#     @property
#     def _id(self):
#         return self.mview[0x0:0x4].cast('i')[0]

#     @_id.setter
#     def _id(self, val):
#         self.mview[0x0:0x4].cast('i')[0] = val

#     @property
#     def mtrcol_index(self):
#         return self.mview[0x4:0x8].cast('i')[0]

#     @mtrcol_index.setter
#     def mtrcol_index(self, val):
#         self.mview[0x4:0x8].cast('i')[0] = val

#     @property
#     def texture_count(self):
#         return self.mview[0xc:0x10].cast('I')[0]

#     @property
#     def _texture_offset_table(self):
#         # max count = 8
#         return self.mview[0x10:0x10 + 4*self.texture_count].cast('I')

#     @property
#     def decl_index(self):
#         return self.mview[0x38:0x3c].cast('I')[0]

#     @decl_index.setter
#     def decl_index(self, val):
#         self.mview[0x38:0x3c].cast('I')[0] = val

#     @property
#     def soft_transparency(self):
#         return self.mview[0x40:0x44].cast('I')[0]

#     @soft_transparency.setter
#     def soft_transparency(self, val):
#         self.mview[0x40:0x44].cast('I')[0] = val

#     @property
#     def hard_transparency(self):
#         return self.mview[0x48:0x4c].cast('I')[0]

#     @hard_transparency.setter
#     def hard_transparency(self, val):
#         self.mview[0x48:0x4c].cast('I')[0] = val

#     @property
#     def index_buffer_offset(self):
#         return self.mview[0x30+self._info_size+0x10:].cast('I')[0]

#     @index_buffer_offset.setter
#     def index_buffer_offset(self, val):
#         self.mview[0x30+self._info_size+0x10:].cast('I')[0] = val

#     @property
#     def ref_index_count(self):
#         return self.mview[0x30+self._info_size+0x14:].cast('I')[0]

#     @ref_index_count.setter
#     def ref_index_count(self, val):
#         self.mview[0x30+self._info_size+0x14:].cast('I')[0] = val

#     @property
#     def vertex_buffer_offset(self):
#         return self.mview[0x30+self._info_size+0x18:].cast('I')[0]

#     @vertex_buffer_offset.setter
#     def vertex_buffer_offset(self, val):
#         self.mview[0x30+self._info_size+0x18:].cast('I')[0] = val

#     @property
#     def ref_vertex_count(self):
#         return self.mview[0x30+self._info_size+0x1c:].cast('I')[0]

#     @ref_vertex_count.setter
#     def ref_vertex_count(self, val):
#         self.mview[0x30+self._info_size+0x1c:].cast('I')[0] = val

#     class Texture:
#         def __init__(self, data):
#             self._mview = memoryview(data)

#         @property
#         def _id(self):
#             return self._mview[0x0:].cast('i')[0]

#         @_id.setter
#         def _id(self, val):
#             self._mview[0x0:].cast('i')[0] = val

#         @property
#         def category(self):
#             return self._mview[0x4:].cast('i')[0]

#         @category.setter
#         def category(self, val):
#             self._mview[0x4:].cast('i')[0] = val

#         @property
#         def buffer_index(self):
#             return self._mview[0x8:].cast('i')[0]

#         @buffer_index.setter
#         def buffer_index(self, val):
#             self._mview[0x8:].cast('i')[0] = val

# class GeoDecl(Container):
#     def __init__(self, data, ldata = None):
#         super().__init__(data, ldata)
#         self.chunks[:] = map(GeoDeclChunk, self.chunks)

# class GeoDeclChunk(Chunk):
#     @property
#     def info_size(self):
#         return self.mview[0x4:].cast('I')[0]

#     @property
#     def index_buffer_index(self):
#         return self.mview[0xc:].cast('i')[0]

#     @index_buffer_index.setter
#     def index_buffer_index(self, val):
#         self.mview[0xc:].cast('i')[0] = val

#     @property
#     def index_count(self):
#         return self.mview[0x10:].cast('I')[0]

#     @property
#     def vertex_count(self):
#         return self.mview[0x14:].cast('I')[0]

#     @property
#     def vertex_buffer_index(self):
#         o = self.info_size
#         return self.mview[o:].cast('i')[0]

#     @vertex_buffer_index.setter
#     def vertex_buffer_index(self, val):
#         o = self.info_size
#         self.mview[o:].cast('i')[0] = val

#     @property
#     def vertex_size(self):
#         o = self.info_size
#         return self.mview[o+4:].cast('i')[0]
    
# class TTDM(Container):
#     def __init__(self, data, ldata):
#         ldata = ldata or self.ttdl.ldata
#         super().__init__(data)
#         self._meta_info = TTDH(self._meta_info)
#         self._optional_chunk = TTDL(self._optional_chunk, ldata)

#     @property
#     def ttdh(self):
#         return self._meta_info

#     @property
#     def ttdl(self):
#         return self._optional_chunk

# class TTDH(Container):
#     def __init__(self, data, ldata = None):
#         super().__init__(data, ldata)
#         self.chunks[:] = map(TTDHChunk, self.chunks)

#     @staticmethod
#     def makechunk():
#         return TTDHChunk(bytearray(0x20))

# class TTDHChunk(Chunk):
#     @property
#     def is_in_l(self):
#         return self.mview[0]

#     @is_in_l.setter
#     def is_in_l(self, val):
#         self.mview[0] = val

#     @property
#     def ttdm_ttdl_index(self):
#         return self.mview[0x4:0x8].cast('i')[0]

#     @ttdm_ttdl_index.setter
#     def ttdm_ttdl_index(self, val):
#         self.mview[0x4:0x8].cast('i')[0] = val

# class TTDL(Container):
#     pass

# class VtxLay(Container):
#     pass

# class IdxLay(Container):
#     pass

class MtrCol(Container):
    matrices: list[array]

    @classmethod
    def from_bytes(cls, data):
        parser = MtrColParser(memoryview(data))
        self.validate_magic(parser)
        instance = cls()
        instance.matrices = [ array('f', c.matrix) for c in parser.chunks ]
        return instance

    def make_chunks(self):
        # size = matrix + index + xrefs_item_count
        #        + (objgeo_idx + refcount)*xrefs
        size = 4*4*13 + 4 + 4 + (4+4)*xrefs_count
        def f():
            for i, m in enumerate(self.matrices):
                B = bytearray()
                B += bytes(m)
                yield B
        return tuple(B)

def MtrColParser(ContainerParser):
    def __post_init__(self):
        super().__post_init__()
        self.chunks = tuple( MtrColChunkParser(c) for c in self.chunks )

class MtrColChunkParser:
    data: memoryview
    matrix: memoryview = field(init=False)
    mtrcol_id: int = field(init=False)
    xrefs_count: int = field(init=False)
    xrefs: tuple[int, int] = field(init=False)

    def __post_init__(self):
        self.matrix = self.data[0:0xd0].cast('f')
        self.mtrcol_id = int.from_bytes(self.data[0xd0:0xd4], 'little', signed=True)
        self.xrefs_count = int.from_bytes(self.data[0xd4:0xd8], 'little')
        def f():
            for i in range(self.xrefs_count):
                o = 0xd0 + i*8
                index = int.from_bytes(self.data[o:o+4], 'little', signed=True)
                count = int.from_bytes(self.data[o+4:o+8], 'little')
                yield (index, count)
        self.xref = tuple(f())


class MdlInfo(Container):
    _chunks: list

    def make_chunks(self):
        for i, objinfo in enumerate(self):
            objinfo._id = i
        return tuple(self.chunks)

class ObjInfoParser(ContainerParser):
    data: memoryview
    obj_id: int = field(init=False)

    def __post_init__(self):
        self.obj_id = int.from_bytes(self.meta_info[0x4:0x8], 'little', signed=True)

class HieLay(Container):
    _MAGIC = b'HieLay'.ljust(8, b'\x00')
    nodes: list[HieLayNode]

    def __init__(self):
        self.nodes = []

    @classmethod
    def from_bytes(cls, data):
        parser = HieLayParser(data)
        self.validate_magic(parser)
        instance = cls()
        instance.nodes = parser.to_list()
        return instance
        
    def make_chunks(self):
        B = bytearray()
        D = dict((v,i) for i,v in enumerate(self.nodes))
        def f():
            for n in self.nodes:
                Bn = bytearray(bytes(n))
                try:
                    i = indexOf(self.nodes, n.parent)
                except ValueError:
                    i = -1
                Bn[0x40:0x44] = i.to_bytes(4, 'little')
                Bn[0x44:0x48] = len(n.children).to_bytes(4, 'little')

                level = 0
                while p := i.parent:
                    level += 1
                Bn[0x48:0x4c] = level.to_bytes(4, 'little')

                for c in n.children:
                    Bn += D[c].to_bytes(4, 'little')
                yield Bc

        return tuple(f())

@dataclass
class HieLayParser(ContainerParser):
    def __post_init__(self):
        super().__post_init__()
        self.chunks = tuple(HieLayChunkParser(c) for c in self.chunks)

    def to_list(self):
        L = tuple( HieLayNode() for _ in self.chunks )
        for i, l in enumerate(L):
            l.matrix = array('f', self.chunks[i].matrix)
            p = self.chunks[i].parent
            l.parent = L[p] if p != -1 else None
            l.children = { L[j] for j, c in enumerate(self.chunks)
                           if c.parent == i }
        return L

class HieLayNode:
    matrix: array
    parent: Self | None
    children: set[Self]

    def __init__(self):
        self.matrix = array('f', ( 0 for _ in range(16)))
        self.parent = None
        self.children = set()

    def __bytes__(self):
        return bytes(self.matrix) + bytes(0x10)

@dataclass
class HieLayChunkParser:
    data: memoryview
    matrix: memoryview = field(init=False)
    parent: int = field(init=False)
    children_count: int = field(init=False)
    level: int = field(init=False)
    children: memoryview = field(init=False)

    def __post_init__(self):
        self.matrix = self.data[0:0x40].cast('f')
        self.parent = int.from_bytes(self.data[0x40:0x44], 'little', signed=True)
        self.children_count = int.from_bytes(self.data[0x44:0x48], 'little')
        self.level = int.from_bytes(self.data[0x48:0x4c], 'little')
        n = self.children_count
        self.children = self.data[0x50:0x50+4*n].cast('i')

class LHeaderParser(ContainerParser):
    chunk_typeid_table: memoryview = field(init=False)
    mdlgeo: memoryview = field(init=False)
    ttdl: memoryview = field(init=False)
    vtxlay: memoryview = field(init=False)
    idxlay: memoryview = field(init=False)
    mtrcol: memoryview = field(init=False)
    mdlinfo: memoryview = field(init=False)
    hielay: memoryview = field(init=False)
    nodelay: memoryview = field(init=False)
    glblmtx: memoryview = field(init=False)
    bnofsmtx: memoryview = field(init=False)

    def __post_init__(self):
        super().__post_init__()
        self.chunk_typeid_table = self.meta_info[0x20:0x20+4*self.chunk_count].cast('I')
        for i, t in enumerate(self.chunk_typeid_table):
            match t:
                case 0xC000_0001:
                    self.mdlgeo = self.chunks[i] or None
                case 0xC000_0002:
                    self.ttdl = self.chunks[i] or None
                case 0xC000_0003:
                    self.vtxlay = self.chunks[i] or None
                case 0xC000_0004:
                    self.idxlay = self.chunks[i] or None
                case 0xC000_0005:
                    self.mtrcol = self.chunks[i] or None
                case 0xC000_0006:
                    self.mdlinfo = self.chunks[i] or None
                case 0xC000_0010:
                    self.hielay = self.chunks[i] or None
                case 0xC000_0030:
                    self.nodelay = self.chunks[i] or None
                case 0xC000_0040:
                    self.glblmtx = self.chunks[i] or None
                case 0xC000_0050:
                    self.bnofsmtx = self.chunks[i] or None
                # case 0xC000_0060:
                #     self.cpf = self.chunks[i] or None
                # case 0xC000_0070:
                #     self.mcapack = self.chunks[i] or None
                # case 0xC000_0080:
                #     self.renpack = self.chunks[i] or None

class NodeLay(Container):
    nodeobjs: list[NodeObj]

    def make_chunks(self):
        def f():
            j = 0
            for i, n in enumerate(self.nodeobjs):
                B = bytearray(bytes(n))
                B[0x8:0xc] = i.to_bytes(4, 'little')
                if n.matrix:
                    o = NodeObjParser(B).chunk_ofs_table[0]
                    B[0x0:0x4] = self._id.to_bytes(4, 'little')
                    B[0x4:0x8] = self._node_id.to_bytes(4, 'little')
                    j += 1
                yield B

        return tuple(f())

class NodeObj(Container):
    data: NodeObjChunk | None
    # 4x4 float matrix
    matrix: bytes | None = b''
    children: set[Self]

    @classmethod
    def from_bytes(cls, data):
        parser = NodeObjChunkParser(memoryview(data))
        return cls(data[0x10:])

    def make_chunks(self):
        if self.matrix:
            B = bytearray(0x10)
            B += self.matrix
            B += bytes(4*len(children))
            return (B,)

class NodeObjParser(ContainerParser):
    unknown1: int = field(init=False)
    unknown2: int = field(init=False)
    node_id1: int = field(init=False)
    name: bytes = field(init=False)
    obj_id: int = field(init=False)
    children_count: int = field(init=False)
    node_id2: int = field(init=False)
    matrix: memoryview = field(init=False)
    children: memoryview = field(init=False)

    def __post_init__(self):
        super().__post_init__()
        self.unknown1 = int.from_bytes(self.meta_info[0x0:0x4], 'little')
        self.unknown2 = int.from_bytes(self.meta_info[0x4:0x8], 'little', signed=True)
        self.node_id = int.from_bytes(self.meta_info[0x8:0xc], 'little')
        self.name = bytes(self.meta_info[0x10:]).partition(b'\x00')[0]
        if self.chunks:
            c = c.chunks[0]
            self.obj_id = int.from_bytes(c.data[0x0:0x4], 'little')
            self.children_count = int.from_bytes(c.data[0x4:0x8], 'little')
            self.node_id = int.from_bytes(c.data[0x8:0xc], 'little')
            self.matrix = c.data[0x10:0x50].cast('f')
            self.children = c.data[0x50:0x50+4*c.children_count].cast('i')

class GlblMtx(Container):
    _MAGIC = b'GlblMtx'
    matrices: list[array]

    @classmethod
    def from_bytes(cls, data):
        parser = BnOfsMtxParser(memoryview(data).toreadonly())
        instance = cls()
        instance.matrices = [ array(m) for m in parser.chunks ]
        return instance

class GlblMtxParser(ContainerParser):
    def __post_init__(self):
        super().__post_init__()
        self.chunks = tuple( c.cast('f') for c in self.chunks )

class BnOfsMtx(Container):
    _MAGIC = b'BnOfsMtx'
    matrices: list[array]

    @classmethod
    def from_bytes(cls, data):
        parser = BnOfsMtxParser(memoryview(data).toreadonly())
        instance = cls()
        instance.matrices = [ array(m) for m in parser.chunks ]
        return instance

class BnOfsMtxParser(ContainerParser):
    def __post_init__(self):
        super().__post_init__()
        self.chunks = tuple( c.cast('f') for c in self.chunks )
