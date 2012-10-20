# Copyright


cdef class DeviceHolder (object):
    "Minimal comedi_t * wrapper to avoid circular imports"
    def __cinit__(self):
        self.device = NULL
