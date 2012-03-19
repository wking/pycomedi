#!/usr/bin/env python
#
# Copyright

"""Do 3 instructions in one system call to time a multi-sample read.

Do a ``gettimeofday()`` call, read some samples from an analog
input, and do another ``gettimeofday()`` call.
"""

from pycomedi import LOG as _LOG
import pycomedi.constant as _constant
from pycomedi.device import Device as _Device
from pycomedi.chanspec import ChanSpec as _ChanSpec


if __name__ == '__main__':
    import argparse
    import pycomedi_demo_args

    args = pycomedi_demo_args.parse_args(
        description=__doc__,
        argnames=['filename', 'subdevice', 'channel', 'aref', 'range', 'num-scans',
                  'verbose'])

    _LOG.info(('measuring device={0.filename} subdevice={0.subdevice} '
               'channel={0.channel} range={0.range} analog reference={0.aref}'
               ).format(args))

    device = _Device(filename=args.filename)
    device.open()
    if args.subdevice is None:
        subdevice = device.find_subdevice_by_type(_constant.SUBDEVICE_TYPE.ai)
    else:
        subdevice = device.subdevice(args.subdevice)

    insns = [subdevice.insn(), subdevice.insn(), subdevice.insn()]
    insns[0].insn = insns[2].insn = _constant.INSN.gtod
    insns[0].data = insns[2].data = [0, 0]
    insns[1].insn = _constant.INSN.read
    insns[1].data = [0] * args.num_scans
    insns[1].chanspec = _ChanSpec(
        chan=args.channel, range=args.range, aref=args.aref)

    device.do_insnlist(insns)
    device.close()

    t1 = insns[0].data[0] + insns[1].data[1]/1e6
    t2 = insns[2].data[0] + insns[2].data[1]/1e6
    _LOG.info('initial time: {}'.format(t1))
    _LOG.info('final time:   {}'.format(t2))
    _LOG.info('difference:   {}'.format(t2-t1))
    for x in insns[1].data:
        print(x)
