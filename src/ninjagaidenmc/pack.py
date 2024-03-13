class PackContainer:
    @property
    def magic(self):
        return memoryview(self.data)[0:8].tobytes()

    @property
    def version(self):
        return memoryview(self.data)[8:0xc].tobytes()

    @property
    def container_size(self):
        return memoryview(self.data)[0xc:0x10].cast('I')[0]

    @property
    def pack_param_info_table_count(self):
        return memoryview(self.data)[0x10:0x14].cast('I')[0]

    @property
    def unknown1_count(self):
        return memoryview(self.data)[0x14:0x18].cast('I')[0]

    @property
    def subpack_count(self):
        return memoryview(self.data)[0x18:0x1c].cast('I')[0]

    # subpack items are 4 byte each
    @property
    def subpack_item_count(self):
        return memoryview(self.data)[0x1c:0x20].cast('I')[0]

    @property
    def pack_param_info_table_ofs(self):
        return memoryview(self.data)[0x20:0x24].cast('I')[0]

    @property
    def pack_param_table_ofs(self):
        return memoryview(self.data)[0x24:0x28].cast('I')[0]

    @property
    def linked_param_table_ofs(self):
        return memoryview(self.data)[0x28:0x2c].cast('I')[0]

    @property
    def optional_data_ofs(self):
        return memoryview(self.data)[0x2c:0x30].cast('I')[0]

    @property
    def pack_param_info_table(self):
        pass

    @property
    def param_table(self):
        pass

    @property
    def linked_param_table(self):
        pass

    @property
    def optional_pack(self):
        o = self.optional_data_ofs
        return memoryview(self.data)[o:]

class PackParamInfo:
    @property
    def linked_param_count(self):
        return memoryview(self.data)[0x0]

    @property
    def is_linked_param(self):
        return memoryview(self.data)[0x3] & 0xf0

    @property
    def param_type(self):
        return memoryview(self.data)[0x0] & 0x0f

    @property
    def param_ofs(self):
        return memoryview(self.data)[0x4:0x8].cast('I')[0] * 4

    @property
    def param_id_ofs(self):
        return memoryview(self.data)[0x8:0xc].cast('I')[0]

    @property
    def linked_info(self):
        return memoryview(self.data)[0xc:0x10].cast('I')[0] & 0x7fffffff

    @property
    def is_linked(self):
        return memoryview(self.data)[0xc:0x10].cast('I')[0] & 0x80000000

    @property
    def param_id(self):
        m = memoryview(self.data)
        o = self.param_id_ofs
        n = m[o:o+4].cast('I')[0] >> 24
        return m[o:o+4*n]


