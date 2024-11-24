# Ninja Gaiden Sigma 2 TMC Importer by Nozomi Miyamori is under the public domain
# and also marked with CC0 1.0. This file is a part of Ninja Gaiden Sigma 2 TMC Importer.

import warnings
import struct

class ContainerParser:
    def __init__(self, magic, data, ldata = b''):
        data = memoryview(data).toreadonly()
        ldata = memoryview(ldata).toreadonly()

        if data[:8] != magic.ljust(8, b'\0'):
            raise ParserError(f'No magic bytes "{magic}" found')

        (
                endian, _, _, header_nbytes,
                container_nbytes, chunk_count, valid_chunk_count,
                offset_table_pos, size_table_pos, sub_container_pos,
        ) = struct.unpack_from('< cxccI III4x III', data, 8)

        self._data = data = data[:container_nbytes]

        lcontainer_nbytes = 0
        if header_nbytes == 0x50:
            if not ldata:
                warnings.warn(f'No ldata was passed to {magic.decode()}')
            else:
                lhead = (_, lcontainer_nbytes, _) = struct.unpack_from('< III', data, 0x40)
                lhead_ = struct.unpack_from('< III', ldata)
                if lhead_ != lhead:
                    raise ParserError(f'Lheads in {magic.decode()} differ: {lhead} != {lhead_}')
        self._ldata = ldata = ldata[:lcontainer_nbytes]

        o = header_nbytes
        p = ( offset_table_pos or size_table_pos or sub_container_pos or container_nbytes )
        self.metadata = self._metadata = data[o:p]

        o = offset_table_pos
        p = o + 4*chunk_count*(o > 0)
        offset_table = data[o:p].cast('I')

        o = size_table_pos
        p = o + 4*chunk_count*(o > 0)
        size_table = data[o:p].cast('I')

        o = sub_container_pos
        p = ( offset_table and offset_table[0] or container_nbytes )*(o > 0)
        self.sub_container = self._sub_container = data[o:p]

        self.chunks = self._chunks = tuple(ContainerParser._gen_chunks(
            ldata or data, offset_table, size_table
        ))

    @staticmethod
    def _gen_chunks(data, offset_table, size_table):
        if size_table:
            yield from ( data[o:o+n] for o, n in zip(offset_table, size_table) )
            return

        for i, o in enumerate(offset_table):
            if not o:
                yield data[:0]
                continue
            for p in offset_table[i+1:]:
                if p:
                    yield data[o:p]
                    break
            else:
                yield data[o:]

    def close(self):
        for c in self._chunks:
            c.release()
        self._sub_container.release()
        self._metadata.release()
        self._ldata.release()
        self._data.release()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.close()

class ParserError(Exception):
    pass
