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

"Wrap device-wide Comedi functions in a `Device` class"

import os as _os
cimport libc.stdlib as _stdlib

from pycomedi import LOG as _LOG
from pycomedi import PyComediError as _PyComediError
cimport _comedi_h
cimport _comedilib_h
import _error
from instruction cimport Insn as _Insn
from instruction import Insn as _Insn
from subdevice import Subdevice as _Subdevice


cdef class Device (object):
    """A Comedi device

    >>> from . import constant

    >>> d = Device('/dev/comediX')
    >>> d.filename
    '/dev/comediX'

    > d.open()  # TODO: re-enable when there is a way to clear comedi_errno
    Traceback (most recent call last):
      ...
    PyComediError: comedi_open (/dev/comediX): No such file or directory (None)
    >>> d.filename = '/dev/comedi0'
    >>> d.open()
    >>> d.fileno()
    3
    >>> d.get_n_subdevices()
    14
    >>> d.get_version()
    (0, 7, 76)
    >>> d.get_driver_name()
    'ni_pcimio'
    >>> s = d.get_read_subdevice()
    >>> s.index
    0
    >>> s = d.get_write_subdevice()
    >>> s.index
    1
    >>> s = d.find_subdevice_by_type(constant.SUBDEVICE_TYPE.calib)
    >>> s.index
    5
    >>> s = d.find_subdevice_by_type(constant.SUBDEVICE_TYPE.pwm)
    Traceback (most recent call last):
      ...
    PyComediError: comedi_find_subdevice_by_type: Success (-1)

    As a test instruction, we'll get the time of day, which fills in
    the data field with `[seconds, microseconds]`.

    >>> insn = d.insn()
    >>> insn.insn = constant.INSN.gtod
    >>> insn.data = [0, 0]  # space where the time value will be stored
    >>> print str(insn)
        insn: gtod
        data: [0 0]
      subdev: 0
    chanspec: <ChanSpec chan:0 range:0 aref:ground flags:->
    >>> d.do_insn(insn)
    2
    >>> print insn.data  # doctest: +SKIP
    [1297377578     105790]
    >>> insn.data = [0, 0]
    >>> d.do_insnlist([insn])
    1
    >>> print insn.data  # doctest: +SKIP
    [1297377578     110559]

    >>> d.get_default_calibration_path()
    '/var/lib/comedi/calibrations/ni_pcimio_pci-6052e_comedi0'

    >>> list(d.subdevices())  # doctest: +ELLIPSIS
    [<pycomedi.subdevice.Subdevice object at 0x...>,...]

    >>> d.close()
    """
    def __cinit__(self):
        self.device = NULL
        self.file = None
        self.filename = None

    def __init__(self, filename):
        super(Device, self).__init__()
        self.filename = filename

    def open(self):
        "Open device"
        self.device = _comedilib_h.comedi_open(self.filename)
        if self.device == NULL:
            _error.raise_error(function_name='comedi_open',
                               error_msg=self.filename)
        self.file = _os.fdopen(self.fileno(), 'r+')

    def close(self):
        "Close device"
        self.file.flush()
        self.file.close()
        ret = _comedilib_h.comedi_close(self.device)
        if ret < 0:
            _error.raise_error(function_name='comedi_close', ret=ret)
        self.device = NULL
        self.file = None

    def fileno(self):
        "File descriptor for this device"
        ret = _comedilib_h.comedi_fileno(self.device)
        if ret < 0:
            _error.raise_error(function_name='comedi_fileno', ret=ret)
        return ret

    def get_n_subdevices(self):
        "Number of subdevices"
        ret = _comedilib_h.comedi_get_n_subdevices(self.device)
        if ret < 0:
            _error.raise_error(function_name='comedi_get_n_subdevices',
                                ret=ret)
        return ret

    def get_version_code(self):
        """Comedi version code as a single integer.

        This is a kernel-module level property, but a valid device is
        necessary to communicate with the kernel module.
        """
        version = _comedilib_h.comedi_get_version_code(self.device)
        if version < 0:
            _error.raise_error(function_name='comedi_get_version_code',
                                ret=version)
        return version

    def get_version(self):
        """Comedi version as a tuple of version numbers.

        Returns the result of `.get_version_code()`, but rephrased as
        a tuple of version numbers, e.g. `(0, 7, 61)`.
        """
        version = self.get_version_code()
        ret = []
        for i in range(3):
            ret.insert(0, version & 0xff)  # grab lowest 8 bits
            version >>= 8  # shift over 8 bits
        return tuple(ret)

    def get_driver_name(self):
        "Comedi driver name"
        ret = _comedilib_h.comedi_get_driver_name(self.device)
        if ret == NULL:
            _error.raise_error(function_name='comedi_get_driver_name',
                                ret=ret)
        return ret

    def get_board_name(self):
        "Comedi board name"
        ret = _comedilib_h.comedi_get_board_name(self.device)
        if ret == NULL:
            _error.raise_error(function_name='comedi_get_driver_name',
                                ret=ret)
        return ret

    def _get_read_subdevice(self):
        "Find streaming input subdevice index"
        ret = _comedilib_h.comedi_get_read_subdevice(self.device)
        if ret < 0:
            _error.raise_error(function_name='comedi_get_read_subdevice',
                                ret=ret)
        return ret

    def get_read_subdevice(self, **kwargs):
        "Find streaming input subdevice"
        return self.subdevice(self._get_read_subdevice(), **kwargs)

    def _get_write_subdevice(self):
        "Find streaming output subdevice index"
        ret = _comedilib_h.comedi_get_write_subdevice(self.device)
        if ret < 0:
            _error.raise_error(function_name='comedi_get_write_subdevice',
                                ret=ret)
        return ret

    def get_write_subdevice(self, **kwargs):
        "Find streaming output subdevice"
        return self.subdevice(self._get_write_subdevice(), **kwargs)

    def _find_subdevice_by_type(self, subdevice_type):
        "Search for a subdevice index for type `subdevice_type`)."
        ret = _comedilib_h.comedi_find_subdevice_by_type(
            self.device, subdevice_type.value, 0)  # 0 is starting subdevice
        if ret < 0:
            _error.raise_error(function_name='comedi_find_subdevice_by_type',
                                ret=ret)
        return ret

    def find_subdevice_by_type(self, subdevice_type, **kwargs):
        """Search for a subdevice by type `subdevice_type`)."

        `subdevice_type` should be an item from `constant.SUBDEVICE_TYPE`.
        """
        return self.subdevice(
            self._find_subdevice_by_type(subdevice_type), **kwargs)

    cpdef do_insnlist(self, insnlist):
        """Perform multiple instructions

        Returns the number of successfully completed instructions.
        """
        cdef _comedi_h.comedi_insnlist il
        cdef _Insn i
        il.n_insns = len(insnlist)
        if il.n_insns == 0:
            return
        il.insns = <_comedi_h.comedi_insn *>_stdlib.malloc(
            il.n_insns*sizeof(_comedi_h.comedi_insn))
        if il.insns is NULL:
            raise _PyComediError('out of memory?')
        try:
            for j,insn in enumerate(insnlist):
                i = insn
                # By copying the pointer to data, changes to this
                # copied instruction will also affect the original
                # instruction's data.
                il.insns[j] = i.get_comedi_insn()
            ret = _comedilib_h.comedi_do_insnlist(self.device, &il)
        finally:
            _stdlib.free(il.insns)
        if ret < len(insnlist):
            _error.raise_error(function_name='comedi_do_insnlist', ret=ret)
        return ret

    cpdef do_insn(self, _Insn insn):
        """Preform a single instruction.

        Returns an instruction-specific integer.
        """
        cdef _comedi_h.comedi_insn i
        # By copying the pointer to data, changes to this
        # copied instruction will also affect the original
        # instruction's data.
        i = insn.get_comedi_insn()
        ret = _comedilib_h.comedi_do_insn(
            self.device, &i)
        if ret < 0:
            _error.raise_error(function_name='comedi_do_insn', ret=ret)
        return ret

    def get_default_calibration_path(self):
        "The default calibration path for this device"
        assert self.device != NULL, (
            'must call get_default_calibration_path on an open device.')
        ret = _comedilib_h.comedi_get_default_calibration_path(self.device)
        if ret == NULL:
            _error.raise_error(
                function_name='comedi_get_default_calibration_path')
        return ret

    # extensions to make a more idomatic Python interface

    def insn(self):
        return _Insn()

    def subdevices(self, **kwargs):
        "Iterate through all available subdevices."
        ret = []
        for i in range(self.get_n_subdevices()):
            #yield self.subdevice(i, **kwargs)
            # Generators are not supported in Cython 0.14.1
            ret.append(self.subdevice(i, **kwargs))
        return ret

    def subdevice(self, index, factory=_Subdevice, **kwargs):
        return factory(device=self, index=index, **kwargs)
