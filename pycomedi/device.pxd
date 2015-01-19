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

"Expose `Device` internals at the C level for other Cython modules"

from pycomedi cimport _comedilib_h
from pycomedi.device_holder cimport DeviceHolder as _DeviceHolder
from pycomedi cimport instruction as _instruction


cdef class Device (_DeviceHolder):
    cdef public object file
    cdef public object filename

    cpdef do_insnlist(self, insnlist)
    cpdef do_insn(self, _instruction.Insn insn)
