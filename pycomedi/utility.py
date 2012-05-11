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

"Useful utility functions and classes"

import array as _array
import mmap as _mmap
import os as _os
import threading as _threading
import time as _time

import numpy as _numpy

from . import LOG as _LOG
from . import constant as _constant


# types from comedi.h
sampl = _numpy.uint16
lsampl = _numpy.uint32
sampl_typecode = 'H'
lsampl_typecode = 'L'

def _subdevice_dtype(subdevice):
    "Return the appropriate `numpy.dtype` based on subdevice flags"
    if subdevice.get_flags().lsampl:
        return lsampl
    return sampl

def _subdevice_typecode(subdevice):
    "Return the appropriate `array` type based on subdevice flags"
    if subdevice.get_flags().lsampl:
        return lsampl_typecode
    return sampl_typecode

def inttrig_insn(subdevice):
    """Setup an internal trigger for a given `subdevice`

    From the Comedi docs `section 4.4`_ (Instruction for internal
    triggering):

      This special instruction has `INSN_INTTRIG` as the insn flag in
      its instruction data structure. Its execution causes an internal
      triggering event. This event can, for example, cause the device
      driver to start a conversion, or to stop an ongoing
      acquisition. The exact meaning of the triggering depends on the
      card and its particular driver.

      The `data[0]` field of the `INSN_INTTRIG` instruction is
      reserved for future use, and should be set to `0`.

    From the comedi source (`comedi.comedi_fops.c:parse_insn()`), we
    see that the `chanspec` attribute is ignored for `INSN_INTTRIG`,
    so we don't bother setting it here.

    .. _section 4.4: http://www.comedi.org/doc/x621.html
    """
    insn = subdevice.insn()
    insn.insn = _constant.INSN.inttrig.value
    insn.data = [0]
    return insn


def _builtin_array(array):
    "`array` is an array from the builtin :mod:`array` module"
    return isinstance(array, _array.array)


class _ReadWriteThread (_threading.Thread):
    "Base class for all reader/writer threads"
    def __init__(self, subdevice, buffer, name=None,
                 block_while_running=False):
        if name == None:
            name = '<%s subdevice %d>' % (
                self.__class__.__name__, subdevice.index)
        self.subdevice = subdevice
        self.buffer = buffer
        self.block_while_running = block_while_running
        self._setup_buffer()
        super(_ReadWriteThread, self).__init__(name=name)

    def _setup_buffer(self):
        "Currently just a hook for an MMapWriter hack."
        pass

    def _file(self):
        """File for reading/writing data to `.subdevice`

        This file may use the internal comedi fileno, so do not close
        it when you are finished.  The file will eventually be closed
        when the backing `Device` instance is closed.
        """
        return self.subdevice.device.file

    def block(self):
        while self.subdevice.get_flags().running:
            _time.sleep(0)
        self.subdevice.cancel()  # become unbusy


class Reader (_ReadWriteThread):
    """`read()`-based reader

    Examples
    --------

    Setup a temporary data file for testing.

    >>> from os import close, remove
    >>> from tempfile import mkstemp
    >>> fd,t = mkstemp(suffix='.dat', prefix='pycomedi-')
    >>> f = _os.fdopen(fd, 'r+')
    >>> buf = _numpy.array([[0,10],[1,11],[2,12]], dtype=_numpy.uint16)
    >>> buf.tofile(t)

    Override the default `Reader` methods for our dummy subdevice.

    >>> class TestReader (Reader):
    ...     def _file(self):
    ...         return f

    Run the test reader.

    >>> rbuf = 0*buf
    >>> r = TestReader(subdevice=None, buffer=rbuf, name='Reader-doctest')
    >>> r.start()
    >>> r.join()

    The input buffer is updated in place, and is also available as the
    reader's `buffer` attribute.

    >>> rbuf
    array([[ 0, 10],
           [ 1, 11],
           [ 2, 12]], dtype=uint16)
    >>> r.buffer
    array([[ 0, 10],
           [ 1, 11],
           [ 2, 12]], dtype=uint16)

    While `numpy` arrays make multi-channel indexing easy, they do
    require an external library.  For single-channel input, the
    `array` module is sufficient.

    >>> f.seek(0)
    >>> rbuf = _array.array('H', [0]*buf.size)
    >>> r = TestReader(subdevice=None, buffer=rbuf, name='Reader-doctest')
    >>> r.start()
    >>> r.join()
    >>> rbuf
    array('H', [0, 10, 1, 11, 2, 12])
    >>> r.buffer
    array('H', [0, 10, 1, 11, 2, 12])

    Cleanup the temporary data file.

    >>> f.close()  # no need for `close(fd)`
    >>> remove(t)
    """
    def run(self):
        builtin_array = _builtin_array(self.buffer)
        f = self._file()
        if builtin_array:
            # TODO: read into already allocated memory (somehow)
            size = len(self.buffer)
            a = _array.array(self.buffer.typecode)
            a.fromfile(f, size)
            self.buffer[:] = a
        else:  # numpy.ndarray
            # TODO: read into already allocated memory (somehow)
            buf = _numpy.fromfile(
                f, dtype=self.buffer.dtype, count=self.buffer.size)
            a = _numpy.ndarray(
                shape=self.buffer.shape, dtype=self.buffer.dtype,
                buffer=buf)
            self.buffer[:] = a
        if self.block_while_running:
            self.block()


class CallbackReader (Reader):
    """`read()`-based reader with callbacks

    Examples
    --------

    Setup a temporary data file for testing.

    >>> from os import close, remove
    >>> from sys import stdout
    >>> from tempfile import mkstemp
    >>> from time import sleep
    >>> fd,t = mkstemp(suffix='.dat', prefix='pycomedi-')
    >>> f = _os.fdopen(fd, 'rb+')
    >>> buf = _numpy.array([[0,10],[1,11],[2,12]], dtype=_numpy.uint16)
    >>> buf.tofile(t)

    Override the default `Reader` methods for our dummy subdevice.

    >>> class TestReader (CallbackReader):
    ...     def _file(self):
    ...         return f

    Define a callback function.

    >>> def callback(data):
    ...     sleep(0.1)  # for consistent output spacing
    ...     print('got: {0}'.format(repr(data)))
    ...     stdout.flush()

    Run the test reader.

    >>> rbuf = _numpy.zeros((buf.shape[1],), dtype=_numpy.uint16)
    >>> r = TestReader(subdevice=None, buffer=rbuf, name='Reader-doctest',
    ...     callback=callback, count=buf.shape[0])
    >>> r.start()
    >>> sleep(0.25)
    got: array([ 0, 10], dtype=uint16)
    got: array([ 1, 11], dtype=uint16)
    >>> r.join()
    got: array([ 2, 12], dtype=uint16)

    While `numpy` arrays make multi-channel indexing easy, they do
    require an external library.  For single-channel input, the
    `array` module is sufficient.

    >>> f.seek(0)
    >>> rbuf = _array.array('H', [0])
    >>> r = TestReader(subdevice=None, buffer=rbuf, name='Reader-doctest',
    ...     callback=callback, count=buf.size)
    >>> r.start()
    >>> sleep(0.35)
    got: array('H', [0])
    got: array('H', [10])
    got: array('H', [1])
    >>> r.join()
    got: array('H', [11])
    got: array('H', [2])
    got: array('H', [12])

    Cleanup the temporary data file.

    >>> f.close()  # no need for `close(fd)`
    >>> remove(t)
    """
    def __init__(self, callback=None, count=None, **kwargs):
        self.callback = callback
        self.count = count
        super(CallbackReader, self).__init__(**kwargs)

    def run(self):
        count = self.count
        block_while_running = self.block_while_running
        while count is None or count > 0:
            if count is not None:
                count -= 1
            try:
                self.block_while_running = False
                super(CallbackReader, self).run()
            finally:
                self.block_while_running = block_while_running
            if self.callback:
                self.callback(self.buffer)
        if self.block_while_running:
            self.block()


class Writer (_ReadWriteThread):
    """`write()`-based writer

    Examples
    --------

    Setup a temporary data file for testing.

    >>> from os import close, remove
    >>> from tempfile import mkstemp
    >>> fd,t = mkstemp(suffix='.dat', prefix='pycomedi-')
    >>> f = _os.fdopen(fd, 'r+')
    >>> buf = _numpy.array([[0,10],[1,11],[2,12]], dtype=_numpy.uint16)

    Override the default `Writer` methods for our dummy subdevice.

    >>> class TestWriter (Writer):
    ...     def _file(self):
    ...         return f

    Run the test writer.

    >>> preload = 3
    >>> w = TestWriter(subdevice=None, buffer=buf, name='Writer-doctest',
    ...                preload=preload)
    >>> a = _array.array('H')
    >>> a.fromfile(open(t, 'rb'), preload)
    >>> a
    array('H', [0, 10, 1])
    >>> w.start()
    >>> w.join()
    >>> a = _array.array('H')
    >>> a.fromfile(open(t, 'rb'), buf.size)
    >>> a
    array('H', [0, 10, 1, 11, 2, 12])

    While `numpy` arrays make multi-channel indexing easy, they do
    require an external library.  For single-channel input, the
    `array` module is sufficient.

    >>> f.seek(0)
    >>> buf = _array.array('H', [2*x for x in buf.flat])
    >>> w = TestWriter(subdevice=None, buffer=buf, name='Writer-doctest',
    ...                preload=preload)
    >>> a = _array.array('H')
    >>> a.fromfile(open(t, 'rb'), preload)
    >>> a
    array('H', [0, 20, 2])
    >>> w.start()
    >>> w.join()
    >>> a = _array.array('H')
    >>> a.fromfile(open(t, 'rb'), len(buf))
    >>> a
    array('H', [0, 20, 2, 22, 4, 24])

    Cleanup the temporary data file.

    >>> f.close()  # no need for `close(fd)`
    >>> remove(t)
    """
    def __init__(self, *args, **kwargs):
        preload = kwargs.pop('preload', 0)
        super(Writer, self).__init__(*args, **kwargs)
        if not _builtin_array(self.buffer):  # numpy.ndarray
            self.buffer = self.buffer.flat
        preload_buffer = self.buffer[:preload]
        self._preload_setup = {'remaining_buffer': self.buffer[preload:]}
        f = self._file()
        preload_buffer.tofile(f)
        f.flush()

    def run(self):
        remaining_buffer = self._preload_setup['remaining_buffer']
        del(self._preload_setup)

        f = self._file()
        remaining_buffer.tofile(f)
        f.flush()
        if self.block_while_running:
            self.block()


class _MMapReadWriteThread (_ReadWriteThread):
    "`mmap()`-based reader/writer"
    def __init__(self, *args, **kwargs):
        preload = kwargs.pop('preload', 0)
        access = kwargs.pop('access')
        super(_MMapReadWriteThread, self).__init__(*args, **kwargs)

        # all sizes measured in bytes
        builtin_array = _builtin_array(self.buffer)
        mmap_size = int(self._mmap_size())
        mmap = _mmap.mmap(self._fileno(), mmap_size, access=access)
        buffer_offset = 0
        remaining = self._buffer_bytes(builtin_array)
        action,mmap_offset = self._initial_action(
            mmap, buffer_offset, remaining, mmap_size, action_bytes=mmap_size,
            builtin_array=builtin_array)
        buffer_offset += action
        remaining -= action
        self._preload_setup = {
            'builtin_array': builtin_array,
            'mmap_size': mmap_size,
            'mmap': mmap,
            'mmap_offset': mmap_offset,
            'buffer_offset': buffer_offset,
            'remaining': remaining,
            }

    def _sleep_time(self, mmap_size):
        "Expected seconds needed to write a tenth of the mmap buffer"
        return 0

    def run(self):
        builtin_array = self._preload_setup['builtin_array']
        mmap_size = self._preload_setup['mmap_size']
        mmap = self._preload_setup['mmap']
        mmap_offset = self._preload_setup['mmap_offset']
        buffer_offset = self._preload_setup['buffer_offset']
        remaining = self._preload_setup['remaining']
        del(self._preload_setup)

        sleep_time = self._sleep_time(mmap_size)
        while remaining > 0:
            action_bytes = self._action_bytes()
            if action_bytes > 0:
                action,mmap_offset = self._act(
                    mmap, mmap_offset, buffer_offset, remaining, mmap_size,
                    action_bytes=action_bytes, builtin_array=builtin_array)
                buffer_offset += action
                remaining -= action
            else:
                _time.sleep(sleep_time)
        if self.block_while_running:
            self.block()

    def _act(self, mmap, mmap_offset, buffer_offset, remaining, mmap_size,
             action_bytes=None, builtin_array=None):
        if action_bytes == None:
            action_bytes = self.subdevice.get_buffer_contents()
        if mmap_offset + action_bytes >= mmap_size - 1:
            action_bytes = mmap_size - mmap_offset
            wrap = True
        else:
            wrap = False
        action_size = min(action_bytes, remaining, mmap_size-mmap_offset)
        self._mmap_action(mmap, buffer_offset, action_size, builtin_array)
        mmap.flush()  # (offset, size),  necessary?  calls msync?
        self._mark_action(action_size)
        if wrap:
            mmap.seek(0)
            mmap_offset = 0
        return action_size, mmap_offset

    # pull out subdevice calls for easier testing

    def _mmap_size(self):
        return self.subdevice.get_buffer_size()

    def _fileno(self):
        return self.subdevice.device.fileno()

    def _action_bytes(self):
        return self.subdevice.get_buffer_contents()

    # hooks for subclasses

    def _buffer_bytes(self, builtin_array):
        if builtin_array:
            return len(self.buffer)*self.buffer.itemsize
        else:  # numpy.ndtype
            return self.buffer.size*self.buffer.itemsize

    def _initial_action(self, mmap, buffer_offset, remaining, mmap_size,
                        action_bytes, builtin_array):
        return (0, 0)

    def _mmap_action(self, mmap, offset, size):
        raise NotImplementedError()

    def _mark_action(self, size):
        raise NotImplementedError()


# MMap classes have more subdevice-based methods to override
_mmap_docstring_overrides = '\n    ...     '.join([
        'def _mmap_size(self):',
        '    from os.path import getsize',
        '    return getsize(t)',
        'def _fileno(self):',
        '    return fd',
        'def _action_bytes(self):',
        '    return 4',
        'def _mark_action(self, size):',
        '    pass',
        'def _file',
        ])


class MMapReader (_MMapReadWriteThread):
    __doc__ = Reader.__doc__
    for _from,_to in [
        # convert class and function names
        ('`read()`', '`mmap()`'),
        ('Reader', 'MMapReader'),
        ('def _file', _mmap_docstring_overrides)]:
        __doc__ = __doc__.replace(_from, _to)

    def __init__(self, *args, **kwargs):
        assert 'access' not in kwargs
        kwargs['access'] = _mmap.ACCESS_READ
        super(MMapReader, self).__init__(*args, **kwargs)

    def _mmap_action(self, mmap, offset, size, builtin_array):
        offset /= self.buffer.itemsize
        s = size / self.buffer.itemsize
        if builtin_array:
            # TODO: read into already allocated memory (somehow)
            a = _array.array(self.buffer.typecode)
            a.fromstring(mmap.read(size))
            self.buffer[offset:offset+s] = a
        else:  # numpy.ndarray
            # TODO: read into already allocated memory (somehow)
            a = _numpy.fromstring(mmap.read(size), dtype=self.buffer.dtype)
            self.buffer.flat[offset:offset+s] = a

    def _mark_action(self, size):
        self.subdevice.mark_buffer_read(size)


class MMapWriter (_MMapReadWriteThread):
    __doc__ = Writer.__doc__
    for _from,_to in [
        ('`write()`', '`mmap()`'),
        ('Writer', 'MMapWriter'),
        ('def _file', _mmap_docstring_overrides),
        ("f = _os.fdopen(fd, 'r+')",
         "f = _os.fdopen(fd, 'r+'); f.write(6*'\\x00'); f.flush(); f.seek(0)"),
        ("a.fromfile(open(t, 'rb'), buf.size)",
         "a.fromfile(open(t, 'rb'), w._mmap_size()/a.itemsize)"),
        ("a.fromfile(open(t, 'rb'), len(buf))",
         "a.fromfile(open(t, 'rb'), w._mmap_size()/a.itemsize)"),
        ("array('H', [0, 10, 1, 11, 2, 12])", "array('H', [11, 2, 12])"),
        ("array('H', [0, 20, 2, 22, 4, 24])", "array('H', [22, 4, 24])")]:

        __doc__ = __doc__.replace(_from, _to)

    def __init__(self, *args, **kwargs):
        assert 'access' not in kwargs
        kwargs['access'] = _mmap.ACCESS_WRITE
        super(MMapWriter, self).__init__(*args, **kwargs)

    def _setup_buffer(self):
        self.buffer = buffer(self.buffer)

    def _buffer_bytes(self, builtin_array):
        return len(self.buffer)  # because of buffer() in _setup_buffer

    def _initial_action(self, mmap, buffer_offset, remaining, mmap_size,
                        action_bytes, builtin_array):
        action_size = min(action_bytes, remaining, mmap_size)
        self._mmap_action(mmap, buffer_offset, action_size, builtin_array)
        if action_size == mmap_size:
            mmap.seek(0)
            mmap_offset = 0
        else:
            mmap_offset = action_size
        return (action_size, mmap_offset)

    def _mmap_action(self, mmap, offset, size, builtin_array):
        mmap.write(self.buffer[offset:offset+size])
        mmap.flush()

    def _mark_action(self, size):
        self.subdevice.mark_buffer_written(size)


del _mmap_docstring_overrides
