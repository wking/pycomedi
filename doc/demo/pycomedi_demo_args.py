# Copyright

import argparse as _argparse
import logging as _logging

from pycomedi import LOG as _LOG
import pycomedi.constant as _constant


class _SetFrequencyAction (_argparse.Action):
    def __call__(self, parser, namespace, values, option_string=None):
        setattr(namespace, self.dest, values)
        setattr(namespace, 'period', 1.0/values)


class _IncrementVerbosityAction (_argparse.Action):
    def __call__(self, parser, namespace, values, option_string=None):
        level = _LOG.level
        level -= 10  # e.g. logging.INFO -> logging.DEBUG
        if level >= _logging.DEBUG:
            _LOG.setLevel(level)


# name -> (args, kwargs)
ARGUMENTS = {
    'filename':(
        ['-f', '--filename'],
        {'default':'/dev/comedi0',
         'help':'path to comedi device file'}),
    'subdevice':(
        ['-s', '--subdevice'],
        {'type':int,
         'help':'subdevice for analog input/output'}),
    'channel':(
        ['-c', '--channel'],
        {'type':int,
         'default':0,
         'help':'channel for analog input/output'}),
    'channels':(
        ['-c', '--channels'],
        {'type':lambda x: [int(i) for i in x.split(',')],
         'default':0,
         'help':'comma-separated channels for analog input/output'}),
    'aref':(
        ['-a', '--analog-reference'],
        {'dest':'aref',
         'default':_constant.AREF.ground,
         'type':lambda x: _constant.AREF.index_by_name(x),
         'choices':_constant.AREF,
         'help':'reference for analog input/output'}),
    'range':(
        ['-r', '--range'],
        {'type':int,
         'default':0,
         'help':'range for analog input/output'}),
    'num-scans':(
        ['-N', '--num-scans'],
        {'type':int,
         'default':10,
         'help':'number of input/output scans'}),
    'frequency':(
        ['-F', '--frequency'],
        {'type':float,
         'action':_SetFrequencyAction,
         'help':'scan frequency in hertz'}),
    'physical':(
        ['-p', '--physical'],
        {'default':False,
         'action':'store_const',
         'const':True,
         'help':'convert input to physical values before printing'}),
    'mmap':(
        ['--mmap'],
        {'default':False,
         'action':'store_const',
         'const':True,
         'help':'use a memory-mapped reader rather than reading the input subdevice directly'}),
    'verbose':(
        ['-v', '--verbose'],
        {'action':_IncrementVerbosityAction}),
    }

def parse_args(description, argnames, args=None):
    """
    >>> args = parse_args(
    ...     description='Parse a bunch of arguments',
    ...     argnames=['frequency'], args=['--frequency', '2'])
    >>> args.period
    0.5
    """
    parser = _argparse.ArgumentParser(description=description)
    for argument in argnames:
        args_,kwargs = ARGUMENTS[argument]
        parser.add_argument(*args_, **kwargs)
    args = parser.parse_args(args=args)
    if 'frequency' in argnames and not hasattr(args, 'period'):
        args.period = 0
    return args
