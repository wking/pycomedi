# Copyright (C) 2011-2012 W. Trevor King <wking@tremily.us>
#
# This file is part of pycomedi.
#
# pycomedi is free software: you can redistribute it and/or modify it under the
# terms of the GNU General Public License as published by the Free Software
# Foundation, either version 2 of the License, or (at your option) any later
# version.
#
# pycomedi is distributed in the hope that it will be useful, but WITHOUT ANY
# WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR
# A PARTICULAR PURPOSE.  See the GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along with
# pycomedi.  If not, see <http://www.gnu.org/licenses/>.

"""Pythonic wrappers for converting between Comedilib and physical units

For one-off conversions, use the functions `comedi_to_physical` and
`comedi_from_physical`.  For repeated conversions, use an instance of
`CalibratedConverter`.
"""

cimport numpy as _numpy
import numpy as _numpy

cimport _comedi_h
cimport _comedilib_h
import constant as _constant
import utility as _utility

cdef void _setup_comedi_polynomial_t(
    _comedilib_h.comedi_polynomial_t *p, coefficients, expansion_origin):
    """Setup the `comedi_polynomial_t` at `p`

    * `coefficients` is an iterable containing polynomial coefficients
    * `expansion_origin` is the center of the polynomial expansion
    """
    for i,x in enumerate(coefficients):
        p.coefficients[i] = x
    p.order = len(coefficients)-1
    p.expansion_origin = expansion_origin

cdef object _convert(
    _comedilib_h.comedi_polynomial_t *p, object data, object direction):
    """Apply the polynomial conversion `p` to `data`.

    `direction` should be a value from `constant.CONVERSION_DIRECTION`.
    """
    to_physical = (_constant.bitwise_value(direction)
                   == _constant.CONVERSION_DIRECTION.to_physical.value)
    if _numpy.isscalar(data):
        if to_physical:
            return _comedilib_h.comedi_to_physical(data, p)
        else:
            return _comedilib_h.comedi_from_physical(data, p)
    if to_physical:
        dtype = _numpy.double
    else:
        dtype = _utility.lsampl
    array = _numpy.array(data, dtype=dtype)
    for i,d in enumerate(data):
        if to_physical:
            array[i] = _comedilib_h.comedi_to_physical(d, p)
        else:
            array[i] = _comedilib_h.comedi_from_physical(d, p)
    return array

cpdef comedi_to_physical(data, coefficients, expansion_origin):
    """Convert Comedi bit values (`lsampl_t`) to physical units (`double`)

    * `data` is the value to be converted (scalar or array-like)
    * `coefficients` and `expansion_origin` should be appropriate
      for `_setup_comedi_polynomial_t`.  TODO: expose it's docstring?

    The conversion algorithm is::

        x = sum_i c_i * (d-d_o)^i

    where `x` is the returned physical value, `d` is the supplied data,
    `c_i` is the `i`\th coefficient, and `d_o` is the expansion origin.

    >>> print comedi_to_physical.__doc__  # doctest: +ELLIPSIS
    Convert Comedi bit values (`lsampl_t`) to physical units (`double`)
    ...
    >>> comedi_to_physical(1, [1, 2, 3], 2)
    2.0
    >>> comedi_to_physical([1, 2, 3], [1, 2, 3], 2)
    array([ 2.,  1.,  6.])
    """
    cdef _comedilib_h.comedi_polynomial_t p
    _setup_comedi_polynomial_t(&p, coefficients, expansion_origin)
    return _convert(&p, data, _constant.CONVERSION_DIRECTION.to_physical)

cpdef comedi_from_physical(data, coefficients, expansion_origin):
    """Convert physical units to Comedi bit values

    Like `comedi_to_physical` but converts `double` -> `lsampl_t`.

    >>> comedi_from_physical(1, [1,2,3], 2)
    2L
    >>> comedi_from_physical([1, 2, 3], [1, 2, 3], 2)
    array([2, 1, 6], dtype=uint32)
    """
    cdef _comedilib_h.comedi_polynomial_t p
    _setup_comedi_polynomial_t(&p, coefficients, expansion_origin)
    return _convert(&p, data, _constant.CONVERSION_DIRECTION.from_physical)


cdef class CalibratedConverter (object):
    """Apply a converion polynomial

    Usually you would get the this converter from
    `DataChannel.get_converter()` or similar. but for testing, we'll
    just create one out of thin air.

    >>> c = CalibratedConverter(
    ...     to_physical_coefficients=[1, 2, 3],
    ...     to_physical_expansion_origin=1)
    >>> c  # doctest: +NORMALIZE_WHITESPACE
    <CalibratedConverter
     to_physical:{coefficients:[1.0, 2.0, 3.0] origin:1.0}
     from_physical:{coefficients:[0.0] origin:0.0}>

    >>> c.to_physical(1)
    1.0
    >>> c.to_physical([0, 1, 2])
    array([ 2.,  1.,  6.])
    >>> c.to_physical(_numpy.array([0, 1, 2, 3], dtype=_numpy.uint))
    array([  2.,   1.,   6.,  17.])

    >>> c.get_to_physical_expansion_origin()
    1.0
    >>> c.get_to_physical_coefficients()
    array([ 1.,  2.,  3.])
    """
    def __init__(self, to_physical_coefficients=None,
                 to_physical_expansion_origin=0,
                 from_physical_coefficients=None,
                 from_physical_expansion_origin=0):
        if to_physical_coefficients:
            _setup_comedi_polynomial_t(
                &self._to_physical, to_physical_coefficients,
                 to_physical_expansion_origin)
        if from_physical_coefficients:
            _setup_comedi_polynomial_t(
                &self._from_physical, from_physical_coefficients,
                 from_physical_expansion_origin)

    cdef _str_poly(self, _comedilib_h.comedi_polynomial_t polynomial):
        return '{coefficients:%s origin:%s}' % (
            [float(polynomial.coefficients[i])
             for i in range(polynomial.order+1)],
            float(polynomial.expansion_origin))

    def __str__(self):
        return '<%s to_physical:%s from_physical:%s>' % (
            self.__class__.__name__, self._str_poly(self._to_physical),
            self._str_poly(self._from_physical))

    def __repr__(self):
        return self.__str__()

    cpdef to_physical(self, data):
        return _convert(&self._to_physical, data,
                        _constant.CONVERSION_DIRECTION.to_physical)

    cpdef from_physical(self, data):
        return _convert(&self._from_physical, data,
                        _constant.CONVERSION_DIRECTION.from_physical)

    cpdef get_to_physical_expansion_origin(self):
        return self._to_physical.expansion_origin

    cpdef get_to_physical_coefficients(self):
        ret = _numpy.ndarray((self._to_physical.order+1,), _numpy.double)
        for i in xrange(len(ret)):
            ret[i] = self._to_physical.coefficients[i]
        return ret

    cpdef get_from_physical_expansion_origin(self):
        return self._from_physical.expansion_origin

    cpdef get_from_physical_coefficients(self):
        ret = _numpy.ndarray((self._from_physical.order+1,), _numpy.double)
        for i in xrange(len(ret)):
            ret[i] = self._from_physical.coefficients[i]
        return ret


# TODO: see comedi_caldac_t and related at end of comedilib.h
