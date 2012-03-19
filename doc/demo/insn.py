#!/usr/bin/env python
#
# Copyright

"""Do 3 instructions in one system call to time a multi-sample read.

Do a ``gettimeofday()`` call, read some samples from an analog
input, and do another ``gettimeofday()`` call.
"""

import logging as _logging

from pycomedi import LOG as _LOG
import pycomedi.constant as _constant
from pycomedi.device import Device as _Device
from pycomedi.chanspec import ChanSpec as _ChanSpec


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        '-f', '--filename', default='/dev/comedi0',
        help='path to comedi device file')
    parser.add_argument(
        '-s', '--subdevice', type=int, help='subdevice for analog input')
    parser.add_argument(
        '-c', '--channel', type=int, default=0,
        help='channel for analog input')
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

    device = _Device(filename=args.filename)
    device.open()
    subdevice = device.find_subdevice_by_type(_constant.SUBDEVICE_TYPE.ai)

    insns = [subdevice.insn(), subdevice.insn(), subdevice.insn()]
    insns[0].insn = insns[2].insn = _constant.INSN.gtod
    insns[0].data = insns[2].data = [0, 0]
    insns[1].insn = _constant.INSN.read
    insns[1].data = [0] * args.num_scans
    aref = _constant.AREF.index_by_name(args.aref)
    insns[1].chanspec = _ChanSpec(
        chan=args.channel, range=args.range, aref=aref)

    device.do_insnlist(insns)
    device.close()

    t1 = insns[0].data[0] + insns[1].data[1]/1e6
    t2 = insns[2].data[0] + insns[2].data[1]/1e6
    print('initial time: {}'.format(t1))
    print('final time:   {}'.format(t2))
    print('difference:   {}'.format(t2-t1))
    print('data:')
    for x in insns[1].data:
        print(x)
