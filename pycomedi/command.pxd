# Copyright

"Expose `Command` internals at the C level for other Cython modules"

cimport _comedi_h


cdef class Command (object):
    cdef _comedi_h.comedi_cmd _cmd
    cdef public list _fields

    cdef _comedi_h.comedi_cmd *get_comedi_cmd_pointer(self)
