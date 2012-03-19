#!/usr/bin/env python
#
# Copyright

"""Gather and display information about a comedi device.
"""

from pycomedi import PyComediError as _PyComediError
import pycomedi.constant as _constant
from pycomedi.device import Device as _Device
from pycomedi.subdevice import StreamingSubdevice as _StreamingSubdevice


def display_maxdata(subdevice):
    if subdevice.maxdata_is_chan_specific():
        print('  max data value: (channel specific)')
        for channel in subdevice.channels():
            print('    chan{}: {}'.format(
                    channel.index, channel.get_maxdata()))
    else:
        print('  max data value: {}'.format(
                subdevice.channel(0).get_maxdata()))

def display_ranges(subdevice):
    if subdevice.range_is_chan_specific():
        print('  ranges: (channel specific)')
        for channel in subdevice.channels():
            print('    chan{}: {}'.format(
                    channel.index,
                    ', '.join(str(r) for r in channel.ranges())))
    else:
        print('  ranges: {}'.format(
                ', '.join(str(r) for r in subdevice.channel(0).ranges())))

def display_max_generic_timed(subdevice):
    """Fastest supported single-channel command"""
    try:
        command = subdevice.get_cmd_generic_timed(chanlist_len=1)
    except _PyComediError, e:
        if e.function_name != 'comedi_get_cmd_generic_timed':
            raise
        print('  command fast 1chan: (not supported)')
    else:
        print('  command fast 1chan:')
        print('    start: {} {}'.format(command.start_src, command.start_arg))
        print('    scan_begin: {} {}'.format(
                command.scan_begin_src, command.scan_begin_arg))
        print('    convert: {} {}'.format(
                command.convert_src, command.convert_arg))
        print('    scan_end: {} {}'.format(
                command.scan_end_src, command.scan_end_arg))
        print('    stop: {} {}'.format(command.stop_src, command.stop_arg))

def display_command(subdevice):
    try:
        command = subdevice.get_cmd_src_mask()
    except _PyComediError, e:
        if e.function_name != 'comedi_get_cmd_src_mask':
            raise
        print('  command: (not supported)')
    else:
        print('  command:')
        print('    start: {}'.format(command.start_src))
        print('    scan_begin: {}'.format(command.scan_begin_src))
        print('    convert: {}'.format(command.convert_src))
        print('    scan_end: {}'.format(command.scan_end_src))
        print('    stop: {}'.format(command.stop_src))
        display_max_generic_timed(subdevice=subdevice)

def display_subdevice(subdevice):
    print('subdevice {}:'.format(subdevice.index))
    subtype = subdevice.get_type()
    print('  type: {}'.format(subtype))
    if subtype == _constant.SUBDEVICE_TYPE.unused:
        return
    print('  flags: {}'.format(subdevice.get_flags()))
    print('  number of channels: {}'.format(subdevice.get_n_channels()))
    display_maxdata(subdevice=subdevice)
    display_ranges(subdevice=subdevice)
    # For testing commands, assume every device supports streaming and
    # catch errors later.
    streaming_subdevice = subdevice.device.subdevice(
        index=subdevice.index, factory=_StreamingSubdevice)
    display_command(subdevice=streaming_subdevice)

def display(device):
    print('overall info')
    print('  comedi version: {}'.format(
            '.'.join(str(x) for x in device.get_version())))
    print('  driver name: {}'.format(device.get_driver_name()))
    print('  board name: {}'.format(device.get_board_name()))
    print('  number of subdevices: {}'.format(device.get_n_subdevices()))
    for subdevice in device.subdevices():
        display_subdevice(subdevice=subdevice)


if __name__ == '__main__':
    import pycomedi_demo_args

    args = pycomedi_demo_args.parse_args(description=__doc__, argnames=['filename'])

    device = _Device(filename=args.filename)
    device.open()
    try:
        display(device)
    finally:
        device.close()
