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


def run(filename, subdevice, channel, range, aref, num_scans):
    """
    >>> t1,data,t2 = run(filename='/dev/comedi0', subdevice=None,
    ...     channel=0, range=0, aref=_constant.AREF.ground, num_scans=10)
    >>> t1  # doctest: +SKIP
    1332242184.029691
    >>> t2  # doctest: +SKIP
    1332242184.3311629
    >>> data  # doctest: +ELLIPSIS
    array([...], dtype=uint32)
    >>> data.shape
    (10,)
    """
    _LOG.info(('measuring device={} subdevice={} channel={} range={} '
               'analog-reference={} num-scans={}'
               ).format(filename, subdevice, channel, range, aref, num_scans))
    device = _Device(filename=filename)
    device.open()
    try:
        if subdevice is None:
            subdevice = device.find_subdevice_by_type(
                _constant.SUBDEVICE_TYPE.ai)
        else:
            subdevice = device.subdevice(subdevice)

        insns = [subdevice.insn(), subdevice.insn(), subdevice.insn()]
        insns[0].insn = insns[2].insn = _constant.INSN.gtod
        insns[0].data = insns[2].data = [0, 0]
        insns[1].insn = _constant.INSN.read
        insns[1].data = [0] * num_scans
        insns[1].chanspec = _ChanSpec(chan=channel, range=range, aref=aref)

        device.do_insnlist(insns)
    finally:
        device.close()

    t1 = insns[0].data[0] + insns[1].data[1]/1e6
    t2 = insns[2].data[0] + insns[2].data[1]/1e6
    return (t1, insns[1].data, t2)
    
def display(t1, data, t2):
    _LOG.info('initial time: {}'.format(t1))
    _LOG.info('final time:   {}'.format(t2))
    _LOG.info('difference:   {}'.format(t2-t1))
    for x in insns[1].data:
        print(x)

if __name__ == '__main__':
    import pycomedi_demo_args

    args = pycomedi_demo_args.parse_args(
        description=__doc__,
        argnames=['filename', 'subdevice', 'channel', 'aref', 'range',
                  'num-scans', 'verbose'],
        args=args)

    t1,data,t2 = run(
        filename=args.filename, subdevice=args.subdevice, channel=args.channel,
        range=args.range, aref=args.aref, num_scans=args.num_scans)
    display(t1=t1, data=data, t2=t2)
