# Copyright

"Expose `Device` internals at the C level for other Cython modules"

cimport _comedilib_h
from instruction cimport Insn as _Insn


cdef class Device (object):
    cdef _comedilib_h.comedi_t * device
    cdef public object file
    cdef public object filename

    cpdef do_insnlist(self, insnlist)
    cpdef do_insn(self, _Insn insn)
