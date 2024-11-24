import os
import mmap
import enum
import itertools
import argparse
import databintool
import tmc11

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('-o', '--output-dir', dest='outdir', default='.')
    parser.add_argument('databin')
    args = parser.parse_args()
    outdir = args.outdir
    if not os.path.isdir(outdir):
        print(f'output directory "{outdir}" not exist.', file=sys.stderr)
        return

    with (open(args.databin, 'rb') as db_f,
          mmap.mmap(db_f.fileno(), 0, access=mmap.ACCESS_READ) as db_m):
        db = None
        try:
            db = databintool.DatabinParser(db_m)
            b = fix_bloodstain(db)
            save(b, args.outdir, 4413)
        finally:
            if db:
                del db

def fix_bloodstain(db):
    effpk = databintool.decompress(db.chunks[4413])
    effpk_L = databintool.decompress(db.chunks[4414])
    tmc = tmc11.TMCParser(effpk, effpk_L)
    epm1 = list(tmc.epm1.packs[0])
    cmn_blood = epm1[41].packs[0].packs
    workpack = list(cmn_blood[0][0].packs)
    # workpack[11] = (list(workpack[93]), workpack[13][1])

    # w = workpack[13][0]

    # # Color mode (RGB = 0, ? = 1, CMYK = 2)
    # w[0][] = 2

    # # CMYK color
    # w[0][] = 1

    # # Size of the decal
    # w[0][]

    # # Repeat count at once
    # w[0][]

    # # 
    # w[0][]

    tmc2 = list(tmc._chunks)
    blobs = [ b''.join(j._data for j in i.packs) for i in epm1 ]
    # blobs[41] = sealize_workpack(workpack)
    tmc2[11] = serialize_epm1(tmc.epm1._data[0x20:0x20+0x690], blobs)
    return serialize_tmc(b'TMC', tmc2, meta_data = tmc._meta_data)

def serialize_sdp1(category, param_info, blobs):
    param_table_size = len(param_info)
    pack_table_size = 4 * 2 * len(blobs)
    blob_table_size = sum( len(b) for b in blobs )
    B = bytearray(0x30 + param_table_size + pack_table_size + blob_table_size)

    match category:
        case SDP1Enum.EPM1:
            magic = b'EPM1'
        case SDP1Enum.WorkPack:
            magic = b'WorkPack'

    B[0x0:0x8] = magic.ljust(0x8, b'\x00')
    B[0x8:0xc] = b'1PDS'
    B[0xc:0x10] = len(B).to_bytes(4, 'little')
    B[0x10:0x14] = len(param_info).to_bytes(4, 'little')
    B[0x14:0x18] = int(category).to_bytes(4, 'little')
    B[0x18:0x1c] = 0x0.to_bytes(4, 'little')
    B[0x1c:0x20] = (pack_table_size // 4).to_bytes(4, 'little')
    x = 0x30
    param_info_table_ofs = x
    B[0x20:0x24] = param_info_table_ofs.to_bytes(4, 'little')
    x += param_table_size
    pack_table_ofs = bool(pack_table_size) * x
    B[0x24:0x28] = pack_table_ofs.to_bytes(4, 'little')
    x += pack_table_size
    blob_table_ofs = bool(blob_table_size) * x
    B[0x2c:0x30] = blob_table_ofs.to_bytes(4, 'little')

    B[0x30:0x30+len(param_info)] = param_info

    O = range(pack_table_ofs, pack_table_ofs + pack_table_size, 0x8)
    o2 = blob_table_ofs
    for o, b in zip(O, blobs):
        B[o:o+4] = o2.to_bytes(4, 'little')
        B[o+4:o+8] = len(b).to_bytes(4, 'little')
        B[o2:o2+len(b)] = b
        o2 += len(b)

    return B

def serialize_epm1(param_info, blobs):
    B = serialize_sdp1(SDP1Enum.EPM1, param_info, blobs)
    return B

def serialize_workpack(workpack):
    # n = sum( len(p) for p in itertools.chain.from_iterable(workpack) if p )
    # B = write_head(B, b'WorkPack')

    # # This writes pack table
    # M = memoryview(B)[0x].cast('I')
    # o =
    # for i, P in zip(range(0, x, 2), bank_packs):
    #     for j, p in enumerate(P):
    #         if p:
    #             B[o:o+n] = p.ljust(len(p) + -len(p) % 0x10, b'\x00')
    #             M[i+j] = o
    #             o += len(p)

    return bytes(B)

class SDP1Enum(enum.IntEnum):
    EPM1 = 0
    WorkPack = 6

# class MdlGeo:
#     @staticmethod
#     def _gen_mdlgeo_chunks(objgeo):
#         for i, o in enumerate(objgeo):
#             meta_data = bytearray(0x20)
#             meta_data[:0x4] = 0x0300_0100.to_bytes(4)
#             meta_data[0x4:0x8] = i.to_bytes(4, 'little')
#             meta_data += o.name + b'\x00'
#             yield serialize(b'ObjGeo', chunks, meta_data = meta_data,
#                             sub_container = bytes(o.geodecl))

# class GeoDecl:
#     @staticmethod
#     def _gen_chunks(data):
#         D = { id(v):i for i,v in enumerate(idxlay.buffer) }
#         for d in data:
#             B = bytearray(d.chunk)
#             # i = D[id(c.index_buffer)]
#             # B[0xc:0x10] = i.to_bytes(4, 'little')
#             # B[0x10:0x14] = len(c.index_buffer).to_bytes(4, 'little')
#             # B[0x14:0x18] = (len(c.vertex_buffer)//c.vertex_size).to_bytes(4, 'little')
#             # B[0x38:0x3c] = i.to_bytes(4, 'little')
#             yield B

# class TTDM:
#     @staticmethod
#     def _gen_ttdh_chunks(textures):
#         for i, t in enumerate(textures):
#             B = bytearray(0x20)
#             B[0x0] = 1
#             B[0x4:0x8] = i.to_bytes(4, 'little', signed=True)
#             yield B

# class MtrCol:
#     @staticmethod
#     def _gen_chunks(data, xref):
#         for i, d in enumerate(data):
#             B = bytearray(0xd8 + 8*len(xref))
#             B[0x0:0xd0] = bytes(d)
#             B[0xd0:0xd4] = i.to_bytes(4, 'little')
#             B[0xd4:0xd8] = len(xref).to_bytes(4, 'little')
#             for o, (i, j) in zip(range(0xd8, len(B), 8), xref):
#                 B[o:o+4] = i
#                 B[o+4:o+8] = j
#             yield B

# class MdlInfo:
#     @staticmethod
#     def _gen_chunks(objinfo):
#         for i, o in enumerate(objinfo):
#             meta_data = bytearray(o._meta_data.rjust(0x10, b'\x00'))
#             meta_data[0x0:0x4] = 0x0300_0200.to_bytes(4)
#             meta_data[0x4:0x8] = i.to_bytes(4, 'little')
#             meta_data[0xc:0x10] = o.obj_type.to_bytes(4, 'little')
#             yield serialize(b'ObjInfo', o._chunks, meta_data = meta_data)

# class HieLay:
#     @staticmethod
#     def _gen_chunks(nodes):
#         D = { v:i for i,v in enumerate(nodes) }
#         for n in nodes:
#             B = bytearray(0x50 + 4*len(n.children))

#             B[0x0:0x40] = bytes(n.matrix)

#             i = (n.parent and D[n.parent]) or -1
#             B[0x40:0x44] = i.to_bytes(4, 'little', signed=True)
#             B[0x44:0x48] = len(n.children).to_bytes(4, 'little')

#             level = 0
#             p = n.parent
#             while p:
#                 level += 1
#                 p = p.parent
#             B[0x48:0x4c] = level.to_bytes(4, 'little')

#             for o, i in zip(range(0x50, len(B), 4), sorted( D[c] for c in n.children )):
#                 B[o:o+4] = i.to_bytes(4, 'little')
#             yield B

# class NodeLay:
#     @staticmethod
#     def _gen_chunks(nodeobjs):
#         obj_id = 0
#         D = { v:i for i,v in enumerate(nodeobjs) }
#         for node_id, n in enumerate(nodeobjs):
#             if n.matrix:
#                 B = bytearray(0x50 + 4*len(n.nodes))
#                 B[0x0:0x4] = obj_id.to_bytes(4, 'little', signed=True)
#                 B[0x4:0x8] = len(n.nodes).to_bytes(4, 'little')
#                 B[0x8:0xc] = node_id.to_bytes(4, 'little', signed=True)
#                 B[0x10:0x50] = bytes(n.matrix)
#                 for o, i in zip(range(0x50, len(B), 4), sorted( D[m] for m in n.nodes )):
#                     B[o:o+4] = i.to_bytes(4, 'little', signed=True)
#                 chunks = (B,)
#                 obj_id += 1
#             else:
#                 chunks = ()

#             meta_data = bytearray(0x10)
#             meta_data[0x4:0x8] = (-1).to_bytes(4, signed=True)
#             meta_data[0x8:0xc] = node_id.to_bytes(4, 'little', signed=True)
#             meta_data += n.name + b'\x00'
#             yield serialize(b'NodeObj', chunks, meta_data=meta_data)

def serialize_tmc(magic_bytes, chunks, /, are_chunks_in_L = False, meta_data = b'', sub_container = b''):
    chunks = tuple( memoryview(c) for c in chunks )
    sub_container = memoryview(sub_container)
    meta_data = memoryview(meta_data)
    are_chunks_in_L = bool(are_chunks_in_L)

    head_size = (are_chunks_in_L and 0x50) or 0x30

    meta_data_size = meta_data.nbytes + -meta_data.nbytes % 0x10
    chunk_ofs_table_size = 4*len(chunks) + -4*len(chunks) % 0x10
    chunk_size_table_size = chunk_ofs_table_size * are_chunks_in_L #any( c.nbytes % 0x10 for c in chunks )
    sub_container_size = sub_container.nbytes + -sub_container.nbytes % 0x10
    chunk_sizes = tuple( c.nbytes + -c.nbytes % 0x10 for c in chunks )
    total_chunk_size = sum(chunk_sizes)
    container_size = ( head_size
                       + meta_data_size
                       + chunk_ofs_table_size
                       + chunk_size_table_size
                       + sub_container_size
                       + bool(not are_chunks_in_L) * total_chunk_size )
    B = bytearray(container_size)
    B[0:8] = magic_bytes.ljust(8, b'\x00')
    B[0x8:0xc] = 0x00000101.to_bytes(4)
    B[0xc:0x10] = head_size.to_bytes(4, 'little')
    B[0x10:0x14] = container_size.to_bytes(4, 'little')
    B[0x14:0x18] = len(chunks).to_bytes(4, 'little')
    valid_chunk_count = sum( n > 0 for n in chunk_sizes )
    B[0x18:0x1c] = valid_chunk_count.to_bytes(4, 'little')

    n = head_size + meta_data_size
    chunk_ofs_table_ofs = n * bool(chunk_ofs_table_size)
    B[0x20:0x24] = chunk_ofs_table_ofs.to_bytes(4, 'little')
    n += chunk_ofs_table_size
    chunk_size_table_ofs = n * bool(chunk_size_table_size)
    B[0x24:0x28] = chunk_size_table_ofs.to_bytes(4, 'little')
    n += chunk_size_table_size
    sub_container_ofs = n * bool(sub_container)
    B[0x28:0x2c] = sub_container_ofs.to_bytes(4, 'little')

    if are_chunks_in_L:
        B[0x40:0x44] = valid_chunk_count.to_bytes(4, 'little')
        lcontainer_size = 0x10 + meta_data_size + total_chunk_size
        B[0x44:0x48] = lcontainer_size.to_bytes(4, 'little')
        B[0x48:0x4c] = (0x01234567).to_bytes(4, 'little')

    if meta_data:
        o1 = head_size
        o2 = o1 + meta_data.nbytes
        B[o1:o2] = bytes(meta_data)

    if chunk_ofs_table_ofs:
        x = ( are_chunks_in_L
              and 0x10 + meta_data_size
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

    if not are_chunks_in_L and chunks:
        o1 = chunk_ofs_table_ofs
        o2 = o1 + 4*len(chunks)
        O = memoryview(B[o1:o2]).cast('I')
        for o1, c in zip(O, chunks):
            o2 = o1 + c.nbytes
            B[o1:o2] = bytes(c)

    return bytes(B)

def serialize_L(chunks, meta_data = b''):
    chunks = tuple( memoryview(c) for c in chunks )
    meta_data = memoryview(meta_data)

    meta_data_size = meta_data.nbytes + -meta_data.nbytes % 0x10
    chunk_sizes = tuple( c.nbytes + -c.nbytes % 0x10 for c in chunks )
    total_chunk_size = sum(chunk_sizes)

    lcontainer_size = 0x10 + meta_data_size + total_chunk_size
    B = bytearray(lcontainer_size)
    B[0x0:0x4] = sum( n > 0 for n in chunk_sizes ).to_bytes(4, 'little')
    B[0x4:0x8] = lcontainer_size.to_bytes(4, 'little')
    B[0x8:0xc] = (0x01234567).to_bytes(4, 'little')

    o = 0x10 + meta_data_size
    for c, n in zip(chunks, chunk_sizes):
        o2 = o+c.nbytes
        B[o:o2] = c
        o += n

    return bytes(B)

def save(data, outdir, i):
    path = os.path.join(outdir, f'{i:05}.dat')
    print(f"output: {path}")
    with open(path, 'wb') as f:
        f.write(data)

if __name__ == '__main__':
    main()
