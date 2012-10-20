# Copyright

cimport _comedilib_h
from device_holder cimport DeviceHolder as _DeviceHolder


cdef class SubdeviceHolder (object):
    cdef public _DeviceHolder device
    cdef public int index

    cdef _comedilib_h.comedi_t * _device(self) except *
