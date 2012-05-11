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

"Wrap subdevice-wide Comedi functions in `Subdevice` and related classes"

cimport _comedi_h
cimport _comedilib_h
cimport device as _device
cimport command as _command
from pycomedi import LOG as _LOG
import _error
from channel import Channel as _Channel
import chanspec as _chanspec
import constant as _constant
import command as _command
from utility import _subdevice_dtype, _subdevice_typecode


cdef class Subdevice (object):
    """Class bundling subdevice-related functions

    >>> from .device import Device
    >>> from . import constant

    >>> d = Device('/dev/comedi0')
    >>> d.open()

    >>> s = d.get_read_subdevice()
    >>> s.get_type()
    <_NamedInt ai>
    >>> f = s.get_flags()
    >>> f  # doctest: +ELLIPSIS
    <pycomedi.constant.FlagValue object at 0x...>
    >>> print str(f)
    cmd_read|readable|ground|common|diff|other|dither
    >>> s.get_n_channels()
    16
    >>> s.range_is_chan_specific()
    False
    >>> s.maxdata_is_chan_specific()
    False
    >>> s.lock()
    >>> s.unlock()

    >>> s = d.find_subdevice_by_type(constant.SUBDEVICE_TYPE.dio)
    >>> s.dio_bitfield()
    255L

    >>> s.get_dtype()
    <type 'numpy.uint16'>
    >>> s.get_typecode()
    'H'

    >>> d.close()
    """
    def __cinit__(self):
        self.index = -1

    def __init__(self, device, index):
        super(Subdevice, self).__init__()
        self.device = device
        self.index = index

    def get_type(self):
        "Type of subdevice (from `SUBDEVICE_TYPE`)"
        ret = _comedilib_h.comedi_get_subdevice_type(
            self.device.device, self.index)
        if ret < 0:
            _error.raise_error(function_name='comedi_get_subdevice_type',
                               ret=ret)
        return _constant.SUBDEVICE_TYPE.index_by_value(ret)

    def _get_flags(self):
        "Subdevice flags"
        ret = _comedilib_h.comedi_get_subdevice_flags(
            self.device.device, self.index)
        if ret < 0:
            _error.raise_error(function_name='comedi_get_subdevice_flags',
                               ret=ret)
        return ret

    def get_flags(self):
        "Subdevice flags (an `SDF` `FlagValue`)"
        return _constant.FlagValue(
            _constant.SDF, self._get_flags())

    def get_n_channels(self):
        "Number of subdevice channels"
        ret = _comedilib_h.comedi_get_n_channels(
            self.device.device, self.index)
        if ret < 0:
            _error.raise_error(function_name='comedi_get_n_channels',
                               ret=ret)
        return ret

    def range_is_chan_specific(self):
        ret = _comedilib_h.comedi_range_is_chan_specific(
            self.device.device, self.index)
        if ret < 0:
            _error.raise_error(
                function_name='comedi_range_is_chan_specific', ret=ret)
        return ret == 1

    def maxdata_is_chan_specific(self):
        ret = _comedilib_h.comedi_maxdata_is_chan_specific(
            self.device.device, self.index)
        if ret < 0:
            _error.raise_error(
                function_name='comedi_maxdata_is_chan_specific', ret=ret)
        return ret == 1

    def lock(self):
        "Reserve the subdevice"
        ret = _comedilib_h.comedi_lock(self.device.device, self.index)
        if ret < 0:
            _error.raise_error(function_name='comedi_lock', ret=ret)

    def unlock(self):
        "Release the subdevice"
        ret = _comedilib_h.comedi_unlock(self.device.device, self.index)
        if ret < 0:
            _error.raise_error(function_name='comedi_unlock', ret=ret)

    cpdef dio_bitfield(self, unsigned int bits=0, write_mask=0, base_channel=0):
        """Read/write multiple digital channels.

        `bits` and `write_mask` are bit fields with the least
        significant bit representing channel `base_channel`.

        Returns a bit field containing the read value of all input
        channels and the last written value of all output channels.
        """
        ret = _comedilib_h.comedi_dio_bitfield2(
            self.device.device, self.index, write_mask, &bits, base_channel)
        if ret < 0:
            _error.raise_error(function_name='comedi_dio_bitfield2', ret=ret)
        return bits

    # extensions to make a more idomatic Python interface

    def insn(self):
        insn = self.device.insn()
        insn.subdev = self.index
        return insn

    def channels(self, **kwargs):
        "Iterate through all available channels."
        ret = []
        for i in range(self.get_n_channels()):
            #yield self.channel(i, **kwargs)
            # Generators are not supported in Cython 0.14.1
            ret.append(self.channel(i, **kwargs))
        return ret

    def channel(self, index, factory=_Channel, **kwargs):
        "`Channel` instance for the `index`\ed channel."
        return factory(subdevice=self, index=index, **kwargs)

    def get_dtype(self):
        "Return the appropriate `numpy.dtype` based on subdevice flags"
        return _subdevice_dtype(self)

    def get_typecode(self):
        "Return the appropriate `array` type based on subdevice flags"
        return _subdevice_typecode(self)


cdef class StreamingSubdevice (Subdevice):
    """Streaming I/O subdevice

    >>> from .device import Device
    >>> from .chanspec import ChanSpec
    >>> from . import constant

    >>> d = Device('/dev/comedi0')
    >>> d.open()

    >>> s = d.get_read_subdevice(factory=StreamingSubdevice)

    >>> cmd = s.get_cmd_src_mask()
    >>> print str(cmd)
            subdev: 0
             flags: -
         start_src: now|ext|int
         start_arg: 0
    scan_begin_src: timer|ext
    scan_begin_arg: 0
       convert_src: timer|ext
       convert_arg: 0
      scan_end_src: count
      scan_end_arg: 0
          stop_src: none|count
          stop_arg: 0
          chanlist: []
              data: []

    >>> chanlist_len = 3
    >>> cmd = s.get_cmd_generic_timed(chanlist_len=chanlist_len,
    ...     scan_period_ns=1e3)
    >>> print str(cmd)  # doctest: +NORMALIZE_WHITESPACE
            subdev: 0
             flags: -
         start_src: now
         start_arg: 0
    scan_begin_src: timer
    scan_begin_arg: 9000
       convert_src: timer
       convert_arg: 3000
      scan_end_src: count
      scan_end_arg: 3
          stop_src: count
          stop_arg: 2
          chanlist: [<ChanSpec chan:0 range:0 aref:ground flags:->,
                     <ChanSpec chan:0 range:0 aref:ground flags:->,
                     <ChanSpec chan:0 range:0 aref:ground flags:->]
              data: []

    >>> cmd.chanlist = [ChanSpec(chan=i, range=0) for i in range(chanlist_len)]
    >>> s.cmd = cmd
    >>> s.command_test()
    >>> s.command()
    >>> s.cancel()


    >>> d.close()
    """
    def __cinit__(self):
        self.cmd = _command.Command()
        self._command_test_errors = [
            None,  # valid
            'unsupported *_src trigger',  # unsupported trigger bits zeroed
            'unsupported *_src combo, or multiple triggers',
            '*_arg out of range',  # offending members adjusted to valid values
            '*_arg required adjustment',  # e.g. trigger timing period rounded
            'invalid chanlist',
            # e.g. some boards require same range across channels
            ]

    def get_cmd_src_mask(self):
        """Detect streaming input/output capabilities

        The command capabilities of the subdevice indicated by the
        parameters device and subdevice are probed, and the results
        placed in the command structure *command.  The trigger source
        elements of the command structure are set to be the bitwise-or
        of the subdevice's supported trigger sources.  Other elements
        in the structure are undefined.
        """
        cdef _command.Command cmd        
        cmd = _command.Command()
        ret = _comedilib_h.comedi_get_cmd_src_mask(
            self.device.device, self.index, cmd.get_comedi_cmd_pointer())
        if ret < 0:
            _error.raise_error(function_name='comedi_get_cmd_src_mask', ret=ret)
        return cmd

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

        Note that the `ChanSpec` instances in `cmd.chanlist` are not
        initialized to reasonable values.
        """
        cdef _command.Command cmd        
        cmd = _command.Command()
        ret = _comedilib_h.comedi_get_cmd_generic_timed(
            self.device.device, self.index, cmd.get_comedi_cmd_pointer(),
            chanlist_len, int(scan_period_ns))
        cmd.chanlist = [0 for i in range(chanlist_len)]
        if ret < 0:
            _error.raise_error(function_name='comedi_get_cmd_generic_timed',
                               ret=ret)
        return cmd

    def cancel(self):
        "Stop streaming input/output in progress."
        ret = _comedilib_h.comedi_cancel(self.device.device, self.index)
        if ret < 0:
            _error.raise_error(function_name='comedi_cancel', ret=ret)

    def command(self):
        "Start streaming input/output"
        ret = _comedilib_h.comedi_command(
            self.device.device, self.cmd.get_comedi_cmd_pointer())
        if ret < 0:
            _error.raise_error(function_name='comedi_command', ret=ret)

    def command_test(self):
        "Test streaming input/output configuration"
        ret = _comedilib_h.comedi_command_test(
            self.device.device, self.cmd.get_comedi_cmd_pointer())
        return self._command_test_errors[ret]

    def poll(self):
        """Force updating of streaming buffer

        If supported by the driver, all available samples are copied
        to the streaming buffer. These samples may be pending in DMA
        buffers or device FIFOs. If successful, the number of
        additional bytes available is returned.
        """
        ret = _comedilib_h.comedi_poll(self.device.device, self.index)
        if ret < 0:
            _error.raise_error(function_name='comedi_poll', ret=ret)
        return ret

    def get_buffer_size(self):
        "Streaming buffer size of subdevice"
        ret = _comedilib_h.comedi_get_buffer_size(
            self.device.device, self.index)
        if ret < 0:
            _error.raise_error(function_name='comedi_get_buffer_size', ret=ret)
        return ret

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
        ret = _comedilib_h.comedi_set_buffer_size(
            self.device.device, self.index, int(size))
        if ret < 0:
            _error.raise_error(function_name='comedi_set_buffer_size', ret=ret)
        return ret

    def get_max_buffer_size(self):
        "Maximum streaming buffer size of subdevice"
        ret = _comedilib_h.comedi_get_max_buffer_size(
            self.device.device, self.index)
        if ret < 0:
            _error.raise_error(function_name='comedi_get_max_buffer_size',
                               ret=ret)
        return ret

    def set_max_buffer_size(self, max_size):
        """Set the maximum streaming buffer size of subdevice

        Returns the old (max?) buffer size on success.
        """
        ret = _comedilib_h.comedi_set_max_buffer_size(
            self.device.device, self.index, int(max_size))
        if ret < 0:
            _error.raise_error(function_name='comedi_set_max_buffer_size',
                               ret=ret)
        return ret

    def get_buffer_contents(self):
        "Number of bytes available on an in-progress command"
        ret = _comedilib_h.comedi_get_buffer_contents(
            self.device.device, self.index)
        if ret < 0:
            _error.raise_error(function_name='comedi_get_buffer_contents',
                               ret=ret)
        return ret

    def mark_buffer_read(self, num_bytes):
        """Next `num_bytes` bytes in the buffer are no longer needed

        Returns the number of bytes successfully marked as read.

        This method should only be used if you are using a `mmap()` to
        read data from Comedi's buffer (as opposed to calling `read()`
        on the device file), since Comedi will automatically keep
        track of how many bytes have been transferred via `read()`
        calls.
        """
        ret = _comedilib_h.comedi_mark_buffer_read(
            self.device.device, self.index, num_bytes)
        if ret < 0:
            _error.raise_error(function_name='comedi_mark_buffer_read',
                               ret=ret)
        return ret

    def mark_buffer_written(self, num_bytes):
        """Next `num_bytes` bytes in the buffer are no longer needed

        Returns the number of bytes successfully marked as written.

        This method should only be used if you are using a `mmap()` to
        read data from Comedi's buffer (as opposed to calling
        `write()` on the device file), since Comedi will automatically
        keep track of how many bytes have been transferred via
        `write()` calls.
        """
        ret = _comedilib_h.comedi_mark_buffer_written(
            self.device.device, self.index, num_bytes)
        if ret < 0:
            _error.raise_error(function_name='comedi_mark_buffer_written',
                               ret=ret)
        return ret

    def get_buffer_offset(self):
        """Offset in bytes of the read(/write?) pointer in the streaming buffer

        This offset is only useful for memory mapped buffers.
        """
        ret = _comedilib_h.comedi_get_buffer_offset(
            self.device.device, self.index)
        if ret < 0:
            _error.raise_error(function_name='comedi_get_buffer_offset', ret=ret)
        return ret
