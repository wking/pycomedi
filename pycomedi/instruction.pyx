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

"Wrap Comedi's `comedi_insn` struct in the `Insn` class"

cimport libc.stdlib as _stdlib
import numpy as _numpy

cimport _comedi_h
cimport _comedilib_h
from pycomedi import PyComediError as _PyComediError
from chanspec import ChanSpec as _ChanSpec
import constant as _constant


cdef class Insn (object):
    """A Comedi instruction

    >>> from .constant import INSN, AREF
    >>> i = Insn()
    >>> print str(i)
        insn: read
        data: []
      subdev: 0
    chanspec: <ChanSpec chan:0 range:0 aref:ground flags:->
    >>> i.insn = INSN.write

    `data` takes any iterable that supports `length()` and returns NumPy arrays.

    >>> i.data = [1, 2, 3]
    >>> type(i.data)
    <type 'numpy.ndarray'>

    `subdev` is currently just an integer (not a `Subdevice` instance).

    >>> i.subdev = 3
    >>> i.subdev
    3
    >>> type(i.subdev)
    <type 'int'>

    Because `ChanSpec` instances store their value internally (not
    using the value stored in the `Insn` instance), direct operations
    on them have no effect on the intruction.

    >>> i.chanspec.aref = AREF.diff
    >>> i.chanspec
    <ChanSpec chan:0 range:0 aref:ground flags:->

    To have an effect, you need to explicity set the `chanspec` attribute:

    >>> c = i.chanspec
    >>> c.aref = AREF.diff
    >>> i.chanspec = c
    >>> i.chanspec
    <ChanSpec chan:0 range:0 aref:diff flags:->

    >>> print str(i)
        insn: write
        data: [1 2 3]
      subdev: 3
    chanspec: <ChanSpec chan:0 range:0 aref:diff flags:->
    """
    def __cinit__(self):
        self._insn.insn = _constant.INSN.read.value
        self._insn.data = NULL
        self._fields = ['insn', 'data', 'subdev', 'chanspec']

    def __dealloc__(self):
        if self._insn.data is not NULL:
            _stdlib.free(self._insn.data)

    cdef _comedi_h.comedi_insn get_comedi_insn(self):
        return self._insn

    def __str__(self):
        max_field_length = max([len(f) for f in self._fields])
        lines = []
        for f in self._fields:
            lines.append('%*s: %s' % (max_field_length, f, getattr(self, f)))
        return '\n'.join(lines)

    def _insn_get(self):
        return _constant.INSN.index_by_value(self._insn.insn)
    def _insn_set(self, value):
        self._insn.insn = _constant.bitwise_value(value)
    insn = property(fget=_insn_get, fset=_insn_set)

    def _data_get(self):
        data = _numpy.ndarray(shape=(self._insn.n,), dtype=_numpy.uint)
        # TODO: point into existing data array?
        for i in range(self._insn.n):
            data[i] = self._insn.data[i]
        return data
    def _data_set(self, value):
        if self._insn.data is not NULL:
            _stdlib.free(self._insn.data)
        self._insn.n = len(value)
        self._insn.data = <_comedi_h.lsampl_t *>_stdlib.malloc(
            self._insn.n*sizeof(_comedi_h.lsampl_t))
        if self._insn.data is NULL:
            self._insn.n = 0
            raise _PyComediError('out of memory?')
        for i,x in enumerate(value):
            self._insn.data[i] = x
    data = property(fget=_data_get, fset=_data_set)

    def _subdev_get(self):
        return int(self._insn.subdev)
    def _subdev_set(self, value):
        self._insn.subdev = value
    subdev = property(fget=_subdev_get, fset=_subdev_set)

    def _chanspec_get(self):
        c = _ChanSpec()
        c.value = self._insn.chanspec
        return c
    def _chanspec_set(self, value):
        self._insn.chanspec = _constant.bitwise_value(value)
    chanspec = property(fget=_chanspec_get, fset=_chanspec_set)
