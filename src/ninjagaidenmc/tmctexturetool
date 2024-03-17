#!/usr/bin/python3
import mmap
import os.path
import sys
from tmc import TMC
import argparse
import warnings

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('-o', '--output-dir', dest='outdir', default='.')
    parser.add_argument('-i', '--index', type=int)
    parser.add_argument('-a', '--extract-all', action='store_true')
    parser.add_argument('-L', '--tmcl', help='must specify if tmc has TMCL file')
    parser.add_argument('tmc')
    args = parser.parse_args()
    outdir = args.outdir

    if (not args.index and not args.extract_all
        or args.index and args.extract_all):
        print('You have to specify --index or --extract-all, but not both.', file=sys.stderr)
        return

    if not os.path.isdir(outdir):
        print(f'output directory "{outdir}" not exist.', file=sys.stderr)
        return

    warnings.simplefilter('error', category=UserWarning)

    if args.tmcl:
        tmcl_f = open(args.tmcl, 'rb')
        tmcl_m = mmap.mmap(tmcl_f.fileno(), 0, access=mmap.ACCESS_READ)

    tmc_f = open(args.tmc, 'rb')
    tmc_m = mmap.mmap(tmc_f.fileno(), 0, access=mmap.ACCESS_READ)

    try:
        tmc = TMC(tmc_m, tmcl_m)
    except (ValueError, UserWarning) as e:
        print(f'ERROR: {e}', file=sys.stderr)
        return

    extract_textures(tmc, args)

def extract_textures(tmc, args):
    textures = tuple(generate_textures(tmc))
    n = len(str(len(textures)))
    save_ = lambda d, i: save(d, os.path.join(args.outdir, str(i).zfill(n)+'.dds'))

    if args.extract_all:
        for i, t in enumerate(textures):
            save_(t.data, i)
        return

    for i in args.index:
        save_(textures[i].data, i)

def generate_textures(tmc):
    for h in tmc.ttdm.ttdh:
        if h.is_in_L:
            yield tmc.ttdm.ttdl[h.ttdm_ttdl_index]
        else:
            yield tmc.ttdm[h.ttdm_ttdl_index]

def save(data, path):
    with open(path, 'wb') as f:
        f.write(data)

if __name__ == '__main__':
    main()
