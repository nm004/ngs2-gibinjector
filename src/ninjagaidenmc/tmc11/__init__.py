# NGMC Script by Nozomi Miyamori is marked with CC0 1.0.
# This file is a part of NGMC Script.
#
# This module is for reading/writing container format that is
# used by some Team Ninja's (Koei-Tecmo) games such as NINJA GAIDEN
# Master Collection and Dead or Alive 5 Last Round.

from __future__ import annotations
from typing import Self, NamedTuple
from array import array
from dataclasses import dataclass, field

@dataclass
class ContainerParser:
    data: memoryview
    ldata: memoryview
    opt_head: memoryview
    sub_container: memoryview
    chunks: tuple[memoryview]

    def __init__(self, magic, data, ldata = memoryview(b'')):
        if (x := bytes(data[0:8])) != magic.ljust(8, b'\x00'):
            raise ValueError('data does not have magic bytes'
                             f' ("{x.decode()}" != "{magic.decode()}").')
        # version
        if (x := int.from_bytes(data[0x8:0xc])) != 0x0000_0101:
            raise ValueError(f'not supported verison {x:04X}')
        head_size = int.from_bytes(data[0xc:0x10], 'little')
        container_size = int.from_bytes(data[0x10:0x14], 'little')
        chunk_count = int.from_bytes(data[0x14:0x18], 'little')
        # valid_chunk_count = int.from_bytes(data[0x18:0x1c], 'little')
        chunk_ofs_table_ofs = int.from_bytes(data[0x20:0x24], 'little')
        chunk_size_table_ofs = int.from_bytes(data[0x24:0x28], 'little')
        sub_container_ofs =  int.from_bytes(data[0x28:0x2c], 'little')
        self.data = data = data[:container_size].toreadonly()

        lcontainer_size = None
        are_chunks_in_L = head_size == 0x50
        if are_chunks_in_L:
            f = lambda x1, x2: (int.from_bytes(x1, 'little'), int.from_bytes(x2, 'little'))
            if not ldata:
                raise ValueError(f'{magic.decode()} should have ldata, but no ldata was passed.')
            elif (x1 := data[0x40:0x44]) != (x2 := ldata[0x0:0x4]):
                x1, x2 = f(x1, x2)
                raise ValueError(f'{magic.decode()} chunk count of ldata read from data differs'
                                 f'from chunk count read from ldata ({x1} != {x2})')
            elif (x1 := data[0x44:0x48]) != (x2 := ldata[0x4:0x8]):
                x1, x2 = f(x1, x2)
                raise ValueError(f'{magic.decode()} size of ldata read from data differs from size'
                                 f'read from ldata ({x1} != {x2})')
            elif (x1 := data[0x48:0x4c]) != (x2 := ldata[0x8:0xc]):
                x1, x2 = f(x1, x2)
                raise ValueError(f'{magic.decode()} check digits read from data differs from check'
                                 f'digits read from ldata ({x1:08X} != {x2:08X})')
            lcontainer_size = int.from_bytes(ldata[0x4:0x8], 'little')
        self.ldata = ldata = ldata[:lcontainer_size].toreadonly()

        o1 = chunk_ofs_table_ofs
        o2 = bool(o1) * (o1 + 4*chunk_count)
        chunk_ofs_table = data[o1:o2].cast('I')

        o1 = chunk_size_table_ofs
        o2 = bool(o1) * (o1 + 4*chunk_count)
        chunk_size_table = data[o1:o2].cast('I')
        
        o1 = sub_container_ofs
        o2 = bool(o1) * ( self.chunk_ofs_table
                          and chunk_ofs_table[0]
                          or container_size )
        self.sub_container = data[o1:o2]

        o1 = head_size
        o2 = ( chunk_ofs_table_ofs
               or chunk_size_table_ofs
               or sub_container_ofs
               or container_size )
        self.opt_head = data[o1:o2]

        D = (chunks_in_L and ldata) or data
        O = self.chunk_ofs_table
        S = self.chunk_size_table
        self.chunks = tuple(ContainerParser._gen_chunks(D, O, S))

    @staticmethod
    def _gen_chunks(data, chunk_ofs_table, chunk_size_table):
        O = chunk_ofs_table
        S = chunk_size_table
        if S:
            # Some chunks are empty
            yield from ( data[o:(o+s)*bool(s)] for o, s in zip(O, S) )
            return

        for i, o1 in enumerate(O):
            if not o1:
                yield data[:0]
                continue
            for o2 in O[i+1:]:
                if o2:
                    yield data[o1:o2]
                    break
            else:
                yield data[o1:]

class TMCParser(ContainerParser):
    mdlgeo: memoryview = memoryview(b'')
    ttdm: memoryview = memoryview(b'')
    vtxlay: memoryview = memoryview(b'')
    idxlay: memoryview = memoryview(b'')
    mtrcol: memoryview = memoryview(b'')
    mdlinfo: memoryview = memoryview(b'')
    hielay: memoryview = memoryview(b'')
    lheader: memoryview = memoryview(b'')
    nodelay: memoryview = memoryview(b'')
    glblmtx: memoryview = memoryview(b'')
    bnofsmtx: memoryview = memoryview(b'')
    cpf: memoryview = memoryview(b'')
    mcapack: memoryview = memoryview(b'')
    renpack: memoryview = memoryview(b'')

    def __init__(self, data):
        super().__init__(b'TMC', data)

        o1 = 0xc0
        o2 = 0xc0 + 4*len(self.chunks)
        chunk_type_id_table = self.opt_head[o1:o2].cast('I')
        for t, c in zip(chunk_type_id_table, self.chunks):
            match t:
                case 0x8000_0001:
                    self.mdlgeo = c
                case 0x8000_0002:
                    self.ttdm = c
                case 0x8000_0003:
                    self.vtxlay = c
                case 0x8000_0004:
                    self.idxlay = c
                case 0x8000_0005:
                    self.mtrcol = c
                case 0x8000_0006:
                    self.mdlinfo = c
                case 0x8000_0010:
                    self.hielay = c
                case 0x8000_0020:
                    self.lheader = c
                case 0x8000_0030:
                    self.nodelay = c
                case 0x8000_0040:
                    self.glblmtx = c
                case 0x8000_0050:
                    self.bnofsmtx = c
                case 0x8000_0060:
                    self.cpf = c
                case 0x8000_0070:
                    self.mcapack = c
                case 0x8000_0080:
                    self.renpack = c
        self.name = bytes(self.opt_head[0x20:0x30]).partition(b'\x00')[0]

class MdlGeoParser(ContainerParser):
    mdlgeo_chunks: tuple[ObjGeoParser]

    def __init__(self, data):
        super().__init__(b'MdlGeo', data)
        self.mdlgeo_chunks = tuple( ObjGeoParser(c) for c in self.chunks )

class ObjGeoParser(ContainerParser):
    objgeo_id: int
    name: bytes
    geodecl: GeoDeclParser
    objgeo_chunks: tuple[ObjGeoChunk]

    def __init__(self, data):
        super().__init__(b'ObjGeo', data)
        self.objgeo_id = int.from_bytes(self.opt_head[0x4:0x8], 'little', signed=True)
        self.name = bytes(self.opt_head[0x20:]).partition(b'\x00')[0]
        self.geodecl = GeoDeclParser(self.sub_container)
        self.objgeo_chunks = tuple(ObjGeoParser._gen_chunks(self.chunks))

    @staticmethod
    def _gen_chunks(chunks, geodecl):
        for c in chunks:
            chunk_id = int.from_bytes(c[0x0:0x4], 'little', signed=True)
            mtrcol_index = int.from_bytes(c[0x4:0x8], 'little', signed=True)
            # texture_map_count is at most 8
            texture_map_count = int.from_bytes(c[0xc:0x10], 'little')
            texture_map_ofs_table = c[0x10:0x10+4*texture_map_count].cast('I')
            geodecl_index = int.from_bytes(c[0x38:0x3c], 'little')
            N = geodecl.geodecl_chunks[geodecl_index].struct_size

            o = 0x30
            soft_transparency = int.from_bytes(c[o+0x10:o+0x14], 'little')
            hard_transparency = int.from_bytes(c[o+0x18:o+0x1c], 'little')

            o = 0x30 + N
            # unknown2_1 = int.from_bytes(c[o:o+0x4], 'little')
            # unknown2_2 = int.from_bytes(c[o+0x4:o+0x8], 'little')
            # unknown2_3 = int.from_bytes(c[o+0x8:o+0xc], 'little')
            # unknown2_4 = int.from_bytes(c[o+0xc:o+0x10], 'little')
            index_buffer_offset = int.from_bytes(c[o+0x10:o+0x14], 'little')
            index_count = int.from_bytes(c[o+0x14:o+0x18], 'little')
            vertex_buffer_offset = int.from_bytes(c[o+0x18:o+0x1c], 'little')
            vertex_count = int.from_bytes(c[o+0x1c:o+0x20], 'little')

            # o = 0x30 + N + N
            # unknown3_1 = c[o:o+0x10].cast('f')
            # unknown3_2 = int.from_bytes(c[o+0x3c:o+0x40], 'little')
            texture_map_table = tuple( ObjGeoParser._make_texture_map(c[o:o+N])
                                       for o in texture_map_ofs_table )

    @staticmethod
    def _make_texture_map(m):
        map_id = int.from_bytes(m[:0x4], 'little')
        map_type = int.from_bytes(m[0x4:0x8], 'little')
        texture_buffer_index = int.from_bytes(m[0x8:0xc], 'little')
        # unknown1 = int.from_bytes(m[0x10:0x14], 'little')
        # unknown2 = int.from_bytes(m[0x14:0x18], 'little')
        # o = N
        # unknown3 = m[o:o+0x10].cast('I')
        # unknown4 = m[o+0x10:o+0x20].cast('f')
        # unknown5 = int.from_bytes(m[o+0x40:o+0x44], 'little')
        return TextureMap(map_id, map_type, texture_buffer_index)

class ObjGeoChunk(NamedTuple):
    chunk_id: int
    mtrcol_index: int
    geodecl_index: int
    soft_transparency: int
    hard_transparency: int
    index_buffer_offset: int
    index_count: int
    vertex_buffer_offset: int
    vertex_count: int
    texture_map_table: tuple[TextureMap]

class TextureMap(NamedTuple):
    map_id: int
    map_type: int
    texture_buffer_index: int

class GeoDeclParser:
    geodecl_chunks: tuple[GeoDeclChunk]

    def __init__(self, data):
        super().__init__(b'GeoDecl', data)
        self.geodecl_chunks = list(GeoDeclParser._gen_chunks(self.chunks))

    def _gen_chunks(chunks):
        for c in chunks:
            # self.unknown1 = int.from_bytes(c[0x0:0x4], 'little')
            self.struct_size = int.from_bytes(c[0x4:0x8], 'little')
            # self.unknown2 = int.from_bytes(c[0x8:0xc], 'little')
            self.index_buffer_index = int.from_bytes(c[0xc:0x10], 'little', signed=True)
            self.index_count = int.from_bytes(c[0x10:0x14], 'little')
            self.vertex_count = int.from_bytes(c[0x14:0x18], 'little')
            # self.unknown3 = int.from_bytes(c[0x8:0xc], 'little')

            o = self.struct_size
            self.vertex_buffer_index = int.from_bytes(self.c[o:o+4], 'little', signed=True)
            self.vertex_size = int.from_bytes(c[o+4:o+8], 'little', signed=True)
            unknown4_count = int.from_bytes(c[o+8:o+c], 'little')
            o1 = self.struct_size + -self.strcut_size % 0x10
            o2 = o1 + 8*unknown4_count
            self.vertices = tuple(GeoDecl._gen_d3dvertexelement9(data[o1:o2]))

    @staticmethod
    def _gen_d3dvertexelement9():
        for o in range(0, len(data), 8):
            stream = int.from_bytes(data[o:o+2], 'little')
            offset = int.from_bytes(data[o+2:o+4], 'little')
            d3d_decl_type = data[o+4]
            method = data[o+5]
            usage = data[o+6]
            usage_index = data[o+7]
            yield D3DVERTEXELEMENT9(stream, offset, d3d_decl_type,
                                    method, usage, usage_index)

    
class GeoDeclChunk(NamedTuple):
    struct_size: int
    index_buffer_index: int
    index_count: int
    vertex_count: int
    vertex_buffer_index: int
    vertex_size: int
    : tuple[D3DVERTEXELEMENT9]

class D3DVERTEXELEMENT9(NamedTuple):
    stream: int
    offset: int
    d3d_decl_type: int
    method: int
    usage: int
    usage_index: int

class TTDMParser(ContainerParser):
    def __init__(self, data):
        super().__init__(b'TTDM', data)

class TTDHParser(ContainerParser):
    ttdh_chunks: tuple[bool, int]

    def __init__(self, data):
        super().__init__(b'TTDH', data)
        self.ttdh_chunks = tuple(TTDHParser._gen_chunks(self.chunks))

    @staticmethod
    def _gen_chunks(chunks):
        for c in chunks:
            # If is_in_L is true, the index points to TTDL.
            # Otherwise, it points to TTDM.
            is_in_L = bool(c[0])
            index = int.from_bytes(c[0x4:0x8], 'little', signed=True)
            yield tuple(is_in_L, index)

class TTDLParser(ContainerParser):
    def __init__(self, data, ldata):
        super().__init__(b'TTDL', data, ldata)

class VtxLayParser(ContainerParser):
    def __init__(self, data, ldata = memoryview(b'')):
        super().__init__(b'VtxLay', data, ldata)

class IdxLayParser(ContainerParser):
    def __init__(self, data, ldata = memoryview(b'')):
        super().__init__(b'IdxLay', data, ldata)

class MtrColParser(ContainerParser):
    mtrcol_chunks: tuple[MtrColChunk]

    def __init__(self, data):
        super().__init__(b'MtrCol', data)
        self.mtrcol_chunks = tuple(MtrColParser._gen_chunks(self.chunks))

    @staticmethod
    def _gen_chunks(chunks):
        for c in chunks:
            colors = c[0:0xd0].cast('f')
            mtrcol_id = int.from_bytes(c[0xd0:0xd4], 'little', signed=True)
            xrefs_count = int.from_bytes(c[0xd4:0xd8], 'little')
            f = lambda x1, x2: ( int.from_bytes(x1, 'little', signed=True),
                                 int.from_bytes(x2, 'little') )
            xref = tuple( f(c[o:o+4], c[o+4:o+8])
                          for o in range(0xd8, 0xd8 + 8*xrefs_count, 8) )
            yield MtrColChunk(colors, mtrcol_id, xrefs)

class MtrColChunk(NamedTuple):
    colors: memoryview
    mtrcol_id: int
    # index, count
    xrefs: tuple[tuple[int, int]]

class MdlInfoParser(ContainerParser):
    mdlinfo_chunks: tuple[ObjInfoParser]

    def __init__(self, data):
        super().__init__(b'MdlInfo', data)
        self.mdlinfo_chunks = tuple( ObjInfoParser(c) for c in self.chunks )

class ObjInfoParser(ContainerParser):
    obj_id: int
    obj_type: int

    def __init__(self, data):
        super().__init__(b'ObjInfo', data)
        self.obj_id = int.from_bytes(self.opt_head[0x4:0x8], 'little', signed=True)
        self.obj_type = int.from_bytes(self.opt_head[0x8:0xc], 'little')

class HieLayParser(ContainerParser):
    hielay_chunks: tuple[HieLayChunk]

    def __init__(self, data):
        super().__init__(b'HieLay', data)
        self.hielay_chunks = tuple(HieLayParser._gen_chunks(self.chunks))

    @staticmethod
    def _gen_chunks(chunks):
        for c in chunks:
            matrix = c[0:0x40].cast('f')
            parent = int.from_bytes(c[0x40:0x44], 'little', signed=True)
            children_count = int.from_bytes(c[0x44:0x48], 'little')
            level = int.from_bytes(c[0x48:0x4c], 'little')
            n = children_count
            children = c[0x50:0x50+4*n].cast('i')
            yield HieLayChunk(matrix, parent, level, children)

class HieLayChunk(NamedTuple):
    matrix: memoryview
    parent: int
    level: int
    children: memoryview

class LHeaderParser(ContainerParser):
    mdlgeo: memoryview = memoryview(b'')
    ttdl: memoryview = memoryview(b'')
    vtxlay: memoryview = memoryview(b'')
    idxlay: memoryview = memoryview(b'')
    mtrcol: memoryview = memoryview(b'')
    mdlinfo: memoryview = memoryview(b'')
    hielay: memoryview = memoryview(b'')
    nodelay: memoryview = memoryview(b'')
    glblmtx: memoryview = memoryview(b'')
    bnofsmtx: memoryview = memoryview(b'')

    def __init__(self, data, ldata):
        super().__init__(b'LHeader', data, ldata)

        o1 = 0x20
        o2 = 0x20 + 4*len(self.chunks)
        chunk_type_id_table = self.opt_head[o1:o2].cast('I')
        for c, t in zip(self.chunks, chunk_type_id_table):
            match t:
                case 0xC000_0001:
                    self.mdlgeo = c
                case 0xC000_0002:
                    self.ttdl = c
                case 0xC000_0003:
                    self.vtxlay = c
                case 0xC000_0004:
                    self.idxlay = c
                case 0xC000_0005:
                    self.mtrcol = c
                case 0xC000_0006:
                    self.mdlinfo = c
                case 0xC000_0010:
                    self.hielay = c
                case 0xC000_0030:
                    self.nodelay = c
                case 0xC000_0040:
                    self.glblmtx = c
                case 0xC000_0050:
                    self.bnofsmtx = c
                case 0xC000_0060:
                    self.cpf = c
                case 0xC000_0070:
                    self.mcapack = c
                case 0xC000_0080:
                    self.renpack = c

class NodeLayParser(ContainerParser):
    nodelay_chunks: tuple[NodeObjParser]

    def __init__(self, data):
        super().__init__(b'NodeLay', data)
        self.nodelay_chunks = tuple( NodeObjParser(c) for c in self.chunks )

class NodeObjParser(ContainerParser):
    unknown1: int
    unknown2: int
    node_id1: int
    name: bytes
    obj_id: int
    nodes_count: int
    node_id2: int
    matrix: memoryview
    nodes: memoryview

    def __init__(self, data):
        super().__init__(b'NodeObj', data)
        self.unknown1 = int.from_bytes(self.opt_head[0x0:0x4], 'little')
        self.unknown2 = int.from_bytes(self.opt_head[0x4:0x8], 'little', signed=True)
        self.node_id1 = int.from_bytes(self.opt_head[0x8:0xc], 'little')
        self.name = bytes(self.opt_head[0x10:]).partition(b'\x00')[0]
        if self.chunks:
            c = self.chunks[0]
            self.obj_id = int.from_bytes(c[0x0:0x4], 'little', signed=True)
            self.nodes_count = int.from_bytes(c[0x4:0x8], 'little', signed=True)
            self.node_id2 = int.from_bytes(c[0x8:0xc], 'little', signed=True)
            self.matrix = c[0x10:0x50].cast('f')
            self.nodes = c[0x50:0x50+4*self.nodes_count].cast('i')

class GlblMtxParser(ContainerParser):
    def __init__(self, data):
        super().__init__(b'GlblMtx', data)
        self.glblmtx_chunks = tuple( c.cast('f') for c in self.chunks )

class BnOfsMtxParser(ContainerParser):
    def __init__(self, data):
        super().__init__(b'BnOfsMtx', data)
        self.bnofsmtx_chunks = tuple( c.cast('f') for c in self.chunks )

class MdlGeo:
    objgeo: list[ObjGeo]
    mtrcol: MtrCol

    @classmethod
    def from_bytes(cls, data):
        parser = MdlGeoParser(data)
        instance = cls()
        instance.objgeo = list(MdlGeo._gen_objgeo(parser.chunks))
        return instance

    @staticmethod
    def _gen_objgeo(chunks):
        for c in chunks:
            yield ObjGeo()

    def __bytes__(self):
        return serialize(b'MdlGeo', MdlGeo._gen_objgeo_chunks())

    @staticmethod
    def _gen_mdlgeo_chunks(objgeo):
        for i, o in enumerate(objgeo):
            opt_head = bytearray(0x20)
            opt_head[:0x4] = 0x0300_0100.to_bytes(4)
            opt_head[0x4:0x8] = i.to_bytes(4, 'little')
            opt_head += o.name + b'\x00'
            yield serialize(b'ObjGeo', chunks, opt_head = opt_head,
                            sub_container = bytes(o.geodecl))

    def _gen_objgeo_chunks
class ObjGeo:
    name: bytes
    geodecl: GeoDecl

@dataclass
class ObjGeoData:
    mtrcol_data: array
    geodecl_data: GeoDeclData
    soft_transparency: int
    hard_transparency: int
    index_buffer_offset: int
    index_count: int
    vertex_buffer_offset: int
    vertex_count: int
    texture_map_table: tuple[TextureMap]

class GeoDecl:
    vtxlay: VtxLay
    idxlay: IdxLay

    def __bytes__(self):
        yield serialize(b'GeoDecl', GeoDecl._gen_chunks(self.data))

    @staticmethod
    def _gen_chunks(data):
        D = { id(v):i for i,v in enumerate(idxlay.buffer) }
        for d in data:
            B = bytearray(d.chunk)
            # i = D[id(c.index_buffer)]
            # B[0xc:0x10] = i.to_bytes(4, 'little')
            # B[0x10:0x14] = len(c.index_buffer).to_bytes(4, 'little')
            # B[0x14:0x18] = (len(c.vertex_buffer)//c.vertex_size).to_bytes(4, 'little')
            # B[0x38:0x3c] = i.to_bytes(4, 'little')
            yield B

@dataclass
class GeoDeclData:
    index_buffer: array
    vertex_buffer: array
    vertex_size: int

class TTDM:
    textures: list[bytes]

    @classmethod
    def from_bytes(cls, data, ldata):
        parser = TTDMParser(data)
        ttdl_parser = TTDLParser(parser.sub_container, ldata)
        instance = cls()
        instance.textures = [ bytes(c) for c in ttdl_parser.chunks ]
        return instance

    def __bytes__(self):
        opt_head = serialize(b'TTDH', TTDM._gen_ttdh_chunks(self.textures), opt_head = b'\x01')
        sub_container = serialize(b'TTDL', self.textures, chunks_in_L = True)
        return serialize(b'TTDM', (), opt_head = opt_head, sub_container = sub_container)

    @staticmethod
    def _gen_ttdh_chunks(textures):
        for i, t in enumerate(textures):
            B = bytearray(0x20)
            B[0x0] = 1
            B[0x4:0x8] = i.to_bytes(4, 'little', signed=True)
            yield B

    def __bytesL(self):
        return serializeL(self.textures)

    def _chunks(self):
        return self.textures

class VtxLay:
    buffers: list[array]

    @classmethod
    def from_bytes(cls, data, ldata = b''):
        parser = VtxLayParser(memoryview(data), memoryview(ldata))
        instance = cls()
        instance.buffers = [ array('B', c) for c in parser.chunks ]
        return instance

    def __bytes__(self):
        return serialize(b'VtxLay', self._chunks(), chunks_in_L = True)

    def __bytesL(self):
        return serializeL(self._chunks())

    def _chunks(self):
        return ( bytes(b) for b in self.buffers )

class IdxLay:
    buffers: list[array]

    @classmethod
    def from_bytes(cls, data, ldata = b''):
        parser = IdxLayParser(memoryview(data), memoryview(ldata))
        instance = cls()
        instance.buffers = [ array('h', c.cast('h')) for c in parser.chunks ]
        return instance

    def __bytes__(self):
        return serialize(b'IdxLay', self._chunks(), chunks_in_L = True)

    def __bytesL(self):
        return serializeL(self._chunks())

    def _chunks(self):
        return ( bytes(b) for b in self.buffers )

class MtrCol:
    # float array[34]
    data: list[array]
    mdlgeo: MdlGeo | None

    @classmethod
    def from_bytes(cls, data):
        parser = MtrColParser(memoryview(data))
        instance = cls()
        instance.data = [ array('f', c.colors) for c in parser.chunks ]
        instance.mdlgeo = None
        return instance

    def __bytes__(self):
        chunks = MtrCol._gen_chunks(self.data, self.mdlgeo)
        return serialize(b'MtrCol', chunks)

    @staticmethod
    def _gen_chunks(data, xref):
        for i, d in enumerate(data):
            B = bytearray(0xd8 + 8*len(xref))
            B[0x0:0xd0] = bytes(d)
            B[0xd0:0xd4] = i.to_bytes(4, 'little')
            B[0xd4:0xd8] = len(xref).to_bytes(4, 'little')
            for o, (i, j) in zip(range(0xd8, len(B), 8), xref):
                B[o:o+4] = i
                B[o+4:o+8] = j
            yield B

class MdlInfo:
    objinfo: list[ObjInfo]

    def __init__(self):
        self.objinfo = []

    @classmethod
    def from_bytes(cls, data):
        parser = MdlInfoParser(memoryview(data))
        instance = cls()
        instance.objinfo = [ ObjInfo(o.obj_type, bytes(o.opt_head),
                                     [ bytes(c) for c in o.chunks ])
                             for o in parser.mdlinfo_chunks ]
        return instance

    def __bytes__(self):
        chunks = MdlInfo._gen_chunks(self.objinfo)
        return serialize(b'MdlInfo', chunks)

    @staticmethod
    def _gen_chunks(objinfo):
        for i, o in enumerate(objinfo):
            opt_head = bytearray(o._opt_head.rjust(0x10, b'\x00'))
            opt_head[0x0:0x4] = 0x0300_0200.to_bytes(4)
            opt_head[0x4:0x8] = i.to_bytes(4, 'little')
            opt_head[0xc:0x10] = o.obj_type.to_bytes(4, 'little')
            yield serialize(b'ObjInfo', o._chunks, opt_head = opt_head)

@dataclass
class ObjInfo:
    obj_type: int = 0
    _opt_head: bytes = b''
    _chunks: list[bytes] = field(default_factory=list)

class HieLay:
    nodes: list[HieLayNode]

    def __init__(self):
        self.nodes = []

    @classmethod
    def from_bytes(cls, data):
        parser = HieLayParser(memoryview(data))
        instance = cls()
        instance.nodes = list(HieLay._gen_nodes(parser.chunks))
        return instance

    @staticmethod
    def _gen_nodes(chunks):
        N = tuple( HieLayNode() for _ in chunks )
        CP = tuple( HieLayChunkParser(c) for c in chunks )
        for i, n in enumerate(N):
            cp = CP[i]
            n.matrix = array('f', cp.matrix)
            p = cp.parent
            n.parent =  (p != -1 and N[p]) or None
            n.children = { N[j] for j, cp in enumerate(CP)
                           if cp.parent == i }
            yield n

    def __bytes__(self):
        chunks = HieLay._gen_chunks(self.nodes)
        sub_container = bytearray(0x20)
        sub_container[0x0:0x4] = (0x1).to_bytes(4, 'little')
        sub_container[0x10:0x14] = (0x2).to_bytes(4, 'little')
        return serialize(b'HieLay', chunks, sub_container=sub_container)

    @staticmethod
    def _gen_chunks(nodes):
        D = { v:i for i,v in enumerate(nodes) }
        for n in nodes:
            B = bytearray(0x50 + 4*len(n.children))

            B[0x0:0x40] = bytes(n.matrix)

            i = (n.parent and D[n.parent]) or -1
            B[0x40:0x44] = i.to_bytes(4, 'little', signed=True)
            B[0x44:0x48] = len(n.children).to_bytes(4, 'little')

            level = 0
            p = n.parent
            while p:
                level += 1
                p = p.parent
            B[0x48:0x4c] = level.to_bytes(4, 'little')

            for o, i in zip(range(0x50, len(B), 4), sorted( D[c] for c in n.children )):
                B[o:o+4] = i.to_bytes(4, 'little')
            yield B

class HieLayNode:
    matrix: array
    parent: Self | None
    children: set[Self]

    def __init__(self):
        self.matrix = array('f', bytes(0x40))
        self.parent = None
        self.children = set()

class LHeader:
    data: list

    def __init__(self):
        self.data = []

    def __bytes__(self):
        chunks = ( d._chunks() for d in self.data )
        opt_head = bytearray(0x20 + 4*len(self.data))
        opt_head[0] = 0x3
        for o, d in zip(range(0x20, len(opt_head), 4), self.data):
            match d:
                case TTDL():
                    opt_head[o:o+4] = 0xc000_0002
                case VtxLay():
                    opt_head[o:o+4] = 0xc000_0003
                case IdxLay():
                    opt_head[o:o+4] = 0xc000_0004
        return serialize(b'LHeader', chunks, chunks_in_L = True, opt_head = opt_head)

    def __bytesL(self):
        return serializeL( d._chunks() for d in self.data )

class NodeLay:
    nodeobjs: list[NodeObj]

    def __init__(self):
        self.nodeobjs = []

    @classmethod
    def from_bytes(cls, data):
        parser = NodeLayParser(memoryview(data))
        instance = cls()
        instance.nodeobjs = list( NodeLay._gen_nodeobj(parser.chunks) )
        for n, c in zip(instance.nodeobjs, parser.chunks):
            n.nodes = set( instance.nodeobjs[i] for i in NodeObjParser(c).nodes )
        return instance

    @staticmethod
    def _gen_nodeobj(chunks):
        for c in chunks:
            parser = NodeObjParser(c)
            n = NodeObj()
            n.name = parser.name
            n.matrix = array('f', parser.matrix)
            yield n

    def __bytes__(self):
        chunks = NodeLay._gen_chunks(self.nodeobjs)
        opt_head = 0x0100_0200.to_bytes(4)
        return serialize(b'NodeLay', chunks, opt_head = opt_head)

    @staticmethod
    def _gen_chunks(nodeobjs):
        obj_id = 0
        D = { v:i for i,v in enumerate(nodeobjs) }
        for node_id, n in enumerate(nodeobjs):
            if n.matrix:
                B = bytearray(0x50 + 4*len(n.nodes))
                B[0x0:0x4] = obj_id.to_bytes(4, 'little', signed=True)
                B[0x4:0x8] = len(n.nodes).to_bytes(4, 'little')
                B[0x8:0xc] = node_id.to_bytes(4, 'little', signed=True)
                B[0x10:0x50] = bytes(n.matrix)
                for o, i in zip(range(0x50, len(B), 4), sorted( D[m] for m in n.nodes )):
                    B[o:o+4] = i.to_bytes(4, 'little', signed=True)
                chunks = (B,)
                obj_id += 1
            else:
                chunks = ()

            opt_head = bytearray(0x10)
            opt_head[0x4:0x8] = (-1).to_bytes(4, signed=True)
            opt_head[0x8:0xc] = node_id.to_bytes(4, 'little', signed=True)
            opt_head += n.name + b'\x00'
            yield serialize(b'NodeObj', chunks, opt_head=opt_head)
        
class NodeObj:
    name: bytes
    # 4x4 float matrix
    matrix: array
    nodes: set[Self]

    def __init__(self):
        self.name = b''
        self.matrix = array('f')
        self.nodes = set()

class GlblMtx:
    # 4x4 float matrix
    matrices: list[array]
    def __init__(self):
        self.matrices = []

    @classmethod
    def from_bytes(cls, data):
        parser = GlblMtxParser(memoryview(data))
        instance = cls()
        instance.matrices = [ array('f', c) for c in parser.glblmtx_chunks ]
        return instance

    def __bytes__(self):
        chunks = ( bytes(m) for m in self.matrices )
        return serialize(b'GlblMtx', chunks)

class BnOfsMtx:
    # 4x4 float matrix
    matrices: list[array]

    @classmethod
    def from_bytes(cls, data):
        parser = BnOfsMtxParser(memoryview(data))
        instance = cls()
        instance.matrices = [ array('f', c) for c in parser.bnofsmtx_chunks ]
        return instance

    def __bytes__(self):
        chunks = ( bytes(m) for m in self.matrices )
        return serialize(b'BnOfsMtx', chunks)

def serialize(magic_bytes, chunks, /, chunks_in_L = False, opt_head = b'', sub_container = b''):
    chunks = tuple( memoryview(c) for c in chunks )
    sub_container = memoryview(sub_container)
    opt_head = memoryview(opt_head)
    chunks_in_L = bool(chunks_in_L)

    head_size = (chunks_in_L and 0x50) or 0x30

    opt_head_size = opt_head.nbytes + -opt_head.nbytes % 0x10
    chunk_ofs_table_size = 4*len(chunks) + -4*len(chunks) % 0x10
    chunk_size_table_size = chunk_ofs_table_size * chunks_in_L #any( c.nbytes % 0x10 for c in chunks )
    sub_container_size = sub_container.nbytes + -sub_container.nbytes % 0x10
    chunk_sizes = tuple( c.nbytes + -c.nbytes % 0x10 for c in chunks )
    total_chunk_size = sum(chunk_sizes)
    container_size = ( head_size
                       + opt_head_size
                       + chunk_ofs_table_size
                       + chunk_size_table_size
                       + sub_container_size
                       + bool(not chunks_in_L) * total_chunk_size )
    B = bytearray(container_size)
    B[0:8] = magic_bytes.ljust(8, b'\x00')
    B[0x8:0xc] = 0x00000101.to_bytes(4)
    B[0xc:0x10] = head_size.to_bytes(4, 'little')
    B[0x10:0x14] = container_size.to_bytes(4, 'little')
    B[0x14:0x18] = len(chunks).to_bytes(4, 'little')
    valid_chunk_count = sum( n > 0 for n in chunk_sizes )
    B[0x18:0x1c] = valid_chunk_count.to_bytes(4, 'little')

    n = head_size + opt_head_size
    chunk_ofs_table_ofs = n * bool(chunk_ofs_table_size)
    B[0x20:0x24] = chunk_ofs_table_ofs.to_bytes(4, 'little')
    n += chunk_ofs_table_size
    chunk_size_table_ofs = n * bool(chunk_size_table_size)
    B[0x24:0x28] = chunk_size_table_ofs.to_bytes(4, 'little')
    n += chunk_size_table_size
    sub_container_ofs = n * bool(sub_container)
    B[0x28:0x2c] = sub_container_ofs.to_bytes(4, 'little')

    if chunks_in_L:
        B[0x40:0x44] = valid_chunk_count.to_bytes(4, 'little')
        lcontainer_size = 0x10 + opt_head_size + total_chunk_size
        B[0x44:0x48] = lcontainer_size.to_bytes(4, 'little')
        B[0x48:0x4c] = (0x01234567).to_bytes(4, 'little')

    if opt_head:
        o1 = head_size
        o2 = o1 + opt_head.nbytes
        B[o1:o2] = bytes(opt_head)

    if chunk_ofs_table_ofs:
        x = ( chunks_in_L
              and 0x10 + opt_head_size
              or ( chunk_ofs_table_ofs
                   + chunk_ofs_table_size
                   + chunk_size_table_size
                   + sub_container_size ) )
        for i, c in enumerate(chunks):
            o = chunk_ofs_table_ofs + 4*i
            n = chunk_sizes[i]
            B[o:o+4] = (bool(n) * x).to_bytes(4, 'little')
            x += n

    if chunk_size_table_ofs:
        for i, c in enumerate(chunks):
            o = chunk_size_table_ofs + 4*i
            B[o:o+4] = c.nbytes.to_bytes(4, 'little')

    if sub_container:
        o1 = sub_container_ofs
        o2 = o1 + sub_container.nbytes
        B[o1:o2] = bytes(sub_container)

    if not chunks_in_L and chunks:
        o1 = chunk_ofs_table_ofs
        o2 = o1 + 4*len(chunks)
        O = memoryview(B[o1:o2]).cast('I')
        for o1, c in zip(O, chunks):
            o2 = o1 + c.nbytes
            B[o1:o2] = bytes(c)

    return bytes(B)

def serializeL(chunks, opt_head = b''):
    chunks = tuple( memoryview(c) for c in chunks )
    opt_head = memoryview(opt_head)

    opt_head_size = opt_head.nbytes + -opt_head.nbytes % 0x10
    chunk_sizes = tuple( c.nbytes + -c.nbytes % 0x10 for c in chunks )
    total_chunk_size = sum(chunk_sizes)

    lcontainer_size = 0x10 + opt_head_size + total_chunk_size
    B = bytearray(lcontainer_size)
    B[0x0:0x4] = sum( n > 0 for n in chunk_sizes ).to_bytes(4, 'little')
    B[0x4:0x8] = lcontainer_size.to_bytes(4, 'little')
    B[0x8:0xc] = (0x01234567).to_bytes(4, 'little')

    o = 0x10 + opt_head_size
    for c, n in zip(chunks, chunk_sizes):
        o2 = o+c.nbytes
        B[o:o2] = c
        o += n

    return bytes(B)

def bytesL(container):
    return getattr(container, '_' + container.__class__.__name__ + '__bytesL')()
