# NINJA GAIDEN Mater Collection scripts by Nozomi Miyamori
# is marked with CC0 1.0. This file is a part of NINJA GAIDEN
# Master Collection Scripts.
#
# This module is for parsing databin bundled with NINJA GAIDEN
# Master Collection.

from .tcmlib.ngs2 import TMCParser

import os.path
import sys
import mmap
from itertools import accumulate
import struct

def main():
    return

def a():
    n = 1098
    srctmc_m, srctmcl_m = mmap_aiueo(n), mmap_aiueo(n+1)
    srctmc = TMCParser(srctmc_m, srctmcl_m)

    n = 1383
    dsttmc_m, dsttmcl_m = mmap_aiueo(n), mmap_aiueo(n+1)
    dsttmc = TMCParser(dsttmc_m, dsttmcl_m)
    with srctmc_m, srctmcl_m, srctmc, dsttmc_m, dsttmcl_m, dsttmc:
        dsttmc_chunks = list(dsttmc._chunks)
        ttdl_chunks = list(dsttmc.ttdm.sub_container._chunks)
        ttdl_chunks[5] = srctmc.ttdm.sub_container.chunks[5]
        ttdl, ttdl_ldata = serialize_container(b'TTDL', ttdl_chunks, separating_body = True, aligned = 0x40)
        ttdh = serialize_container(
                b'TTDH', ( struct.pack('< IIqqq', 1, i, 0, 0, 0) for i in range(len(ttdl_chunks)) ),
                (0x1).to_bytes(4, 'little')
        )
        dsttmc_chunks[dsttmc_chunks.index(dsttmc.ttdm._data)] = serialize_container(b'TTDM', (), ttdh, ttdl)

        src_slice = slice(0x18, 0x18+0x11)
        # OPTscat object has just one GeoDecl so we just copy all fo them.
        V, I = zip(*(
                ( bytearray(srctmc.vtxlay.chunks[c.vertex_buffer_index]),
                 bytearray(srctmc.idxlay.chunks[c.index_buffer_index]) )
                for c in srctmc.mdlgeo.chunks[src_slice] for c in c.sub_container.chunks ))

        c = dsttmc.mdlgeo.chunks[0xf].sub_container.chunks[0]
        vidx = c.vertex_buffer_index
        iidx = c.index_buffer_index
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
            s = b''.join( struct.pack('< iI', i+0x11*(i>=0xf), j) for i,j in xrefs )
            struct.pack_into(f'< {len(s)}s', c, 0xd8, s)
        c = mtrcol_chunks[6]
        xrefs = list(dsttmc.mtrcol.chunks[6].xrefs)
        n = len(xrefs) + 0x11
        c += ((0xd8 + 8*n) - len(c)) * b'\0'
        xrefs += ( (i, 1) for i in range(0xf, 0xf+0x11) )
        xrefs.sort()
        s = b''.join( struct.pack('< iI', i, j) for i,j in xrefs )
        # xref count
        struct.pack_into(f'< I{len(s)}s', c, 0xd4, n, s)
        dsttmc_chunks[dsttmc_chunks.index(dsttmc.mtrcol._data)] = serialize_container(b'MtrCol', mtrcol_chunks)

        mdlgeo_chunks = list(dsttmc.mdlgeo._chunks)
        mdlgeo_chunks[0xf:0xf] = ( bytearray(c) for c in srctmc.mdlgeo._chunks[src_slice] )
        mdlgeo_chunks[0xf+0x11:] = ( bytearray(c) for c in mdlgeo_chunks[0xf+17:] )
        for objgeo in mdlgeo_chunks[0xf:0xf+0x11]:
            for o in offset_table_of(objgeo):
                # mtrcol index
                struct.pack_into('< I', objgeo, o+0x4, 6)
                # texture index
                _, _, texture_info_count = struct.unpack_from(f'< ii4xI', objgeo, o)
                texture_info_offset_table = struct.unpack_from(f'< {texture_info_count}I', objgeo, o+0x10)
                # albedo
                struct.pack_into('< I', objgeo, o+texture_info_offset_table[0]+0x8, 5)
                # overlay color
                struct.pack_into('< I', objgeo, o+texture_info_offset_table[1]+0x8, 15)
                # normal
                struct.pack_into('< I', objgeo, o+texture_info_offset_table[2]+0x8, 0)

        for idx, objgeo in enumerate(mdlgeo_chunks[0xf:], 0xf):
            # obj index
            struct.pack_into('< I', objgeo, 0x34, idx)

            o, = struct.unpack_from('< I', objgeo, 0x28)
            geodecl = memoryview(objgeo)[o:]
            for o in offset_table_of(geodecl):
                struct.pack_into('< I', geodecl, o+0xc, iidx)
                iidx += 1

                vertex_info_offset, = struct.unpack_from('< 4xI', geodecl, o)
                vertex_buffer_index, = struct.unpack_from('< I', geodecl, o+vertex_info_offset)
                struct.pack_into('< I', geodecl, o+vertex_info_offset, vidx)
                vidx += 1
        dsttmc_chunks[dsttmc_chunks.index(dsttmc.mdlgeo._data)] = serialize_container(b'MdlGeo', mdlgeo_chunks)

        mdlinfo_chunks = list(dsttmc.mdlinfo._chunks)
        mdlinfo_chunks[0xf:0xf] = ( bytearray(c) for c in srctmc.mdlinfo._chunks[src_slice] )
        mdlinfo_chunks[0xf+0x11:] = ( bytearray(c) for c in mdlinfo_chunks[0xf+17:] )
        for idx, objinfo in enumerate(mdlinfo_chunks[0xf:], 0xf):
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
                C = list( i+0x11*(i>=0xf) for i in a.children )
                C += range(0xf, 0xf+0x11)
                C.sort()
                struct.pack_into(f'< {len(C)}i', c, 0x50, *C)
            else:
                # child index
                struct.pack_into(f'< {len(a.children)}i', c, 0x50, *( i+0x11*(i>=0xf) for i in a.children ))

        hielay_chunks[0xf:0xf] = ( bytearray(c) for c in srctmc.hielay._chunks[src_slice] )
        for c in hielay_chunks[0xf:0xf+0x11]:
            # parent, child count and level
            struct.pack_into('< III', c, 0x40, root_index, 0, 1)
        dsttmc_chunks[dsttmc_chunks.index(dsttmc.hielay._data)] = serialize_container(b'HieLay', hielay_chunks, b'', dsttmc.hielay._sub_container)

        nodelay_chunks = list( bytearray(c) for c in dsttmc.nodelay._chunks )
        for i, nodeobj in enumerate(nodelay_chunks):
            ng = dsttmc.nodelay.chunks[i].chunks[0].node_group
            o, = offset_table_of(nodeobj)
            struct.pack_into(f'< {len(ng)}i', nodeobj, o+0x50, *( i+0x11*(i>=0xf) for i in ng ))

        nodelay_chunks[0xf:0xf] = ( bytearray(c) for c in srctmc.nodelay._chunks[src_slice] )
        for idx, nodeobj in enumerate(nodelay_chunks[0xf:], 0xf):
            # node index
            struct.pack_into('< I', nodeobj, 0x38, idx)
            o, = offset_table_of(nodeobj)
            # obj index and node index (both are the same for enemies models)
            struct.pack_into('< I', nodeobj, o, idx)
            struct.pack_into('< I', nodeobj, o+8, idx)
        dsttmc_chunks[dsttmc_chunks.index(dsttmc.nodelay._data)] = serialize_container(b'NodeLay', nodelay_chunks, dsttmc.nodelay._metadata)

        glblmtx_chunks = list(dsttmc.glblmtx._chunks)
        glblmtx_chunks[0xf:0xf] = srctmc.glblmtx._chunks[src_slice]
        dsttmc_chunks[dsttmc_chunks.index(dsttmc.glblmtx._data)] = serialize_container(b'GlblMtx', glblmtx_chunks)

        bnofsmtx_chunks = list(dsttmc.bnofsmtx._chunks)
        bnofsmtx_chunks[0xf:0xf] = srctmc.bnofsmtx._chunks[src_slice]
        dsttmc_chunks[dsttmc_chunks.index(dsttmc.bnofsmtx._data)] = serialize_container(b'BnOfsMtx', bnofsmtx_chunks)

        lheader_chunks = list(dsttmc.lheader._chunks)
        lheader_chunks[lheader_chunks.index(dsttmc.lheader.ttdl)] = ttdl_ldata
        lheader_chunks[lheader_chunks.index(dsttmc.lheader.vtxlay)] = vtxlay_ldata
        lheader_chunks[lheader_chunks.index(dsttmc.lheader.idxlay)] = idxlay_ldata
        lheader, lheader_ldata = serialize_container(b'LHeader', lheader_chunks, dsttmc.lheader._metadata, separating_body = True, aligned = 0x80)
        dsttmc_chunks[dsttmc_chunks.index(dsttmc.lheader._data)] = lheader

        dsttmc_chunks[13] = c = bytearray(dsttmc._chunks[13])
        x, = struct.unpack_from('< H', c, 4*4)
        struct.pack_into('< H', c, 4*4, x+0x11)
        x, = struct.unpack_from('< H', c, 4*5)
        struct.pack_into('< HH', c, 4*5, 0xf, x+0x11)

        x = dsttmc._chunks[14]
        n = len(nodelay_chunks)
        n += -n%8
        dsttmc_chunks[14] = y = bytearray(4*n + 0x60*len(nodelay_chunks))
        O = range(4*n, len(y), 0x60)
        R = struct.unpack_from(f'< {n-0x11}I', x)
        y[O[0]:O[0xf]] = x[R[0]:R[0xf]]
        for i, o in enumerate(O[0xf:0xf+0x11]):
            struct.pack_into('< III', y, o, 5, 3, i)
        y[O[0xf+0x11]:] = x[R[0xf]:]
        struct.pack_into(f'< {len(O)}I', y, 0, *O)

        new_tmc = serialize_container(b'TMC', dsttmc_chunks, dsttmc._metadata)

def offset_table_of(x):
    n, = struct.unpack_from('< I', x, 0x14)
    o, = struct.unpack_from('< I', x, 0x20)
    return struct.unpack_from(f' {n}I', x, o)

def mmap_open(path):
    with open(path, 'rb') as f: 
        return mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ)

def save(path, data):
    with open(path, 'wb') as f:
        f.write(data)

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

if __name__ == '__main__':
    main()
