from databintool import databin
from texturetool import tmc11
import mmap

def main():
    f = open(r'R:\tmp\list_of_tmc.txt', 'w')
    db_m = mmap_open(r"R:\tmp\databin")
    db = databin.DatabinParser(db_m)
    with db_m, db, f:
        for c in db.chunks:
            tmp = databin.decompress(c)
            if tmp[:8] == b'TMC\0\0\0\0\0':
                tmc = tmc11.TMCParser(tmp, b'')
                print(tmc.metadata.name.decode(), c.index, file=f)

def mmap_open(path):
    with open(path, 'rb') as f:
        return mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ)

if __name__ == '__main__':
    main()
