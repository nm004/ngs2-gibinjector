import mmap
import os.path
import sys
from .tmc11 import TMCParser
from itertools import accumulate
import argparse
import struct

def mmap_open(path):
    with open(path, 'rb') as f: 
        return mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('-o', '--output-dir', dest='outdir', default='.')
    parser.add_argument('-e', '--extract-by-index', nargs=1, type=int)
    parser.add_argument('-E', '--extract-all', action='store_true')
    parser.add_argument('tmc')
    parser.add_argument('tmcl')
    args = parser.parse_args()
    outdir = args.outdir

    if ((not args.extract_by_index and not args.extract_all)
        or (args.extract_by_index and args.extract_all)):
        print('You have to specify one of --extract-by-index or --extract-all.', file=sys.stderr)
        return

    if not os.path.isdir(outdir):
        print(f'output directory "{outdir}" not exist.', file=sys.stderr)
        return

    tmc_m, tmcl_m = mmap_open(args.tmc), mmap_open(args.tmcl)
    tmc = TMCParser(tmc_m, tmcl_m)
    with tmc_m, tmcl_m, tmc:
        textures = tuple(generate_textures(tmc.ttdm))
        n = len(str(len(textures)))
        j = lambda i: os.path.join(args.outdir, str(i).zfill(n)+'.dds')
        if args.extract_all:
            for i, t in enumerate(textures):
                save(j(i), t)
        else:
            save(j(i), textures[args.e])

def generate_textures(ttdm):
    for h in ttdm.metadata.chunks:
        if h.is_in_L:
            yield ttdm.sub_container.chunks[h.index]
        else:
            yield ttdm.chunks[h.index]

def save(path, data):
    with open(path, 'wb') as f:
        f.write(data)

def mmap_aiueo(n):
    with open(os.path.join(r'R:\tmp\aiueo', str(n).zfill(5) + '.dat'), 'rb') as f:
        return mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ)

def offset_table_of(x):
    n, = struct.unpack_from('< I', x, 0x14)
    o, = struct.unpack_from('< I', x, 0x20)
    return struct.unpack_from(f' {n}I', x, o)

def main2():
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
        ttdl, ttdl_ldata = serialize_container(b'TTDL', ttdl_chunks, separating_body = True)
        ttdh = serialize_container(
                b'TTDH', ( struct.pack('< IIqqq', 1, i, 0, 0, 0) for i in range(len(ttdl_chunks)) ),
                (0x1).to_bytes(4, 'little')
        )
        dsttmc_chunks[dsttmc_chunks.index(dsttmc.ttdm._data)] = serialize_container(b'TTDM', (), ttdh, ttdl)

        src_slice = slice(24, 24+17)
        idxlay_chunks = list(dsttmc.idxlay._chunks)
        vtxlay_chunks = list(dsttmc.vtxlay._chunks)
        mdlgeo_chunks = list(dsttmc.mdlgeo._chunks)
        for objgeo in srctmc.mdlgeo._chunks[src_slice]:
            idx = len(mdlgeo_chunks)
            objgeo = bytearray(objgeo)
            mdlgeo_chunks.append(objgeo)

            # obj index
            struct.pack_into('< I', objgeo, 0x34, idx)

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

            # index buffers and vertex buffers
            o, = struct.unpack_from('< I', objgeo, 0x28)
            geodecl = memoryview(objgeo)[o:]
            S = set()
            T = set()
            for o in offset_table_of(geodecl):
                _, vertex_info_offset, _, index_buffer_index = struct.unpack_from('< IIII', geodecl, o)
                if index_buffer_index not in S:
                    S.add(index_buffer_index)
                    struct.pack_into('< I', geodecl, o+0xc, len(idxlay_chunks))
                    idxlay_chunks.append(srctmc.idxlay._chunks[index_buffer_index])

                vertex_buffer_index, = struct.unpack_from('< I', geodecl, o+vertex_info_offset)
                if vertex_buffer_index not in T:
                    T.add(vertex_buffer_index)
                    struct.pack_into('< I', geodecl, o+vertex_info_offset, len(vtxlay_chunks))
                    vtxlay_chunks.append(srctmc.vtxlay._chunks[vertex_buffer_index])
        dsttmc_chunks[dsttmc_chunks.index(dsttmc.mdlgeo._data)] = serialize_container(b'MdlGeo', mdlgeo_chunks)

        vtxlay, vtxlay_ldata = serialize_container(b'VtxLay', vtxlay_chunks, separating_body = True)
        dsttmc_chunks[dsttmc_chunks.index(dsttmc.vtxlay._data)] = vtxlay
        idxlay, idxlay_ldata = serialize_container(b'IdxLay', idxlay_chunks, separating_body = True)
        dsttmc_chunks[dsttmc_chunks.index(dsttmc.idxlay._data)] = idxlay

        mdlinfo_chunks = list(dsttmc.mdlinfo._chunks)
        n = len(mdlinfo_chunks)
        for objinfo, idx in zip(srctmc.mdlinfo._chunks[src_slice], range(n, n+17)):
            objinfo = bytearray(objinfo)
            mdlinfo_chunks.append(objinfo)
            # obj index
            struct.pack_into('< I', objinfo, 0x34, idx)
        dsttmc_chunks[dsttmc_chunks.index(dsttmc.mdlinfo._data)] = serialize_container(b'MdlInfo', mdlinfo_chunks)

        for i, c in enumerate(dsttmc.hielay.chunks):
            if c.parent == -1:
                break
        root_chunk = c
        root_index = i

        hielay_chunks = list(dsttmc.hielay._chunks)
        for c in srctmc.hielay._chunks[src_slice]:
            c = bytearray(c)
            hielay_chunks.append(c)
            # parent, child count and level
            struct.pack_into('< III', c, 0x40, root_index, 0, 1)
        c = bytearray(hielay_chunks[root_index])
        hielay_chunks[root_index] = c

        # child count of root
        struct.pack_into('< I', c, 4*16+4, len(root_chunk.children) + 17)

        # child index of root
        x = struct.calcsize(f'< {len(root_chunk.children)}i')
        c.extend((struct.calcsize('< 17i') - (-x % 0x10)) * b'\0')
        n = len(dsttmc.hielay._chunks)
        struct.pack_into('< 17i', c, 0x50+x, *range(n, n+17))
        dsttmc_chunks[dsttmc_chunks.index(dsttmc.hielay._data)] = serialize_container(b'HieLay', hielay_chunks)

        nodelay_chunks = list(dsttmc.nodelay._chunks)
        n = len(nodelay_chunks)
        for nodeobj, idx in zip(srctmc.nodelay._chunks[src_slice], range(n, n+17)):
            nodeobj = bytearray(nodeobj)
            nodelay_chunks.append(nodeobj)

            # node index
            struct.pack_into('< I', nodeobj, 0x38, idx)
            for o in offset_table_of(nodeobj):
                # obj index and node index (both are the same for enemies models)
                struct.pack_into('< I4xI', nodeobj, o, idx, idx)
        dsttmc_chunks[dsttmc_chunks.index(dsttmc.nodelay._data)] = serialize_container(b'NodeLay', nodelay_chunks)

        glblmtx_chunks = list(dsttmc.glblmtx._chunks)
        glblmtx_chunks.extend(srctmc.glblmtx._chunks[src_slice])
        dsttmc_chunks[dsttmc_chunks.index(dsttmc.glblmtx._data)] = serialize_container(b'GlblMtx', glblmtx_chunks)

        bnofsmtx_chunks = list(dsttmc.bnofsmtx._chunks)
        bnofsmtx_chunks.extend(srctmc.bnofsmtx._chunks[src_slice])
        dsttmc_chunks[dsttmc_chunks.index(dsttmc.bnofsmtx._data)] = serialize_container(b'BnOfsMtx', bnofsmtx_chunks)

        lheader_chunks = list(dsttmc.lheader._chunks)
        lheader_chunks[lheader_chunks.index(dsttmc.lheader.ttdl)] = ttdl_ldata
        lheader_chunks[lheader_chunks.index(dsttmc.lheader.idxlay)] = idxlay_ldata
        lheader_chunks[lheader_chunks.index(dsttmc.lheader.vtxlay)] = vtxlay_ldata
        lheader, lheader_ldata = serialize_container(b'LHeader', lheader_chunks, dsttmc.lheader._metadata, separating_body = True)
        dsttmc_chunks[dsttmc_chunks.index(dsttmc.lheader._data)] = lheader

        c = bytearray(dsttmc._chunks[13])
        struct.pack_into('< HH', c, 0x14, len(dsttmc.nodelay._chunks), 17)
        dsttmc_chunks[13] = c

        c = bytearray(dsttmc._chunks[14])
        x = struct.calcsize(f'< {len(dsttmc.nodelay._chunks)}I')
        c_head = c[:x + (-x % 0x20)]
        c_body = c[len(c_head):]
        x = (struct.calcsize('< 17i') - (-x % 0x20))
        x += -x % 0x20
        c_head.extend(x * b'\0')
        c = c_head + c_body
        struct.pack_into(f'< {len(nodelay_chunks)}I', c, 0, *(range(len(c_head), len(c_head) + len(nodelay_chunks)*0x60, 0x60)))
        c.extend(0x60 * 17 * b'\0')
        for i, o in enumerate(struct.unpack_from('< 17I', c, struct.calcsize(f'< {len(dsttmc.nodelay._chunks)}I'))):
            struct.pack_into('< III', c, o, 5, 3, i)
        dsttmc_chunks[14] = c

        new_tmc = serialize_container(b'TMC', dsttmc_chunks, dsttmc._metadata)
    with open(r'R:\tmp\aiueo\00000.dat', 'wb') as f:
        f.write(new_tmc)
    with open(r'R:\tmp\aiueo\00001.dat', 'wb') as f:
        f.write(lheader_ldata)

def serialize_container(magic, chunks = (), metadata = b'', sub_container = b'', *, separating_body = False):
    chunks = tuple( memoryview(c) for c in chunks )
    tuple_of_chunk_nbytes = tuple( c.nbytes for c in chunks )
    metadata = memoryview(metadata)
    sub_container = memoryview(sub_container)
    separating_body = bool(separating_body)

    # We calculate sizes and offsets first.
    valid_chunk_count = sum( i > 0 for i in tuple_of_chunk_nbytes )
    offset_table_nbytes = struct.calcsize(f'<{len(chunks)}I')
    offset_table_nbytes += -offset_table_nbytes % 0x10
    size_table_nbytes = offset_table_nbytes * any( i % 0x10 for i in tuple_of_chunk_nbytes )
    chunks_nbytes = sum( i + -i % 0x10 for i in tuple_of_chunk_nbytes )
    metadata_pos = 0x50 if separating_body else 0x30
    metadata_end = metadata_pos + metadata.nbytes
    metadata_end += -metadata_end % 0x10
    offset_table_pos = metadata_end * (offset_table_nbytes > 0)
    size_table_pos = (offset_table_pos + offset_table_nbytes) * (size_table_nbytes > 0)
    sub_container_pos = (metadata_end + offset_table_nbytes + size_table_nbytes) * (sub_container.nbytes > 0)

    i0 = ( 0x10 * separating_body
          or sub_container_pos + sub_container.nbytes
          or size_table_pos + size_table_nbytes
          or offset_table_pos + offset_table_nbytes)
    I = accumulate(( i + -i % 0x10 for i in tuple_of_chunk_nbytes[:-1] ), initial=i0)
    offset_table = (offset_table_pos > 0) * tuple( i*(j > 0) for i,j in zip(I, tuple_of_chunk_nbytes) )
    size_table = (size_table_pos > 0) * tuple( i for i in tuple_of_chunk_nbytes )

    data = bytearray(
            metadata_end
            + offset_table_nbytes
            + size_table_nbytes
            + sub_container.nbytes
            + chunks_nbytes * (not separating_body)
    )
    ldata = bytearray((0x10 + chunks_nbytes) * separating_body)

    # Let's pack the data.
    struct.pack_into(
            '< 8sII III4x III', data, 0,
            magic, 0x01010000, metadata_pos,
            len(data), len(chunks), valid_chunk_count,
            offset_table_pos, size_table_pos, sub_container_pos
    )

    if ldata:
        struct.pack_into(
                '< III', data, 0x40,
                valid_chunk_count, len(ldata), 0x01234567
        )
        ldata[:0x10] = data[0x40:0x50]

    struct.pack_into(f'< {metadata.nbytes}s', data, metadata_pos, metadata.tobytes())
    struct.pack_into(f'< {len(offset_table)}I', data, offset_table_pos, *offset_table)
    struct.pack_into(f'< {len(size_table)}I', data, size_table_pos, *size_table)
    struct.pack_into(f'< {sub_container.nbytes}s', data, sub_container_pos, sub_container.tobytes())

    A = ldata or data
    for o, c in zip(offset_table, chunks):
        A[o:o+c.nbytes] = c

    return (ldata and (data, ldata)) or data

# This assumes that the objects are soreted
def make_nodetypes(tmc, /, *, key=None):
    nodetype_map = {
        b'MOT': 1,
        b'WGT': 3,
        b'SUP': 4,
        b'OPT': 5,
        b'WPB': 7,
    }

    # First, let's make a head.
    # 10*(ofs + count) + name
    size = 10*(2 + 2) + 0x58
    head = memoryview(bytearray(size))

    K = sorted(nodetype_map, key=key)
    C = tuple( sum( 1 for nodeobj in tmc.nodelay
                    if nodeobj.name.startswith(s) )
               for s in K )
    h = head.cast('H')
    for i, (c, k) in enumerate(zip(C, K)):
        j = nodetype_map[k]
        if c:
            h[2*j], h[2*j+1] = sum( d for d in C[:i] ), c

    head[0x28:0x28+len(tmc.name)] = tmc.name

    # Let's make a body.
    # item_offset_table + item
    t = 4*len(tmc.nodelay)
    t += -t % 0x20
    # content_offset_table + 0x60*contents
    size = t + 0x60*len(tmc.nodelay)
    body = memoryview(bytearray(size))

    o = t
    for i in range(len(tmc.nodelay)):
        body.cast('I')[i] = o
        o += 0x60

    optblur = 0
    optr = 0
    optscat = 0
    optacs = 0
    optcorpse = 0
    T = body.cast('I')[:len(tmc.nodelay)]
    N = ( nodeobj.name for nodeobj in tmc.nodelay )
    for i, n in zip(T, N):
        B = body[i:].cast('I')
        t = nodetype_map[n[:3]]
        B[0] = t
        if t != 5:
            continue
        n = n[3:]
        b = body[i:].cast('I')
        if n.startswith(b'blur'):
            B[1] = 1
            B[2] = optblur
            optacs += 1
        elif n.startswith(b'r_'):
            B[1] = 2
            B[2] = optr
            optr += 1
        elif n.startswith(b'scat'):
            B[1] = 3
            B[2] = optscat
            optscat += 1
        elif n.startswith(b'_acs') or n.startswith(b'kami'):
            B[1] = 4
            B[2] = optacs
            optacs += 1
        elif n.startswith(b'corpse'):
            B[1] = 0xB
            B[2] = optcorpse
            optcorpse += 1
        else:
            raise ValueError(f'No matching OPT NodeObj subtype found for "{n}".')


if __name__ == '__main__':
    main2()
    #main()
