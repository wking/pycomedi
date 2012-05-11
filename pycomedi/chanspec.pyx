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

"Replace Comedi's CR_PACK and related macros with a Python class"

cimport _comedi_h
import constant as _constant


class ChanSpec (_constant.BitwiseOperator):
    """Channel specification bitfield

    >>> from .constant import AREF, CR
    >>> c = ChanSpec(chan=1, range=3, aref=AREF.diff,
    ...     flags=CR.edge|CR.invert)
    >>> print c
    <ChanSpec chan:1 range:3 aref:diff flags:edge|invert>
    >>> c.chan
    1L
    >>> c.chan = 2
    >>> c.chan
    2L
    """
    _fields = ['chan', 'range', 'aref', 'flags']
    _all = 0xffffffffL

    def __init__(self, chan=0, range=0, aref=0, flags=0):
        self.value = 0L
        self.chan = chan
        self.range = range
        self.aref = aref
        self.flags = flags

    def __str__(self):
        # TODO: consolidate to a utility class or function
        fields = ['%s:%s' % (f, getattr(self, f)) for f in self._fields]
        return '<%s %s>' % (self.__class__.__name__, ' '.join(fields))

    def __repr__(self):
        return self.__str__()

    def _chan_get(self):
        return self.value & 0xff
    def _chan_set(self, value):
        self.value &= self._all - 0xff
        self.value |= _constant.bitwise_value(value) & 0xff
    chan = property(fget=_chan_get, fset=_chan_set)

    def _range_get(self):
        return (self.value >> 16) & 0xff
    def _range_set(self, value):
        self.value &= self._all - (0xff << 16)
        self.value |= (_constant.bitwise_value(value) & 0xff) << 16
    range = property(fget=_range_get, fset=_range_set)

    def _aref_get(self):
        v = (self.value >> 24) & 0x03
        return _constant.AREF.index_by_value(v)
    def _aref_set(self, value):
        self.value &= self._all - (0x03 << 24)
        self.value |= (_constant.bitwise_value(value) & 0x03) << 24
    aref = property(fget=_aref_get, fset=_aref_set)

    def _flags_get(self):
        v = self.value & _constant.CR._all.value
        return _constant.FlagValue(_constant.CR, v)
    def _flags_set(self, value):
        self.value &= self._all - _constant.CR._all.value
        self.value |= _constant.bitwise_value(value) & _constant.CR._all.value
    flags = property(fget=_flags_get, fset=_flags_set)
