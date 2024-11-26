# Ninja Gaiden Sigma 2 TMC Importer by Nozomi Miyamori is under the public domain
# and also marked with CC0 1.0. This file is a part of Ninja Gaiden Sigma 2 TMC Importer.

from __future__ import annotations

from ..parser import ContainerParser

from typing import NamedTuple
from enum import IntEnum
from operator import indexOf
import struct

class TMCParser(ContainerParser):
    def __init__(self, data, ldata = b''):
        super().__init__(b'TMC', data)

        (
                _, _, _,
                _,
                name
        ) = struct.unpack_from('< HH4xI4x I4x8x 10s', self._metadata)

        self.metadata = TMCMetaData(name.partition(b'\0')[0])

        o = 0xc0
        p = o+4*len(self._chunks)
        tbl = self._metadata[o:p].cast('I')
        i = indexOf(tbl, 0x8000_0020)
        self.lheader = LHeaderParser(self._chunks[i], ldata)

        for t, c in zip(tbl, self._chunks):
            match t:
                case 0x8000_0001:
                    self.mdlgeo = c and MdlGeoParser(c, getattr(self.lheader, 'mdlgeo', b''))
                case 0x8000_0002:
                    self.ttdm = c and TTDMParser(c, getattr(self.lheader, 'ttdl', b''))
                case 0x8000_0003:
                    self.vtxlay = c and VtxLayParser(c, getattr(self.lheader, 'vtxlay', b''))
                case 0x8000_0004:
                    self.idxlay = c and IdxLayParser(c, getattr(self.lheader, 'idxlay', b''))
                case 0x8000_0005:
                    self.mtrcol = c and MtrColParser(c, getattr(self.lheader, 'mtrcol', b''))
                case 0x8000_0006:
                    self.mdlinfo = c and MdlInfoParser(c, getattr(self.lheader, 'mdlinfo', b''))
                case 0x8000_0010:
                    self.hielay = c and HieLayParser(c, getattr(self.lheader, 'hielay', b''))
                case 0x8000_0030:
                    self.nodelay = c and NodeLayParser(c, getattr(self.lheader, 'nodelay', b''))
                case 0x8000_0040:
                    self.glblmtx = c and GlblMtxParser(c, getattr(self.lheader, 'glblmtx', b''))
                case 0x8000_0050:
                    self.bnofsmtx = c and BnOfsMtxParser(c, getattr(self.lheader, 'bnofsmtx', b''))
                case 0x8000_0060:
                    self.cpf = c
                case 0x8000_0070:
                    self.mcapack = c
                case 0x8000_0080:
                    self.renpack = c

    def close(self):
        super().close()
        self.lheader.close()
        (x := getattr(self, 'mdlgeo', None)) and x.close()
        (x := getattr(self, 'ttdm', None)) and x.close()
        (x := getattr(self, 'vtxlay', None)) and x.close()
        (x := getattr(self, 'idxlay', None)) and x.close()
        (x := getattr(self, 'mtrcol', None)) and x.close()
        (x := getattr(self, 'mdlinfo', None)) and x.close()
        (x := getattr(self, 'hielay', None)) and x.close()
        (x := getattr(self, 'nodelay', None)) and x.close()
        (x := getattr(self, 'glblmtx', None)) and x.close()
        (x := getattr(self, 'bnofsmtx', None)) and x.close()

class TMCMetaData(NamedTuple):
    #unknown0x0: int
    #unknown0x2: int
    #unknown0x8: int
    #general_chunks_count: int
    #addr0x18
    name: bytes

class MdlGeoParser(ContainerParser):
    def __init__(self, data, ldata = b''):
        super().__init__(b'MdlGeo', data)
        self.chunks = tuple( ObjGeoParser(c) for c in self._chunks )

    def close(self):
        super().close()
        for c in self.chunks:
            c.close()

class ObjGeoParser(ContainerParser):
    def __init__(self, data):
        super().__init__(b'ObjGeo', data)
        a = struct.unpack_from('< HHi8x 8x8x 10s', self._metadata)
        self.metadata = ObjGeoMetaData(*a[:-1], a[-1].partition(b'\0')[0])
        self.sub_container = GeoDeclParser(self._sub_container)
        self.chunks = tuple(ObjGeoParser._gen_chunks(self._chunks))

    @staticmethod
    def _gen_chunks(chunks):
        for c in chunks:
            a = struct.unpack_from(f'< ii4xI', c)
            assert a[2] <= 4
            b = struct.unpack_from('< II8x III4x IIII II8x 8xII I?3xII IIII'
                                   'IIII ffff IIII IIII IIII', c, 0x20)
            I = ( c[o:o+0x7c] for o in struct.unpack_from(f'< {a[2]}I', c, 0x10) )
            yield ObjGeoChunk(*a[:-1], *b, tuple(ObjGeoParser._gen_texture_info(I)))

    @staticmethod
    def _gen_texture_info(data):
        for d in data:
            x = struct.unpack_from('< III4x IIII IIII IIII IIII IIII ffII III', d)
            yield TextureInfo(x[0], TextureUsage(x[1]), *x[2:])

    def close(self):
        super().close()
        self.sub_container.close()

class ObjGeoMetaData(NamedTuple):
    unknown0x0: int # 3
    unknown0x2: int # 1
    obj_index: int
    #padding
    #objinfo_address0x10
    #address0x18
    name: bytes
    
class ObjGeoChunk(NamedTuple):
    objgeo_chunk_index: int
    mtrcol_index: int
    #padding
    #texture_count: int

    unknown0x20: int
    unknown0x24: int
    #mtrcol_address0x28

    unknown0x30: int
    unknown0x34: int
    #geodecl_chunk_address0x38
    geodecl_chunk_index: int

    unknown0x40: int
    unknown0x44: int
    unknown0x48: int
    unknown0x4c: int

    unknown0x50: int
    unknown0x54: int
    #objinfo_chunk_address0x58

    #address0x60
    unknown0x68: int # 1
    unknown0x6c: int # 5

    unknown0x70: int # 1
    show_backface: bool
    first_index_index: int
    index_count: int

    first_vertex_index: int
    vertex_count: int
    unknown0x88: int
    unknown0x8c: int

    unknown0x90: int
    unknown0x94: int
    unknown0x98: int
    unknown0x9c: int

    unknown0xa0: float # 1.0
    unknown0xa4: float # 0.0
    unknown0xa8: float # 1.0
    unknown0xac: float # 1.0

    unknown0xb0: int
    unknown0xb4: int
    unknown0xb8: int # 1
    unknown0xbc: int # 1

    unknown0xc0: int
    unknown0xc4: int
    unknown0xc8: int
    unknown0xcc: int

    unknown0xd0: int
    unknown0xd4: int
    unknown0xd8: int
    unknown0xdc: int
    texture_info_table: tuple[TextureInfo]

class TextureInfo(NamedTuple):
    info_index: int
    usage: TextureUsage
    texture_index: int
    #padding
    color_usage: int
    unknown0x14: int
    unknown0x18: int
    unknown0x1c: int

    unknown0x20: int
    unknown0x24: int
    unknown0x28: int
    unknown0x2c: int

    unknown0x30: int
    unknown0x34: int
    unknown0x38: int
    unknown0x3c: int

    unknown0x40: int
    unknown0x44: int
    unknown0x48: int
    unknown0x4c: int # 1

    unknown0x50: int # 1
    unknown0x54: int # 1
    unknown0x58: int
    unknown0x5c: int

    unknown0x60: float # 12.0
    unknown0x64: float # -1.0
    unknown0x68: int
    unknown0x6c: int

    unknown0x70: int
    unknown0x74: int
    unknown0x78: int # 2

class TextureUsage(IntEnum):
    Albedo = 0
    Normal = 1
    Multiply = 2
    Add = 3

class GeoDeclParser(ContainerParser):
    def __init__(self, data):
        super().__init__(b'GeoDecl', data)
        self.chunks = tuple(GeoDeclParser._gen_chunks(self._chunks))

    @staticmethod
    def _gen_chunks(chunks):
        for c in chunks:
            a = struct.unpack_from('< IIII III', c)
            b = struct.unpack_from('< III', c, a[1])
            o = a[1] + 0x18
            E = ( c[i:i+8] for i in range(o, 8*b[2]+o, 8) )
            yield GeoDeclChunk(a[0], *a[2:], *b[0:2],
                               tuple(GeoDeclParser._gen_d3dvertexelement9(E)))

    @staticmethod
    def _gen_d3dvertexelement9(data):
        for d in data:
            (stream, offset, d3d_decl_type,
             method, usage, usage_index) = struct.unpack('< hhBBBB', d)
            yield D3DVERTEXELEMENT9(stream, offset, D3DDECLTYPE(d3d_decl_type),
                                    method, D3DDECLUSAGE(usage), usage_index)

class GeoDeclChunk(NamedTuple):
    unknown0x0: int # 0
    #vertex_info_offset
    unknown0x8: int # 1
    index_buffer_index: int

    index_count: int
    vertex_count: int
    unknown0x18: int # 0, 1, 2, 3, 4
    #padding

    #address0x20
    #address0x28
    #vtxlay_chunk_address0x30
    vertex_buffer_index: int
    vertex_size: int

    #vertex_elements_count
    #padding
    #address0x48
    vertex_elements: tuple[D3DVERTEXELEMENT9]

class D3DVERTEXELEMENT9(NamedTuple):
    stream: int
    offset: int
    d3d_decl_type: D3DDECLTYPE
    method: int
    usage: D3DDECLUSAGE
    usage_index: int

class D3DDECLTYPE(IntEnum):
    FLOAT1     = 0
    FLOAT2     = 1
    FLOAT3     = 2
    FLOAT4     = 3
    D3DCOLOR   = 4
    UBYTE4     = 5
    SHORT2     = 6
    SHORT4     = 7
    UBYTE4N    = 8
    SHORT2N    = 9
    SHORT4N    = 10
    USHORT2N   = 11
    USHORT4N   = 12
    UDEC3      = 13
    DEC3N      = 14
    FLOAT16_2  = 15
    FLOAT16_4  = 16
    UNUSED     = 17

class D3DDECLUSAGE(IntEnum):
    POSITION      = 0
    BLENDWEIGHT   = 1
    BLENDINDICES  = 2
    NORMAL        = 3
    PSIZE         = 4
    TEXCOORD      = 5
    TANGENT       = 6
    BINORMAL      = 7
    TESSFACTOR    = 8
    POSITIONT     = 9
    COLOR         = 10
    FOG           = 11
    DEPTH         = 12
    SAMPLE        = 13

class TTDMParser(ContainerParser):
    def __init__(self, data, ldata):
        super().__init__(b'TTDM', data)
        self.metadata = TTDHParser(self._metadata)
        self.sub_container = TTDLParser(self._sub_container, ldata)

    def close(self):
        super().close()
        self.metadata.close()
        self.sub_container.close()

class TTDHParser(ContainerParser):
    def __init__(self, data):
        super().__init__(b'TTDH', data)
        self.chunks = tuple(TTDHParser._gen_chunks(self._chunks))

    @staticmethod
    def _gen_chunks(chunks):
        for c in chunks:
            yield TTDHChunk(*struct.unpack_from('< ?3xi', c))

class TTDHChunk(NamedTuple):
    # If in_ttdl is true, the index points to TTDL, otherwise it points to TTDM.
    # Although, all data seems be in TTDL when it comes to NGS2 TMC.
    in_ttdl: bool
    chunk_index: int

class TTDLParser(ContainerParser):
    def __init__(self, data, ldata):
        super().__init__(b'TTDL', data, ldata)

class VtxLayParser(ContainerParser):
    def __init__(self, data, ldata = b''):
        super().__init__(b'VtxLay', data, ldata)

class IdxLayParser(ContainerParser):
    def __init__(self, data, ldata = b''):
        super().__init__(b'IdxLay', data, ldata)
        # Index size of an index buffer s is depends on the number of elements in the corresponding 
        # vertex buffer N, i.e., if N < 1<<16 then s is 2 bytes, otherwise it's 4 bytes.

class MtrColParser(ContainerParser):
    def __init__(self, data, ldata = b''):
        super().__init__(b'MtrCol', data)
        self.chunks = tuple(MtrColParser._gen_chunks(self._chunks))

    @staticmethod
    def _gen_chunks(chunks):
        for c in chunks:
            mtrcol_index, xrefs_count = struct.unpack_from('< iI', c, 0xd0)
            xrefs = struct.unpack_from(f'<' + xrefs_count*'iI', c, 0xd8)
            xrefs = tuple(xrefs[i:i+2] for i in range(0, len(xrefs), 2))
            yield MtrColChunk(
                    struct.unpack_from('< 4f', c),
                    struct.unpack_from('< 4f', c, 0x10),
                    struct.unpack_from('< 4f', c, 0x20),
                    *struct.unpack_from('< ff', c, 0x68),
                    struct.unpack_from('< 4f', c, 0x80),
                    struct.unpack_from('< 4f', c, 0x90),
                    mtrcol_index, xrefs)

class MtrColChunk(NamedTuple):
    mix: tuple[float]
    diffuse: tuple[float]
    specular: tuple[float]
    # unknown0x30: tuple[float]
    # unknown0x40: tuple[float]
    # unknown0x50: tuple[float]
    # address0x60
    # unknown0x70: tuple[float]
    specular_emission_power: float
    diffuse_emission_power: float

    coat: tuple[float]
    sheen: tuple[float]
    # unknown0xa0: tuple[float]
    # unknown0xb0: tuple[float]
    # unknown0xc0: tuple[float]
    mtrcol_index: int
    # Each tuple has (objindex, count)
    # that means the mtrcol is used by "objindex" "count" times
    xrefs: tuple[tuple[int, int]]

class MdlInfoParser(ContainerParser):
    def __init__(self, data, ldata = b''):
        super().__init__(b'MdlInfo', data)
        self.chunks = tuple( ObjInfoParser(c) for c in self._chunks )

    def close(self):
        super().close()
        for c in self.chunks:
            c.close()

class ObjInfoParser(ContainerParser):
    def __init__(self, data):
        super().__init__(b'ObjInfo', data)
        _, obj_index, _ = struct.unpack_from('< Ii4xI', self._metadata)
        self.metadata = ObjInfoMetaData(obj_index)

class ObjInfoMetaData(NamedTuple):
    #unknown0x0: int # 3
    #unknown0x2: int # 2
    obj_index: int
    #unknown0xc: int
    #unknown0x14: int

class HieLayParser(ContainerParser):
    def __init__(self, data, ldata = b''):
        super().__init__(b'HieLay', data)
        self.chunks = tuple(HieLayParser._gen_chunks(self._chunks))

    @staticmethod
    def _gen_chunks(chunks):
        for c in chunks:
            *matrix, parent, children_count, level = struct.unpack_from('< 16f iII', c)
            children = struct.unpack_from(f'< {children_count}i', c, 0x50)
            yield HieLayChunk(matrix, parent, level, children)

class HieLaySubContainer(NamedTuple):
    #unknown0x0: int # 1
    #unknown0x10: int # 2
    pass

class HieLayChunk(NamedTuple):
    matrix: tuple[float]
    parent: int
    level: int
    children: tuple[int]

class LHeaderParser(ContainerParser):
    def __init__(self, data, ldata):
        super().__init__(b'LHeader', data, ldata)

        o1 = 0x20
        o2 = 0x20 + 4*len(self._chunks)
        chunk_type_id_table = self._metadata[o1:o2].cast('I')
        for c, t in zip(self._chunks, chunk_type_id_table):
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
    def __init__(self, data, ldata = b''):
        super().__init__(b'NodeLay', data)
        self.chunks = tuple( NodeObjParser(c) for c in self._chunks )

    def close(self):
        super().close()
        for c in self.chunks:
            c.close()

class NodeLayMetaData(NamedTuple):
    #unknown0x0: int # 1
    #unknown0x2: int # 2
    pass

class NodeObjParser(ContainerParser):
    def __init__(self, data):
        super().__init__(b'NodeObj', data)
        (
                master, node_index,
                name
        ) = struct.unpack_from(f'< 4xii4x {self._metadata.nbytes-0x10}s', self._metadata)
        self.metadata = NodeObjMetaData(master, node_index, name.partition(b'\0')[0])
        if self._chunks:
            c = self._chunks[0]
            obj_index, node_count, node_index, *matrix = struct.unpack_from('< iIi4x 16f', c)
            node_group = struct.unpack_from(f'< {node_count}i', c, 0x50)
            self.chunks = (NodeObjChunk(obj_index, node_index, matrix, node_group),)

class NodeObjMetaData(NamedTuple):
    #unknown0x0: int
    master: int
    node_index: int
    name: bytes

class NodeObjChunk(NamedTuple):
    obj_index: int
    node_index: int
    matrix: tuple[float]
    node_group: tuple[int]
    
class GlblMtxParser(ContainerParser):
    def __init__(self, data, ldata = b''):
        super().__init__(b'GlblMtx', data)
        self.chunks = tuple( struct.unpack_from('< 16f', c) for c in self._chunks )

class BnOfsMtxParser(ContainerParser):
    def __init__(self, data, ldata = b''):
        super().__init__(b'BnOfsMtx', data)
        self.chunks = tuple( struct.unpack_from('< 16f', c) for c in self._chunks )

# NGS2 specific data parsers below

class MTRLCHNGParser(ContainerParser):
    def __init__(self, data, ldata = b''):
        super().__init__(b'MTRLCHNG', data)
        self.metadata = MTRLCHNGMetaData(*struct.unpack_from('< HHIII', self._metadata))
        c = self._chunks[2]
        m = self.metadata.variant_count
        n = self.metadata.element_count
        self.color_variants = tuple( tuple(
            MTRLCHNGParser._make_element( c[(n*i+j)*0xd0:(n*i+(j+1))*0xd0]) for j in range(n)
        ) for i in range(m) )

    @staticmethod
    def _make_element(c):
        return MTRLCHNGElement(
                struct.unpack_from('< 4f', c),
                struct.unpack_from('< 4f', c, 0x10),
                struct.unpack_from('< 4f', c, 0x20),
                *struct.unpack_from('< ff', c, 0x68),
                struct.unpack_from('< 4f', c, 0x80),
                struct.unpack_from('< 4f', c, 0x90))

class MTRLCHNGMetaData(NamedTuple):
    unknown0x0: int
    unknown0x2: int
    unknown0x4: int
    variant_count: int
    element_count: int

# Same as MtrColChunk but w/o mtrcol_index and xrefs
class MTRLCHNGElement(NamedTuple):
    mix: tuple[float]
    diffuse: tuple[float]
    specular: tuple[float]
    # unknown0x30: tuple[float]
    # unknown0x40: tuple[float]
    # unknown0x50: tuple[float]
    # address0x60
    # unknown0x70: tuple[float]
    specular_emission_power: float
    diffuse_emission_power: float

    coat: tuple[float]
    sheen: tuple[float]
    # unknown0xa0: tuple[float]
    # unknown0xb0: tuple[float]
    # unknown0xc0: tuple[float]
