#!/usr/bin/python3
import mmap
import sys
import os.path
import argparse
import databin
from enum import IntEnum
from collections import ChainMap

class ChunkType(IntEnum):
    LANG = 0
    UNKNOWN1 = 1
    UNKNOWN2 = 2
    TDP4ACT = 3
    TDP4CLD = 4
    UNKNOWN5 = 5
    UNKNOWN6 = 6
    UNKNOWN7 = 7
    TMC_effpk = 8
    UNKNOWN9 = 9
    UNKNOWN10 = 10
    TMC = 11
    UNKNOWN12 = 12
    itm_dat2 = 13
    UNKNOWN14 = 14
    sprpackL = 15
    UNKNOWN16 = 16
    chr_dat = 17
    rtm_dat = 18
    tdpack = 19
    TDP4SOB = 20
    TDP4SOC = 21
    sprpack = 22
    STAGEETC = 23
    TDP4STY = 24
    TNF = 25
    TNFL = 26
    TMCL = 27
    XWSFILE = 28
    PNG = 29
    WMV = 30
    UNKNOWN255 = 255

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('databin')
    parser.add_argument('-a', '--extract-all', action='store_true')
    parser.add_argument('-l', '--with-linked', action='store_true',
                        help='automatically extract linked items too')
    parser.add_argument('-o', '--output-dir', dest='outdir', default='.')
    parser.add_argument('index', nargs='*', type=int)
    args = parser.parse_args()

    if not args.extract_all and not len(args.index):
        parser.print_usage()
        return

    if not os.path.isdir(args.outdir):
        print(f'output directory "{args.outdir}" not exist.', file=sys.stderr)
        return

    with (open(args.databin, 'rb') as db_f,
        mmap.mmap(db_f.fileno(), 0, access=mmap.ACCESS_READ) as db_m):
        extract(databin.DatabinParser(db_m), args)

def extract(db, args):
    if args.extract_all:
        C = enumerate(db.chunks)
    else:
        I = set(args.index) & set(range(len(db.chunks)))
        for i in sorted(set(args.index) ^ I):
            print(f'data {i} is not in databin. ignored.', file=sys.stderr)
        if not args.extract_all and args.with_linked:
            C = ( db.get_linked_chunks(i) | {i:db.chunks[i]} for i in I )
            C = ChainMap(*C).items()
        else:
            C = ( (i, db.chunks[i]) for i in I )

    f = lambda i: os.path.join(args.outdir, f"{i:05}.dat")
    for i, c in C:
        if not c.size:
            print(f'data {i} is empty. ignored.', file=sys.stderr)
        else:
            save(databin.decompress(c), f(i))

def save(data, path):
    with open(path, 'wb') as f:
        f.write(data)

if __name__ == '__main__':
    main()
