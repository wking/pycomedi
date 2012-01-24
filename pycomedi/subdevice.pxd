# Copyright (C) 2011-2012 W. Trevor King <wking@drexel.edu>
#
# This file is part of pycomedi.
#
# pycomedi is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License as published by the
# Free Software Foundation, either version 2 of the License, or (at your
# option) any later version.
#
# pycomedi is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with pycomedi.  If not, see <http://www.gnu.org/licenses/>.

"Expose `Subdevice` internals at the C level for other Cython modules"

from device cimport Device as _Device
from command cimport Command as _Command


cdef class Subdevice (object):
    cdef public _Device device
    cdef public int index

    cpdef dio_bitfield(self, unsigned int bits=*, write_mask=*, base_channel=*)

cdef class StreamingSubdevice (Subdevice):
    cdef public _Command cmd
    cdef public list _command_test_errors
