#!/usr/bin/env python
#
# Copyright (C) 2012 W. Trevor King <wking@drexel.edu>
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

"""Use comedi commands for asyncronous input.

An example for directly using Comedi commands.  Comedi commands
are used for asynchronous acquisition, with the timing controlled
by on-board timers or external events.

Based on David A. Schleef's `comedilib/demo/cmd.c`.
"""

import sys as _sys
import time as _time

import numpy as _numpy

from pycomedi import LOG as _LOG
import pycomedi.constant as _constant
from pycomedi.device import Device as _Device
from pycomedi.subdevice import StreamingSubdevice as _StreamingSubdevice
from pycomedi.channel import AnalogChannel as _AnalogChannel
from pycomedi.chanspec import ChanSpec as _ChanSpec
import pycomedi.utility as _utility


def open_channels(device, subdevice, channels, range, aref):
    """Subdevice index and list of channel indexes
    to ``Subdevice`` instance and list of ``AnalogChannel`` instances
    """
    if subdevice >= 0:
        subdevice = device.subdevice(subdevice, factory=_StreamingSubdevice)
    else:
        subdevice = device.find_subdevice_by_type(
            _constant.SUBDEVICE_TYPE.ai, factory=_StreamingSubdevice)
    channels = [subdevice.channel(
            index=i, factory=_AnalogChannel, range=range, aref=aref)
                for i in channels]
    return(subdevice, channels)

def prepare_command(subdevice, channels, period, num_scans):
    """Create a periodic sampling command.

    Ask comedilib to create a generic sampling command and then modify
    the parts we want.
    """
    command = subdevice.get_cmd_generic_timed(
        len(channels), scan_period_ns=period)
    command.chanlist = channels
    command.stop_src = _constant.TRIG_SRC.count
    command.stop_arg = num_scans
    return command

def test_command(subdevice, num_tests=2):
    """Adjust a command as necessary to get valid arguments.
    """
    _LOG.info('command before testing:\n{}'.format(subdevice.cmd))
    for i in range(2):
        rc = subdevice.command_test()
        if rc is None:
            _LOG.info('command is valid')
            return
        _LOG.info('test {} returned {}\n{}'.format(i, rc, subdevice.cmd))
    _LOG.error('error preparing command: {}'.format(rc))
    _sys.exit(1)
test_command.__test__ = False  # test_command is not a Nose test

def write_data(stream, channels, data, physical=False):
    if physical:
        converters = [c.get_converter() for c in channels]
        physical_data = _numpy.zeros(data.shape, dtype=float32)
        for i,c in enumerate(converters):
            physical_data[:,i] = c.to_physical(data[:,i])
        data = physical_data
    for row in range(data.shape[0]):
        stream.write('\t'.join(str(x) for x in data[row,:]))
        stream.write('\n')

def read(device, subdevice=None, channels=[0], range=0, aref=0, period=0,
         num_scans=2, reader=_utility.Reader, physical=False,
         stream=_sys.stdout):
    """Read ``num_scans`` samples from each specified channel.
    """
    subdevice,channels = open_channels(
        device=device, subdevice=subdevice, channels=channels, range=range,
        aref=aref)
    subdevice.cmd = prepare_command(
        subdevice=subdevice, channels=channels, period=period,
        num_scans=num_scans)
    rc = test_command(subdevice=subdevice)
    read_buffer = _numpy.zeros(
        (num_scans, len(channels)),
        dtype=subdevice.get_dtype())
    reader = reader(subdevice=subdevice, buffer=read_buffer, name='Reader')
    start = _time.time()
    _LOG.info('start time: {}'.format(start))
    subdevice.command()
    reader.start()
    reader.join()
    stop = _time.time()
    _LOG.info('stop time: {}'.format(stop))
    _LOG.info('time: {}'.format(stop - start))
    write_data(
        stream=stream, channels=channels, data=read_buffer, physical=physical)


def run(filename, **kwargs):
    """
    >>> import StringIO
    >>> stdout = StringIO.StringIO()
    >>> run(filename='/dev/comedi0', stream=stdout)
    >>> print(stdout.getvalue())  # doctest: +SKIP
    29694
    29693
    <BLANKLINE>
    >>> stdout.truncate(0)
    >>> run(filename='/dev/comedi0', reader=_utility.MMapReader, stream=stdout)
    >>> print(stdout.getvalue())  # doctest: +SKIP
    29691
    29691
    <BLANKLINE>
    """
    device = _Device(filename=filename)
    device.open()
    try:
        read(device=device, **kwargs)
    finally:
        device.close()


if __name__ == '__main__':
    import pycomedi_demo_args

    args = pycomedi_demo_args.parse_args(
        description=__doc__,
        argnames=['filename', 'subdevice', 'channels', 'aref', 'range',
                  'num-scans', 'mmap', 'frequency', 'physical', 'verbose'])

    _LOG.info(('measuring device={0.filename} subdevice={0.subdevice} '
               'channels={0.channels} range={0.range} '
               'analog-reference={0.aref}'
               ).format(args))

    if args.mmap:
        reader = _utility.MMapReader
    else:
        reader = _utility.Reader

    run(filename=args.filename, subdevice=args.subdevice,
        channels=args.channels, aref=args.aref, range=args.range,
        num_scans=args.num_scans, reader=reader, period=args.period,
        physical=args.physical)
