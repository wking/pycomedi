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

"Wrap Comedi's `comedi_cmd` struct in the `Command` class"

cimport libc.stdlib as _stdlib
import numpy as _numpy

cimport _comedi_h
cimport _comedilib_h
from pycomedi import PyComediError as _PyComediError
from chanspec import ChanSpec as _ChanSpec
import constant as _constant


cdef class Command (object):
    """A Comedi command

    >>> from .constant import AREF, CMDF, TRIG_SRC    
    >>> from .channel import AnalogChannel
    >>> from .chanspec import ChanSpec
    >>> from .device import Device

    >>> c = Command()
    >>> print str(c)
            subdev: 0
             flags: -
         start_src: -
         start_arg: 0
    scan_begin_src: -
    scan_begin_arg: 0
       convert_src: -
       convert_arg: 0
      scan_end_src: -
      scan_end_arg: 0
          stop_src: -
          stop_arg: 0
          chanlist: []
              data: []

    `data` takes any iterable that supports `length()` and returns NumPy arrays.

    >>> c.data = [1, 2, 3]
    >>> type(c.data)
    <type 'numpy.ndarray'>

    `subdev` is currently just an integer (not a `Subdevice` instance).

    >>> c.subdev = 3
    >>> c.subdev
    3L
    >>> type(c.subdev)
    <type 'long'>

    `flags` and trigger sources return `FlagValue` instances.

    >>> c.flags  # doctest: +ELLIPSIS
    <pycomedi.constant.FlagValue object at 0x...>
    >>> c.flags = CMDF.priority | CMDF.write

    >>> c.start_src  # doctest: +ELLIPSIS
    <pycomedi.constant.FlagValue object at 0x...>
    >>> c.start_src = TRIG_SRC.int | TRIG_SRC.now
    >>> c.scan_begin_src = TRIG_SRC.timer
    >>> c.scan_begin_arg = 10
    >>> c.convert_src = TRIG_SRC.now
    >>> c.scan_end_src = TRIG_SRC.count
    >>> c.scan_end_arg = 4
    >>> c.stop_src = TRIG_SRC.none

    Because `ChanSpec` instances store their value internally (not
    using the value stored in the `Command` instance), direct
    operations on them have no effect on the intruction.

    >>> chanlist = [
    ...     ChanSpec(chan=0, aref=AREF.diff),
    ...     ChanSpec(chan=1, aref=AREF.diff),
    ...     ]
    >>> c.chanlist = chanlist
    >>> c.chanlist[0]
    <ChanSpec chan:0 range:0 aref:diff flags:->
    >>> c.chanlist[0].aref = AREF.ground
    >>> c.chanlist[0]
    <ChanSpec chan:0 range:0 aref:diff flags:->

    To have an effect, you need to explicity set the `chanlist` attribute:

    >>> chanlist = c.chanlist
    >>> chanlist[0].aref = AREF.ground
    >>> c.chanlist = chanlist
    >>> c.chanlist[0]
    <ChanSpec chan:0 range:0 aref:ground flags:->

    You can also set chanspec items with `AnalogChannel` instances (or
    any object that has a `chanspec` method).

    >>> d = Device('/dev/comedi0')
    >>> d.open()
    >>> subdevice = d.get_read_subdevice()
    >>> c.chanlist = [subdevice.channel(1, factory=AnalogChannel,
    ...     aref=AREF.diff)]
    >>> d.close()

    >>> print str(c)
            subdev: 3
             flags: priority|write
         start_src: now|int
         start_arg: 0
    scan_begin_src: timer
    scan_begin_arg: 10
       convert_src: now
       convert_arg: 0
      scan_end_src: count
      scan_end_arg: 4
          stop_src: none
          stop_arg: 0
          chanlist: [<ChanSpec chan:1 range:0 aref:diff flags:->]
              data: [1 2 3]
    """
    def __cinit__(self):
        self._cmd.chanlist = NULL
        self._cmd.data = NULL
        self._fields = [
            'subdev', 'flags', 'start_src', 'start_arg', 'scan_begin_src',
            'scan_begin_arg', 'convert_src', 'convert_arg', 'scan_end_src',
            'scan_end_arg', 'stop_src', 'stop_arg', 'chanlist', 'data']

    def __dealloc__(self):
        if self._cmd.chanlist is not NULL:
            _stdlib.free(self._cmd.chanlist)
        if self._cmd.data is not NULL:
            _stdlib.free(self._cmd.data)

    cdef _comedi_h.comedi_cmd *get_comedi_cmd_pointer(self):
        return &self._cmd

    def __str__(self):
        max_field_length = max([len(f) for f in self._fields])
        lines = []
        for f in self._fields:
            lines.append('%*s: %s' % (max_field_length, f, getattr(self, f)))
        return '\n'.join(lines)

    def _subdev_get(self):
        return self._cmd.subdev
    def _subdev_set(self, value):
        self._cmd.subdev = _constant.bitwise_value(value)
    subdev = property(fget=_subdev_get, fset=_subdev_set)

    def _flags_get(self):
        return _constant.FlagValue(_constant.CMDF, self._cmd.flags)
    def _flags_set(self, value):
        self._cmd.flags = _constant.bitwise_value(value)
    flags = property(fget=_flags_get, fset=_flags_set)

    def _start_src_get(self):
        return _constant.FlagValue(_constant.TRIG_SRC, self._cmd.start_src)
    def _start_src_set(self, value):
        self._cmd.start_src = _constant.bitwise_value(value)
    start_src = property(fget=_start_src_get, fset=_start_src_set)

    def _start_arg_get(self):
        return self._cmd.start_arg
    def _start_arg_set(self, value):
        self._cmd.start_arg = value
    start_arg = property(fget=_start_arg_get, fset=_start_arg_set)

    def _scan_begin_src_get(self):
        return _constant.FlagValue(_constant.TRIG_SRC, self._cmd.scan_begin_src)
    def _scan_begin_src_set(self, value):
        self._cmd.scan_begin_src = _constant.bitwise_value(value)
    scan_begin_src = property(fget=_scan_begin_src_get, fset=_scan_begin_src_set)

    def _scan_begin_arg_get(self):
        return self._cmd.scan_begin_arg
    def _scan_begin_arg_set(self, value):
        self._cmd.scan_begin_arg = value
    scan_begin_arg = property(fget=_scan_begin_arg_get, fset=_scan_begin_arg_set)

    def _convert_src_get(self):
        return _constant.FlagValue(_constant.TRIG_SRC, self._cmd.convert_src)
    def _convert_src_set(self, value):
        self._cmd.convert_src = _constant.bitwise_value(value)
    convert_src = property(fget=_convert_src_get, fset=_convert_src_set)

    def _convert_arg_get(self):
        return self._cmd.convert_arg
    def _convert_arg_set(self, value):
        self._cmd.convert_arg = value
    convert_arg = property(fget=_convert_arg_get, fset=_convert_arg_set)


    def _scan_end_src_get(self):
        return _constant.FlagValue(_constant.TRIG_SRC, self._cmd.scan_end_src)
    def _scan_end_src_set(self, value):
        self._cmd.scan_end_src = _constant.bitwise_value(value)
    scan_end_src = property(fget=_scan_end_src_get, fset=_scan_end_src_set)

    def _scan_end_arg_get(self):
        return self._cmd.scan_end_arg
    def _scan_end_arg_set(self, value):
        self._cmd.scan_end_arg = value
    scan_end_arg = property(fget=_scan_end_arg_get, fset=_scan_end_arg_set)

    def _stop_src_get(self):
        return _constant.FlagValue(_constant.TRIG_SRC, self._cmd.stop_src)
    def _stop_src_set(self, value):
        self._cmd.stop_src = _constant.bitwise_value(value)
    stop_src = property(fget=_stop_src_get, fset=_stop_src_set)

    def _stop_arg_get(self):
        return self._cmd.stop_arg
    def _stop_arg_set(self, value):
        self._cmd.stop_arg = value
    stop_arg = property(fget=_stop_arg_get, fset=_stop_arg_set)

    def _chanlist_get(self):
        ret = list()
        for i in range(self._cmd.chanlist_len):
            c = _ChanSpec()
            c.value = self._cmd.chanlist[i]
            ret.append(c)
        return ret
    def _chanlist_set(self, value):
        if self._cmd.chanlist is not NULL:
            _stdlib.free(self._cmd.chanlist)
        self._cmd.chanlist_len = len(value)
        self._cmd.chanlist = <unsigned int *>_stdlib.malloc(
            self._cmd.chanlist_len*sizeof(unsigned int))
        if self._cmd.chanlist is NULL:
            self._cmd.chanlist_len = 0
            raise _PyComediError('out of memory?')
        for i,x in enumerate(value):
            if hasattr(x, 'chanspec'):
                x = x.chanspec()
            self._cmd.chanlist[i] = _constant.bitwise_value(x)
    chanlist = property(fget=_chanlist_get, fset=_chanlist_set)

    def _data_get(self):
        data = _numpy.ndarray(shape=(self._cmd.data_len,), dtype=_numpy.uint16)
        # TODO: point into existing data array?
        for i in range(self._cmd.data_len):
            data[i] = self._cmd.data[i]
        return data
    def _data_set(self, value):
        if self._cmd.data is not NULL:
            _stdlib.free(self._cmd.data)
        self._cmd.data_len = len(value)
        self._cmd.data = <_comedi_h.sampl_t *>_stdlib.malloc(
            self._cmd.data_len*sizeof(_comedi_h.sampl_t))
        if self._cmd.data is NULL:
            self._cmd.data_len = 0
            raise _PyComediError('out of memory?')
        for i,x in enumerate(value):
            self._cmd.data[i] = x
    data = property(fget=_data_get, fset=_data_set)
