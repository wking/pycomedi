# Copyright (C) 2010-2011  W. Trevor King
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

"Object oriented wrappers around the comedi module."

import os as _os

import comedi as _comedi
import numpy as _numpy

from . import LOG as _LOG
from . import PyComediError as _PyComediError
from . import constants as _constants


def _comedi_arg(arg):
    "Replace arguments with their comedilib value."
    if isinstance(arg, _constants._BitwiseOperator):
        return arg.value
    elif isinstance(arg, Command):
        _LOG.debug(str(arg))
        return arg.cmd
    elif isinstance(arg, Chanlist):
        return arg.chanlist()
    return arg

def _comedi_getter(name, is_invalid):
    def comedi_get(function_name, *args, **kwargs):
        if 'error_msg' in kwargs:
            error_msg = kwargs.pop('error_msg')
        else:
            error_msg = 'error while running %s with %s and %s' % (
                function_name, args, kwargs)
        fn = getattr(_comedi, function_name)

        _LOG.debug('calling %s with %s %s' % (function_name, args, kwargs))

        args = list(args)
        for i,arg in enumerate(args):
            args[i] = _comedi_arg(arg)
        for key,value in kwargs.iteritems():
            kwargs[key] = _comedi_arg(value)

        ret = fn(*args, **kwargs)
        _LOG.debug('  call to %s returned %s' % (function_name, ret))
        if is_invalid(ret):
            errno = _comedi.comedi_errno()
            comedi_msg = _comedi.comedi_strerror(errno)
            _comedi.comedi_perror(function_name)
            raise _PyComediError('%s: %s (%s)' % (error_msg, comedi_msg, ret))
        return ret
    comedi_get.__name__ = name
    comedi_get.__doc__ = (
        'Execute `comedi.<function_name>(*args, **kwargs)` safely.')
    return comedi_get

_comedi_int = _comedi_getter('comedi_int', lambda ret: ret < 0)
_comedi_ptr = _comedi_getter('comedi_ptr', lambda ret: ret == None)
_comedi_tup = _comedi_getter('comedi_tup', lambda ret: ret[0] < 0)


def _cache(method):
    def wrapper(self, *args, **kwargs):
        key = (method.__name__, args, str(kwargs))
        if key not in self._cache:
            self._cache[key] = method(self, *args, **kwargs)
        return self._cache[key]
    wrapper.__name__ = method.__name__
    wrapper.__doc__ = method.__doc__
    return wrapper


class CacheObject (object):
    """An object that caches return values for decoreated merthods.

    >>> class A (CacheObject):
    ...     @_cache
    ...     def double(self, x):
    ...         print 'calculating 2*%d' % x
    ...         return x*2
    >>> a = A()
    >>> a.double(2)
    calculating 2*2
    4
    >>> a.double(2)
    4
    >>> a.double(3)
    calculating 2*3
    6
    >>> a.double(3)
    6
    >>> print sorted(a._cache.keys())
    [('double', (2,), '{}'), ('double', (3,), '{}')]
    """
    def __init__(self):
        self.clear_cache()

    def clear_cache(self):
        self._cache = {}


class Channel (CacheObject):
    def __init__(self, subdevice, index):
        super(Channel, self).__init__()
        self._subdevice = subdevice
        self._index = index

    @_cache
    def get_maxdata(self):
        return _comedi_int(
            'comedi_get_maxdata', self._subdevice._device._device,
            self._subdevice._index, self._index)

    @_cache
    def get_n_ranges(self):
        return _comedi_int(
            'comedi_get_n_ranges', self._subdevice._device._device,
            self._subdevice._index, self._index)

    def get_range(self, index):
        r = _comedi_ptr(
            'comedi_get_range', self._subdevice._device._device,
            self._subdevice._index, self._index, index)
        return Range(index=index, range=r)

    @_cache
    def _find_range(self, unit, min, max):
        "Search for range"
        return _comedi_int(
            'comedi_find_range', self._subdevice._device._device,
            self._subdevice._index, self._index, unit.value, min, max)

    def find_range(self, unit, min, max):
        """Search for range

        `unit` should be an item from `constants.UNIT`.
        """
        return self.get_range(self._find_range(unit, min, max))


class Subdevice (CacheObject):
    def __init__(self, device, index):
        super(Subdevice, self).__init__()
        self._device = device
        self._index = index

    @_cache
    def get_type(self):
        "Type of subdevice (from `SUBDEVICE_TYPE`)"
        _type = _comedi_int(
            'comedi_get_subdevice_type', self._device._device, self._index)
        return _constants.SUBDEVICE_TYPE.index_by_value(_type)

    @_cache
    def _get_flags(self):
        "Subdevice flags"
        return _comedi_int(
            'comedi_get_subdevice_flags', self._device._device, self._index)

    def get_flags(self):
        "Subdevice flags (an `SDF` `FlagValue`)"
        return _constants.FlagValue(
            _constants.SDF, self._get_flags())

    @_cache
    def n_channels(self):
        "Number of subdevice channels"
        return _comedi_int(
            'comedi_get_n_channels', self._device._device, self._index)

    @_cache
    def range_is_chan_specific(self):
        return _comedi_int(
            'comedi_range_is_chan_specific', self._device._device, self._index)

    @_cache
    def maxdata_is_chan_specific(self):
        return _comedi_int(
            'comedi_maxdata_is_chan_specific',
            self._device._device, self._index)

    def lock(self):
        "Reserve the subdevice"
        _comedi_int('comedi_lock', self._device._device, self._index)

    def unlock(self):
        "Release the subdevice"
        _comedi_int('comedi_unlock', self._device._device, self._index)
        
    def dio_bitfield(self, bits=0, write_mask=0, base_channel=0):
        """Read/write multiple digital channels.

        `bits` and `write_mask` are bit fields with the least
        significant bit representing channel `base_channel`.

        Returns a bit field containing the read value of all input
        channels and the last written value of all output channels.
        """
        rc,bits = _comedi_tup(
            'comedi_dio_bitfield2', self._device._device,
            self._index, write_mask, bits, base_channel)
        return bits

    # extensions to make a more idomatic Python interface

    def insn(self):
        insn = self._device.insn()
        insn.subdev = self._index
        return insn

    def channel(self, index, factory=Channel, **kwargs):
        "`Channel` instance for the `index`\ed channel."
        return factory(subdevice=self, index=index, **kwargs)


class Device (CacheObject):
    "Class bundling device-related functions."
    def __init__(self, filename):
        super(Device, self).__init__()
        self.filename = filename
        self._device = None
        self.file = None

    def open(self):
        "Open device"
        self._device = _comedi_ptr('comedi_open', self.filename)
        self.file = _os.fdopen(self.fileno(), 'r+')
        self.clear_cache()

    def close(self):
        "Close device"
        self.file.flush()
        self.file.close()
        _comedi_int('comedi_close', self._device)
        self._device = None
        self.file = None
        self.clear_cache()

    @_cache
    def fileno(self):
        "File descriptor for this device"
        return _comedi_int('comedi_fileno', self._device)

    @_cache
    def get_n_subdevices(self):
        "Number of subdevices"
        self._cache
        return _comedi_int('comedi_get_n_subdevices', self._device)

    @_cache
    def get_version_code(self):
        """Comedi version code.

        This is a kernel-module level property, but a valid device is
        necessary to communicate with the kernel module.

        Returns a tuple of version numbers, e.g. `(0, 7, 61)`.
        """
        version = _comedi_int('comedi_get_version_code', self._device)
        ret = []
        for i in range(3):
            ret.insert(0, version & (2**8-1))
            version >>= 2**8  # shift over 8 bits
        return tuple(ret)

    @_cache
    def get_driver_name(self):
        "Comedi driver name"
        return _comedi_ptr('get_driver_name', self._device)

    @_cache
    def get_board_name(self):
        "Comedi board name"
        return _comedi_ptr('get_board_name', self._device)

    @_cache
    def _get_read_subdevice(self):
        "Find streaming input subdevice index"
        return _comedi_int('comedi_get_read_subdevice', self._device)

    def get_read_subdevice(self, **kwargs):
        "Find streaming input subdevice"
        return self.subdevice(self._get_read_subdevice(), **kwargs)

    @_cache
    def _get_write_subdevice(self):
        "Find streaming output subdevice index"
        return _comedi_int('comedi_get_write_subdevice', self._device)

    def _get_write_subdevice(self, **kwargs):
        "Find streaming output subdevice"
        return self.subdevice(self._get_write_subdevice(), **kwargs)

    @_cache
    def _find_subdevice_by_type(self, subdevice_type):
        "Search for a subdevice index for type `subdevice_type`)."
        return _comedi_int(
            'comedi_find_subdevice_by_type',
            self._device, subdevice_type.value, 0)   # 0 is starting subdevice

    def find_subdevice_by_type(self, subdevice_type, **kwargs):
        """Search for a subdevice by type `subdevice_type`)."
    
        `subdevice_type` should be an item from `constants.SUBDEVICE_TYPE`.
        """
        return self.subdevice(
            self._find_subdevice_by_type(subdevice_type), **kwargs)

    def do_insnlist(self, insnlist):
        """Perform multiple instructions

        Returns the number of successfully completed instructions.
        """
        return _comedi_int('comedi_do_insn', self._device, insn)

    def do_insn(self, insn):
        """Preform a single instruction.

        Returns an instruction-specific integer.
        """
        return _comedi_int('comedi_do_insn', self._device, insn)

    def get_default_calibration_path(self):
        "The default calibration path for this device"
        assert self._device != None, (
            'Must call get_default_calibration_path on an open device.')
        return _comedi_ptr('comedi_get_default_calibration_path', self._device)

    # extensions to make a more idomatic Python interface

    def insn(self):
        return _comedi.comedi_insn_struct()

    def subdevices(self, **kwargs):
        "Iterate through all available subdevices."
        for i in range(self.n_subdevices):
            yield self.subdevice(i, **kwargs)

    def subdevice(self, index, factory=Subdevice, **kwargs):
        return factory(device=self, index=index, **kwargs)


class Range (object):
    def __init__(self, index, range):
        self.index = index
        self.range = range

    def __getattr__(self, name):
        return getattr(self.range, name)


class Command (object):
    """Wrap `comedi.comedi_cmd` with a nicer interface.

    Examples
    --------

    >>> from .utility import set_cmd_chanlist, set_cmd_data
    >>> CMDF = _constants.CMDF
    >>> TRIG_SRC = _constants.TRIG_SRC
    >>> c = Command()
    >>> c.subdev = 1
    >>> c.flags = CMDF.priority | CMDF.write
    >>> c.start_src = TRIG_SRC.int | TRIG_SRC.now
    >>> c.scan_begin_src = TRIG_SRC.timer
    >>> c.scan_begin_arg = 10
    >>> c.scan_convert_src = TRIG_SRC.now
    >>> c.scan_end_src = TRIG_SRC.count
    >>> c.scan_end_arg = 4
    >>> c.stop_src = TRIG_SRC.none
    >>> set_cmd_chanlist(c, [])
    >>> set_cmd_data(c, [1,2,3])
    >>> print c  # doctest: +ELLIPSIS, +REPORT_UDIFF
    Comedi command:
              subdev : 1
               flags : priority|write
           start_src : now|int
           start_arg : 0
      scan_begin_src : timer
      scan_begin_arg : 10
         convert_src : -
         convert_arg : 0
        scan_end_src : count
        scan_end_arg : 4
            stop_src : none
            stop_arg : 0
            chanlist : <comedi.lsampl_array... at 0x...>
        chanlist_len : 0
                data : <comedi.sampl_array... at 0x...>
            data_len : 3
    """
    _str_fields = [
        'subdev', 'flags', 'start_src', 'start_arg', 'scan_begin_src',
        'scan_begin_arg', 'convert_src', 'convert_arg', 'scan_end_src',
        'scan_end_arg', 'stop_src', 'stop_arg', 'chanlist', 'chanlist_len',
        'data', 'data_len']

    def __init__(self):
        self.cmd = _comedi.comedi_cmd_struct()

    def _get_flag_field(self, name, flag):
        f = _constants.FlagValue(flag, getattr(self.cmd, name))
        return f

    def get_flags(self):
        return self._get_flag_field('flags', _constants.CMDF)

    def get_trigger_field(self, name):
        return self._get_flag_field(name, _constants.TRIG_SRC)

    def __str__(self):
        values = {}
        for f in self._str_fields:
            if f.endswith('_src'):
                values[f] = str(self.get_trigger_field(f))
            elif f == 'flags':
                values[f] = str(self.get_flags())
            else:
                values[f] = getattr(self, f)
        max_len = max([len(f) for f in self._str_fields])
        lines = ['%*s : %s' % (max_len, f, values[f])
                 for f in self._str_fields]
        return 'Comedi command:\n  %s' % '\n  '.join(lines)

    def __setattr__(self, name, value):
        if name == 'cmd':
            return super(Command, self).__setattr__(name, value)
        return setattr(self.cmd, name, _comedi_arg(value))

    def __getattr__(self, name):
        return getattr(self.cmd, name)  # TODO: lookup _NamedInt?


class DataChannel (Channel):
    """Channel configured for reading data.

    `range` should be a `Range` instance, `aref` should be an
    `constants.AREF` instance,
    """
    def __init__(self, range=None, aref=None, **kwargs):
        super(DataChannel, self).__init__(**kwargs)
        self.range = range
        self.aref = aref

    # syncronous stuff

    def data_read(self):
        "Read one sample"
        read,data = _comedi_tup(
            'comedi_data_read', self._subdevice._device._device,
            self._subdevice._index, self._index, self.range.index, self.aref)
        return data

    def data_read_n(self, n):
        "Read `n` samples (timing between samples is undefined)."
        read,data = _comedi_tup(
            'comedi_data_read', self._subdevice._device._device,
            self._subdevice._index, self._index, self.range.index, self.aref,
            n)
        return data

    def data_read_hint(self):
        """Tell driver which channel/range/aref you will read next

       Used to prepare an analog input for a subsequent call to
       comedi_data_read.  It is not necessary to use this function,
       but it can be useful for eliminating inaccuaracies caused by
       insufficient settling times when switching the channel or gain
       on an analog input.  This function sets an analog input to the
       channel, range, and aref specified but does not perform an
       actual analog to digital conversion.

       Alternatively, one can simply use `.data_read_delayed()`, which
       sets up the input, pauses to allow settling, then performs a
       conversion.
       """
        _comedi_int(
            'comedi_data_read_hint', self._subdevice._device._device,
            self._subdevice._index, self._index, self.range.index,
            self.aref.value)
        
    def data_read_delayed(self, nano_sec=0):
        """Read single sample after delaying specified settling time.

        Although the settling time is specified in integer
        nanoseconds, the actual settling time will be rounded up to
        the nearest microsecond.
        """
        read,data = _comedi_tup(
            'comedi_data_read_delayed', self._subdevice._device._device,
            self._subdevice._index, self._index, self.range.index,
            self.aref.value, int(nano_sec))
        return data

    def data_write(self, data):
        "Write one sample"
        written = _comedi_int(
            'comedi_data_write', self._subdevice._device._device,
            self._subdevice._index, self._index, self.range.index, self.aref,
            int(data))
        return written

    def dio_config(self, dir):
        """Change input/output properties

        `dir` should be an item from `constants.IO_DIRECTION`.
        """
        _comedi_int(
            'comedi_dio_config', self._subdevice._device._device,
            self._subdevice._index, self._index, dir)

    def _dio_get_config(self):
        "Query input/output properties"
        return _comedi_int(
            'comedi_dio_get_config', self._subdevice._device._device,
            self._subdevice._index, self._index)

    def dio_get_config(self):
        """Query input/output properties

        Return an item from `constants.IO_DIRECTION`.
        """
        return _constants.IO_DIRECTION.index_by_value(self._dio_get_config())

    def dio_read(self):
        "Read a single bit"
        rc,bit = _comedi_tup(
            'comedi_dio_read', self._subdevice._device._device,
            self._subdevice._index, self._index)
        return bit

    def dio_write(self, bit):
        "Write a single bit"
        return _comedi_int(
            'comedi_dio_write', self._subdevice._device._device,
            self._subdevice._index, self._index, bit)

    def cr_pack(self):
        return _comedi.cr_pack(self._index, self.range.index, self.aref.value) 


class SlowlyVaryingChannel (Channel):
    "Slowly varying channel"
    def __init__(self, **kwargs):
        super(SlowlyVaryingChannel, self).__init__(**kwargs)
        self._sv = _comedi.comedi_sv_t()
        self.init()

    def init(self):
        "Initialise `._sv`"
        _comedi_int(
            'comedi_sv_init', self._sv, self._subdevice._device._device,
            self._subdevice._index, self._index)

    def update(self):
        "Update internal `._sv` parameters."
        _comedi_int('comedi_sv_update', self._sv)

    def measure(self):
        """Measure a slowy varying signal.

        Returns `(num_samples, physical_value)`.
        """
        return _comedi_tup(
            'comedi_sv_measure', self._sv)


class StreamingSubdevice (Subdevice):
    "Streaming I/O channel"
    def __init__(self, **kwargs):
        super(StreamingSubdevice, self).__init__(**kwargs)
        self.cmd = Command()

    def get_cmd_src_mask(self):
        """Detect streaming input/output capabilities

        The command capabilities of the subdevice indicated by the
        parameters device and subdevice are probed, and the results
        placed in the command structure *command.  The trigger source
        elements of the command structure are set to be the bitwise-or
        of the subdevice's supported trigger sources.  Other elements
        in the structure are undefined.
        """
        rc = _comedi_int(
            'comedi_get_cmd_src_mask', self._device._device, self._index,
            self.cmd)

    def get_cmd_generic_timed(self, chanlist_len, scan_period_ns=0):
        """Detect streaming input/output capabilities

        The command capabilities of the subdevice indicated by the
        parameters device and subdevice are probed, and the results
        placed in the command structure pointed to by the parameter
        command.  The command structure *command is modified to be a
        valid command that can be used as a parameter to
        comedi_command (after the command has additionally been
        assigned a valid chanlist array).  The command measures scans
        consisting of chanlist_len channels at a scan rate that
        corresponds to a period of scan_period_ns nanoseconds.  The
        rate is adjusted to a rate that the device can handle.
        """
        rc = _comedi_int(
            'comedi_get_cmd_generic_timed', self._device._device, self._index,
            self.cmd, chanlist_len, scan_period_ns)

    def cancel(self):
        "Stop streaming input/output in progress."
        _comedi_int('comedi_cancel', self._device._device, self._index)

    def command(self):
        "Start streaming input/output"
        _comedi_int('comedi_command',  self._device._device, self.cmd)

    _command_test_errors = [
        None,  # valid
        'unsupported *_src trigger',  # unsupported trigger bits zeroed
        'unsupported *_src combo, or multiple triggers',
        '*_arg out of range',  # offending members adjusted to valid values
        '*_arg required adjustment',  # e.g. trigger timing period rounded
        'invalid chanlist',  # e.g. some boards require same range across chans
        ]

    def command_test(self):
        "Test streaming input/output configuration"
        rc = _comedi.comedi_command_test(
            self._device._device, _comedi_arg(self.cmd))
        return self._command_test_errors[rc]

    def poll(self):
        """Force updating of streaming buffer

        If supported by the driver, all available samples are copied
        to the streaming buffer. These samples may be pending in DMA
        buffers or device FIFOs. If successful, the number of
        additional bytes available is returned.
        """
        return _comedi_int('comedi_poll', self._device._device, self._index)

    def get_buffer_size(self):
        "Streaming buffer size of subdevice"
        return _comedi_int(
            'comedi_get_buffer_size', self._device._device, self._index)

    def set_buffer_size(self, size):
        """Change the size of the streaming buffer

        Returns the new buffer size in bytes.

        The buffer size will be set to size bytes, rounded up to a
        multiple of the virtual memory page size. The virtual memory
        page size can be determined using `sysconf(_SC_PAGE_SIZE)`.

        This function does not require special privileges. However, it
        is limited to a (adjustable) maximum buffer size, which can be
        changed by a priveliged user calling
        `.comedi_set_max_buffer_size`, or running the program
        `comedi_config`.
        """
        return _comedi_int(
            'comedi_set_buffer_size',
            self._device._device, self._index, size)

    def get_max_buffer_size(self):
        "Maximum streaming buffer size of subdevice"
        return _comedi_int(
            'comedi_get_max_buffer_size', self._device._device, self._index)

    def set_max_buffer_size(self, max_size):
        """Set the maximum streaming buffer size of subdevice

        Returns the old (max?) buffer size on success.
        """
        return _comedi_int(
            'comedi_set_max_buffer_size', self._device._device, self._index,
            max_size)

    def get_buffer_contents(self):
        "Number of bytes available on an in-progress command"
        return _comedi_int(
            'comedi_get_buffer_contents', self._device._device, self._index)

    def mark_buffer_read(self, num_bytes):
        """Next `num_bytes` bytes in the buffer are no longer needed

        Returns the number of bytes successfully marked as read.

        This method should only be used if you are using a `mmap()` to
        read data from Comedi's buffer (as opposed to calling `read()`
        on the device file), since Comedi will automatically keep
        track of how many bytes have been transferred via `read()`
        calls.
        """
        return _comedi_int(
            'comedi_mark_buffer_read', self._device._device, self._index,
            num_bytes)

    def mark_buffer_written(self, num_bytes):
        """Next `num_bytes` bytes in the buffer are no longer needed

        Returns the number of bytes successfully marked as written.

        This method should only be used if you are using a `mmap()` to
        read data from Comedi's buffer (as opposed to calling
        `write()` on the device file), since Comedi will automatically
        keep track of how many bytes have been transferred via
        `write()` calls.
        """
        return _comedi_int(
            'comedi_mark_buffer_written', self._device._device, self._index,
            num_bytes)        

    def get_buffer_offset(self):
        """Offset in bytes of the read(/write?) pointer in the streaming buffer

        This offset is only useful for memory mapped buffers.
        """
        return _comedi_int(
            'comedi_get_buffer_offset', self._device._device, self._index)


class Chanlist (list):
    def chanlist(self):
        ret = _comedi.chanlist(len(self))
        for i,channel in enumerate(self):
            ret[i] = channel.cr_pack()
        return ret


class CalibratedConverter (object):
    """Apply a converion polynomial 

    Usually you would get the conversion polynomial from
    `Channel.get_hardcal_converter()` or similar. bit for testing,
    we'll just create one out of thin air.

    TODO: we'll need to use Cython, because the current SWIG bindings
    don't provide a way to create or edit `double *` arrays.

    >>> p = _comedi.comedi_polynomial_t()
    >>> p.order = 2
    >>> p.coefficients[0] = 1  # this fails.  Silly SWIG.
    >>> p.coefficients[1] = 2
    >>> p.coefficients[2] = 3    
    >>> dir(p.coefficients)
    >>> p.coefficients = _numpy.array([1, 2, 3, 4], dtype=_numpy.double)
    >>> p.expansion_origin = -1;

    >>> c = CalibratedConverter(polynomial=p)
    >>> c(-1)
    >>> c(_numpy.array([-1, 0, 0.5, 2], dtype=_numpy.double))
    """
    def __init__(self, polynomial):
        self.polynomial = polynomial

    def __call__(self, data):
        # Iterating through the coefficients fails.  Silly SWIG.
        coefficients = list(reversed(self.polynomial.coefficients))[0:p.order]
        print coefficients
        print self.polynomial.expansion_origin
        return _numpy.polyval(
            coefficients, data-self.polynomial.expansion_origin)

# see comedi_caldac_t and related at end of comedilib.h
