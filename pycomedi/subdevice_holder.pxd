# Copyright

from pycomedi cimport _comedilib_h
from pycomedi cimport device_holder as _device_holder


cdef class SubdeviceHolder (object):
    cdef public _device_holder.DeviceHolder device
    cdef public int index

    cdef _comedilib_h.comedi_t * _device(self) except *
