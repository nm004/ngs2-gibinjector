# NINJA GAIDEN Master Collection Scripts by Nozomi Miyamori
# is marked with CC0 1.0. This file is a part of NINJA GAIDEN
# Master Collection Scripts.
#
# This module is for reading/writing container format that is
# used by some Team Ninja's (Koei-Tecmo) games such as NINJA GAIDEN
# Master Collection and Dead or Alive 5 Last Round.

from __future__ import annotations
from . import sdp1
from typing import NamedTuple
from operator import indexOf

class ContainerParser:
    meta_data: memoryview
    _meta_data: memoryview
    sub_container: memoryview
    _sub_container: memoryview
    chunks: tuple[memoryview]
    _chunks: tuple[memoryview]

    def __init__(self, magic, data, ldata = b''):
        data = memoryview(data)
        ldata = memoryview(ldata)

        if (x := bytes(data[0:8])) != magic.ljust(8, b'\x00'):
            raise ValueError('data has wrong magic bytes'
                             f' ("{x.decode()}" != "{magic.decode()}").')

        if (x := int.from_bytes(data[0x8:0xc])) != 0x0000_0101:
            raise ValueError(f'not supported verison "{x:04X}"')
        head_size = int.from_bytes(data[0xc:0x10], 'little')
        container_size = int.from_bytes(data[0x10:0x14], 'little')

        data = data[:container_size].toreadonly()

        chunk_count = int.from_bytes(data[0x14:0x18], 'little')
        # valid_chunk_count = int.from_bytes(data[0x18:0x1c], 'little')
        chunk_ofs_table_ofs = int.from_bytes(data[0x20:0x24], 'little')
        chunk_size_table_ofs = int.from_bytes(data[0x24:0x28], 'little')
        sub_container_ofs =  int.from_bytes(data[0x28:0x2c], 'little')

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
        ldata = ldata[:lcontainer_size].toreadonly()

        o1 = chunk_ofs_table_ofs
        o2 = bool(o1) * (o1 + 4*chunk_count)
        chunk_ofs_table = data[o1:o2].cast('I')

        o1 = chunk_size_table_ofs
        o2 = bool(o1) * (o1 + 4*chunk_count)
        chunk_size_table = data[o1:o2].cast('I')

        o1 = head_size
        o2 = ( chunk_ofs_table_ofs
               or chunk_size_table_ofs
               or sub_container_ofs
               or container_size )
        self._meta_data = data[o1:o2]
        self.meta_data = self._meta_data
        
        o1 = sub_container_ofs
        o2 = bool(o1) * ( chunk_ofs_table
                          and chunk_ofs_table[0]
                          or container_size )
        self._sub_container = data[o1:o2]
        self.sub_container = self._sub_container

        D = (are_chunks_in_L and ldata) or data
        O = chunk_ofs_table
        S = chunk_size_table
        self._chunks = tuple(ContainerParser._gen_chunks(D, O, S))
        self.chunks = self._chunks

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
    mdlgeo: MdlGeoParser | None = None
    ttdm: TTDMParser | None = None
    vtxlay: VtxLayParser | None = None
    idxlay: IdxLayParser | None = None
    mtrcol: MtrColParser | None = None
    mdlinfo: MdlInfoParser | None = None
    hielay: HieLayParser | None = None
    lheader: LHeaderParser
    nodelay: NodeLayParser | None = None
    glblmtx: GlblMtxParser | None = None
    bnofsmtx: BnOfsMtxParser | None = None
    cpf: cpfParser | None = None
    mcapack: MCAPACKParser | None = None
    renpack: RENPACKParser | None = None
    collide: memoryview | None = None
    mtrlchng: memoryview | None = None
    effcnf: memoryview | None = None
    acscls: memoryview | None = None
    epm1: sdp1.EPM1Parser | None = None

    def __init__(self, data, ldata):
        super().__init__(b'TMC', data)

        o1 = 0xc0
        o2 = 0xc0 + 4*len(self.chunks)

        chunk_type_id_table = self.meta_data[o1:o2].cast('I')
        i = indexOf(chunk_type_id_table, 0x8000_0020)
        self.lheader = LHeaderParser(self.chunks[i], ldata)

        for t, c in zip(chunk_type_id_table, self.chunks):
            match t:
                case 0x4:
                    self.collide = c
                case 0x5:
                    self.mtrlchng = c
                case 0x6:
                    self.effcnf = c
                case 0x9:
                    self.acscls = c
                case 0x45_50_4d_31:
                    # EPM1
                    self.epm1 = c and sdp1.EPM1Parser(c) or None
                case 0x8000_0001:
                    self.mdlgeo = c and MdlGeoParser(c, self.lheader.mdlgeo) or None
                case 0x8000_0002:
                    self.ttdm = c and TTDMParser(c, self.lheader.ttdm) or None
                case 0x8000_0003:
                    self.vtxlay = c and VtxLayParser(c, self.lheader.vtxlay) or None
                case 0x8000_0004:
                    self.idxlay = c and IdxLayParser(c, self.lheader.idxlay) or None
                case 0x8000_0005:
                    self.mtrcol = c and MtrColParser(c, self.lheader.mtrcol) or None
                case 0x8000_0006:
                    self.mdlinfo = c and MdlInfoParser(c, self.lheader.mdlinfo) or None
                case 0x8000_0010:
                    self.hielay = c and HieLayParser(c, self.lheader.hielay) or None
                case 0x8000_0030:
                    self.nodelay = c and NodeLayParser(c, self.lheader.nodelay) or None
                case 0x8000_0040:
                    self.glblmtx = c and GlblMtxParser(c, self.lheader.glblmtx) or None
                case 0x8000_0050:
                    self.bnofsmtx = c and BnOfsMtxParser(c, self.lheader.bnofsmtx) or None
                case 0x8000_0060:
                    self.cpf = c and cpfParser(c) or None
                case 0x8000_0070:
                    self.mcapack = c and MCAPACKParser(c) or None
                case 0x8000_0080:
                    self.renpack = c and RENPACKParser(c) or None
        self.name = bytes(self.meta_data[0x20:0x30]).partition(b'\x00')[0]

class MdlGeoParser(ContainerParser):
    chunks: tuple[ObjGeoParser]

    def __init__(self, data, ldata = b''):
        super().__init__(b'MdlGeo', data)
        self.chunks = tuple( ObjGeoParser(c) for c in self.chunks )

class ObjGeoParser(ContainerParser):
    meta_data: ObjGeoMetaData
    sub_container: GeoDeclParser
    geodecl: GeoDeclParser
    chunks: tuple[ObjGeoChunk]

    def __init__(self, data):
        super().__init__(b'ObjGeo', data)
        objgeo_id = int.from_bytes(self.meta_data[0x4:0x8], 'little', signed=True)
        name = bytes(self.meta_data[0x20:]).partition(b'\x00')[0]
        self.meta_data = ObjGeoMetaData(objgeo_id, name)
        self.geodecl = self.sub_container = GeoDeclParser(self.sub_container)
        self.chunks = tuple(ObjGeoParser._gen_chunks(self.chunks))

    @staticmethod
    def _gen_chunks(chunks):
        for c in chunks:
            # NINJA GAIDEN SIGMA2 has more members than DOA5LR (+16 bytes)

            chunk_id = int.from_bytes(c[0x0:0x4], 'little', signed=True)
            mtrcol_index = int.from_bytes(c[0x4:0x8], 'little', signed=True)
            texture_map_count = int.from_bytes(c[0xc:0x10], 'little')
            texture_map_ofs_table = c[0x10:0x10+4*texture_map_count].cast('I')

            # 0x20:0x40 written by the application

            geodecl_index = int.from_bytes(c[0x38:0x3c], 'little')
            transparent1 = int.from_bytes(c[0x40:0x44], 'little')
            unknown_0x44 = int.from_bytes(c[0x44:0x48], 'little')
            transparent2 = int.from_bytes(c[0x48:0x4c], 'little')
            unknown_0x4c = int.from_bytes(c[0x4c:0x50], 'little')

            # 0x50:0x60 written by the application

            unknown_0x60 = int.from_bytes(c[0x60:0x64], 'little')
            unknown_0x64 = int.from_bytes(c[0x64:0x68], 'little')
            unknown_0x68 = int.from_bytes(c[0x68:0x6c], 'little')
            unknown_0x6c = int.from_bytes(c[0x6c:0x70], 'little')
            unknown_0x70 = int.from_bytes(c[0x70:0x74], 'little')
            two_sided = bool(c[0x74])
            index_buffer_offset = int.from_bytes(c[0x78:0x7c], 'little')
            index_count = int.from_bytes(c[0x7c:0x80], 'little')
            vertex_buffer_offset = int.from_bytes(c[0x80:0x84], 'little')
            vertex_count = int.from_bytes(c[0x84:0x88], 'little')

            # unknown = int.from_bytes(c[0x88:0x8c], 'little')
            # unknown = int.from_bytes(c[0x8c:0x90], 'little')
            # unknown = int.from_bytes(c[0x90:0x94], 'little')
            texture_map_table = ( c[o:o+0x7c] for o in texture_map_ofs_table )
            texture_map_table = tuple(ObjGeoParser._gen_texture_maps(texture_map_table))
            yield ObjGeoChunk(chunk_id, mtrcol_index,
                              geodecl_index,
                              transparent1, unknown_0x44, transparent2, unknown_0x4c,
                              unknown_0x60, unknown_0x64, unknown_0x68, unknown_0x6c,
                              unknown_0x70, two_sided, index_buffer_offset, index_count,
                              vertex_buffer_offset, vertex_count, texture_map_table)

    @staticmethod
    def _gen_texture_maps(texture_map_table):
        # NINJA GAIDEN SIGMA2 has more members than DOA5LR (+12 bytes)
        for m in texture_map_table:
            map_id = int.from_bytes(m[:0x4], 'little')
            usage = int.from_bytes(m[0x4:0x8], 'little')
            texture_buffer_index = int.from_bytes(m[0x8:0xc], 'little')
            unknown_0x10 = int.from_bytes(m[0x10:0x14], 'little')
            unknown_0x14 = int.from_bytes(m[0x14:0x18], 'little')
            # unknown_0x = m[:0x10].cast('I')
            # unknown_0x = m[0x10:0x20].cast('f')
            unknown_0x78 = int.from_bytes(m[0x78:0x7c], 'little')
            yield TextureMap(map_id, usage, texture_buffer_index,
                             unknown_0x10, unknown_0x14,
                             unknown_0x78)

class ObjGeoMetaData(NamedTuple):
    obj_id: int
    name: bytes
    
class ObjGeoChunk(NamedTuple):
    chunk_id: int
    mtrcol_index: int
    geodecl_index: int
    transparent1: int
    unknown_0x44: int
    transparent2: int
    unknown_0x4c: int

    unknown_0x60: int
    unknown_0x64: int
    unknown_0x68: int
    unknown_0x6c: int
    unknown_0x70: int
    two_sided: bool
    index_buffer_offset: int
    index_count: int
    vertex_buffer_offset: int
    vertex_count: int
    texture_map_table: tuple[TextureMap]

class TextureMap(NamedTuple):
    map_id: int
    usage: int
    texture_buffer_index: int
    unknown_0x10: int
    unknown_0x14: int
    unknown_0x78: int

class GeoDeclParser(ContainerParser):
    chunks: tuple[GeoDeclChunk]

    def __init__(self, data):
        super().__init__(b'GeoDecl', data)
        self.chunks = tuple(GeoDeclParser._gen_chunks(self.chunks))

    @staticmethod
    def _gen_chunks(chunks):
        for c in chunks:
            # self.unknown1 = int.from_bytes(c[0x0:0x4], 'little')
            struct_size = int.from_bytes(c[0x4:0x8], 'little')
            # self.unknown2 = int.from_bytes(c[0x8:0xc], 'little')
            index_buffer_index = int.from_bytes(c[0xc:0x10], 'little', signed=True)
            index_count = int.from_bytes(c[0x10:0x14], 'little')
            vertex_count = int.from_bytes(c[0x14:0x18], 'little')
            # self.unknown3 = int.from_bytes(c[0x8:0xc], 'little')

            o = struct_size
            vertex_buffer_index = int.from_bytes(c[o:o+4], 'little', signed=True)
            vertex_size = int.from_bytes(c[o+4:o+8], 'little', signed=True)
            vertex_format_count = int.from_bytes(c[o+0x8:o+0xc], 'little')
            o1 = struct_size + 0x18
            o2 = o1 + 8*vertex_format_count
            vertex_format = tuple(GeoDeclParser._gen_d3dvertexelement9(c[o1:o2]))
            yield GeoDeclChunk(index_buffer_index, index_count,
                               vertex_count, vertex_buffer_index, vertex_size,
                               vertex_format)

    @staticmethod
    def _gen_d3dvertexelement9(data):
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
    index_buffer_index: int
    index_count: int
    vertex_count: int
    vertex_buffer_index: int
    vertex_size: int
    vertex_format: tuple[D3DVERTEXELEMENT9]

class D3DVERTEXELEMENT9(NamedTuple):
    stream: int
    offset: int
    d3d_decl_type: int
    method: int
    usage: int
    usage_index: int

class TTDMParser(ContainerParser):
    meta_data: TTDHParser
    ttdh: TTDHParser
    sub_container: TTDLParser
    ttdl: TTDLParser

    def __init__(self, data, ldata):
        super().__init__(b'TTDM', data)
        self.ttdh = self.meta_data = TTDHParser(self.meta_data)
        self.ttdl = self.sub_container = TTDLParser(self.sub_container, ldata)

class TTDHParser(ContainerParser):
    chunks: tuple[tuple[bool, int]]

    def __init__(self, data):
        super().__init__(b'TTDH', data)
        self.chunks = tuple(TTDHParser._gen_chunks(self.chunks))

    @staticmethod
    def _gen_chunks(chunks):
        for c in chunks:
            # If is_in_L is true, the index points to TTDL.
            # Otherwise, it points to TTDM.
            is_in_L = bool(c[0])
            index = int.from_bytes(c[0x4:0x8], 'little', signed=True)
            yield TTDHChunk(is_in_L, index)

class TTDHChunk(NamedTuple):
    is_in_L: bool
    index: int

class TTDLParser(ContainerParser):
    def __init__(self, data, ldata):
        super().__init__(b'TTDL', data, ldata)

class VtxLayParser(ContainerParser):
    def __init__(self, data, ldata = b''):
        super().__init__(b'VtxLay', data, ldata)

class IdxLayParser(ContainerParser):
    def __init__(self, data, ldata = b''):
        super().__init__(b'IdxLay', data, ldata)
        self.chunks = tuple( c.cast('h') for c in self.chunks )

class MtrColParser(ContainerParser):
    chunks: tuple[MtrColChunk]

    def __init__(self, data, ldata = b''):
        super().__init__(b'MtrCol', data)
        self.chunks = tuple(MtrColParser._gen_chunks(self.chunks))

    @staticmethod
    def _gen_chunks(chunks):
        for c in chunks:
            colors = c[0:0xd0].cast('f')
            mtrcol_id = int.from_bytes(c[0xd0:0xd4], 'little', signed=True)
            xrefs_count = int.from_bytes(c[0xd4:0xd8], 'little')
            f = lambda x1, x2: ( int.from_bytes(x1, 'little', signed=True),
                                 int.from_bytes(x2, 'little') )
            xrefs = tuple( f(c[o:o+4], c[o+4:o+8])
                          for o in range(0xd8, 0xd8 + 8*xrefs_count, 8) )
            yield MtrColChunk(colors, mtrcol_id, xrefs)

class MtrColChunk(NamedTuple):
    colors: memoryview
    mtrcol_id: int
    # index, count
    xrefs: tuple[tuple[int, int]]

class MdlInfoParser(ContainerParser):
    chunks: tuple[ObjInfoParser]

    def __init__(self, data, ldata = b''):
        super().__init__(b'MdlInfo', data)
        self.chunks = tuple( ObjInfoParser(c) for c in self.chunks )

class ObjInfoParser(ContainerParser):
    meta_data: ObjInfoMetaData

    def __init__(self, data):
        super().__init__(b'ObjInfo', data)
        obj_id = int.from_bytes(self.meta_data[0x4:0x8], 'little', signed=True)
        obj_type = int.from_bytes(self.meta_data[0xc:0x10], 'little')
        self.meta_data = ObjInfoMetaData(obj_id, obj_type)

class ObjInfoMetaData(NamedTuple):
    obj_id: int
    obj_type: int

class HieLayParser(ContainerParser):
    chunks: tuple[HieLayChunk]

    def __init__(self, data, ldata = b''):
        super().__init__(b'HieLay', data)
        self.chunks = tuple(HieLayParser._gen_chunks(self.chunks))

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
    ttdm: memoryview = memoryview(b'')
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
        chunk_type_id_table = self.meta_data[o1:o2].cast('I')
        for c, t in zip(self.chunks, chunk_type_id_table):
            match t:
                case 0xC000_0001:
                    self.mdlgeo = c
                case 0xC000_0002:
                    self.ttdm = c
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
    chunks: tuple[NodeObjParser]

    def __init__(self, data, ldata = b''):
        super().__init__(b'NodeLay', data)
        self.chunks = tuple( NodeObjParser(c) for c in self.chunks )

class NodeObjParser(ContainerParser):
    unknown1: int
    master: int
    name: bytes
    chunks: tuple[NodeObjChunk]

    def __init__(self, data):
        super().__init__(b'NodeObj', data)
        self.unknown1 = int.from_bytes(self.meta_data[0x0:0x4], 'little')
        self.master = int.from_bytes(self.meta_data[0x4:0x8], 'little', signed=True)
        self.node_id = int.from_bytes(self.meta_data[0x8:0xc], 'little')
        self.name = bytes(self.meta_data[0x10:]).partition(b'\x00')[0]
        if self.chunks:
            c = self.chunks[0]
            obj_id = int.from_bytes(c[0x0:0x4], 'little', signed=True)
            nodes_count = int.from_bytes(c[0x4:0x8], 'little', signed=True)
            node_id = int.from_bytes(c[0x8:0xc], 'little', signed=True)
            matrix = c[0x10:0x50].cast('f')
            nodes = c[0x50:0x50+4*nodes_count].cast('i')
            self.chunks = (NodeObjChunk(obj_id, node_id, matrix, nodes),)
            

class NodeObjChunk(NamedTuple):
    obj_id: int
    node_id: int
    matrix: memoryview
    nodes: int
    
class GlblMtxParser(ContainerParser):
    def __init__(self, data, ldata = memoryview(b'')):
        super().__init__(b'GlblMtx', data)
        self.chunks = tuple( c.cast('f') for c in self.chunks )

class BnOfsMtxParser(ContainerParser):
    def __init__(self, data, ldata = memoryview(b'')):
        super().__init__(b'BnOfsMtx', data)
        self.chunks = tuple( c.cast('f') for c in self.chunks )
