# Copyright

"Expose `Insn` internals at the C level for other Cython modules"

cimport _comedi_h


cdef class Insn (object):
    cdef _comedi_h.comedi_insn _insn
    cdef public list _fields

    cdef _comedi_h.comedi_insn get_comedi_insn(self)
