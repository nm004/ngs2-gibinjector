#!/usr/bin/python3
import mmap
import os.path
import sys
from tmc11 import TMCParser
import argparse

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('-o', '--output-dir', dest='outdir', default='.')
    parser.add_argument('-i', '--index', nargs='+', type=int)
    parser.add_argument('-a', '--extract-all', action='store_true')
    parser.add_argument('tmc')
    parser.add_argument('tmcl')
    args = parser.parse_args()
    outdir = args.outdir

    if ((not args.index and not args.extract_all)
        or (args.index and args.extract_all)):
        print('You have to specify --index or --extract-all, but not both.', file=sys.stderr)
        return

    if not os.path.isdir(outdir):
        print(f'output directory "{outdir}" not exist.', file=sys.stderr)
        return

    if args.tmcl:
        tmcl_f = open(args.tmcl, 'rb')
        tmcl_m = mmap.mmap(tmcl_f.fileno(), 0, access=mmap.ACCESS_READ)

    with (open(args.tmc, 'rb') as tmc_f
          mmap.mmap(tmc_f.fileno(), 0, access=mmap.ACCESS_READ) as tmc_m):
        tmc = None
        try:
            tmc = TMCParser(tmc_m, tmcl_m)
            extract_textures(tmc, args)
        except ValueError as e:
            print(f'ERROR: {e}', file=sys.stderr)
            return
        finally:
            if tmc:
                del tmc

def extract_textures(tmc, args):
    textures = tuple(generate_textures(tmc.ttdm))
    n = len(str(len(textures)))
    save_ = lambda d, i: save(d, os.path.join(args.outdir, str(i).zfill(n)+'.dds'))

    if args.extract_all:
        for i, t in enumerate(textures):
            save_(t, i)
        return

    for i in args.index:
        save_(textures[i], i)

def generate_textures(ttdm):
    for h in ttdm.ttdh.chunks:
        if h.is_in_L:
            yield ttdm.ttdl.chunks[h.index]
        else:
            yield ttdm.chunks[h.index]

def save(data, path):
    with open(path, 'wb') as f:
        f.write(data)

if __name__ == '__main__':
    main()
