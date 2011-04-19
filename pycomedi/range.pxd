# Copyright

"Expose `Range` internals at the C level for other Cython modules"

cimport _comedilib_h
from constant cimport BitwiseOperator as _BitwiseOperator


cdef class Range (_BitwiseOperator):
    cdef _comedilib_h.comedi_range range

    cdef set_comedi_range(self, _comedilib_h.comedi_range range)
