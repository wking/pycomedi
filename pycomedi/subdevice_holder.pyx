# Copyright

cimport _comedilib_h


cdef class SubdeviceHolder (object):
    "Minimal subdevice wrapper to avoid circular imports"
    def __cinit__(self):
        self.device = None
        self.index = -1

    def __init__(self, device, index):
        super(SubdeviceHolder, self).__init__()
        self.device = device
        self.index = index

    cdef _comedilib_h.comedi_t * _device(self) except *:
        return self.device.device
