# This program is by Nozomi Miyamori, under the public domain and marked with CC0 1.0.

from .tcmlib.ngs2 import TMCParser, NodeLayParser
from .databin import DatabinParser, decompress

import os.path
import sys
import mmap
from itertools import accumulate
import struct

def main():
    db = 'databin'
    e_nin_c_cut_dds = r'e_nin_c_05.dds'
    with mmap_open(db) as db, DatabinParser(db) as db, mmap_open(e_nin_c_cut_dds) as e_nin_c_cut_dds:
        ### Humans and red blood Fiends

        # e_you_c has middle sized gibs, a vivid red cut surface texture.
        e_you_c = parse_tmc(db, 1359)
        def inject_gibs_(n, **kwargs):
            y = inject_gibs(e_you_c, parse_tmc(db, n),
                            src_gib_first_index = 0x23,
                            src_gib_tex = e_you_c.ttdm.sub_container.chunks[1],
                            src_gib_normal_tex = e_you_c.ttdm.sub_container.chunks[0],
                            src_metal_tex = e_you_c.ttdm.sub_container.chunks[2],
                            **kwargs)
            save_(n, *y)

        # e_jgm_a: no gibs, has surface, has metal.
        inject_gibs_(1090, dst_gib_insert_index = 0x16, dst_mtrcol_index = 4,
                     dst_gib_tex_index = 5, dst_gib_normal_tex_index = 0,
                     dst_metal_tex_index = 13)

        # e_nin_a: no gibs, has surface, has metal.
        inject_gibs_(1094, dst_gib_insert_index = 0xf, dst_mtrcol_index = 6,
                     dst_gib_tex_index = 5, dst_gib_normal_tex_index = 0,
                     dst_metal_tex_index = 16)

        # e_wlf_a: has gibs.
        inject_gibs_(1112, dst_gib_insert_index = None, dst_mtrcol_index = 1,
                     dst_gib_tex_index = 11, dst_gib_normal_tex_index = 0,
                     dst_metal_tex_index = 15)

        # e_gaj_b: no gibs, has surface, has metal.
        inject_gibs_(1167, dst_gib_insert_index = 0x20, dst_mtrcol_index = 3,
                     dst_gib_tex_index = 4, dst_gib_normal_tex_index = 5,
                     dst_metal_tex_index = 13)

        # e_you_a: has gibs.
        inject_gibs_(1235, dst_gib_insert_index = None, dst_mtrcol_index = 3,
                     dst_gib_tex_index = 12, dst_gib_normal_tex_index = 4,
                     dst_metal_tex_index = 21)

        # e_nin_c: has gibs.
        inject_gibs_(1262, dst_gib_insert_index = None, dst_mtrcol_index = 2,
                     dst_gib_tex_index = 7, dst_gib_normal_tex_index = 0,
                     dst_metal_tex_index = 17, e_nin_c_cut_tex = e_nin_c_cut_dds,
                     dst_e_nin_c_cut_index = 5)

        # e_bni_a: has gibs.
        inject_gibs_(1311, dst_gib_insert_index = None, dst_mtrcol_index = 9,
                     dst_gib_tex_index = 37, dst_gib_normal_tex_index = 0,
                     dst_metal_tex_index = 38)

        # e_jgm_c: no gibs, no surface, has metal.
        inject_gibs_(1333, dst_gib_insert_index = 0xf, dst_mtrcol_index = 1,
                     dst_gib_tex_index = None, dst_gib_normal_tex_index = None,
                     dst_metal_tex_index = 14, e_nin_c_cut_tex = e_nin_c_cut_dds,
                     dst_e_nin_c_cut_index = 5)

        # e_wlf_b: has gibs.
        inject_gibs_(1364, dst_gib_insert_index = None, dst_mtrcol_index = 1,
                     dst_gib_tex_index = 11, dst_gib_normal_tex_index = 0,
                     dst_metal_tex_index = 15)

        # e_you_d: has gibs.
        inject_gibs_(1366, dst_gib_insert_index = None, dst_mtrcol_index = 3,
                     dst_gib_tex_index = 12, dst_gib_normal_tex_index = 4,
                     dst_metal_tex_index = 21)

        # e_gja_c: has gibs, has surface, has metal.
        inject_gibs_(1376, dst_gib_insert_index = 0x20, dst_mtrcol_index = 1,
                     dst_gib_tex_index = 4, dst_gib_normal_tex_index = 5,
                     dst_metal_tex_index = 13)

        # e_nin_d: no gibs, has surface, has metal.
        inject_gibs_(1383, dst_gib_insert_index = 0xf, dst_mtrcol_index = 6,
                     dst_gib_tex_index = 5, dst_gib_normal_tex_index = 0,
                     dst_metal_tex_index = 15)

        # e_jgm_d: no gibs, has surface, has metal.
        inject_gibs_(1817, dst_gib_insert_index = 0xf, dst_mtrcol_index = 4,
                     dst_gib_tex_index = 5, dst_gib_normal_tex_index = 0,
                     dst_metal_tex_index = 14)

        ### Green large gibs

        # e_chg_a has large sized gibs and a green cut surface texture.
        e_chg_a = parse_tmc(db, 1116)
        def inject_gibs_(n, **kwargs):
            y = inject_gibs(e_chg_a, parse_tmc(db, n),
                            src_gib_first_index = 0x14,
                            src_gib_tex = e_chg_a.ttdm.sub_container.chunks[13],
                            src_gib_normal_tex = e_chg_a.ttdm.sub_container.chunks[5],
                            src_metal_tex = e_chg_a.ttdm.sub_container.chunks[21],
                            **kwargs)
            save_(n, *y)


        # e_van_a: no gibs, has metal.
        inject_gibs_(1107, dst_gib_insert_index = 0x14, dst_mtrcol_index = 1,
                     dst_gib_tex_index = None, dst_gib_normal_tex_index = None,
                     dst_metal_tex_index = 11)

        # e_van_b: no gibs, no surface, has metal.
        inject_gibs_(1342, dst_gib_insert_index = 0x1e, dst_mtrcol_index = 1,
                     dst_gib_tex_index = None, dst_gib_normal_tex_index = None,
                     dst_metal_tex_index = 11)

        # e_van_c: no gibs, no surface, has metal.
        inject_gibs_(1361, dst_gib_insert_index = 0x1e, dst_mtrcol_index = 1,
                     dst_gib_tex_index = None, dst_gib_normal_tex_index = None,
                     dst_metal_tex_index = 11)

        ### Green blood fiends whose has Mid-sized gibs
        def inject_gibs_(n, **kwargs):
            y = inject_gibs(e_you_c, parse_tmc(db, n),
                            src_gib_first_index = 0x23,
                            src_gib_tex = e_chg_a.ttdm.sub_container.chunks[13],
                            src_gib_normal_tex = e_chg_a.ttdm.sub_container.chunks[5],
                            src_metal_tex = e_chg_a.ttdm.sub_container.chunks[21],
                            **kwargs)
            save_(n, *y)

        # kage: no gibs, no surface
        inject_gibs_(1138, dst_gib_insert_index = 0x10, dst_mtrcol_index = 2,
                     dst_gib_tex_index = None, dst_gib_normal_tex_index = None,
                     dst_metal_tex_index = 16)

        # e_kag_b: no gibs, no surface
        inject_gibs_(1148, dst_gib_insert_index = 0x10, dst_mtrcol_index = 2,
                     dst_gib_tex_index = None, dst_gib_normal_tex_index = None,
                     dst_metal_tex_index = 7)

        ### Small sized red blood Fiends

        # e_okm_a has mid-sized gibs and a vivid surface texture.
        e_okm_a = parse_tmc(db, 1098)
        def inject_gibs_(n, **kwargs):
            y = inject_gibs(e_okm_a, parse_tmc(db, n),
                            src_gib_first_index = 0x18,
                            src_gib_tex = e_okm_a.ttdm.sub_container.chunks[5],
                            src_gib_normal_tex = e_okm_a.ttdm.sub_container.chunks[2],
                            src_metal_tex = e_okm_a.ttdm.sub_container.chunks[11],
                            **kwargs)
            save_(n, *y)

        # bat: no gibs, no surface.
        #inject_gibs_(1085, dst_gib_insert_index = 0x7, dst_mtrcol_index = 0,
                      #dst_gib_tex_index = None, dst_gib_normal_tex_index = None,
                      #dst_metal_tex_index = 2)

        # e_bat_b: no gibs.
        inject_gibs_(1353, dst_gib_insert_index = 0x16, dst_mtrcol_index = 1,
                     dst_gib_tex_index = None, dst_gib_normal_tex_index = None,
                     dst_metal_tex_index = 4)

        ### Machines

        # e_ciw_a has robot parts.
        e_ciw_a = parse_tmc(db, 1280)
        def inject_gibs_(n, **kwargs):
            y = inject_gibs(e_ciw_a, parse_tmc(db, n),
                            src_gib_first_index = 0x3,
                            src_gib_tex = e_ciw_a.ttdm.sub_container.chunks[8],
                            src_gib_normal_tex = e_ciw_a.ttdm.sub_container.chunks[0],
                            src_metal_tex = e_ciw_a.ttdm.sub_container.chunks[9],
                            **kwargs)
            save_(n, *y)

        # e_mac_a: no gibs, no surface.
        inject_gibs_(1178, dst_gib_insert_index = 0x1D, dst_mtrcol_index = 2,
                     dst_gib_tex_index = None, dst_gib_normal_tex_index = None,
                     dst_metal_tex_index = 17)

def inject_gibs(srctmc, dsttmc, *, src_gib_first_index, src_gib_tex, src_gib_normal_tex,
                src_metal_tex, dst_gib_insert_index = None, dst_gib_tex_index = None,
                dst_gib_normal_tex_index = None, dst_metal_tex_index = None, dst_mtrcol_index =None,
                e_nin_c_cut_tex = None, dst_e_nin_c_cut_index = None):
    dsttmc_chunks = list(dsttmc._chunks)
    ttdl_chunks = list(dsttmc.ttdm.sub_container._chunks)
    if dst_gib_tex_index is None:
        dst_gib_tex_index = len(ttdl_chunks)
        ttdl_chunks.append(src_gib_tex)
    else:
        ttdl_chunks[dst_gib_tex_index] = src_gib_tex

    if dst_gib_normal_tex_index is None:
        dst_gib_normal_tex_index = len(ttdl_chunks)
        ttdl_chunks.append(src_gib_normal_tex)
    else:
        ttdl_chunks[dst_gib_normal_tex_index] = src_gib_normal_tex

    if dst_metal_tex_index is None:
        dst_metal_tex_index = len(ttdl_chunks)
        ttdl_chunks.append(src_metal_tex)

    if e_nin_c_cut_tex:
        ttdl_chunks[dst_e_nin_c_cut_index] = e_nin_c_cut_tex
    ttdl, ttdl_ldata = serialize_container(b'TTDL', ttdl_chunks, separating_body = True, aligned = 0x40)
    ttdh = serialize_container(
            b'TTDH', ( struct.pack('< IIqqq', 1, i, 0, 0, 0) for i in range(len(ttdl_chunks)) ),
            (0x1).to_bytes(4, 'little')
    )
    dsttmc_chunks[dsttmc_chunks.index(dsttmc.ttdm._data)] = serialize_container(b'TTDM', (), ttdh, ttdl)

    # No need to inject gibs.
    if dst_gib_insert_index is None:
        lheader_chunks = list(dsttmc.lheader._chunks)
        lheader_chunks[lheader_chunks.index(dsttmc.lheader.ttdl)] = ttdl_ldata
        lheader, lheader_ldata = serialize_container(b'LHeader', lheader_chunks, dsttmc.lheader._metadata, separating_body = True, aligned = 0x80)
        dsttmc_chunks[dsttmc_chunks.index(dsttmc.lheader._data)] = lheader
        return (serialize_container(b'TMC', dsttmc_chunks, dsttmc._metadata), lheader_ldata)

    src_slice = slice(src_gib_first_index, src_gib_first_index+0x11)
    dst_slice = slice(dst_gib_insert_index, dst_gib_insert_index+0x11)
    dst_insert_slice = slice(dst_slice.start, dst_slice.start)
    # OPTscat object has just one GeoDecl so we just copy all fo them.
    V, I = zip(*(
            ( bytearray(srctmc.vtxlay.chunks[c.vertex_buffer_index]),
                bytearray(srctmc.idxlay.chunks[c.index_buffer_index]) )
            for c in srctmc.mdlgeo.chunks[src_slice] for c in c.sub_container.chunks ))

    c = dsttmc.mdlgeo.chunks[dst_slice.start-1].sub_container.chunks[-1]
    # we use vidx and iidx later
    vidx = c.vertex_buffer_index+1
    iidx = c.index_buffer_index+1
    vtxlay_chunks = list(dsttmc.vtxlay._chunks)
    vtxlay_chunks[vidx:vidx] = V
    vtxlay, vtxlay_ldata = serialize_container(b'VtxLay', vtxlay_chunks, separating_body = True)
    dsttmc_chunks[dsttmc_chunks.index(dsttmc.vtxlay._data)] = vtxlay
    idxlay_chunks = list(dsttmc.idxlay._chunks)
    idxlay_chunks[iidx:iidx] = I
    idxlay, idxlay_ldata = serialize_container(b'IdxLay', idxlay_chunks, separating_body = True)
    dsttmc_chunks[dsttmc_chunks.index(dsttmc.idxlay._data)] = idxlay

    mtrcol_chunks = list( bytearray(c) for c in dsttmc.mtrcol._chunks)
    for i,c in enumerate(mtrcol_chunks):
        xrefs = dsttmc.mtrcol.chunks[i].xrefs
        s = b''.join( struct.pack('< iI', i+0x11*(i>=dst_slice.start), j) for i,j in xrefs )
        struct.pack_into(f'< {len(s)}s', c, 0xd8, s)
    c = mtrcol_chunks[dst_mtrcol_index]
    xrefs = list(dsttmc.mtrcol.chunks[dst_mtrcol_index].xrefs)
    n = len(xrefs) + 0x11
    c += ((0xd8 + 8*n) - len(c)) * b'\0'
    xrefs += ( (i, 1) for i in range(dst_slice.start, dst_slice.stop) )
    xrefs.sort()
    s = b''.join( struct.pack('< iI', i, j) for i,j in xrefs )
    # xref count
    struct.pack_into(f'< I{len(s)}s', c, 0xd4, n, s)
    dsttmc_chunks[dsttmc_chunks.index(dsttmc.mtrcol._data)] = serialize_container(b'MtrCol', mtrcol_chunks)

    mdlgeo_chunks = list(dsttmc.mdlgeo._chunks)
    mdlgeo_chunks[dst_insert_slice] = ( bytearray(c) for c in srctmc.mdlgeo._chunks[src_slice] )
    mdlgeo_chunks[dst_slice.stop:] = ( bytearray(c) for c in mdlgeo_chunks[dst_slice.stop:] )
    for objgeo in mdlgeo_chunks[dst_slice]:
        for o in offset_table_of(objgeo):
            # mtrcol index
            struct.pack_into('< I', objgeo, o+0x4, dst_mtrcol_index)
            # texture index
            _, _, texture_info_count = struct.unpack_from(f'< ii4xI', objgeo, o)
            texture_info_offset_table = struct.unpack_from(f'< {texture_info_count}I', objgeo, o+0x10)
            # albedo
            struct.pack_into('< I', objgeo, o+texture_info_offset_table[0]+0x8, dst_gib_tex_index)
            # metalness
            struct.pack_into('< I', objgeo, o+texture_info_offset_table[1]+0x8, dst_metal_tex_index)
            # normal
            struct.pack_into('< I', objgeo, o+texture_info_offset_table[2]+0x8, dst_gib_normal_tex_index)

    for i, objgeo in enumerate(mdlgeo_chunks[dst_slice.start:], dst_slice.start):
        # obj index
        struct.pack_into('< I', objgeo, 0x34, i)

    j = vidx
    k = iidx
    for i, objgeo in enumerate(mdlgeo_chunks[dst_slice]):
        o, = struct.unpack_from('< I', objgeo, 0x28)
        geodecl = memoryview(objgeo)[o:]
        for k, (j, o) in enumerate(enumerate(offset_table_of(geodecl), j), k):
            # index_buffer_index
            struct.pack_into('< I', geodecl, o+0xc, k)
            vertex_info_offset, = struct.unpack_from('< 4xI', geodecl, o)
            vertex_buffer_index, = struct.unpack_from('< I', geodecl, o+vertex_info_offset)
            # vertex_buffer_index
            struct.pack_into('< I', geodecl, o+vertex_info_offset, j)
        j += 1
        k += 1

    for objgeo0, objgeo in zip(dsttmc.mdlgeo.chunks[dst_slice.start:], mdlgeo_chunks[dst_slice.stop:]):
        o, = struct.unpack_from('< I', objgeo, 0x28)
        geodecl = memoryview(objgeo)[o:]
        for c, o in zip(objgeo0.sub_container.chunks, offset_table_of(geodecl)):
            struct.pack_into('< I', geodecl, o+0xc, c.index_buffer_index+0x11)
            vertex_info_offset, = struct.unpack_from('< 4xI', geodecl, o)
            vertex_buffer_index, = struct.unpack_from('< I', geodecl, o+vertex_info_offset)
            struct.pack_into('< I', geodecl, o+vertex_info_offset, c.vertex_buffer_index+0x11)

    dsttmc_chunks[dsttmc_chunks.index(dsttmc.mdlgeo._data)] = serialize_container(b'MdlGeo', mdlgeo_chunks)

    mdlinfo_chunks = list(dsttmc.mdlinfo._chunks)
    mdlinfo_chunks[dst_insert_slice] = ( bytearray(c) for c in srctmc.mdlinfo._chunks[src_slice] )
    mdlinfo_chunks[dst_slice.stop:] = ( bytearray(c) for c in mdlinfo_chunks[dst_slice.stop:] )
    for idx, objinfo in enumerate(mdlinfo_chunks[dst_slice.start:], dst_slice.start):
        # obj index
        struct.pack_into('< I', objinfo, 0x34, idx)
    dsttmc_chunks[dsttmc_chunks.index(dsttmc.mdlinfo._data)] = serialize_container(b'MdlInfo', mdlinfo_chunks)

    hielay_chunks = list( bytearray(c) for c in dsttmc.hielay._chunks )
    for i, c in enumerate(hielay_chunks):
        a = dsttmc.hielay.chunks[i]
        if a.parent == -1:
            root_index = i
            n = len(a.children) + 0x11
            c += ((0x50 + 4*n) - len(c)) * b'\0'
            # child count
            struct.pack_into(f'< I', c, 4*16+4, n)

            # child index
            C = list( i+0x11*(i>=dst_slice.start) for i in a.children )
            C += range(dst_slice.start, dst_slice.stop)
            C.sort()
            struct.pack_into(f'< {len(C)}i', c, 0x50, *C)
        else:
            # child index
            struct.pack_into(f'< {len(a.children)}i', c, 0x50, *( i+0x11*(i>=dst_slice.start) for i in a.children ))

    hielay_chunks[dst_insert_slice] = ( bytearray(c) for c in srctmc.hielay._chunks[src_slice] )
    for c in hielay_chunks[dst_slice]:
        # parent, child count and level
        struct.pack_into('< III', c, 0x40, root_index, 0, 1)
    dsttmc_chunks[dsttmc_chunks.index(dsttmc.hielay._data)] = serialize_container(b'HieLay', hielay_chunks, b'', dsttmc.hielay._sub_container)

    nodelay_chunks = list( bytearray(c) for c in dsttmc.nodelay._chunks )
    for i, nodeobj in enumerate(nodelay_chunks):
        ng = dsttmc.nodelay.chunks[i].chunks[0].node_group
        o, = offset_table_of(nodeobj)
        struct.pack_into(f'< {len(ng)}i', nodeobj, o+0x50, *( i+0x11*(i>=dst_slice.start) for i in ng ))

    nodelay_chunks[dst_insert_slice] = ( bytearray(c) for c in srctmc.nodelay._chunks[src_slice] )
    for idx, nodeobj in enumerate(nodelay_chunks[dst_slice.start:], dst_slice.start):
        # node index
        struct.pack_into('< I', nodeobj, 0x38, idx)
        o, = offset_table_of(nodeobj)
        # obj index and node index (both are the same for enemies models)
        struct.pack_into('< I', nodeobj, o, idx)
        struct.pack_into('< I', nodeobj, o+8, idx)
    new_nodelay = dsttmc_chunks[dsttmc_chunks.index(dsttmc.nodelay._data)] = serialize_container(b'NodeLay', nodelay_chunks, dsttmc.nodelay._metadata)

    glblmtx_chunks = list(dsttmc.glblmtx._chunks)
    glblmtx_chunks[dst_insert_slice] = srctmc.glblmtx._chunks[src_slice]
    dsttmc_chunks[dsttmc_chunks.index(dsttmc.glblmtx._data)] = serialize_container(b'GlblMtx', glblmtx_chunks)

    bnofsmtx_chunks = list(dsttmc.bnofsmtx._chunks)
    bnofsmtx_chunks[dst_insert_slice] = srctmc.bnofsmtx._chunks[src_slice]
    dsttmc_chunks[dsttmc_chunks.index(dsttmc.bnofsmtx._data)] = serialize_container(b'BnOfsMtx', bnofsmtx_chunks)

    lheader_chunks = list(dsttmc.lheader._chunks)
    lheader_chunks[lheader_chunks.index(dsttmc.lheader.ttdl)] = ttdl_ldata
    lheader_chunks[lheader_chunks.index(dsttmc.lheader.vtxlay)] = vtxlay_ldata
    lheader_chunks[lheader_chunks.index(dsttmc.lheader.idxlay)] = idxlay_ldata
    lheader, lheader_ldata = serialize_container(b'LHeader', lheader_chunks, dsttmc.lheader._metadata, separating_body = True, aligned = 0x80)
    dsttmc_chunks[dsttmc_chunks.index(dsttmc.lheader._data)] = lheader

    # This chunk consists of 8 chunks of data. Each of them contains two "short":
    # the first index of the type of Node (MOT, OPT, SUP, etc.), and number of nodes of the type.
    dsttmc_chunks[13] = c = bytearray(dsttmc._chunks[13])
    # 0x0 NML?
    # 0x4 MOT
    n = 0x8 # ?
    x, = struct.unpack_from('< H', c, n)
    struct.pack_into('< H', c, n, x+(x>0)*0x11)
    n = 0xc # WGT
    x, = struct.unpack_from('< H', c, n)
    struct.pack_into('< H', c, n, x+(x>0)*0x11)
    n = 0x10 # SUP
    x, = struct.unpack_from('< H', c, n)
    struct.pack_into('< H', c, n, x+(x>0)*0x11)
    n = 0x14 # OPT
    i = tuple( c.metadata.name[:3] for c in NodeLayParser(new_nodelay).chunks ).index(b'OPT')
    x, = struct.unpack_from('< 2xH', c, n)
    struct.pack_into('< HH', c, n, i, x+0x11)
    n = 0x18 # ?
    x, = struct.unpack_from('< H', c, n)
    struct.pack_into('< H', c, n, x+(x>0)*0x11)
    n = 0x1c # WPB
    x, = struct.unpack_from('< H', c, n)
    struct.pack_into('< H', c, n, x+(x>0)*0x11)

    x = dsttmc._chunks[14]
    n = len(nodelay_chunks)
    n += -n%8
    dsttmc_chunks[14] = y = bytearray(4*n + 0x60*len(nodelay_chunks))
    O = range(4*n, len(y), 0x60)
    R = struct.unpack_from(f'< {n-0x11}I', x)
    y[O[0]:O[dst_slice.start]] = x[R[0]:R[dst_slice.start]]
    for i, o in enumerate(O[dst_slice]):
        struct.pack_into('< III', y, o, 5, 3, i)
    y[O[dst_slice.stop]:] = x[R[dst_slice.start]:]
    struct.pack_into(f'< {len(O)}I', y, 0, *O)

    return (serialize_container(b'TMC', dsttmc_chunks, dsttmc._metadata), lheader_ldata)

def serialize_container(magic, chunks = (), metadata = b'', sub_container = b'', *, separating_body = False, aligned = 0x10):
    chunks = tuple( memoryview(c) for c in chunks )
    tuple_of_chunk_nbytes = tuple( c.nbytes for c in chunks )
    metadata = memoryview(metadata)
    sub_container = memoryview(sub_container)
    separating_body = bool(separating_body)

    # We calculate sizes and offsets first.
    valid_chunk_count = sum( i > 0 for i in tuple_of_chunk_nbytes )
    offset_table_nbytes = 4*len(chunks)
    offset_table_nbytes += -offset_table_nbytes % 0x10
    size_table_nbytes = offset_table_nbytes * (separating_body or aligned % 0x10)
    chunks_nbytes = sum( i + -i % aligned for i in tuple_of_chunk_nbytes )
    metadata_nbytes = metadata.nbytes + -metadata.nbytes % 0x10
    sub_container_nbytes = sub_container.nbytes + -sub_container.nbytes % 0x10
    header_nbytes = separating_body and 0x50 or 0x30
    offset_table_pos0 = header_nbytes + metadata_nbytes
    size_table_pos0 = offset_table_pos0 + offset_table_nbytes
    sub_container_pos0 = size_table_pos0 + size_table_nbytes

    i0 = ( 0x10 * separating_body
          or sub_container_pos0 * (sub_container_nbytes > 0) + sub_container_nbytes
          or size_table_pos0 * (size_table_nbytes > 0) + size_table_nbytes
          or offset_table_pos0 * (offset_table_nbytes > 0) + offset_table_nbytes )
    i0 += -i0 % aligned
    I = accumulate(( i + -i % aligned for i in tuple_of_chunk_nbytes[:-1] ), initial=i0)
    offset_table = (offset_table_nbytes > 0) * tuple( i*(j > 0) for i,j in zip(I, tuple_of_chunk_nbytes) )
    size_table = (size_table_nbytes > 0) * tuple( i for i in tuple_of_chunk_nbytes )

    n = (
            header_nbytes
            + metadata_nbytes
            + offset_table_nbytes
            + size_table_nbytes
            + sub_container_nbytes
            + chunks_nbytes * (not separating_body)
    )
    data = bytearray(n + -n%0x10)

    # Let's pack the data.
    struct.pack_into(
            '< 8sII III4x III', data, 0,
            magic, 0x01010000, header_nbytes,
            len(data), len(chunks), valid_chunk_count,
            offset_table_pos0 * (offset_table_nbytes > 0),
            size_table_pos0 * (size_table_nbytes > 0),
            sub_container_pos0 * (sub_container_nbytes > 0)
    )

    if separating_body:
        n = 0x10 + chunks_nbytes
        ldata = bytearray(n + -n%aligned)
        struct.pack_into(
                '< III', data, 0x40,
                valid_chunk_count, len(ldata), 0x01234567
        )
        ldata[:0x10] = data[0x40:0x50]

    struct.pack_into(f'< {metadata.nbytes}s', data, header_nbytes, metadata.tobytes())
    struct.pack_into(f'< {len(offset_table)}I', data, offset_table_pos0, *offset_table)
    struct.pack_into(f'< {len(size_table)}I', data, size_table_pos0, *size_table)
    struct.pack_into(f'< {sub_container.nbytes}s', data, sub_container_pos0, sub_container.tobytes())

    A = separating_body and ldata or data
    for o, c in zip(offset_table, chunks):
        A[o:o+c.nbytes] = c

    return separating_body and (data, ldata) or data

def offset_table_of(x):
    n, = struct.unpack_from('< I', x, 0x14)
    o, = struct.unpack_from('< I', x, 0x20)
    return struct.unpack_from(f' {n}I', x, o)

def mmap_open(path):
    with open(path, 'rb') as f:
        return mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ)

def parse_tmc(db, n):
    return TMCParser(decompress(db.chunks[n]), decompress(db.chunks[n+1]))

def save(path, data):
    with open(path, 'wb') as f:
        f.write(data)

def save_(n, tmc, tmcl):
    s = r'mods\{:05}.dat'
    save(s.format(n), tmc)
    save(s.format(n+1), tmcl)

if __name__ == '__main__':
    main()
