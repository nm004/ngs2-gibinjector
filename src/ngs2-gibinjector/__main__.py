#!/usr/bin/python3
# NGS2 Gib Injector by Nozomi Miyamori is marked with CC0 1.0.
# This file is a part of NGS2 Gib Injector.
#
# This module is for modding enemy TMC files in NINJA GAIDEN SIGMA 2
# Master Collection. This injects missing gib mesh objects and gib textures
# to TMC files.
import mmap
import os
import os.path
import argparse
from operator import itemgetter
from databin import Databin
from collections import Counter
from tmc import TMC, LHeader, TTDH, MtrCol, HieLay, MdlGeo

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
        inject_optscat(Databin(db_m), outdir)

def inject_optscat(databin, outdir):
    # e_okm_* has a redder gib texture and small OPTscat objects.
    e_okm_a = extract_tmc(databin, 1098, mutable=False)
    # e_gja_* has a bit higher res gib normal, so we are gonna use it too.
    e_gja_a = extract_tmc(databin, 1163, mutable=False)
    # e_chg_g has a green gib texture.
    e_chg_a = extract_tmc(databin, 1116, mutable=False)
    # e_tky_* has scrap OPTscat objects.
    e_tky_b = extract_tmc(databin, 1296, mutable=False)
    # e_dgr_a and e_wlf_* has large OPTscat objects.
    e_dgr_a = extract_tmc(databin, 1119, mutable=False)

    # e_nin_a
    tmc_id = 1094
    tmc = extract_tmc(databin, tmc_id)
    copy_optscats(e_dgr_a, tmc)
    sort_objects_by_nodename(tmc)
    copy_texture_buffer(e_okm_a, 5, tmc, 5)
    copy_texture_buffer(e_gja_a, 5, tmc, 0)
    set_optscat_texture_buffer(tmc, (5, 16, 0))
    save_tmc(outdir, tmc, tmc_id)

    # e_nin_c
    tmc_id = 1262
    tmc = extract_tmc(databin, tmc_id)
    remove_optscats(tmc)
    copy_optscats(e_dgr_a, tmc)
    sort_objects_by_nodename(tmc)
    copy_texture_buffer(e_okm_a, 5, tmc, 5)
    copy_texture_buffer(e_gja_a, 5, tmc, 0)
    # e_nin_c and e_jgm_c have a different cut surface texture, but it seems that
    # there is no redder one of it. So, let's copy the redder gib texture instead
    # (other models use a gib texture as a cut surface).
    copy_texture_buffer(e_okm_a, 5, tmc, 7)
    copy_texture_buffer(e_gja_a, 5, tmc, 6)
    set_optscat_texture_buffer(tmc, (5, 17, 0))
    save_tmc(outdir, tmc, tmc_id)

    # e_nin_d
    tmc_id = 1383
    tmc = extract_tmc(databin, tmc_id)
    copy_optscats(e_dgr_a, tmc)
    sort_objects_by_nodename(tmc)
    copy_texture_buffer(e_okm_a, 5, tmc, 5)
    copy_texture_buffer(e_gja_a, 5, tmc, 0)
    set_optscat_texture_buffer(tmc, (5, 15, 0))
    save_tmc(outdir, tmc, tmc_id)

    # e_jgm_a
    tmc_id = 1090
    tmc = extract_tmc(databin, tmc_id)
    copy_optscats(e_dgr_a, tmc)
    sort_objects_by_nodename(tmc)
    copy_texture_buffer(e_okm_a, 5, tmc, 5)
    copy_texture_buffer(e_gja_a, 5, tmc, 0)
    set_optscat_texture_buffer(tmc, (5, 13, 0))
    save_tmc(outdir, tmc, tmc_id)

    # e_jgm_c
    tmc_id = 1333
    tmc = extract_tmc(databin, tmc_id)
    copy_optscats(e_dgr_a, tmc)
    sort_objects_by_nodename(tmc)
    copy_texture_buffer(e_okm_a, 5, tmc, 5)
    copy_texture_buffer(e_gja_a, 5, tmc, 6)
    set_optscat_texture_buffer(tmc, (5, 14, 6))
    save_tmc(outdir, tmc, tmc_id)

    # e_jgm_d
    tmc_id = 1817
    tmc = extract_tmc(databin, tmc_id)
    copy_optscats(e_dgr_a, tmc)
    sort_objects_by_nodename(tmc)
    copy_texture_buffer(e_okm_a, 5, tmc, 5)
    copy_texture_buffer(e_gja_a, 5, tmc, 0)
    set_optscat_texture_buffer(tmc, (5, 14, 0))
    save_tmc(outdir, tmc, tmc_id)

    # e_bni_a
    tmc_id = 1311
    tmc = extract_tmc(databin, tmc_id)
    remove_optscats(tmc)
    copy_optscats(e_dgr_a, tmc)
    sort_objects_by_nodename(tmc)
    copy_texture_buffer(e_okm_a, 5, tmc, 37)
    copy_texture_buffer(e_gja_a, 5, tmc, 0)
    set_optscat_texture_buffer(tmc, (37, 38, 0))
    save_tmc(outdir, tmc, tmc_id)

    # e_you_a
    tmc_id = 1235
    tmc = extract_tmc(databin, tmc_id)
    remove_optscats(tmc)
    copy_optscats(e_dgr_a, tmc)
    sort_objects_by_nodename(tmc)
    copy_texture_buffer(e_okm_a, 5, tmc, 12)
    copy_texture_buffer(e_gja_a, 5, tmc, 4)
    set_optscat_texture_buffer(tmc, (12, 21, 4))
    save_tmc(outdir, tmc, tmc_id)

    # e_you_c
    tmc_id = 1359
    tmc = extract_tmc(databin, tmc_id)
    remove_optscats(tmc)
    copy_optscats(e_dgr_a, tmc)
    sort_objects_by_nodename(tmc)
    copy_texture_buffer(e_gja_a, 5, tmc, 0)
    set_optscat_texture_buffer(tmc, (1, 2, 0))
    save_tmc(outdir, tmc, tmc_id)

    # e_you_d
    tmc_id = 1366
    tmc = extract_tmc(databin, tmc_id)
    remove_optscats(tmc)
    copy_optscats(e_dgr_a, tmc)
    sort_objects_by_nodename(tmc)
    copy_texture_buffer(e_okm_a, 5, tmc, 12)
    copy_texture_buffer(e_gja_a, 5, tmc, 4)
    set_optscat_texture_buffer(tmc, (12, 21, 4))
    save_tmc(outdir, tmc, tmc_id)

    # e_gja_b
    tmc_id = 1167
    tmc = extract_tmc(databin, tmc_id)
    copy_optscats(e_dgr_a, tmc)
    set_optscat_texture_buffer(tmc, (4, 13, 5))
    sort_objects_by_nodename(tmc)
    save_tmc(outdir, tmc, tmc_id)

    # e_gja_c
    tmc_id = 1376
    tmc = extract_tmc(databin, tmc_id)
    copy_optscats(e_dgr_a, tmc)
    set_optscat_texture_buffer(tmc, (4, 13, 5))
    sort_objects_by_nodename(tmc)
    save_tmc(outdir, tmc, tmc_id)

    # e_wlf_a
    tmc_id = 1112
    tmc = extract_tmc(databin, tmc_id)
    copy_texture_buffer(e_okm_a, 5, tmc, 11)
    copy_texture_buffer(e_gja_a, 5, tmc, 0)
    save_tmc(outdir, tmc, tmc_id)

    # e_wlf_b
    tmc_id = 1364
    tmc = extract_tmc(databin, tmc_id)
    copy_texture_buffer(e_okm_a, 5, tmc, 11)
    copy_texture_buffer(e_gja_a, 5, tmc, 0)
    save_tmc(outdir, tmc, tmc_id)

    # e_chg_a
    tmc_id = 1116
    tmc = extract_tmc(databin, tmc_id)
    copy_texture_buffer(e_gja_a, 5, tmc, None)
    set_optscat_texture_buffer(tmc, (13, 21, 23))
    save_tmc(outdir, tmc, tmc_id)

    # kage
    tmc_id = 1138
    tmc = extract_tmc(databin, tmc_id)
    copy_optscats(e_dgr_a, tmc)
    sort_objects_by_nodename(tmc)
    copy_texture_buffer(e_chg_a, 13, tmc, None)
    copy_texture_buffer(e_gja_a, 5, tmc, None)
    set_optscat_texture_buffer(tmc, (17, 16, 18))
    save_tmc(outdir, tmc, tmc_id)

    # e_kag_b
    tmc_id = 1148
    tmc = extract_tmc(databin, tmc_id)
    copy_optscats(e_dgr_a, tmc)
    sort_objects_by_nodename(tmc)
    copy_texture_buffer(e_chg_a, 13, tmc, None)
    copy_texture_buffer(e_gja_a, 5, tmc, None)
    set_optscat_texture_buffer(tmc, (8, 7, 9))
    save_tmc(outdir, tmc, tmc_id)

    # e_van_* need their nodes to be sorted with the following
    # order to avoid a visual glitch. This is at least as I know
    # (I don't know why).
    order = {
        v:i
        for i,v in
        enumerate((
            b'MOT', 
            b'SUP', 
            b'WPB', 
            b'OPT', 
            b'WGT',))
    }
    key = lambda x: order[x[:3]]

    # e_van_a
    tmc_id = 1107
    tmc = extract_tmc(databin, tmc_id)
    copy_optscats(e_dgr_a, tmc)
    sort_objects_by_nodename(tmc, key=key)
    copy_texture_buffer(e_chg_a, 13, tmc, None)
    copy_texture_buffer(e_gja_a, 5, tmc, None)
    set_optscat_texture_buffer(tmc, (12, 11, 13))
    save_tmc(outdir, tmc, tmc_id)

    # e_van_b
    tmc_id = 1342
    tmc = extract_tmc(databin, tmc_id)
    copy_optscats(e_dgr_a, tmc)
    sort_objects_by_nodename(tmc, key=key)
    copy_texture_buffer(e_chg_a, 13, tmc, None)
    copy_texture_buffer(e_gja_a, 5, tmc, None)
    set_optscat_texture_buffer(tmc, (12, 11, 13))
    save_tmc(outdir, tmc, tmc_id)

    # e_van_c
    tmc_id = 1361
    tmc = extract_tmc(databin, tmc_id)
    copy_optscats(e_dgr_a, tmc)
    sort_objects_by_nodename(tmc, key=key)
    copy_texture_buffer(e_chg_a, 13, tmc, None)
    copy_texture_buffer(e_gja_a, 5, tmc, None)
    set_optscat_texture_buffer(tmc, (12, 11, 13))
    save_tmc(outdir, tmc, tmc_id)

    # e_mac_a
    tmc_id = 1178
    tmc = extract_tmc(databin, tmc_id)
    copy_optscats(e_tky_b, tmc)
    copy_texture_buffer(e_tky_b, 9, tmc, None)
    copy_texture_buffer(e_tky_b, 0, tmc, None)
    set_optscat_texture_buffer(tmc, (18, 17, 19))
    sort_objects_by_nodename(tmc)
    save_tmc(outdir, tmc, tmc_id)

    # e_ciw_a
    tmc_id = 1280
    tmc = extract_tmc(databin, tmc_id)
    copy_texture_buffer(e_tky_b, 9, tmc, 8)
    save_tmc(outdir, tmc, tmc_id)

    # e_ciw_b
    tmc_id = 1284
    tmc = extract_tmc(databin, tmc_id)
    copy_texture_buffer(e_tky_b, 9, tmc, 16)
    save_tmc(outdir, tmc, tmc_id)

    # e_bat_b
    tmc_id = 1085
    tmc = extract_tmc(databin, tmc_id)
    copy_optscats(e_okm_a, tmc)
    copy_texture_buffer(e_okm_a, 5, tmc, None)
    copy_texture_buffer(e_gja_a, 5, tmc, None)
    set_optscat_texture_buffer(tmc, (3, 2, 4))
    sort_objects_by_nodename(tmc, key=key)
    save_tmc(outdir, tmc, tmc_id)

    # e_bat_b
    tmc_id = 1353
    tmc = extract_tmc(databin, tmc_id)
    copy_optscats(e_okm_a, tmc)
    copy_texture_buffer(e_okm_a, 5, tmc, None)
    copy_texture_buffer(e_gja_a, 5, tmc, None)
    set_optscat_texture_buffer(tmc, (5, 4, 6))
    sort_objects_by_nodename(tmc, key=key)
    save_tmc(outdir, tmc, tmc_id)

def extract_tmc(databin, tmc_id, mutable = True):
    tmc_data = databin.chunks[tmc_id].decompress()
    tmcl_data = databin.chunks[tmc_id + 1].decompress()
    if not mutable:
        return TMC(tmc_data, tmcl_data)
    else:
        tmc = TMC(bytearray(tmc_data), bytearray(tmcl_data))
        return tmc

def copy_optscats(src_tmc, dst_tmc):
    object_idx = tuple( i for i, b in enumerate(src_tmc.nodelay)
                         if b.name.startswith(b'OPTscat') )
    copy_objects(src_tmc, object_idx, dst_tmc)

def copy_objects(src_tmc, object_idx, dst_tmc):
    assert len(dst_tmc.mdlgeo) == len(dst_tmc.nodelay)
    assert len(dst_tmc.mdlinfo) == len(dst_tmc.nodelay)
    assert len(dst_tmc.hielay) == len(dst_tmc.nodelay)
    assert len(dst_tmc.glblmtx) == len(dst_tmc.nodelay)
    assert len(dst_tmc.bnofsmtx) == len(dst_tmc.nodelay)

    getobj = itemgetter(*object_idx)

    # These copies block in each section that refers to the object.
    # We must copy ObjGeo and HieLay as mutable to modify them later.
    dst_tmc.mdlgeo.extend( MdlGeo.Block(bytearray(objgeo.data))
                           for objgeo in getobj(src_tmc.mdlgeo) )
    dst_tmc.mdlinfo.extend(getobj(src_tmc.mdlinfo))
    dst_tmc.hielay.extend( HieLay.Block(bytearray(h.data))
                           for h in getobj(src_tmc.hielay) )
    dst_tmc.nodelay.extend(getobj(src_tmc.nodelay))
    dst_tmc.glblmtx.extend(getobj(src_tmc.glblmtx))
    dst_tmc.bnofsmtx.extend(getobj(src_tmc.bnofsmtx))

    # This copies the vertex buffers and the index buffers of the object.
    G = tuple( (g.vertex_buffer_index, g.index_buffer_index)
               for objgeo in getobj(src_tmc.mdlgeo) for g in objgeo.geodecl )
    V, I = zip(*G)
    dst_tmc.vtxlay.extend( src_tmc.vtxlay[v] for v in V )
    dst_tmc.idxlay.extend( src_tmc.idxlay[i] for i in I )

    # This assigns the new vertex buffer index and index buffer index.
    i = len(dst_tmc.vtxlay) - len(G)
    j = len(dst_tmc.idxlay) - len(G)
    n = len(dst_tmc.mdlgeo) - len(object_idx)
    for objgeo in dst_tmc.mdlgeo[n:]:
        for blk in objgeo.geodecl:
            blk.vertex_buffer_index = i
            blk.index_buffer_index = j
            i += 1
            j += 1

    # This copies MtrCol blocks used by objects.
    mtrcol_I = ( (i, b.mtrcol_index)
                 for i, objgeo in enumerate(dst_tmc.mdlgeo)
                 for b in objgeo )
    mtrcol_I = tuple( (i, j) for i, j in mtrcol_I
                      if i >= len(dst_tmc.nodelay) - len(object_idx) )
    new_mtrcols = { (src_tmc.mtrcol[j], j) for _, j in mtrcol_I }
    old_new_mtrcol_idx = {}
    for b, i in new_mtrcols:
        old_new_mtrcol_idx[i] = len(dst_tmc.mtrcol)
        counts = Counter(( j for j,k in mtrcol_I if k == i))
        new_b = MtrCol.makeblock(len(counts))
        new_b.matrix = b.matrix
        for j, (k, c) in enumerate(sorted(counts.items(), key=lambda x: x[0])):
            new_b.xrefs[j].index = k
            new_b.xrefs[j].count = c
        dst_tmc.mtrcol.append(new_b)

    # This assigns the new MtrCol index to the copied objects.
    n = len(dst_tmc.mdlgeo) - len(object_idx)
    for objgeo in dst_tmc.mdlgeo[n:]:
        for b in objgeo:
            b.mtrcol_index = old_new_mtrcol_idx[b.mtrcol_index]

    # This make new HieLay blocks that have an object as a child
    n = len(dst_tmc.mdlgeo) - len(object_idx)
    for p in { b.parent for b in dst_tmc.hielay[n:] }:
        b = dst_tmc.hielay[p]
        new_children = tuple( i for i, c in enumerate(dst_tmc.hielay[n:], n)
                              if c.parent == p ) + tuple(b.children)
        new_b = HieLay.makeblock(len(new_children))
        new_b.matrix = b.matrix
        new_b.parent = b.parent
        new_b.level = b.level
        for i, v in enumerate(sorted(new_children)):
            new_b.children[i] = v
        dst_tmc.hielay[p] = new_b

def remove_optscats(tmc):
    object_idx = tuple( i for i, b in enumerate(tmc.nodelay)
                         if b.name.startswith(b'OPTscat') )
    remove_objects(tmc, object_idx)

def remove_objects(tmc, object_idx):
    assert len(tmc.mdlgeo) == len(tmc.nodelay)
    assert len(tmc.mdlinfo) == len(tmc.nodelay)
    assert len(tmc.hielay) == len(tmc.nodelay)
    assert len(tmc.glblmtx) == len(tmc.nodelay)
    assert len(tmc.bnofsmtx) == len(tmc.nodelay)

    obj_idx_diff = tuple( sum( j < i for j in object_idx ) for i in range(len(tmc.nodelay) ) )

    # This remove child objects from HieLay blocks.
    for i, b in enumerate(tmc.hielay):
        if i in object_idx:
            continue
        new_children = set(b.children) - set(object_idx)
        if len(new_children) == b.children_count:
            continue
        new_b = HieLay.makeblock(len(new_children))
        new_b.matrix = b.matrix
        new_b.parent = b.parent
        new_b.level = b.level
        for j, c in enumerate(sorted(new_children)):
            new_b.children[j] = c
        tmc.hielay[i] = new_b

    # Update index
    for b in tmc.hielay:
        b.parent = b.parent - obj_idx_diff[b.parent] if b.parent > -1 else -1
        for i, c in enumerate(b.children):
            b.children[i] = c - obj_idx_diff[c]

    # This removes xref objects from MtrCol blocks.
    for i, b in enumerate(tmc.mtrcol):
        new_xrefs = { x for x in b.xrefs } - { x for x in b.xrefs if x.index in object_idx }
        if len(new_xrefs) == b.xrefs_count:
            continue
        new_b = MtrCol.makeblock(len(new_xrefs))
        new_b.matrix = b.matrix
        for j, x in enumerate(sorted(new_xrefs, key=lambda x: x.index)):
            new_b.xrefs[j].index = x.index
            new_b.xrefs[j].count = x.count
        tmc.mtrcol[i] = new_b

    # Update index
    for b in tmc.mtrcol:
        for x in b.xrefs:
            x.index = x.index - obj_idx_diff[x.index]

    getobj = itemgetter(*( i for i in range(len(tmc.nodelay)) if i not in object_idx))
    tmc.mdlgeo[:] = getobj(tmc.mdlgeo)
    tmc.mdlinfo[:] = getobj(tmc.mdlinfo)
    tmc.hielay[:] = getobj(tmc.hielay)
    tmc.nodelay[:] = getobj(tmc.nodelay)
    tmc.glblmtx[:] = getobj(tmc.glblmtx)
    tmc.bnofsmtx[:] = getobj(tmc.bnofsmtx)

def copy_texture_buffer(src_tmc, src_tex_idx, dst_tmc, dst_tex_idx = None):
    H = src_tmc.ttdm.ttdh[src_tex_idx]
    m_or_l = ( src_tmc.ttdm.ttdl if H.is_in_L
               else src_tmc.ttdm )
    stex = m_or_l[H.ttdm_ttdl_index]

    if dst_tex_idx != None:
        H = dst_tmc.ttdm.ttdh[dst_tex_idx]
        m_or_l = ( dst_tmc.ttdm.ttdl if H.is_in_L
                   else dst_tmc.ttdm )
        m_or_l[H.ttdm_ttdl_index] = stex
    else:
        H = TTDH.makeblock()
        H.is_in_L = True
        H.ttdm_ttdl_index = len(dst_tmc.ttdm.ttdl)
        dst_tmc.ttdm.ttdh.append(H)
        dst_tmc.ttdm.ttdl.append(stex)

def set_optscat_texture_buffer(tmc, texbuf_idx):
    object_idx = tuple( i for i, b in enumerate(tmc.nodelay)
                         if b.name.startswith(b'OPTscat') )
    for i in object_idx:
        for objgeo in tmc.mdlgeo[i]:
            for t, j in zip(objgeo.textures, texbuf_idx, strict=True):
                t.buffer_index = j

# This assumes that the original index is equal to the number where the object is
# placed from the first place (from zero). This also sorts VtxLay and IdxLay based
# on references from objects. As a side effect, it drops vtxlay blocks and idxlay
# blocks which are not reffered by any objects.
def sort_objects_by_nodename(tmc, /, *, key=None):
    assert len(tmc.mdlgeo) == len(tmc.nodelay)
    assert len(tmc.mdlinfo) == len(tmc.nodelay)
    assert len(tmc.hielay) == len(tmc.nodelay)
    assert len(tmc.glblmtx) == len(tmc.nodelay)
    assert len(tmc.bnofsmtx) == len(tmc.nodelay)

    # First, we calculate the new sort order.
    O = ( (nodeobj.name, i)
          for i, nodeobj in enumerate(tmc.nodelay))
    f = (lambda x: key(x[0])) if key else (lambda x: x[0])
    obj_sort_order = tuple( i for _, i in sorted(O, key=f) )
    obj_sorted = itemgetter(*obj_sort_order)

    # This sorts VtxLay and IdxLay
    G = tuple( (g.vertex_buffer_index, g.index_buffer_index)
               for objgeo in obj_sorted(tmc.mdlgeo) for g in objgeo.geodecl )
    V, I = zip(*G)
    tmc.vtxlay[:] = ( tmc.vtxlay[v] for v in V )
    tmc.idxlay[:] = ( tmc.idxlay[i] for i in I )

    # This sorts objects
    tmc.mdlgeo[:] = obj_sorted(tmc.mdlgeo)
    tmc.mdlinfo[:] = obj_sorted(tmc.mdlinfo)
    tmc.hielay[:] = obj_sorted(tmc.hielay)
    tmc.nodelay[:] = obj_sorted(tmc.nodelay)
    tmc.glblmtx[:] = obj_sorted(tmc.glblmtx)
    tmc.bnofsmtx[:] = obj_sorted(tmc.bnofsmtx)

    # This assigns new vertex buffer index and index buffer index
    i = 0
    for objgeo in tmc.mdlgeo:
        for blk in objgeo.geodecl:
            blk.vertex_buffer_index = i
            blk.index_buffer_index = i
            i += 1

    # This assigns new HieLay parent and children indices
    R = { j:i for i, j in enumerate(obj_sort_order) } | {-1: -1}
    for b in tmc.hielay:
        b.parent = R[b.parent]
    for i, b in enumerate(tmc.hielay):
        C = tuple( j for j, c in enumerate(tmc.hielay) if c.parent == i )
        for j, c in enumerate(C):
            b.children[j] = c

    # This assigns new xref index of MtrCol
    for i, blk in enumerate(tmc.mtrcol):
        j = 0
        for k, objgeo in enumerate(tmc.mdlgeo):
            if s := sum( b.mtrcol_index == i for b in objgeo ):
                blk.xrefs[j].index = k
                blk.xrefs[j].count = s
                j += 1

    tmc[13], tmc[14] = make_nodetypes(tmc, key=key)

def save_tmc(outdir, tmc, tmc_id):
    def save(data, i):
        path = os.path.join(outdir, f'{i:05}.dat')
        print(f"output: {path}")
        with open(path, 'wb') as f:
            f.write(data)

    # Original textures, vertex buffers and index buffers of NGS2 model data
    # are in the TMCL file. We commit them first.
    tmc.ttdm.ttdl.commit()
    tmc.vtxlay.commit()
    tmc.idxlay.commit()
    tmc.lheader.ttdl = LHeader.Block(tmc.ttdm.ttdl.ldata)
    tmc.lheader.vtxlay = LHeader.Block(tmc.vtxlay.ldata)
    tmc.lheader.idxlay = LHeader.Block(tmc.idxlay.ldata)

    tmc.commit()
    save(tmc.data, tmc_id)
    save(tmc.lheader.ldata, tmc_id + 1)

# This assumes that the objects are soreted by their node name.
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

    return TMC.Block(head), TMC.Block(body)

if __name__ == '__main__':
    main()
