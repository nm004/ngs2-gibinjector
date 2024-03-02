# TCM Container Lib by Nozomi Miyamori is marked with CC0 1.0.
# This file is a part of TCM Container Lib.
#
# This module is for reading/writing Tecmo Container format file
# used by some Team Ninja's (Koei-Tecmo) games such as NINJA GAIDEN
# Master Collection and Dead or Alice 5 Last Round.

def read_magic(data):
    return data[0:8]

def write_rawmagic(data, val):
    data[0:8] = val

def read_version(data):
    return data[0x8:0xc].cast('I')[0]

def write_version(data, val):
    data[0x8:0xc].cast('I')[0] = val

def read_info_size(data):
    return data[0xc:0x10].cast('I')[0]

def write_info_size(data, val):
    data[0xc:].cast('I')[0] = val

def read_section_size(data):
    return data[0x10:0x14].cast('I')[0]

def write_section_size(data, val):
    data[0x10:0x14].cast('I')[0] = val

def read_block_count(data):
    return data[0x14:0x18].cast('I')[0]

def write_block_count(data, val):
    data[0x14:0x18].cast('I')[0] = val

def read_valid_block_count(data):
    return data[0x18:0x1c].cast('I')[0]

def write_valid_block_count(data, val):
    data[0x18:0x1c].cast('I')[0] = val

def read_block_ofs_table_ofs(data):
    return data[0x20:0x24].cast('I')[0]

def write_block_ofs_table_ofs(data, val):
    data[0x20:0x24].cast('I')[0] = val

def read_block_size_table_ofs(data):
    return data[0x24:0x28].cast('I')[0]

def write_block_size_table_ofs(data, val):
    data[0x24:0x28].cast('I')[0] = val

def read_optional_data_ofs(data):
    return data[0x28:0x2c].cast('I')[0]

def write_optional_data_ofs(data, val):
    data[0x28:0x2c].cast('I')[0] = val

def read_L_block_count(data):
    return data[0x40:0x44].cast('I')[0]

def read_L_block_count_L(ldata):
    return ldata[0x0:0x4].cast('I')[0]

def write_L_block_count(data, ldata, val):
    data[0x40:0x44].cast('I')[0] = ldata[0x0:0x4].cast('I')[0] = val

def read_L_size(data):
    return data[0x44:0x48].cast('I')[0]

def read_L_size_L(ldata):
    return ldata[0x4:0x8].cast('I')[0]

def write_L_size(data, ldata, val):
    data[0x44:0x48].cast('I')[0] = ldata[0x4:0x8].cast('I')[0] = val

def read_L_check_digits(data):
    return data[0x48:0x4c].cast('I')[0]

def read_L_check_digits_L(ldata):
    return ldata[0x8:0xc].cast('I')[0]

def write_L_check_digits(data, ldata, val):
    data[0x48:0x4c].cast('I')[0] = ldata[0x8:0xc].cast('I')[0] = val

def read_info(data):
    n = read_info_size(data)
    return data[0:n]

def read_meta_info(data):
    n = read_info_size(data)
    o = ( read_block_ofs_table_ofs(data)
          or read_block_size_table_ofs(data)
          or read_optional_data_ofs(data)
          or None )
    return data[n:o]

def write_meta_info(data, val):
    read_meta_info(data)[:] = val

def read_block_ofs_table(data):
    o = read_block_ofs_table_ofs(data) or data.nbytes
    n = read_block_count(data)
    return data[o:o+4*n].cast('I')

def read_block_size_table(data):
    o = read_block_size_table_ofs(data) or data.nbytes
    n = read_block_count(data)
    return data[o:o+4*n].cast('I')

def read_optional_data(data):
    o = read_optional_data_ofs(data) or data.nbytes
    t = read_block_ofs_table(data)
    p = t[0] if t else None
    return data[o:p]

def write_optional_data(data, val):
    o = read_optional_data_ofs(data) or data.nbytes
    t = read_block_ofs_table(data)
    p = t[0] if t else None
    data[o:p] = val
