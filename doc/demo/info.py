#!/usr/bin/env python
#
# Copyright (C) 2012 W. Trevor King <wking@tremily.us>
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

"""Gather and display information about a comedi device.
"""

try:
    import kmod as _kmod
    import kmod.error as _kmod_error
except ImportError as e:
    _kmod = None
    _kmod_import_error = e

from pycomedi import PyComediError as _PyComediError
import pycomedi.constant as _constant
from pycomedi.device import Device as _Device
from pycomedi.subdevice import StreamingSubdevice as _StreamingSubdevice


class ModuleNotFound (ValueError):
    pass


def display_modinfo(module_name):
    if _kmod is None:
        raise _kmod_import_error
    kmod = _kmod.Kmod()
    mod = kmod.module_from_name(name=module_name)
    items = [('filename', mod.path)]
    try:
        items.extend(mod.info.items())
    except _kmod_error.KmodError as e:
        raise ModuleNotFound(module_name)
    longest_key = max(len(k) for k,v in items)
    print('modinfo for {}'.format(module_name))
    for k,v in items:
        space = ' '*(longest_key + 4 - len(k))
        print('  {}:{}{}'.format(k, space, v))

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
    except _PyComediError as e:
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
    except _PyComediError as e:
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

def run(filename):
    """
    >>> run(filename='/dev/comedi0')  # doctest: +ELLIPSIS, +REPORT_UDIFF
    overall info
      comedi version: 0.7.76
      driver name: ni_pcimio
      board name: pci-6052e
      number of subdevices: 14
    subdevice 0:
      type: ai
      flags: cmd_read|readable|ground|common|diff|other|dither
    ...
    subdevice 13:
      type: counter
      flags: readable|writable
      number of channels: 1
      max data value: 15
      ranges: <Range unit:none min:0.0 max:1.0>
      command: (not supported)
    """
    try:
        display_modinfo('comedi')
    except ImportError as e:
        print('could not load module info (kmod not installed)')
        print('  {}'.format(e))
    except ModuleNotFound as e:
        print('could not load module info (module not found)')
        print('  {}'.format(e))
    device = _Device(filename=filename)
    device.open()
    try:
        display(device)
    finally:
        device.close()


if __name__ == '__main__':
    import pycomedi_demo_args

    args = pycomedi_demo_args.parse_args(
        description=__doc__,
        argnames=['filename', 'verbose'])

    run(filename=args.filename)
