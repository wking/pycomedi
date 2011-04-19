# Copyright

"Expose `CalibratedConverter` internals at the C level for other Cython modules"

cimport _comedilib_h


cdef class CalibratedConverter (object):
    cdef _comedilib_h.comedi_polynomial_t _to_physical, _from_physical

    cdef _str_poly(self, _comedilib_h.comedi_polynomial_t polynomial)
    cpdef to_physical(self, data)
    cpdef from_physical(self, data)
    cpdef get_to_physical_expansion_origin(self)
    cpdef get_to_physical_coefficients(self)
    cpdef get_from_physical_expansion_origin(self)
    cpdef get_from_physical_coefficients(self)
