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

"Wrap `comedi_range` in a Python class"

from constant cimport BitwiseOperator as _BitwiseOperator
import constant as _constant


cdef class Range (_BitwiseOperator):
    """Stucture displaying a possible channel range

    Warning: You probably want to use `channel.Channel.get_range()` or
    `channel.Channel.find_range()` rather than initializing this
    stucture by hand.  If you do initialize it by hand (or set any
    values by hand), remember that it may no longer correspond to your
    devices built-in range with that index.

    For consistency with other integer wrappers, the range index is
    stored in the `.value` attribute.

    >>> from constant import UNIT
    >>> r = Range(1)
    >>> r
    <Range unit:volt min:0.0 max:0.0>
    >>> r.value
    1
    >>> r.unit = UNIT.mA
    >>> r.min = -2.71828
    >>> r.max = 3.14159
    >>> r
    <Range unit:mA min:-2.71828 max:3.14159>
    >>> r.unit
    <_NamedInt mA>
    """
    def __cinit__(self):
        self.value = -1

    def __init__(self, value):
        self.range.unit = 0
        self.range.min = 0
        self.range.max = 0
        self.value = value

    cdef set_comedi_range(self, _comedilib_h.comedi_range range):
        self.range = range

    def __str__(self):
        fields = ['%s:%s' % (f, getattr(self, f))
                  for f in ['unit', 'min', 'max']]
        return '<%s %s>' % (self.__class__.__name__, ' '.join(fields))

    def __repr__(self):
        return self.__str__()

    def _unit_get(self):
        return _constant.UNIT.index_by_value(self.range.unit)
    def _unit_set(self, value):
        self.range.unit = _constant.bitwise_value(value)
    unit = property(fget=_unit_get, fset=_unit_set)

    def _min_get(self):
        return self.range.min
    def _min_set(self, value):
        self.range.min = value
    min = property(fget=_min_get, fset=_min_set)

    def _max_get(self):
        return self.range.max
    def _max_set(self, value):
        self.range.max = value
    max = property(fget=_max_get, fset=_max_set)
