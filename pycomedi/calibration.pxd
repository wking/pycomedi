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

"Expose `CalibratedConverter` internals at the C level for other Cython modules"

cimport _comedilib_h


cdef class CalibratedConverter (object):
    cdef _comedilib_h.comedi_polynomial_t _to_physical, _from_physical
    cdef object _from_physical_error

    cdef _str_poly(self, _comedilib_h.comedi_polynomial_t polynomial)
    cpdef to_physical(self, data)
    cpdef from_physical(self, data)
    cpdef get_to_physical_expansion_origin(self)
    cpdef get_to_physical_coefficients(self)
    cpdef get_from_physical_expansion_origin(self)
    cpdef get_from_physical_coefficients(self)


cdef class Caldac (object):
    cdef _comedilib_h.comedi_caldac_t *caldac
    cdef bint _local


cdef class CalibrationSetting (object):
    cdef _comedilib_h.comedi_calibration_setting_t *setting
    cdef public object subdevice  # pycomedi.subdevice.Subdevice

    cdef _caldacs_set_single(self, index, Caldac caldac)
    cpdef _soft_calibration_set(self, CalibratedConverter value)


cdef class Calibration (object):
    cdef _comedilib_h.comedi_calibration_t *calibration
    cdef public object device  # pycomedi.device.Device

    cpdef from_file(self, path)
