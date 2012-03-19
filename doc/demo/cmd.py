#!/usr/bin/env python
#
# Copyright

"""Use comedi commands for asyncronous input.

An example for directly using Comedi commands.  Comedi commands
are used for asynchronous acquisition, with the timing controlled
by on-board timers or external events.

Based on David A. Schleef's `comedilib/demo/cmd.c`.
"""

import logging as _logging
import sys as _sys
import time as _time

import numpy as _numpy

from pycomedi import LOG as _LOG
import pycomedi.constant as _constant
from pycomedi.device import Device as _Device
from pycomedi.subdevice import StreamingSubdevice as _StreamingSubdevice
from pycomedi.channel import AnalogChannel as _AnalogChannel
from pycomedi.chanspec import ChanSpec as _ChanSpec
from pycomedi.utility import Reader as _Reader


def open_channels(device, subdevice, channels, range, aref):
    """Subdevice index and list of channel indexes
      -> ``Subdevice`` instance and list of ``AnalogChannel`` instances
    """
    if args.subdevice >= 0:
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

def print_data(channels, data, physical=False):
    if physical:
        converters = [c.get_converter() for c in channels]
        physical_data = _numpy.zeros(data.shape, dtype=float32)
        for i,c in enumerate(converters):
            physical_data[:,i] = c.to_physical(data[:,i])
        data = physical_data
    for row in range(data.shape[0]):
        print '\t'.join(str(x) for x in data[row,:])

def read(device, subdevice=None, channels=[0], range=0, aref=0, period=0,
         num_scans=2, physical=False):
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
    reader = _Reader(subdevice, read_buffer)
    start = _time.time()
    _LOG.info('start time: {}'.format(start))
    subdevice.command()
    reader.start()
    reader.join()
    stop = _time.time()
    _LOG.info('stop time: {}'.format(stop))
    _LOG.info('time: {}'.format(stop - start))
    print_data(channels=channels, data=read_buffer, physical=physical)


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        '-f', '--filename', default='/dev/comedi0',
        help='path to comedi device file')
    parser.add_argument(
        '-s', '--subdevice', type=int, help='subdevice for analog input')
    parser.add_argument(
        '-c', '--channel', type=int, action='append',
        help='add a channel for analog input')
    parser.add_argument(
        '-a', '--analog-reference', dest='aref', default='ground',
        choices=['diff', 'ground', 'other', 'common'],
        help='reference for analog input')
    parser.add_argument(
        '-r', '--range', type=int, default=0, help='range for analog input')
    parser.add_argument(
        '-N', '--num-scans', type=int, default=10,
        help='number of analog input scans')
    parser.add_argument(
        '-F', '--frequency', type=float, help='scan frequency in hertz')
    parser.add_argument(
        '-p', '--physical', default=False, action='store_const', const=True,
        help='convert input to physical values before printing')
    parser.add_argument(
        '-v', '--verbose', default=0, action='count')

    args = parser.parse_args()

    if args.verbose >= 3:
        _LOG.setLevel(_logging.DEBUG)
    elif args.verbose >= 2:
        _LOG.setLevel(_logging.INFO)
    elif args.verbose >= 1:
        _LOG.setLevel(_logging.WARN)

    _LOG.info(('measuring device={0.filename} subdevice={0.subdevice} '
               'channel={0.channel} range={0.range} analog reference={0.aref}'
               ).format(args))

    channel_indexes = args.channel
    if not channel_indexes:
        channel_indexes = [0]  # user gave no channels on the command line
    aref = _constant.AREF.index_by_name(args.aref)
    if args.frequency is None:
        period = 0
    else:
        period = 1/args.frequency

    device = _Device(filename=args.filename)
    device.open()
    try:
        read(
            device=device, subdevice=args.subdevice,
            channels=channel_indexes, range=args.range, aref=aref,
            period=period, num_scans=args.num_scans, physical=args.physical)
    finally:
        device.close()
