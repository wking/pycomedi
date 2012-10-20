# Copyright

cimport _comedilib_h


cdef class DeviceHolder (object):
    cdef _comedilib_h.comedi_t * device
