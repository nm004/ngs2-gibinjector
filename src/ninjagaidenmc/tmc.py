# NGS2 Gib Injector by Nozomi Miyamori is marked with CC0 1.0.
# This file is a part of NGS2 Gib Injector.
#
# This module is for reading/writing container format which is
# used by some Team Ninja's (Koei-Tecmo) games such as NINJA GAIDEN
# Master Collection and Dead or Alive 5 Last Round.
from container import AbstractChunk, AbstractContainer

class Chunk(AbstractChunk):
    def __init__(self, data):
        if isinstance(data, AbstractChunk):
            data = data.data
        self._mview = memoryview(data)

    def commit(self):
        pass

    @property
    def mview(self):
        return self._mview

class Container(AbstractContainer):
    def __init__(self, data, ldata = None):
        if isinstance(data, AbstractChunk):
            data = data.data
        data = data[:memoryview(data)[0x10:0x14].cast('I')[0]]
        self._mview = memoryview(data)

        c = self.__class__.__name__.encode() 
        if c != self.magic:
            raise ValueError(f'data does not have magic bytes "{c}".')

        if isinstance(ldata, AbstractChunk):
            ldata = ldata.data
        ldata = ldata[:memoryview(ldata)[0x4:0x8].cast('I')[0]] if ldata or b''
        self._lmview = memoryview(ldata)

        magic = self.magic.decode()
        if self.info_size == 0x50:
            if not self.ldata:
                raise ValueError(f'{magic} should have ldata, but no ldata was passed.')
            elif self.lcontainer_chunk_count != self.mview[0x40:0x44].cast('I')[0]:
                raise ValueError(f'{magic} chunk count of ldata read from data differs'
                                 f'from chunk count read from ldata ({count} != {count1})')
            elif self.lcontainer_size != self.mview[0x44:0x48].cast('I')[0]:
                raise ValueError(f'{magic} size of ldata read from data differs from size'
                                 f'read from ldata ({size} != {size1})')
            elif self.lcontainer_check_digits != self.mview[0x48:0x4c]:
                raise ValueError(f'{magic} check digits read from data differs from check'
                                 f'digits read from ldata ({digits:08X} != {digits1:08X})')
        elif self.ldata:
            raise ValueError(f'{magic} should NOT have ldata, but ldata was passed')

        self._meta_info = Chunk(self.meta_info_buf)
        self._optional_chunk = Chunk(self.optional_chunk_buf)

        mview = self.lmview or self.mview
        O = self.chunk_ofs_table_buf
        if S := self.chunk_size_table_buf:
            self._chunks = list( Chunk(mview[o:(o+s)*bool(s)]) for o, s in zip(O, S) )
        else:
            def f():
                for i, o in enumerate(O):
                    if not o:
                        yield Chunk(mview[o:o])
                        continue
                    for p in O[i+1:]:
                        if p:
                            yield Chunk(mview[o:p])
                            break
                    else:
                        yield Chunk(mview[o:])
            self._chunks = list( f() )

    def commit(self, enable_l = None):
        if enable_l is None:
            enable_l = bool(self._lmview)

        for c in self.chunks:
            c.commit()
        self._meta_info.commit()
        self._optional_chunk.commit()

        C = tuple( c.mview for c in self.chunks )

        # These calculate sizes of new data
        info_size = 0x50 if enable_l else 0x30
        # Tables must be 16 bytes aligned
        cotbl_size = 4*len(C) + -4*len(C) % 0x10
        cstbl_size = cotbl_size * any( c.nbytes % 0x10 for c in C )
        # cstbl_size = cotbl_size * bool( self.chunk_size_table_buf )
        head_size = ( info_size + self._meta_info.mview.nbytes
                      + cotbl_size + cstbl_size + self._optional_chunk.mview.nbytes )
        # Chunks must be 16 bytes aligned
        s = sum(c.nbytes + -c.nbytes % 0x10 for c in C)
        body_size, lhead_size, lbody_size = (
            (0, 0x10+self._meta_info.mview.nbytes, s) if enable_l else (s, 0, 0)
        )

        self._mview = memoryview(bytearray(head_size + body_size))
        self._lmview = memoryview(bytearray(lhead_size + lbody_size))

        # This writes the container info
        self.magic = self.__class__.__name__.encode()
        self.version = 0x00000101.to_bytes(4)
        self.info_size = info_size
        self.container_size = head_size + body_size
        self.chunk_count = len(C)
        self.valid_chunk_count = sum( c.nbytes > 0 for c in C )

        n0 = info_size + self._meta_info.mview.nbytes
        n1 = n0 * bool(cotbl_size)
        self.chunk_ofs_table_ofs = n1
        n2 = (n0 + cotbl_size) * bool(cstbl_size)
        self.chunk_size_table_ofs = n2
        n3 = (n0 + cotbl_size + cstbl_size) * bool(self._optional_chunk)
        self.optional_chunk_ofs = n3

        if self.ldata:
            self.lcontainer_chunk_count = self.valid_chunk_count
            self.lcontainer_size = lhead_size + lbody_size
            self.lcontainer_check_digits = 0x01234567.to_bytes(4, 'little')

        # This writes the new meta info
        self.meta_info_buf[:] = self._meta_info.data

        # This writes the new chunk offset table
        o = lhead_size or head_size
        for i, c in enumerate(C):
            p = c.nbytes + -c.nbytes % 0x10
            self.chunk_ofs_table_buf[i] = o * bool(p)
            o += p

        # This writes the chunk size table
        # chunk_size_table_buf might be empty
        for i in range(len(self.chunk_size_table_buf)):
            self.chunk_size_table_buf[i] = C[i].nbytes

        # This writes the new optional data
        self.optional_chunk_buf[:] = self._optional_chunk.data

        # This writes the new chunks
        mview = self.lmview or self.mview
        for o, c in zip(self.chunk_ofs_table_buf, C, strict=True):
            mview[o:o+c.nbytes] = c

        self.__init__(self.data, self.ldata)

    @property
    def chunks(self):
        return self._chunks

    @property
    def mview(self):
        return self._mview

    @property
    def lcontainer_size(self):
        return self.lmview[0x4:0x8].cast('I')[0]

    @lcontainer_size.setter
    def lcontainer_size(self, val):
        self.mview[0x44:0x48].cast('I')[0] = val
        self.lmview[0x4:0x8].cast('I')[0] = val

    @property
    def lcontainer_chunk_count(self):
        return self.lmview[0x0:0x4].cast('I')[0]

    @lcontainer_chunk_count.setter
    def lcontainer_chunk_count(self, val):
        self.mview[0x40:0x44].cast('I')[0] = val
        self.lmview[0x0:0x4].cast('I')[0] = val

    @property
    def lcontainer_check_digits(self):
        return self.lmview[0x8:0xc].tobytes()

    @lcontainer_check_digits.setter
    def lcontainer_check_digits(self, val):
        self.mview[0x48:0x4c] = val
        self.lmview[0x8:0xc] = val

class TMC(Container):
    def __init__(self, data, ldata):
        ldata = ldata or self.lheader.ldata
        super().__init__(data)

        tbl = tuple(self._chunk_typeid_table)
        L = LHeader(self[tbl.index(0x8000_0020)], ldata)

        for i, t in enumerate(tbl):
            if not (c := self[i]):
                continue
            match t:
                case 0x8000_0001:
                    try:
                        ldata = L.mdlgeo
                    except AttributeError:
                        ldata = None
                    self[i] = MdlGeo(c, ldata)
                    self._mdlgeo_cidx = i
                case 0x8000_0002:
                    try:
                        ldata = L.ttdl
                    except AttributeError:
                        ldata = None
                    self[i] = TTDM(c, ldata)
                    self._ttdm_cidx = i
                case 0x8000_0003:
                    try:
                        ldata = L.vtxlay
                    except AttributeError:
                        ldata = None
                    self[i] = VtxLay(c, ldata)
                    self._vtxlay_cidx = i
                case 0x8000_0004:
                    try:
                        ldata = L.idxlay
                    except AttributeError:
                        ldata = None
                    self[i] = IdxLay(c, ldata)
                    self._idxlay_cidx = i
                case 0x8000_0005:
                    try:
                        ldata = L.mtrcol
                    except AttributeError:
                        ldata = None
                    self[i] = MtrCol(c, ldata)
                    self._mtrcol_cidx = i
                case 0x8000_0006:
                    try:
                        ldata = L.mdlinfo
                    except AttributeError:
                        ldata = None
                    self[i] = MdlInfo(c, ldata)
                    self._mdlinfo_cidx = i
                case 0x8000_0010:
                    self[i] = HieLay(c)
                    self._hielay_cidx = i
                case 0x8000_0020:
                    self[i] = L
                    self._lheader_cidx = i
                case 0x8000_0030:
                    self[i] = NodeLay(c)
                    self._nodelay_cidx = i
                case 0x8000_0040:
                    self[i] = GlblMtx(c)
                    self._glblmtx_cidx = i
                case 0x8000_0050:
                    self[i] = BnOfsMtx(c)
                    self._bnofsmtx_cidx = i
                case 0x8000_0060:
                    self[i] = cpf(c)
                    self._cpf_cidx = i
                case 0x8000_0070:
                    self[i] = MCAPACK(c)
                    self._mcapack_cidx = i
                case 0x8000_0080:
                    self[i] = RENPACK(c)
                    self._renpack_cidx = i

    def commit(self):
        try:
            _ = self.lheader.mdlgeo
            self.mdlgeo.commit()
            self.lheader.mdlgeo = Chunk(self.mdlgeo.ldata)
        except AttributeError:
            pass
        try:
            _ = self.lheader.ttdl
            self.ttdm.commit()
            self.lheader.ttdl = Chunk(self.ttdm.ttdl.ldata)
        except AttributeError:
            pass
        try:
            _ = self.lheader.vtxlay
            self.vtxlay.commit()
            self.lheader.vtxlay = Chunk(self.vtxlay.ldata)
        except AttributeError:
            pass
        try:
            _ = self.lheader.idxlay
            self.idxlay.commit()
            self.lheader.idxlay = Chunk(self.idxlay.ldata)
        except AttributeError:
            pass
        try:
            _ = self.lheader.mtrcol
            self.mtrcol.commit()
            self.lheader.mtrcol = Chunk(self.mtrcol.ldata)
        except AttributeError:
            pass
        try:
            _ = self.lheader.mdlinfo
            self.mdlinfo.commit()
            self.lheader.mdlinfo = Chunk(self.mdlinfo.ldata)
        except AttributeError:
            pass
        super().commit()

    @property
    def name(self):
        return self._meta_info.mview[0x20:].tobytes().partition(b'\x00')[0]

    @property
    def mdlgeo(self):
        return self[self._mdlgeo_cidx]

    @mdlgeo.setter
    def mdlgeo(self, val):
        self[self._mdlgeo_cidx] = val

    @property
    def ttdm(self):
        return self[self._ttdm_cidx]

    @ttdm.setter
    def ttdm(self, val):
        self[self._ttdm_cidx] = val

    @property
    def vtxlay(self):
        return self[self._vtxlay_cidx]

    @vtxlay.setter
    def vtxlay(self, val):
        self[self._vtxlay_cidx] = val

    @property
    def idxlay(self):
        return self[self._idxlay_cidx]

    @idxlay.setter
    def idxlay(self, val):
        self[self._idxlay_cidx] = val

    @property
    def mtrcol(self):
        return self[self._mtrcol_cidx]

    @mtrcol.setter
    def mtrcol(self, val):
        self[self._mtrcol_cidx] = val

    @property
    def mdlinfo(self):
        return self[self._mdlinfo_cidx]

    @mdlinfo.setter
    def mdlinfo(self, val):
        self[self._mdlinfo_cidx] = val

    @property
    def hielay(self):
        return self[self._hielay_cidx]

    @hielay.setter
    def hielay(self, val):
        self[self._hielay_cidx] = val

    @property
    def lheader(self):
        return self[self._lheader_cidx]

    @lheader.setter
    def lheader(self, val):
        self[self._lheader_cidx] = val

    @property
    def nodelay(self):
        return self[self._nodelay_cidx]

    @nodelay.setter
    def nodelay(self, val):
        self[self._nodelay_cidx] = val

    @property
    def glblmtx(self):
        return self[self._glblmtx_cidx]

    @glblmtx.setter
    def glblmtx(self, val):
        self[self._glblmtx_cidx] = val

    @property
    def bnofsmtx(self):
        return self[self._bnofsmtx_cidx]

    @bnofsmtx.setter
    def bnofsmtx(self, val):
        self[self._bnofsmtx_cidx] = val

    @property
    def _chunk_typeid_table(self):
        c = self.chunk_count
        return self._meta_info.mview[0xc0:0xc0+4*c].cast('I')

class MdlGeo(Container):
    def __init__(self, data, ldata = None):
        super().__init__(data, ldata)
        self.chunks[:] = map(ObjGeo, self.chunks)

    def commit(self):
        super().commit()
        for i, objgeo in enumerate(self):
            objgeo._id = i

class ObjGeo(Container):
    def __init__(self, data, ldata = None):
        super().__init__(data, ldata)
        self._optional_chunk = GeoDecl(self._optional_chunk)
        self.chunks[:] = map(ObjGeoChunk, self.chunks)
        for b in self:
            T = ( ObjGeoChunk.Texture(b.mview[o:])
                  for o in b._texture_offset_table )
            b._textures = list(T)
            b._info_size = self.geodecl[b.decl_index].info_size

    def commit(self):
        super().commit()
        for i, b in enumerate(self):
            b._id = i

    @property
    def geodecl(self):
        return self._optional_chunk

    @property
    def name(self):
        return self._meta_info.mview[0x20:].tobytes().partition(b'\x00')[0]

    @property
    def _id(self):
        return self._meta_info.mview[0x4:0x8].cast('i')[0]

    @_id.setter
    def _id(self, val):
        self._meta_info.mview[0x4:0x8].cast('i')[0] = val

class ObjGeoChunk(Chunk):
    @property
    def textures(self):
        return self._textures

    @property
    def _id(self):
        return self.mview[0x0:0x4].cast('i')[0]

    @_id.setter
    def _id(self, val):
        self.mview[0x0:0x4].cast('i')[0] = val

    @property
    def mtrcol_index(self):
        return self.mview[0x4:0x8].cast('i')[0]

    @mtrcol_index.setter
    def mtrcol_index(self, val):
        self.mview[0x4:0x8].cast('i')[0] = val

    @property
    def texture_count(self):
        return self.mview[0xc:0x10].cast('I')[0]

    @property
    def _texture_offset_table(self):
        # max count = 8
        return self.mview[0x10:0x10 + 4*self.texture_count].cast('I')

    @property
    def decl_index(self):
        return self.mview[0x38:0x3c].cast('I')[0]

    @decl_index.setter
    def decl_index(self, val):
        self.mview[0x38:0x3c].cast('I')[0] = val

    @property
    def soft_transparency(self):
        return self.mview[0x40:0x44].cast('I')[0]

    @soft_transparency.setter
    def soft_transparency(self, val):
        self.mview[0x40:0x44].cast('I')[0] = val

    @property
    def hard_transparency(self):
        return self.mview[0x48:0x4c].cast('I')[0]

    @hard_transparency.setter
    def hard_transparency(self, val):
        self.mview[0x48:0x4c].cast('I')[0] = val

    @property
    def index_buffer_offset(self):
        return self.mview[0x30+self._info_size+0x10:].cast('I')[0]

    @index_buffer_offset.setter
    def index_buffer_offset(self, val):
        self.mview[0x30+self._info_size+0x10:].cast('I')[0] = val

    @property
    def ref_index_count(self):
        return self.mview[0x30+self._info_size+0x14:].cast('I')[0]

    @ref_index_count.setter
    def ref_index_count(self, val):
        self.mview[0x30+self._info_size+0x14:].cast('I')[0] = val

    @property
    def vertex_buffer_offset(self):
        return self.mview[0x30+self._info_size+0x18:].cast('I')[0]

    @vertex_buffer_offset.setter
    def vertex_buffer_offset(self, val):
        self.mview[0x30+self._info_size+0x18:].cast('I')[0] = val

    @property
    def ref_vertex_count(self):
        return self.mview[0x30+self._info_size+0x1c:].cast('I')[0]

    @ref_vertex_count.setter
    def ref_vertex_count(self, val):
        self.mview[0x30+self._info_size+0x1c:].cast('I')[0] = val

    class Texture:
        def __init__(self, data):
            self._mview = memoryview(data)

        @property
        def _id(self):
            return self._mview[0x0:].cast('i')[0]

        @_id.setter
        def _id(self, val):
            self._mview[0x0:].cast('i')[0] = val

        @property
        def category(self):
            return self._mview[0x4:].cast('i')[0]

        @category.setter
        def category(self, val):
            self._mview[0x4:].cast('i')[0] = val

        @property
        def buffer_index(self):
            return self._mview[0x8:].cast('i')[0]

        @buffer_index.setter
        def buffer_index(self, val):
            self._mview[0x8:].cast('i')[0] = val

class GeoDecl(Container):
    def __init__(self, data, ldata = None):
        super().__init__(data, ldata)
        self.chunks[:] = map(GeoDeclChunk, self.chunks)

class GeoDeclChunk(Chunk):
    @property
    def info_size(self):
        return self.mview[0x4:].cast('I')[0]

    @property
    def index_buffer_index(self):
        return self.mview[0xc:].cast('i')[0]

    @index_buffer_index.setter
    def index_buffer_index(self, val):
        self.mview[0xc:].cast('i')[0] = val

    @property
    def index_count(self):
        return self.mview[0x10:].cast('I')[0]

    @property
    def vertex_count(self):
        return self.mview[0x14:].cast('I')[0]

    @property
    def vertex_buffer_index(self):
        o = self.info_size
        return self.mview[o:].cast('i')[0]

    @vertex_buffer_index.setter
    def vertex_buffer_index(self, val):
        o = self.info_size
        self.mview[o:].cast('i')[0] = val

    @property
    def vertex_size(self):
        o = self.info_size
        return self.mview[o+4:].cast('i')[0]
    
class TTDM(Container):
    def __init__(self, data, ldata):
        ldata = ldata or self.ttdl.ldata
        super().__init__(data)
        self._meta_info = TTDH(self._meta_info)
        self._optional_chunk = TTDL(self._optional_chunk, ldata)

    @property
    def ttdh(self):
        return self._meta_info

    @property
    def ttdl(self):
        return self._optional_chunk

class TTDH(Container):
    def __init__(self, data, ldata = None):
        super().__init__(data, ldata)
        self.chunks[:] = map(TTDHChunk, self.chunks)

    @staticmethod
    def makechunk():
        return TTDHChunk(bytearray(0x20))

class TTDHChunk(Chunk):
    @property
    def is_in_l(self):
        return self.mview[0]

    @is_in_l.setter
    def is_in_l(self, val):
        self.mview[0] = val

    @property
    def ttdm_ttdl_index(self):
        return self.mview[0x4:0x8].cast('i')[0]

    @ttdm_ttdl_index.setter
    def ttdm_ttdl_index(self, val):
        self.mview[0x4:0x8].cast('i')[0] = val

class TTDL(Container):
    pass

class VtxLay(Container):
    pass

class IdxLay(Container):
    pass

class MtrCol(Container):
    def __init__(self, data, ldata = None):
        super().__init__(data, ldata)
        self.chunks[:] = map(MtrColChunk, self.chunks)
        for b in self:
            X = ( b.mview[0xd0:].cast('Q')[i:i+1].cast('b')
                  for i in range(b.xrefs_count) )
            b._xrefs = tuple( MtrColChunk.Xref(x) for x in X )

    def commit(self):
        super().commit()
        for i, c in enumerate(self):
            c._id = i

    @staticmethod
    def makechunk(xrefs_count):
        # size = matrix + index + xrefs_item_count
        #        + (objgeo_idx + refcount)*xrefs
        size = 4*4*13 + 4 + 4 + (4+4)*xrefs_count
        size += -size % 0x10
        b = MtrColChunk(bytearray(size))
        b._xrefs_count = xrefs_count
        X = ( b.mview[0xd8:].cast('Q')[i:i+1].cast('b')
              for i in range(b.xrefs_count) )
        b._xrefs = tuple( MtrColChunk.Xref(x) for x in X )
        return b

class MtrColChunk(Chunk):
    @property
    def matrix(self):
        return self.mview[0:0xd0].cast('f')

    @matrix.setter
    def matrix(self, val):
        self.mview[0:0xd0].cast('f')[:] = val

    @property
    def _id(self):
        return self.mview[0xd0:0xd4].cast('i')[0]

    @_id.setter
    def _id(self, val):
        self.mview[0xd0:0xd4].cast('i')[0] = val

    @property
    def xrefs_count(self):
        return self.mview[0xd4:0xd8].cast('I')[0]

    @xrefs_count.setter
    def _xrefs_count(self, val):
        self.mview[0xd4:0xd8].cast('I')[0] = val

    @property
    def xrefs(self):
        return self._xrefs

    class Xref:
        def __init__(self, data):
            self._mview = data.cast('i')

        @property
        def index(self):
            return self._mview[0]

        @index.setter
        def index(self, val):
            self._mview[0] = val

        @property
        def count(self):
            return self._mview[1]

        @count.setter
        def count(self, val):
            self._mview[1] = val

class MdlInfo(Container):
    def __init__(self, data, ldata = None):
        super().__init__(data, ldata)
        self.chunks[:] = map(ObjInfo, self.chunks)

    def commit(self):
        super().commit()
        for i, objinfo in enumerate(self):
            objinfo._id = i

class ObjInfo(Container):
    @property
    def _id(self):
        return self._meta_info.mview[0x4:0x8].cast('i')[0]

    @_id.setter
    def _id(self, val):
        self._meta_info.mview[0x4:0x8].cast('i')[0] = val

class HieLay(Container):
    def __init__(self, data, ldata = None):
        super().__init__(data, ldata)
        self.chunks[:] = map(HieLayChunk, self.chunks)

    @staticmethod
    def makechunk(children_count):
        # size = matrix + (parent_id + children_count + level + padding) + children_count
        size = 4*4*4 + (4+4+4+4) + 4*children_count
        size += -size % 0x10
        b = HieLayChunk(bytearray(size))
        b._children_count = children_count
        return b

class HieLayChunk(Chunk):
    @property
    def matrix(self):
        return self.mview.cast('f')[:4*4]

    @matrix.setter
    def matrix(self, val):
        self.mview.cast('f')[:4*4] = val

    @property
    def parent(self):
        return self.mview[0x40:].cast('i')[0]

    @parent.setter
    def parent(self, val):
        self.mview[0x40:].cast('i')[0] = val

    @property
    def children_count(self):
        return self.mview[0x44:].cast('I')[0]

    @children_count.setter
    def _children_count(self, val):
        self.mview[0x44:].cast('I')[0] = val

    @property
    def level(self):
        return self.mview[0x48:].cast('i')[0]

    @level.setter
    def level(self, val):
        self.mview[0x48:].cast('i')[0] = val

    @property
    def children(self):
        return self.mview[0x50:].cast('i')[:self.children_count]

    @children.setter
    def children(self, val):
        self.mview[0x50:].cast('i')[:self.children_count] = val

class LHeader(Container):
    def __init__(self, data, ldata = None):
        super().__init__(data, ldata)
        for i, t in enumerate(self._chunk_typeid_table()):
            if not self[i]:
                continue
            match t:
                case 0xC000_0001:
                    self._mdlgeo_cidx = i
                case 0xC000_0002:
                    self._ttdl_cidx = i
                case 0xC000_0003:
                    self._vtxlay_cidx = i
                case 0xC000_0004:
                    self._idxlay_cidx = i
                case 0xC000_0005:
                    self._mtrcol_cidx = i
                case 0xC000_0006:
                    self._mdlinfo_cidx = i
                case 0xC000_0010:
                    self._hielay_cidx = i
                case 0xC000_0030:
                    self._nodelay_cidx = i
                case 0xC000_0040:
                    self._glblmtx_cidx = i
                case 0xC000_0050:
                    self._bnofsmtx_cidx = i
                case 0xC000_0060:
                    self._cpf_cidx = i
                case 0xC000_0070:
                    self._mcapack_cidx = i
                case 0xC000_0080:
                    self._renpack_cidx = i

    @property
    def mdlgeo(self):
        return self[self._mdlgeo_cidx]

    @mdlgeo.setter
    def mdlgeo(self, val):
        self[self._mdlgeo_cidx] = val

    @property
    def ttdl(self):
        return self[self._ttdl_cidx]

    @ttdl.setter
    def ttdl(self, val):
        self[self._ttdl_cidx] = val

    @property
    def vtxlay(self):
        return self[self._vtxlay_cidx]

    @vtxlay.setter
    def vtxlay(self, val):
        self[self._vtxlay_cidx] = val

    @property
    def idxlay(self):
        return self[self._idxlay_cidx]

    @idxlay.setter
    def idxlay(self, val):
        self[self._idxlay_cidx] = val

    @property
    def mtrcol(self):
        return self[self._mtrcol_cidx]

    @mtrcol.setter
    def mtrcol(self, val):
        self[self._mtrcol_cidx] = val

    @property
    def mdlinfo(self):
        return self[self._mdlinfo_cidx]

    @mdlinfo.setter
    def mdlinfo(self, val):
        self[self._mdlinfo_cidx] = val

    @property
    def hielay(self):
        return self[self._hielay_cidx]

    @hielay.setter
    def hielay(self, val):
        self[self._hielay_cidx] = val

    @property
    def lheader(self):
        return self[self._lheader_cidx]

    @lheader.setter
    def lheader(self, val):
        self[self._lheader_cidx] = val

    @property
    def nodelay(self):
        return self[self._nodelay_cidx]

    @nodelay.setter
    def nodelay(self, val):
        self[self._nodelay_cidx] = val

    @property
    def glblmtx(self):
        return self[self._glblmtx_cidx]

    @glblmtx.setter
    def glblmtx(self, val):
        self[self._glblmtx_cidx] = val

    @property
    def bnofsmtx(self):
        return self[self._bnofsmtx_cidx]

    @bnofsmtx.setter
    def bnofsmtx(self, val):
        self[self._bnofsmtx_cidx] = val

    def _chunk_typeid_table(self):
        c = self.chunk_count
        return self._meta_info.mview[0x20:0x20+4*c].cast('I')

class NodeLay(Container):
    def __init__(self, data, ldata = None):
        super().__init__(data, ldata)
        self.chunks[:] = map(NodeObj, self.chunks)

    def commit(self):
        super().commit()
        j = 0
        for i, nodeobj in enumerate(self):
            nodeobj._id = i
            for c in nodeobj:
                c._id = j
                c._node_id = i
                j += 1

class NodeObj(Container):
    def __init__(self, data, ldata = None):
        super().__init__(data, ldata)
        self.chunks[:] = map(NodeObjChunk, self.chunks)

    @property
    def name(self):
        return self._meta_info.mview[0x10:].tobytes().partition(b'\x00')[0]

    @property
    def _id(self):
        return self._meta_info.mview[0x8:0xc].cast('I')[0]

    @_id.setter
    def _id(self, val):
        self._meta_info.mview[0x8:0xc].cast('I')[0] = val

class NodeObjChunk(Chunk):
    @property
    def _id(self):
        return self.mview[0x0:0x4].cast('I')[0]

    @_id.setter
    def _id(self, val):
        self.mview[0x0:0x4].cast('I')[0] = val

    @property
    def _node_id(self):
        return self.mview[0x8:0xc].cast('I')[0]

    @_node_id.setter
    def _node_id(self, val):
        self.mview[0x8:0xc].cast('I')[0] = val

class GlblMtx(Container):
    pass

class BnOfsMtx(Container):
    pass

class cpf(Container):
    pass

class MCAPACK(Container):
    pass

class RENPACK(Container):
    pass
