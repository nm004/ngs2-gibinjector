# NGS2 Gib Injector by Nozomi Miyamori is marked with CC0 1.0.
# This file is a part of NGS2 Gib Injector.
#
# This module is for reading/writing TMC and TMCL file which is
# used by some Team Ninja's (Koei-Tecmo) games such as NINJA GAIDEN
# Master Collection and Dead or Alice 5 Last Round.
from abc import ABC, abstractmethod
from collections.abc import MutableSequence
import warnings
import struct

class AbstractBlock(ABC):
    # Commit operations and update the underlying data.
    # It is implementation-defined if the underlying
    # data is mutable or not before and after calling commit().
    @abstractmethod
    def commit(self):
        pass

    @property
    @abstractmethod
    def data(self): pass

    def __bool__(self):
        return bool(self.data)

class Block(AbstractBlock):
    def __init__(self, data):
        self._data = memoryview(data)

    def commit(self): pass

    @property
    def data(self):
        return self._data

class Section(Block, MutableSequence):
    @staticmethod
    @abstractmethod
    def Block(self, data): pass

    def __init__(self, data, ldata = b''):
        super().__init__(data)
        data = self.data
        self._ldata = ldata = memoryview(ldata)

        clsname = self.__class__.__name__
        if not self._has_magic(data):
            raise ValueError(f'data does not have magic bytes "{clsname}".')
        self._data = data = data[:self._get_section_size(data)]

        if self._has_ldata(data):
            self.L_is_enabled = True
            if ldata:
                self._warn_if_diff_header(data, ldata)
                self._ldata = ldata = ldata[:self._get_L_size(data)]
            else:
                warnings.warn(f'{clsname} should have ldata, but no ldata was passed.')
        else:
            self.L_is_enabled = False

        self._info0 = self._get_info(data)
        self._meta_info0 = self._get_meta_info(data)
        self._optional_data0 = self._get_optional_data(data)
        self._blocks0 = list(self._generate_blocks())

        self._info = memoryview(self._info0)
        self._meta_info = memoryview(self._meta_info0)
        self._optional_data = memoryview(self._optional_data0)
        self._blocks = self._blocks0.copy()

    def count(self, val):
        return self._blocks.count(val)

    def index(self, val):
        return self._blocks.index(val)

    def insert(self, key, val):
        self._blocks.insert(key, val)

    def append(self, val):
        self._blocks.append(val)

    def clear(self):
        self._blocks.clear()

    def extend(self, other):
        self._blocks.extend(other)

    def pop(self, key=0):
        self._blocks.pop(key)

    def remove(self, val):
        self._blocks.remove(val)

    def reverse(self):
        self._blocks.reverse()

    def __len__(self):
        return len(self._blocks)

    def __getitem__(self, key):
        return self._blocks[key]

    def __setitem__(self, key, val):
        self._blocks[key] = val

    def __delitem__(self, key):
        del self._blocks[key]

    def __iter__(self):
        return iter(self._blocks)

    def __reversed__(self):
        return reversed(self._blocks)

    def __add__(self, other):
        return self._blocks + other

    def __radd__(self, other):
        return other + self._blocks

    def __iadd__(self, other):
        self._blocks += other

    def __mul__(self, other):
        return self._blocks * other

    def __rmul__(self, other):
        return other * self._blocks

    def __imul__(self, other):
        self._blocks *= other

    @property
    def ldata(self):
        return self._ldata

    def enableL(self):
        pass

    def disableL(self):
        pass

    @property
    def L_is_enabled(self):
        return self._L_is_enabled

    @L_is_enabled.setter
    def L_is_enabled(self, val):
        self._L_is_enabled = val

    def commit(self):
        for blk in self._blocks:
            assert isinstance(blk, AbstractBlock)
            blk.commit()
        blks = tuple( memoryview(blk.data) for blk in self._blocks )

        # These calculate sizes of new data
        info_size = 0x50 if self.L_is_enabled else 0x30
        # Tables must be 16 bytes aligned
        botbl_size = 4*len(blks)
        botbl_size += -botbl_size % 0x10
        # bstbl_size = botbl_size * any( b.nbytes % 0x10 for b in blks )
        bstbl_size = botbl_size * bool( self._get_block_size_table_ofs(self.data) )
        head_size = ( info_size + self._meta_info.nbytes
                      + botbl_size + bstbl_size + self._optional_data.nbytes )
        # Blocks must be 16 bytes aligned
        padded_block_sizes = tuple( blk.nbytes + -blk.nbytes % 0x10 for blk in blks )
        s = sum(padded_block_sizes)
        body_size, lhead_size, lbody_size = (0, 0x10+self._meta_info.nbytes, s) if self.L_is_enabled else (s, 0, 0)

        new_data = memoryview(bytearray(head_size + body_size))
        new_ldata = memoryview(bytearray(lhead_size + lbody_size))

        # This writes the section info
        self._set_rawmagic(new_data, self.__class__.__name__.encode().ljust(0x8, b'\x00'))
        self._set_version(new_data, 0x0101_0000)
        self._set_info_size(new_data, info_size)
        self._set_section_size(new_data, head_size + body_size)
        self._set_block_count(new_data, len(blks))
        self._set_valid_block_count(new_data, sum( blk.nbytes > 0 for blk in blks ))

        n0 = info_size + self._meta_info.nbytes
        n1 = n0 if botbl_size else 0
        self._set_block_ofs_table_ofs(new_data, n1)
        # n2 = n0 + botbl_size if bstbl_size else 0
        n2 = n0 + botbl_size if self._get_block_size_table_ofs(self.data) else 0
        self._set_block_size_table_ofs(new_data, n2)
        n3 = n0 + botbl_size + bstbl_size if self._optional_data else 0
        self._set_optional_data_ofs(new_data, n3)

        if new_ldata:
            self._set_L_block_count(new_data, new_ldata, self._get_valid_block_count(new_data))
            self._set_L_size(new_data, new_ldata, lhead_size + lbody_size)
            self._set_L_check_digits(new_data, new_ldata, 0x01234567)

        # This writes the section meta info
        self._set_meta_info(new_data, self._meta_info)

        # This writes the block offset table
        n = lhead_size or head_size
        T = self._get_block_ofs_table(new_data)
        for i in range(len(T)):
            b = padded_block_sizes[i]
            T[i] = n if b else 0
            n += b

        # This writes the block size table
        T = self._get_block_size_table(new_data)
        for i in range(len(T)):
            T[i] = blks[i].nbytes

        # This writes the optional data
        self._set_optional_data(new_data, self._optional_data)

        # This writes the blocks
        T = self._get_block_ofs_table(new_data)
        m = new_ldata or new_data
        for o, blk in zip(T, blks, strict=True):
            m[o:o+blk.nbytes] = blk

        # Reinit self
        self.__init__(new_data, new_ldata)

    def _generate_blocks(self):
        boT = self._get_block_ofs_table(self.data)
        bsT = self._get_block_size_table(self.data)
        I = range(self._get_block_count(self.data))
        x = self.ldata if self.L_is_enabled else self.data
        for i in I:
            if not (o := boT[i]):
                yield self.Block(x[0:0])
                continue
            if bsT:
                yield self.Block(x[o:o+bsT[i]])
                continue
            for p in boT[i+1:]:
                if p:
                    yield self.Block(x[o:p])
                    break
            else:
                yield self.Block(x[o:])

    @staticmethod
    def _get_magic(data):
        return Section._get_rawmagic(data).tobytes().partition(b'\x00')[0]

    @classmethod
    def _has_magic(cls, data):
        data = cls._get_magic(data)
        return data == cls.__name__.encode()

    @staticmethod
    def _has_ldata(data):
        return Section._get_info_size(data) == 0x50

    @staticmethod
    def _warn_if_diff_header(data, ldata):
        name = Section._get_magic(data).decode()
        count = Section._get_L_block_count(data) 
        count1 = Section._get_L_block_count_L(ldata)
        if count != count1:
            warnings.warn(f'{name} block count of ldata read from data differs from block count read from ldata'
                          f'({count} != {count1})')
            return
        size = Section._get_L_size(data) 
        size1 = Section._get_L_size_L(ldata)
        if size != size1:
            warnings.warn(f'{name} size of ldata read from data differs from size read from ldata'
                          f'({size} != {size1})')
            return
        digits = Section._get_L_check_digits(data)
        digits1 = Section._get_L_check_digits_L(ldata)
        if digits != digits1:
            warnings.warn(f'{name} check digits read from data differs from check digits read from ldata'
                          f'({digits:08X} != {digits1:08X})')

    @staticmethod
    def _get_info(data):
        n = Section._get_info_size(data)
        return data[0:n]

    @staticmethod
    def _get_meta_info(data):
        n = Section._get_info_size(data)
        o = ( Section._get_block_ofs_table_ofs(data)
              or Section._get_block_size_table_ofs(data)
              or Section._get_optional_data_ofs(data)
              or None )
        return data[n:o]

    @staticmethod
    def _set_meta_info(data, val):
        n = Section._get_info_size(data)
        o = ( Section._get_block_ofs_table_ofs(data)
              or Section._get_block_size_table_ofs(data)
              or Section._get_optional_data_ofs(data)
              or None)
        data[n:o] = val

    @staticmethod
    def _get_block_ofs_table(data):
        o = Section._get_block_ofs_table_ofs(data) or data.nbytes
        n = Section._get_block_count(data)
        return data[o:].cast('I')[:n]

    @staticmethod
    def _get_block_size_table(data):
        o = Section._get_block_size_table_ofs(data) or data.nbytes
        n = Section._get_block_count(data)
        return data[o:].cast('I')[:n]

    @staticmethod
    def _get_optional_data(data):
        o = Section._get_optional_data_ofs(data) or data.nbytes
        t = Section._get_block_ofs_table(data)
        p = t[0] if t else None
        return data[o:p]

    @staticmethod
    def _set_optional_data(data, val):
        o = Section._get_optional_data_ofs(data) or data.nbytes
        t = Section._get_block_ofs_table(data)
        p = t[0] if t else None
        data[o:p] = val            

    @staticmethod
    def _get_rawmagic(data):
        return data[0:8]

    @staticmethod
    def _set_rawmagic(data, val):
        data[0:8] = val

    @staticmethod
    def _get_version(data):
        return data[0x8:].cast('I')[0]

    @staticmethod
    def _set_version(data, val):
        data[0x8:].cast('I')[0] = val

    @staticmethod
    def _get_info_size(data):
        return data[0xc:].cast('I')[0]

    @staticmethod
    def _set_info_size(data, val):
        data[0xc:].cast('I')[0] = val

    @staticmethod
    def _get_section_size(data):
        return data[0x10:].cast('I')[0]

    @staticmethod
    def _set_section_size(data, val):
        data[0x10:].cast('I')[0] = val

    @staticmethod
    def _get_block_count(data):
        return data[0x14:].cast('I')[0]

    @staticmethod
    def _set_block_count(data, val):
        data[0x14:].cast('I')[0] = val

    @staticmethod
    def _get_valid_block_count(data):
        return data[0x18:].cast('I')[0]

    @staticmethod
    def _set_valid_block_count(data, val):
        data[0x18:].cast('I')[0] = val

    @staticmethod
    def _get_block_ofs_table_ofs(data):
        return data[0x20:].cast('I')[0]

    @staticmethod
    def _set_block_ofs_table_ofs(data, val):
        data[0x20:].cast('I')[0] = val

    @staticmethod
    def _get_block_size_table_ofs(data):
        return data[0x24:].cast('I')[0]

    @staticmethod
    def _set_block_size_table_ofs(data, val):
        data[0x24:].cast('I')[0] = val

    @staticmethod
    def _get_optional_data_ofs(data):
        return data[0x28:].cast('I')[0]

    @staticmethod
    def _set_optional_data_ofs(data, val):
        data[0x28:].cast('I')[0] = val

    @staticmethod
    def _get_L_block_count(data):
        return data[0x40:].cast('I')[0]

    @staticmethod
    def _get_L_block_count_L(ldata):
        return ldata[0x0:].cast('I')[0]

    @staticmethod
    def _set_L_block_count(data, ldata, val):
        data[0x40:].cast('I')[0] = ldata[0x0:].cast('I')[0] = val

    @staticmethod
    def _get_L_size(data):
        return data[0x44:].cast('I')[0]

    @staticmethod
    def _get_L_size_L(ldata):
        return ldata[0x4:].cast('I')[0]

    @staticmethod
    def _set_L_size(data, ldata, val):
        data[0x44:].cast('I')[0] = ldata[0x4:].cast('I')[0] = val

    @staticmethod
    def _get_L_check_digits(data):
        return data[0x48:].cast('I')[0]

    @staticmethod
    def _get_L_check_digits_L(ldata):
        return ldata[0x8:].cast('I')[0]

    @staticmethod
    def _set_L_check_digits(data, ldata, val):
        data[0x48:].cast('I')[0] = ldata[0x8:].cast('I')[0] = val

class TMC(Section):
    Block = Block

    def __init__(self, data, ldata = b''):
        super().__init__(data)
        tbl = tuple(self._get_block_typeid_table())
        data = self[i := tbl.index(0x8000_0020)].data
        ldata = self.lheader.ldata if self.lheader else ldata

        self._lheader = self[i] = L = LHeader(data, ldata)
        for i, t in enumerate(tbl):
            m = self[i].data
            if not m:
                continue
            match t:
                case 0x8000_0001:
                    self._mdlgeo = self[i] = MdlGeo(m, L.mdlgeo.data)
                    self._mdlgeo_section_index = i
                case 0x8000_0002:
                    self._ttdm = self[i] = TTDM(m, L.ttdl.data)
                    self._ttdm_section_index = i
                case 0x8000_0003:
                    self._vtxlay = self[i] = VtxLay(m, L.vtxlay.data)
                    self._vtxlay_section_index = i
                case 0x8000_0004:
                    self._idxlay = self[i] = IdxLay(m, L.idxlay.data)
                    self._idxlay_section_index = i
                case 0x8000_0005:
                    self._mtrcol = self[i] = MtrCol(m, L.mtrcol.data)
                    self._mtrcol_section_index = i
                case 0x8000_0006:
                    self._mdlinfo = self[i] = MdlInfo(m, L.mdlinfo.data)
                    self._mdlinfo_section_index = i
                case 0x8000_0010:
                    self._hielay = self[i] = HieLay(m)
                    self._hielay_section_index = i
                case 0x8000_0020:
                    self._lheader_section_index = i
                case 0x8000_0030:
                    self._nodelay = self[i] = NodeLay(m)
                    self._nodelay_section_index = i
                case 0x8000_0040:
                    self._glblmtx = self[i] = GlblMtx(m)
                    self._glblmtx_section_index = i
                case 0x8000_0050:
                    self._bnofsmtx = self[i] = BnOfsMtx(m)
                    self._bnofsmtx_section_index = i
                case 0x8000_0060:
                    self._cpf = self[i] = cpf(m)
                    self._cpf_section_index = i
                case 0x8000_0070:
                    self._mcapack = self[i] = MCAPACK(m)
                    self._mcapack_section_index = i
                case 0x8000_0080:
                    self._renpack = self[i] = RENPACK(m)
                    self._renpack_section_index = i
    @property
    def name(self):
        return self._meta_info[0x20:].tobytes().partition(b'\x00')[0]

    @property
    def mdlgeo(self):
        try:
            return self._mdlgeo
        except AttributeError:
            return self.Block(b'')

    @mdlgeo.setter
    def mdlgeo(self, val):
        self._mdlgeo = self[self._mdlgeo_section_index] = val

    @property
    def ttdm(self):
        try:
            return self._ttdm
        except AttributeError:
            return self.Block(b'')

    @ttdm.setter
    def ttdm(self, val):
        self._ttdm = self[self._ttdm_section_index] = val

    @property
    def vtxlay(self):
        try:
            return self._vtxlay
        except AttributeError:
            return self.Block(b'')

    @vtxlay.setter
    def vtxlay(self, val):
        self._vtxlay = self[self._vtxlay_section_index] = val

    @property
    def idxlay(self):
        try:
            return self._idxlay
        except AttributeError:
            return self.Block(b'')

    @idxlay.setter
    def idxlay(self, val):
        self._idxlay = self[self._idxlay_section_index] = val

    @property
    def mtrcol(self):
        try:
            return self._mtrcol
        except AttributeError:
            return self.Block(b'')

    @mtrcol.setter
    def mtrcol(self, val):
        self._mtrcol = self[self._mtrcol_section_index] = val

    @property
    def mdlinfo(self):
        try:
            return self._mdlinfo
        except AttributeError:
            return self.Block(b'')

    @mdlinfo.setter
    def mdlinfo(self, val):
        self._mdlinfo = self[self._mdlinfo_section_index] = val

    @property
    def hielay(self):
        try:
            return self._hielay
        except AttributeError:
            return self.Block(b'')

    @hielay.setter
    def hielay(self, val):
        self._hielay = self[self._hielay_section_index] = val

    @property
    def lheader(self):
        try:
            return self._lheader
        except AttributeError:
            return self.Block(b'')

    @lheader.setter
    def lheader(self, val):
        self._lheader = self[self._lheader_section_index] = val

    @property
    def nodelay(self):
        try:
            return self._nodelay
        except AttributeError:
            return self.Block(b'')

    @nodelay.setter
    def nodelay(self, val):
        self._nodelay = self[self._nodelay_section_index] = val

    @property
    def glblmtx(self):
        try:
            return self._glblmtx
        except AttributeError:
            return self.Block(b'')

    @glblmtx.setter
    def glblmtx(self, val):
        self._glblmtx = self[self._glblmtx_section_index] = val

    @property
    def bnofsmtx(self):
        try:
            return self._bnofsmtx
        except AttributeError:
            return self.Block(b'')

    @bnofsmtx.setter
    def bnofsmtx(self, val):
        self._bnofsmtx = self[self._bnofsmtx_section_index] = val

    def _get_block_typeid_table(self):
        c = self._get_block_count(self.data)
        T = self._meta_info[0xc0:].cast('I')
        return T[:c]

class ObjGeo(Section):
    Block = Block

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._geodecl = GeoDecl(self._optional_data)
        for b in self:
            T = ( self.Block.Texture(b.data[o:])
                  for o in b._texture_offset_table )
            b._textures = list(T)
            b._outer = self

    def commit(self):
        super().commit()
        for i, b in enumerate(self):
            b._id = i

    @property
    def geodecl(self):
        return self._geodecl

    @property
    def name(self):
        return self._meta_info[0x20:].tobytes().partition(b'\x00')[0]

    @property
    def _id(self):
        return self._meta_info[0x4:].cast('i')[0]

    @_id.setter
    def _id(self, val):
        self._meta_info[0x4:].cast('i')[0] = val

    class Block(Block):
        @property
        def textures(self):
            return self._textures

        @property
        def _id(self):
            return self.data[0x0:].cast('i')[0]

        @_id.setter
        def _id(self, val):
            self.data[0x0:].cast('i')[0] = val

        @property
        def mtrcol_index(self):
            return self.data[0x4:].cast('i')[0]

        @mtrcol_index.setter
        def mtrcol_index(self, val):
            self.data[0x4:].cast('i')[0] = val

        @property
        def texture_count(self):
            return self.data[0xc:].cast('I')[0]

        @property
        def _texture_offset_table(self):
            # max count = 8
            return self.data[0x10:].cast('I')[:self.texture_count]

        @property
        def decl_index(self):
            return self.data[0x38:].cast('I')[0]

        @decl_index.setter
        def decl_index(self, val):
            self.data[0x38:].cast('I')[0] = val

        @property
        def soft_transparency(self):
            return self.data[0x40:].cast('I')[0] and True

        @soft_transparency.setter
        def soft_transparency(self, val):
            self.data[0x40:].cast('I')[0] = bool(val)

        @property
        def hard_transparency(self):
            return self.data[0x48:].cast('I')[0] and True

        @hard_transparency.setter
        def hard_transparency(self, val):
            self.data[0x48:].cast('I')[0] = 0xc0 if val else 0

        @property
        def index_buffer_offset(self):
            o = self._outer.geodecl[self.decl_index].info_size
            return self.data[0x30+o+0x10:].cast('I')[0]

        @index_buffer_offset.setter
        def index_buffer_offset(self, val):
            o = self._outer.geodecl[self.decl_index].info_size
            self.data[0x30+o+0x10:].cast('I')[0] = val

        @property
        def ref_index_count(self):
            o = self._outer.geodecl[self.decl_index].info_size
            return self.data[0x30+o+0x14:].cast('I')[0]

        @ref_index_count.setter
        def ref_index_count(self, val):
            o = self._outer.geodecl[self.decl_index].info_size
            self.data[0x30+o+0x14:].cast('I')[0] = val

        @property
        def vertex_buffer_offset(self):
            o = self._outer.geodecl[self.decl_index].info_size
            return self.data[0x30+o+0x18:].cast('I')[0]

        @vertex_buffer_offset.setter
        def vertex_buffer_offset(self, val):
            o = self._outer.geodecl[self.decl_index].info_size
            self.data[0x30+o+0x18:].cast('I')[0] = val

        @property
        def ref_vertex_count(self):
            o = self._outer.geodecl[self.decl_index].info_size
            return self.data[0x30+o+0x1c:].cast('I')[0]

        @ref_vertex_count.setter
        def ref_vertex_count(self, val):
            o = self._outer.geodecl[self.decl_index].info_size
            self.data[0x30+o+0x1c:].cast('I')[0] = val

        class Texture:
            def __init__(self, data):
                self._data = memoryview(data)

            @property
            def _id(self):
                return self._data[0x0:].cast('i')[0]

            @_id.setter
            def _id(self, val):
                self._data[0x0:].cast('i')[0] = val

            @property
            def category(self):
                return self._data[0x4:].cast('i')[0]

            @category.setter
            def category(self, val):
                self._data[0x4:].cast('i')[0] = val

            @property
            def buffer_index(self):
                return self._data[0x8:].cast('i')[0]

            @buffer_index.setter
            def buffer_index(self, val):
                self._data[0x8:].cast('i')[0] = val

class MdlGeo(Section):
    Block = ObjGeo

    def commit(self):
        super().commit()
        for i, objgeo in enumerate(self):
            objgeo._id = i

class GeoDecl(Section):
    class Block(Block):
        @property
        def info_size(self):
            return self.data[0x4:].cast('I')[0]

        @property
        def index_buffer_index(self):
            return self.data[0xc:].cast('i')[0]

        @index_buffer_index.setter
        def index_buffer_index(self, val):
            self.data[0xc:].cast('i')[0] = val

        @property
        def index_count(self):
            return self.data[0x10:].cast('I')[0]

        @property
        def vertex_count(self):
            return self.data[0x14:].cast('I')[0]

        @property
        def vertex_buffer_index(self):
            o = self.info_size
            return self.data[o:].cast('i')[0]

        @vertex_buffer_index.setter
        def vertex_buffer_index(self, val):
            o = self.info_size
            self.data[o:].cast('i')[0] = val

        @property
        def vertex_size(self):
            o = self.info_size
            return self.data[o+4:].cast('i')[0]

class TTDM(Section):
    Block = Block

    def __init__(self, data, ldata = b''):
        super().__init__(data)
        try:
            ldata = ldata or self.ttdl.ldata
        except AttributeError:
            pass
        self._ttdh = TTDH(self._meta_info)
        self._ttdl = TTDL(self._optional_data, ldata)

    def commit(self):
        self.ttdh.commit()
        self._meta_info = self.ttdh.data
        self.ttdl.commit()
        self._optional_data = self.ttdl.data
        super().commit()

    @property
    def ttdh(self):
        return self._ttdh

    @property
    def ttdl(self):
        return self._ttdl

class TTDH(Section):
    @staticmethod
    def makeblock():
        return TTDH.Block(bytearray(0x20))

    class Block(Block):
        @property
        def is_in_L(self):
            return self.data[0]

        @is_in_L.setter
        def is_in_L(self, val):
            self.data[0] = val

        @property
        def ttdm_ttdl_index(self):
            return self.data[0x4:].cast('i')[0]

        @ttdm_ttdl_index.setter
        def ttdm_ttdl_index(self, val):
            self.data[0x4:].cast('i')[0] = val

class TTDL(Section):
    Block = Block

class VtxLay(Section):
    Block = Block

class IdxLay(Section): Block = Block

class MtrCol(Section):
    def __init__(self, data, ldata = b''):
        super().__init__(data, ldata)
        for b in self:
            X = ( b.data[0xd8:].cast('Q')[i:i+1].cast('b')
                  for i in range(b.xrefs_count) )
            b._xrefs = tuple( self.Block.Xref(x) for x in X )

    def commit(self):
        super().commit()
        for i, blk in enumerate(self):
            blk._id = i

    @staticmethod
    def makeblock(xrefs_count):
        # size = matrix + index + xrefs_item_count
        #        + (objgeo_idx + refcount)*xrefs
        size = 4*4*13 + 4 + 4 + (4+4)*xrefs_count
        size += -size % 0x10
        b = MtrCol.Block(bytearray(size))
        b._xrefs_count = xrefs_count
        X = ( b.data[0xd8:].cast('Q')[i:i+1].cast('b')
              for i in range(b.xrefs_count) )
        b._xrefs = tuple( MtrCol.Block.Xref(x) for x in X )
        return b

    class Block(Block):
        @property
        def matrix(self):
            return self.data[0:0xd0].cast('f')

        @matrix.setter
        def matrix(self, val):
            self.data[0:0xd0].cast('f')[:] = val

        @property
        def _id(self):
            return self.data[0xd0:].cast('i')[0]

        @_id.setter
        def _id(self, val):
            self.data[0xd0:].cast('i')[0] = val

        @property
        def xrefs_count(self):
            return self.data[0xd4:].cast('I')[0]

        @xrefs_count.setter
        def _xrefs_count(self, val):
            self.data[0xd4:].cast('I')[0] = val

        @property
        def xrefs(self):
            return self._xrefs

        class Xref:
            def __init__(self, data):
                self._data = data.cast('i')

            @property
            def index(self):
                return self._data[0]

            @index.setter
            def index(self, val):
                self._data[0] = val

            @property
            def count(self):
                return self._data[1]

            @count.setter
            def count(self, val):
                self._data[1] = val

class ObjInfo(Section):
    Block = Block

    @property
    def _id(self):
        return self._meta_info[0x4:].cast('i')[0]

    @_id.setter
    def _id(self, val):
        self._meta_info[0x4:].cast('i')[0] = val

class MdlInfo(Section):
    Block = ObjInfo

    def commit(self):
        super().commit()
        for i, objinfo in enumerate(self):
            objinfo._id = i

class HieLay(Section):
    @staticmethod
    def makeblock(children_count):
        # size = matrix + (parent_id + children_count + level + padding) + children_count
        size = 4*4*4 + (4+4+4+4) + 4*children_count
        size += -size % 0x10
        b = HieLay.Block(bytearray(size))
        b._children_count = children_count
        return b

    class Block(Block):
        @property
        def matrix(self):
            return self.data.cast('f')[:4*4]

        @matrix.setter
        def matrix(self, val):
            self.data.cast('f')[:4*4] = val

        @property
        def parent(self):
            return self.data[0x40:].cast('i')[0]

        @parent.setter
        def parent(self, val):
            self.data[0x40:].cast('i')[0] = val

        @property
        def children_count(self):
            return self.data[0x44:].cast('I')[0]

        @children_count.setter
        def _children_count(self, val):
            self.data[0x44:].cast('I')[0] = val

        @property
        def level(self):
            return self.data[0x48:].cast('i')[0]

        @level.setter
        def level(self, val):
            self.data[0x48:].cast('i')[0] = val

        @property
        def children(self):
            return self.data[0x50:].cast('i')[:self.children_count]

        @children.setter
        def children(self, val):
            self.data[0x50:].cast('i')[:self.children_count] = val

class LHeader(Section):
    Block = Block

    def __init__(self, data, ldata = b''):
        super().__init__(data, ldata)
        for i, t in enumerate(self._get_block_typeid_table()):
            b = self[i]
            if not b.data:
                continue
            match t:
                case 0xC000_0001:
                    self._mdlgeo = b
                    self._mdlgeo_section_index = i
                case 0xC000_0002:
                    self._ttdl = b
                    self._ttdl_section_index = i
                case 0xC000_0003:
                    self._vtxlay = b
                    self._vtxlay_section_index = i
                case 0xC000_0004:
                    self._idxlay = b
                    self._idxlay_section_index = i
                case 0xC000_0005:
                    self._mtrcol = b
                    self._mtrcol_section_index = i
                case 0xC000_0006:
                    self._mdlinfo = b
                    self._mdlinfo_section_index = i
                case 0xC000_0010:
                    self._hielay = b
                    self._hielay_section_index = i
                case 0xC000_0030:
                    self._nodelay = b
                    self._nodelay_section_index = i
                case 0xC000_0040:
                    self._glblmtx = b
                    self._glblmtx_section_index = i
                case 0xC000_0050:
                    self._bnofsmtx = b
                    self._bnofsmtx_section_index = i
                case 0xC000_0060:
                    self._cpf = b
                    self._cpf_section_index = i
                case 0xC000_0070:
                    self._mcapack = b
                    self._mcapack_section_index = i
                case 0xC000_0080:
                    self._renpack = b
                    self._renpack_section_index = i

    @property
    def mdlgeo(self):
        try:
            return self._mdlgeo
        except AttributeError:
            return self.Block(b'')

    @mdlgeo.setter
    def mdlgeo(self, val):
        self._mdlgeo = self[self._mdlgeo_section_index] = val

    @property
    def ttdl(self):
        try:
            return self._ttdl
        except AttributeError:
            return self.Block(b'')

    @ttdl.setter
    def ttdl(self, val):
        self._ttdl = self[self._ttdl_section_index] = val

    @property
    def vtxlay(self):
        try:
            return self._vtxlay
        except AttributeError:
            return self.Block(b'')

    @vtxlay.setter
    def vtxlay(self, val):
        self._vtxlay = self[self._vtxlay_section_index] = val

    @property
    def idxlay(self):
        try:
            return self._idxlay
        except AttributeError:
            return self.Block(b'')

    @idxlay.setter
    def idxlay(self, val):
        self._idxlay = self[self._idxlay_section_index] = val

    @property
    def mtrcol(self):
        try:
            return self._mtrcol
        except AttributeError:
            return self.Block(b'')

    @mtrcol.setter
    def mtrcol(self, val):
        self._mtrcol = self[self._mtrcol_section_index] = val

    @property
    def mdlinfo(self):
        try:
            return self._mdlinfo
        except AttributeError:
            return self.Block(b'')

    @mdlinfo.setter
    def mdlinfo(self, val):
        self._mdlinfo = self[self._mdlinfo_section_index] = val

    @property
    def hielay(self):
        try:
            return self._hielay
        except AttributeError:
            return self.Block(b'')

    @hielay.setter
    def hielay(self, val):
        self._hielay = self[self._hielay_section_index] = val

    @property
    def lheader(self):
        try:
            return self._lheader
        except AttributeError:
            return self.Block(b'')

    @lheader.setter
    def lheader(self, val):
        self._lheader = self[self._lheader_section_index] = val

    @property
    def nodelay(self):
        try:
            return self._nodelay
        except AttributeError:
            return self.Block(b'')

    @nodelay.setter
    def nodelay(self, val):
        self._nodelay = self[self._nodelay_section_index] = val

    @property
    def glblmtx(self):
        try:
            return self._glblmtx
        except AttributeError:
            return self.Block(b'')

    @glblmtx.setter
    def glblmtx(self, val):
        self._glblmtx = self[self._glblmtx_section_index] = val

    @property
    def bnofsmtx(self):
        try:
            return self._bnofsmtx
        except AttributeError:
            return self.Block(b'')

    @bnofsmtx.setter
    def bnofsmtx(self, val):
        self._bnofsmtx = self[self._bnofsmtx_section_index] = val

    def _get_block_typeid_table(self):
        c = self._get_block_count(self.data)
        T = self._meta_info[0x20:].cast('I')
        return T[:c]

class NodeObj(Section):
    Block = Block

    @property
    def name(self):
        return self._meta_info[0x10:].tobytes().partition(b'\x00')[0]

    @property
    def _id(self):
        return self._meta_info[0x10:].tobytes().partition(b'\x00')[0]

    @_id.setter
    def _id(self, val):
        self._meta_info[0x8:].cast('I')[0] = val

    class Block(Block):
        @property
        def _object_index(self):
            return self.data[0x0:].cast('I')[0]

        @_object_index.setter
        def _object_index(self, val):
            self.data[0x0:].cast('I')[0] = val

        @property
        def _node_index(self):
            return self.data[0x8:].cast('I')[0]

        @_node_index.setter
        def _node_index(self, val):
            self.data[0x8:].cast('I')[0] = val

class NodeLay(Section):
    Block = NodeObj

    def commit(self):
        super().commit()
        j = 0
        for i, nodeobj in enumerate(self):
            nodeobj._id = i
            for blk in nodeobj:
                blk._object_index = j
                blk._node_index = i
                j += 1

class GlblMtx(Section):
    Block = Block

class BnOfsMtx(Section):
    Block = Block

class cpf(Section):
    Block = Block

class MCAPACK(Section):
    Block = Block

class RENPACK(Section):
    Block = Block
