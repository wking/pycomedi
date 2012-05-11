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

"Wrap channel-wide Comedi functions in `Channel` and related classes"

cimport cython
cimport numpy as _numpy
import numpy as _numpy

cimport _comedi_h
cimport _comedilib_h
from calibration cimport CalibratedConverter as _CalibratedConverter
from range cimport Range as _Range
from subdevice cimport Subdevice as _Subdevice

from pycomedi import LOG as _LOG
from chanspec import ChanSpec as _ChanSpec
from pycomedi import PyComediError as _PyComediError
import _error
import constant as _constant


cdef class Channel (object):
    """Class bundling channel-related functions

    >>> from .device import Device
    >>> from . import constant

    >>> d = Device('/dev/comedi0')
    >>> d.open()
    >>> s = d.get_read_subdevice()
    >>> c = s.channel(index=0)

    >>> c.get_maxdata()
    65535L
    >>> c.get_n_ranges()
    16
    >>> c.get_range(index=0)
    <Range unit:volt min:-10.0 max:10.0>
    >>> c.find_range(constant.UNIT.volt, 0, 5)
    <Range unit:volt min:0.0 max:5.0>

    >>> d.close()
    """
    cdef public _Subdevice subdevice
    cdef public int index

    def __cinit__(self):
        self.index = -1

    def __init__(self, subdevice, index):
        super(Channel, self).__init__()
        self.subdevice = subdevice
        self.index = index

    def get_maxdata(self):
        ret = _comedilib_h.comedi_get_maxdata(
            self.subdevice.device.device,
            self.subdevice.index, self.index)
        if ret < 0:
            _error.raise_error(function_name='comedi_get_maxdata', ret=ret)
        return ret

    def get_n_ranges(self):
        ret = _comedilib_h.comedi_get_n_ranges(
            self.subdevice.device.device,
            self.subdevice.index, self.index)
        if ret < 0:
            _error.raise_error(function_name='comedi_get_n_ranges', ret=ret)
        return ret

    cdef _get_range(self, index):
        cdef _comedilib_h.comedi_range *rng
        cdef _Range ret
        # Memory pointed to by the return value is freed on Device.close().
        rng = _comedilib_h.comedi_get_range(
            self.subdevice.device.device,
            self.subdevice.index, self.index, index)
        if rng is NULL:
            _error.raise_error(function_name='comedi_get_range')
        ret = _Range(value=index)
        ret.set_comedi_range(rng[0])
        # rng[0] is a sneaky way to dereference rng, since Cython
        # doesn't support *rng.
        return ret

    @cython.always_allow_keywords(True)
    def get_range(self, index):
        "`Range` instance for the `index`\ed range."
        return self._get_range(index)

    def _find_range(self, unit, min, max):
        "Search for range"
        ret = _comedilib_h.comedi_find_range(
            self.subdevice.device.device,
            self.subdevice.index, self.index,
            _constant.bitwise_value(unit), min, max)
        if ret < 0:
            _error.raise_error(function_name='comedi_find_range', ret=ret)
        return ret

    def find_range(self, unit, min, max):
        """Search for range

        `unit` should be an item from `constants.UNIT`.
        """
        return self.get_range(self._find_range(unit, min, max))

    def ranges(self, **kwargs):
        "Iterate through all available ranges."
        ret = []
        for i in range(self.get_n_ranges()):
            #yield self.subdevice(i, **kwargs)
            # Generators are not supported in Cython 0.14.1
            ret.append(self.get_range(i, **kwargs))
        return ret


cdef class DigitalChannel (Channel):
    """Channel configured for reading or writing digital data.

    >>> from .device import Device
    >>> from . import constant

    >>> d = Device('/dev/comedi0')
    >>> d.open()
    >>> s = d.find_subdevice_by_type(constant.SUBDEVICE_TYPE.dio)
    >>> c = s.channel(0, factory=DigitalChannel)

    >>> c.get_maxdata()
    1L
    >>> c.get_n_ranges()
    1
    >>> c.get_range(0)
    <Range unit:volt min:0.0 max:5.0>

    >>> direction = c.dio_get_config()
    >>> direction  # doctest: +SKIP
    <_NamedInt input>

    >>> c.dio_config(_constant.IO_DIRECTION.input)
    >>> data = c.dio_read()
    >>> data
    1

    >>> c.dio_config(_constant.IO_DIRECTION.output)
    >>> c.dio_write(1)

    >>> c.dio_config(direction)

    >>> d.close()
    """
    def dio_config(self, dir):
        """Change input/output properties

        `dir` should be an item from `constants.IO_DIRECTION`.
        """
        ret = _comedilib_h.comedi_dio_config(
            self.subdevice.device.device,
            self.subdevice.index, self.index,
            _constant.bitwise_value(dir))
        if ret < 0:
            _error.raise_error(function_name='comedi_dio_config', ret=ret)

    def dio_get_config(self):
        """Query input/output properties

        Return an item from `constant.IO_DIRECTION`.
        """
        cpdef unsigned int dir
        ret = _comedilib_h.comedi_dio_get_config(
            self.subdevice.device.device,
           self.subdevice.index, self.index, &dir)
        if ret < 0:
            _error.raise_error(function_name='comedi_dio_get_config', ret=ret)
        return _constant.IO_DIRECTION.index_by_value(dir)

    def dio_read(self):
        "Read a single bit"
        cpdef unsigned int bit
        ret = _comedilib_h.comedi_dio_read(
            self.subdevice.device.device,
            self.subdevice.index, self.index, &bit)
        if ret < 0:
            _error.raise_error(function_name='comedi_dio_read', ret=ret)
        return int(bit)

    def dio_write(self, bit):
        "Write a single bit"
        ret = _comedilib_h.comedi_dio_write(
            self.subdevice.device.device,
            self.subdevice.index, self.index, bit)
        if ret < 0:
            _error.raise_error(function_name='comedi_dio_write', ret=ret)


cdef class AnalogChannel (Channel):
    """Channel configured for reading or writing analog data.

    `range` should be a `Range` instance, `aref` should be an
    `constants.AREF` instance.  If not specified, defaults are chosen
    based on the capabilities of the subdevice.

    >>> from .device import Device
    >>> from . import constant

    >>> d = Device('/dev/comedi0')
    >>> d.open()
    >>> s = d.get_read_subdevice()
    >>> c = s.channel(0, factory=AnalogChannel)

    >>> c.range
    <Range unit:volt min:-10.0 max:10.0>
    >>> c.aref
    <_NamedInt ground>

    >>> data = c.data_read()
    >>> data  # doctest: +SKIP
    32670L
    >>> converter = c.get_converter()
    >>> converter  # doctest: +NORMALIZE_WHITESPACE
    <CalibratedConverter
     to_physical:{coefficients:[-10.0, 0.00030518043793392844] origin:0.0}
     from_physical:{coefficients:[0.0, 3276.75] origin:-10.0}>
    >>> physical_data = converter.to_physical(data)
    >>> physical_data  # doctest: +SKIP
    -0.029755092698558021
    >>> converter.from_physical(physical_data) == data
    True

    >>> data = c.data_read_n(5)
    >>> data  # doctest: +SKIP
    array([32674, 32673, 32674, 32672, 32675], dtype=uint32)

    >>> c.data_read_hint()
    >>> c.data_read()  # doctest: +SKIP
    32672L

    >>> data = c.data_read_delayed(nano_sec=1e3)
    >>> data  # doctest: +SKIP
    32672L

    >>> s = d.get_write_subdevice()
    >>> c = s.channel(0, factory=AnalogChannel)

    >>> converter = c.get_converter()
    >>> converter  # doctest: +NORMALIZE_WHITESPACE
    <CalibratedConverter
     to_physical:{coefficients:[-10.0, 0.00030518043793392844] origin:0.0}
     from_physical:{coefficients:[0.0, 3276.75] origin:-10.0}>

    >>> c.data_write(converter.from_physical(0))

    >>> d.close()

    Even after the device is closed, the range information is
    retained.

    >>> c.range
    <Range unit:volt min:-10.0 max:10.0>
    """
    cdef public _Range range
    cdef public object aref

    def __init__(self, range=None, aref=None, **kwargs):
        super(AnalogChannel, self).__init__(**kwargs)
        if range == None:
            range = self.get_range(0)
        elif isinstance(range, int):
            range = self.get_range(range)
        self.range = range
        if aref == None:
            flags = self.subdevice.get_flags()
            for ar in _constant.AREF:
                if getattr(flags, ar.name):
                    aref = ar
                    break
                raise _PyComediError(
                    '%s does not support any known analog reference type (%s)'
                    % (self.subdevice, flags))
        self.aref = aref

    # syncronous stuff

    def data_read(self):
        "Read one sample"
        cdef _comedi_h.lsampl_t data
        ret = _comedilib_h.comedi_data_read(
            self.subdevice.device.device,
            self.subdevice.index, self.index,
            _constant.bitwise_value(self.range),
            _constant.bitwise_value(self.aref),
            &data)
        if ret < 0:
            _error.raise_error(function_name='comedi_data_read', ret=ret)
        return data

    def data_read_n(self, n):
        "Read `n` samples (timing between samples is undefined)."
        data = _numpy.ndarray(shape=(n,), dtype=_numpy.uint32)
        ret = _comedilib_h.comedi_data_read_n(
            self.subdevice.device.device,
            self.subdevice.index, self.index,
            _constant.bitwise_value(self.range),
            _constant.bitwise_value(self.aref),
            <_comedilib_h.lsampl_t *>_numpy.PyArray_DATA(data), n)
        if ret < 0:
            _error.raise_error(function_name='comedi_data_read_n', ret=ret)
        return data

    def data_read_hint(self):
        """Tell driver which channel/range/aref you will read next

        Used to prepare an analog input for a subsequent call to
        comedi_data_read.  It is not necessary to use this function,
        but it can be useful for eliminating inaccuaracies caused by
        insufficient settling times when switching the channel or gain
        on an analog input.  This function sets an analog input to the
        channel, range, and aref specified but does not perform an
        actual analog to digital conversion.

        Alternatively, one can simply use `.data_read_delayed()`,
        which sets up the input, pauses to allow settling, then
        performs a conversion.
        """
        ret = _comedilib_h.comedi_data_read_hint(
            self.subdevice.device.device,
            self.subdevice.index, self.index,
            _constant.bitwise_value(self.range),
            _constant.bitwise_value(self.aref))
        if ret < 0:
            _error.raise_error(function_name='comedi_data_read_hint', ret=ret)

    def data_read_delayed(self, nano_sec=0):
        """Read single sample after delaying specified settling time.

        Although the settling time is specified in integer
        nanoseconds, the actual settling time will be rounded up to
        the nearest microsecond.
        """
        cdef _comedi_h.lsampl_t data
        ret = _comedilib_h.comedi_data_read_delayed(
            self.subdevice.device.device,
            self.subdevice.index, self.index,
            _constant.bitwise_value(self.range),
            _constant.bitwise_value(self.aref),
            &data, int(nano_sec))
        if ret < 0:
            _error.raise_error(function_name='comedi_data_read_delayed',
                               ret=ret)
        return data

    def data_write(self, data):
        """Write one sample

        Returns 1 (the number of data samples written).
        """
        ret = _comedilib_h.comedi_data_write(
            self.subdevice.device.device,
            self.subdevice.index, self.index,
            _constant.bitwise_value(self.range),
            _constant.bitwise_value(self.aref),
            int(data))
        if ret != 1:
            _error.raise_error(function_name='comedi_data_write', ret=ret)

    def chanspec(self):
        return _ChanSpec(chan=self.index, range=self.range, aref=self.aref)


    cdef _comedilib_h.comedi_polynomial_t get_softcal_converter(
        self, direction, calibration):
        """

        `direction` should be a value from `constant.CONVERSION_DIRECTION`.
        """
        cdef _comedilib_h.comedi_polynomial_t poly
        #rc = _comedilib_h.comedi_get_softcal_converter(
        #    self.subdevice.device.device,
        #    self.subdevice.index, self.index,
        #    _constant.bitwise_value(self.range),
        #    _constant.bitwise_value(direction),
        #    calibration, &poly)
        #if rc < 0:
        #    _error.raise_error(function_name='comedi_get_softcal_converter',
        #                       ret=rc)
        return poly

    cdef _comedilib_h.comedi_polynomial_t get_hardcal_converter(
        self, direction):
        """

        `direction` should be a value from `constant.CONVERSION_DIRECTION`.
        """
        cdef _comedilib_h.comedi_polynomial_t poly
        rc = _comedilib_h.comedi_get_hardcal_converter(
            self.subdevice.device.device,
            self.subdevice.index, self.index,
            _constant.bitwise_value(self.range),
            _constant.bitwise_value(direction), &poly)
        if rc < 0:
            _error.raise_error(function_name='comedi_get_hardcal_converter',
                               ret=rc)
        return poly

    cdef _get_converter(self, calibration):
        cdef _comedilib_h.comedi_polynomial_t to_physical, from_physical
        cdef _CalibratedConverter ret
        flags = self.subdevice.get_flags()
        if flags.soft_calibrated:
            #if calibration is None:
            #    calibration = self.subdevice.device.parse_calibration()
            raise NotImplementedError()
        else:
            to_physical = self.get_hardcal_converter(
                _constant.CONVERSION_DIRECTION.to_physical)
            from_physical = self.get_hardcal_converter(
                _constant.CONVERSION_DIRECTION.from_physical)
        ret = _CalibratedConverter()
        ret._to_physical = to_physical
        ret._from_physical = from_physical
        return ret

    def get_converter(self, calibration=None):
        return self._get_converter(calibration)
