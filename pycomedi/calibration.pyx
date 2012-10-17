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

from libc cimport stdlib as _stdlib
from libc cimport string as _string
cimport numpy as _numpy
import numpy as _numpy

cimport _comedi_h
cimport _comedilib_h
import _error
import constant as _constant
import utility as _utility


cdef void _python_to_charp(char **charp, object obj, object encoding):
    """Convert a Python string into a `char *`.

    Cython automatically converts string or byte array to a `char *`
    for use with external C libraries.  However, the resulting
    pointers are only valid until the Python object is garbage
    collected.  For the `Calibration` class, we need persistent
    pointers that will be manually freed later.  This function creates
    these manual copies.
    """
    cdef char *ret
    cdef char *src
    if charp[0] is not NULL:  # charp[0] is the same as *charp
        _stdlib.free(charp[0])
        charp[0] = NULL
    if hasattr(obj, 'encode'):
        obj = obj.encode(encoding, 'strict')
    src = obj
    ret = <char *> _stdlib.malloc(len(obj) + 1)
    if ret is NULL:
        raise MemoryError()
    _string.strncpy(ret, src, len(obj) + 1)
    charp[0] = ret

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


cdef class Caldac (object):
    """Class wrapping comedi_caldac_t

    >>> from .device import Device
    >>> from . import constant

    >>> d = Device('/dev/comedi0')
    >>> d.open()

    >>> c = d.parse_calibration()
    >>> s = c.settings[0]
    >>> print(s)
    <CalibrationSetting device:/dev/comedi0 subdevice:0>
    >>> caldac = s.caldacs[0]
    >>> print(caldac)
    <Caldac subdevice:5 channel:4 value:255>

    >>> d.close()
    """
    def __cinit__(self):
        self.caldac = NULL

    def __str__(self):
        fields = ['{}:{}'.format(f, getattr(self, f))
                  for f in ['subdevice', 'channel', 'value']]
        return '<{} {}>'.format(self.__class__.__name__, ' '.join(fields))

    def __repr__(self):
        return self.__str__()

    def _subdevice_get(self):
        if self.caldac is not NULL:
            return self.caldac.subdevice
    def _subdevice_set(self, value):
        assert self.caldac is not NULL, 'load caldac first'
        self.caldac.subdevice = value
    subdevice = property(fget=_subdevice_get, fset=_subdevice_set)

    def _channel_get(self):
        if self.caldac is not NULL:
            return self.caldac.channel
    def _channel_set(self, value):
        assert self.caldac is not NULL, 'load caldac first'
        self.caldac.channel = value
    channel = property(fget=_channel_get, fset=_channel_set)

    def _value_get(self):
        if self.caldac is not NULL:
            return self.caldac.value
    def _value_set(self, value):
        assert self.caldac is not NULL, 'load caldac first'
        self.caldac.value = value
    value = property(fget=_value_get, fset=_value_set)


cdef class CalibrationSetting (object):
    """Class wrapping comedi_calibration_setting_t

    >>> from .device import Device
    >>> from . import constant

    >>> d = Device('/dev/comedi0')
    >>> d.open()

    >>> c = d.parse_calibration()
    >>> s = c.settings[0]

    >>> print(s)
    <CalibrationSetting device:/dev/comedi0 subdevice:0>
    >>> print(s.subdevice)  # doctest: +ELLIPSIS
    <pycomedi.subdevice.Subdevice object at 0x...>
    >>> for s in c.settings:
    ...     print('{} {}'.format(s.subdevice.index, s.subdevice.get_type()))
    ...     print('  channels: {}'.format(s.channels))
    ...     print('  ranges: {}'.format(s.ranges))
    ...     print('  arefs: {}'.format(s.arefs))
    ...     print('  caldacs:')
    ...     for caldac in s.caldacs:
    ...         print('    {}'.format(caldac))
    ...     print('  soft_calibration:')
    ...     sc = s.soft_calibration
    ...     print('    to physical coefficients: {}'.format(
    ...         sc.get_to_physical_coefficients()))
    ...     print('    to physical origin: {}'.format(
    ...         sc.get_to_physical_expansion_origin()))
    ...     print('    from physical coefficients: {}'.format(
    ...         sc.get_from_physical_coefficients()))
    ...     print('    from physical origin: {}'.format(
    ...         sc.get_from_physical_expansion_origin()))
    ... # doctest: +REPORT_UDIFF
    0 ai
      channels: []
      ranges: []
      arefs: []
      caldacs:
        <Caldac subdevice:5 channel:4 value:255>
        <Caldac subdevice:5 channel:2 value:255>
        <Caldac subdevice:5 channel:3 value:255>
        <Caldac subdevice:5 channel:0 value:255>
        <Caldac subdevice:5 channel:5 value:255>
        <Caldac subdevice:5 channel:1 value:1>
      soft_calibration:
        to physical coefficients: [ 0.]
        to physical origin: 0.0
        from physical coefficients: [ 0.]
        from physical origin: 0.0
    0 ai
      channels: []
      ranges: [ 8  9 10 11 12 13 14 15]
      arefs: []
      caldacs:
        <Caldac subdevice:5 channel:6 value:255>
        <Caldac subdevice:5 channel:7 value:0>
      soft_calibration:
        to physical coefficients: [ 0.]
        to physical origin: 0.0
        from physical coefficients: [ 0.]
        from physical origin: 0.0
    1 ao
      channels: [0]
      ranges: [0 2]
      arefs: []
      caldacs:
        <Caldac subdevice:5 channel:16 value:255>
        <Caldac subdevice:5 channel:19 value:0>
        <Caldac subdevice:5 channel:17 value:0>
        <Caldac subdevice:5 channel:18 value:0>
      soft_calibration:
        to physical coefficients: [ 0.]
        to physical origin: 0.0
        from physical coefficients: [ 0.]
        from physical origin: 0.0
    1 ao
      channels: [0]
      ranges: [1 3]
      arefs: []
      caldacs:
        <Caldac subdevice:5 channel:16 value:239>
        <Caldac subdevice:5 channel:19 value:0>
        <Caldac subdevice:5 channel:17 value:0>
        <Caldac subdevice:5 channel:18 value:0>
      soft_calibration:
        to physical coefficients: [ 0.]
        to physical origin: 0.0
        from physical coefficients: [ 0.]
        from physical origin: 0.0
    1 ao
      channels: [1]
      ranges: [0 2]
      arefs: []
      caldacs:
        <Caldac subdevice:5 channel:20 value:255>
        <Caldac subdevice:5 channel:23 value:0>
        <Caldac subdevice:5 channel:21 value:0>
        <Caldac subdevice:5 channel:22 value:0>
      soft_calibration:
        to physical coefficients: [ 0.]
        to physical origin: 0.0
        from physical coefficients: [ 0.]
        from physical origin: 0.0
    1 ao
      channels: [1]
      ranges: [1 3]
      arefs: []
      caldacs:
        <Caldac subdevice:5 channel:20 value:249>
        <Caldac subdevice:5 channel:23 value:0>
        <Caldac subdevice:5 channel:21 value:0>
        <Caldac subdevice:5 channel:22 value:0>
      soft_calibration:
        to physical coefficients: [ 0.]
        to physical origin: 0.0
        from physical coefficients: [ 0.]
        from physical origin: 0.0

    >>> d.close()
    """
    def __cinit__(self):
        self.setting = NULL

    def __init__(self, subdevice):
        super(CalibrationSetting, self).__init__()
        self.subdevice = subdevice

    def __str__(self):
        fields = [
            'device:{}'.format(self.subdevice.device.filename),
            'subdevice:{}'.format(self.subdevice.index),
            ]
        return '<{} {}>'.format(self.__class__.__name__, ' '.join(fields))

    def _channels_get(self):
        if self.setting is NULL:
            return None
        ret = _numpy.ndarray(shape=(self.setting.num_channels,), dtype=int)
        # TODO: point into existing data array?
        for i in range(self.setting.num_channels):
            ret[i] = self.setting.channels[i]
        return ret
    def _channels_set(self, value):
        assert self.setting is not NULL, 'load setting first'
        if self.setting.channels is not NULL:
            _stdlib.free(self.setting.channels)
        length = len(value)
        self.setting.channels = <unsigned int *> _stdlib.malloc(
            length * sizeof(unsigned int))
        if self.setting.channels is NULL:
            self.setting.num_channels = 0
            raise MemoryError()
        self.setting.num_channels = length
        for i,x in enumerate(value):
            if i >= length:
                raise ValueError((i, length))
            self.setting.channels[i] = x
    channels = property(fget=_channels_get, fset=_channels_set)

    def _ranges_get(self):
        if self.setting is NULL:
            return None
        ret = _numpy.ndarray(shape=(self.setting.num_ranges,), dtype=int)
        # TODO: point into existing data array?
        for i in range(self.setting.num_ranges):
            ret[i] = self.setting.ranges[i]
        return ret
    def _ranges_set(self, value):
        assert self.setting is not NULL, 'load setting first'
        if self.setting.ranges is not NULL:
            _stdlib.free(self.setting.ranges)
        length = len(value)
        self.setting.ranges = <unsigned int *> _stdlib.malloc(
            length * sizeof(unsigned int))
        if self.setting.ranges is NULL:
            self.setting.num_ranges = 0
            raise MemoryError()
        self.setting.num_ranges = length
        for i,x in enumerate(value):
            if i >= length:
                raise ValueError((i, length))
            self.setting.ranges[i] = x
    ranges = property(fget=_ranges_get, fset=_ranges_set)

    def _arefs_get(self):
        if self.setting is NULL:
            return None
        ret = _numpy.ndarray(shape=(self.setting.num_arefs,), dtype=int)
        # TODO: point into existing data array?
        for i in range(self.setting.num_arefs):
            ret[i] = self.setting.arefs[i]
        return ret
    def _arefs_set(self, value):
        assert self.setting is not NULL, 'load setting first'
        length = len(value)
        for i,x in enumerate(value):
            if i >= _comedilib_h.CS_MAX_AREFS_LENGTH:
                raise ValueError((i, _comedilib_h.CS_MAX_AREFS_LENGTH))
            self.setting.arefs[i] = x
        for i in range(length, _comedilib_h.CS_MAX_AREFS_LENGTH):
            self.setting.arefs[i] = 0
    arefs = property(fget=_arefs_get, fset=_arefs_set)

    def _caldacs_get(self):
        if self.setting is NULL:
            return None
        if not self.setting.num_caldacs:
            return []
        # TODO: point into existing data array?
        ret = []
        for i in range(self.setting.num_caldacs):
            c = Caldac()
            c.caldac = &self.setting.caldacs[i]
            ret.append(c)
        return ret
    def _caldacs_set(self, value):
        assert self.setting is not NULL, 'load setting first'
        if self.setting.caldacs is not NULL:
            _stdlib.free(self.setting.caldacs)
        length = len(value)
        self.setting.caldacs = <_comedilib_h.comedi_caldac_t *> _stdlib.malloc(
            length * sizeof(_comedilib_h.comedi_caldac_t))
        if self.setting.caldacs is NULL:
            self.setting.num_caldacs = 0
            raise MemoryError()
        self.setting.num_caldacs = length
        for i,x in enumerate(value):
            if i >= length:
                raise ValueError((i, length))
            self.setting.caldacs[i] = x
    caldacs = property(fget=_caldacs_get, fset=_caldacs_set)

    def _soft_calibration_get(self):
        cdef CalibratedConverter ret
        if self.setting is NULL:
            return None
        ret = CalibratedConverter()
        if self.setting.soft_calibration.to_phys is not NULL:
            ret._to_physical = self.setting.soft_calibration.to_phys[0]
        if self.setting.soft_calibration.from_phys is not NULL:
            ret._from_physical = self.setting.soft_calibration.from_phys[0]
        return ret
    cpdef _soft_calibration_set(self, CalibratedConverter value):
        assert self.setting is not NULL, 'load setting first'
        if (self.setting.soft_calibration.to_phys is NULL and
            (value._to_physical.expansion_origin or
             value._to_physical.order >= 0)):
            self.setting.soft_calibration.to_phys = (
                <_comedilib_h.comedi_polynomial_t *> _stdlib.malloc(
                    sizeof(_comedilib_h.comedi_polynomial_t)))
        self.setting.soft_calibration.to_phys[0] = value._to_physical
        if (self.setting.soft_calibration.from_phys is NULL and
            (value._from_physical.expansion_origin or
             value._from_physical.order >= 0)):
            self.setting.soft_calibration.from_phys = (
                <_comedilib_h.comedi_polynomial_t *> _stdlib.malloc(
                    sizeof(_comedilib_h.comedi_polynomial_t)))
        self.setting.soft_calibration.from_phys[0] = value._from_physical
    soft_calibration = property(
        fget=_soft_calibration_get, fset=_soft_calibration_set)


cdef class Calibration (object):
    """A board calibration configuration.

    Wraps comedi_calibration_t.

    Warning: You probably want to use the `.from_file()` method or
    `device.parse_calibration()` rather than initializing this
    stucture by hand.

    >>> from .device import Device
    >>> from . import constant

    >>> d = Device('/dev/comedi0')
    >>> d.open()

    >>> c = d.parse_calibration()

    >>> print(c)
    <Calibration device:/dev/comedi0>
    >>> c.driver_name
    'ni_pcimio'
    >>> c.board_name
    'pci-6052e'

    >>> c.settings  # doctest: +ELLIPSIS, +NORMALIZE_WHITESPACE
    [<pycomedi.calibration.CalibrationSetting object at 0x...>,
     ...
     <pycomedi.calibration.CalibrationSetting object at 0x...>]
    >>> print(c.settings[0])
    <CalibrationSetting device:/dev/comedi0 subdevice:0>

    >>> name = c.driver_name
    >>> c.driver_name = "Override with your own value"
    >>> c.driver_name = name

    >>> d.close()
    """
    def __cinit__(self):
        self.calibration = NULL

    def __init__(self, device):
        super(Calibration, self).__init__()
        self.device = device

    def __dealloc__(self):
        if self.calibration is not NULL:
            _comedilib_h.comedi_cleanup_calibration(self.calibration)
            self.calibration = NULL

    def __str__(self):
        fields = ['device:{}'.format(self.device.filename)]
        return '<{} {}>'.format(self.__class__.__name__, ' '.join(fields))

    def __repr__(self):
        return '<{} {}>'.format(self.__class__.__name__, id(self))

    def _driver_name_get(self):
        if self.calibration is NULL:
            return None
        return self.calibration.driver_name
    def _driver_name_set(self, value):
        assert self.calibration is not NULL, 'load calibration first'
        _python_to_charp(&self.calibration.driver_name, value, 'ascii')
    driver_name = property(fget=_driver_name_get, fset=_driver_name_set)

    def _board_name_get(self):
        if self.calibration is NULL:
            return None
        return self.calibration.board_name
    def _board_name_set(self, value):
        assert self.calibration is not NULL, 'load calibration first'
        _python_to_charp(&self.calibration.board_name, value, 'ascii')
    board_name = property(fget=_board_name_get, fset=_board_name_set)

    def _settings_get(self):
        if self.calibration is NULL:
            return None
        ret = []
        for i in range(self.calibration.num_settings):
            s = CalibrationSetting(
                subdevice=self.device.subdevice(
                    index=self.calibration.settings[i].subdevice))
            s.setting = &self.calibration.settings[i]
            ret.append(s)
        return ret
    def _settings_set(self, value):
        assert self.calibration is not NULL, 'load calibration first'
        return None
    settings = property(fget=_settings_get, fset=_settings_set)

    cpdef from_file(self, path):
        self.calibration = _comedilib_h.comedi_parse_calibration_file(path)
        if self.calibration == NULL:
            _error.raise_error(
                function_name='comedi_parse_calibration_file')


# TODO: see comedi_caldac_t and related at end of comedilib.h
