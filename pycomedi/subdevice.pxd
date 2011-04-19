# Copyright

"Expose `Subdevice` internals at the C level for other Cython modules"

from device cimport Device as _Device
from command cimport Command as _Command


cdef class Subdevice (object):
    cdef public _Device device
    cdef public int index

    cpdef dio_bitfield(self, unsigned int bits=*, write_mask=*, base_channel=*)

cdef class StreamingSubdevice (Subdevice):
    cdef public _Command cmd
    cdef public list _command_test_errors
