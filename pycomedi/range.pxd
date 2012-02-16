# Copyright (C) 2011-2012 W. Trevor King <wking@drexel.edu>
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

"Expose `Range` internals at the C level for other Cython modules"

cimport _comedilib_h
from constant cimport BitwiseOperator as _BitwiseOperator


cdef class Range (_BitwiseOperator):
    cdef _comedilib_h.comedi_range range

    cdef set_comedi_range(self, _comedilib_h.comedi_range range)
