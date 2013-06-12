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

"Expose `Subdevice` internals at the C level for other Cython modules"

from pycomedi cimport _comedilib_h
from pycomedi cimport command as _command
from pycomedi cimport subdevice_holder as _subdevice_holder


cdef class Subdevice (_subdevice_holder.SubdeviceHolder):
    cpdef dio_bitfield(self, unsigned int bits=*, write_mask=*, base_channel=*)


cdef class StreamingSubdevice (Subdevice):
    cdef public _command.Command cmd
    cdef public list _command_test_errors
