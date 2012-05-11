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

"""Enums and flags are bundled into class instances for easier browsing

>>> SUBDEVICE_TYPE  # doctest: +NORMALIZE_WHITESPACE
[<_NamedInt unused>, <_NamedInt ai>, <_NamedInt ao>, <_NamedInt di>,
 <_NamedInt do>, <_NamedInt dio>, <_NamedInt counter>, <_NamedInt timer>,
 <_NamedInt memory>, <_NamedInt calib>, <_NamedInt proc>, <_NamedInt serial>,
 <_NamedInt pwm>]
>>> SUBDEVICE_TYPE.dio
<_NamedInt dio>
>>> SUBDEVICE_TYPE.dio.value == _comedi.COMEDI_SUBD_DIO
True
>>> SUBDEVICE_TYPE.dio.doc
'COMEDI_SUBD_DIO (digital input/output)'

You can also search by name or value.

>>> TRIG_SRC.index_by_name('timer')
<_NamedInt timer>
>>> TRIG_SRC.index_by_value(_comedi.TRIG_NOW)
<_NamedInt now>

Some flags have constants for setting or clearing all the flags at once.

>>> TRIG_SRC  # doctest: +NORMALIZE_WHITESPACE
[<_NamedInt none>, <_NamedInt now>, <_NamedInt follow>, <_NamedInt time>,
 <_NamedInt timer>, <_NamedInt count>, <_NamedInt ext>, <_NamedInt int>,
 <_NamedInt other>]
>>> TRIG_SRC._empty
<_NamedInt invalid>
>>> TRIG_SRC._all
<_NamedInt any>

Flag instances have a special wrapper that stores their value.

>>> f = FlagValue(SDF, 17)
>>> f.flag  # doctest: +ELLIPSIS
[<_NamedInt busy>, <_NamedInt busy_owner>, ...]
>>> f.busy
True
>>> f.busy = False
>>> f._value
16

You can treat named integers as Python integers with bitwise operations,

>>> a = TRIG_SRC.now | TRIG_SRC.follow | TRIG_SRC.time | 64
>>> a
<BitwiseOperator 78>
>>> a.value
78
>>> TRIG_SRC.none & TRIG_SRC.now
<BitwiseOperator 0>

Because of the way Python operator overloading works [#ops]_, you can
also start a bitwise chain with an integer.

>>> 64 | TRIG_SRC.now
<BitwiseOperator 66>

Rich comparisons with other flags and integers are also supported.

>>> 64 > TRIG_SRC.now
True
>>> TRIG_SRC.now > 64
False
>>> TRIG_SRC.now >= 2
True
>>> TRIG_SRC.now >= 3
False
>>> import copy
>>> TRIG_SRC.now == copy.deepcopy(TRIG_SRC.now)
True
>>> TRIG_SRC.now != TRIG_SRC.now
False
>>> TRIG_SRC.now <= 2
True
>>> TRIG_SRC.now < 3
True
>>> TRIG_SRC.now > None
True

The ``UNIT`` constant treats ``RF_EXTERNAL`` as a full-fledged unit:

>>> UNIT.index_by_name('external')
<_NamedInt external>
>>> UNIT.index_by_value(_comedi.RF_EXTERNAL)
<_NamedInt external>

.. [#ops] See `emulating numeric types`_ and `NotImplementedError` in
   `the standard type hierarchy`_.

.. _emulating numeric types:
  http://docs.python.org/reference/datamodel.html#emulating-numeric-types
.. _the standard type hierarchy`_
  http://docs.python.org/reference/datamodel.html#the-standard-type-hierarchy
"""

from math import log as _log
import sys as _sys

import numpy as _numpy
import comedi as _comedi

from pycomedi import LOG as _LOG


def bitwise_value(object):
    """Convenience function for flexible value specification

    This funciton makes it easy for functions and methods to accept
    either integers or `BitwiseOperator` instances as integer
    parameters.
    """
    if isinstance(object, BitwiseOperator):
        return object.value
    return object


def _pso(s, o):
    """External definition of staticmethod until Cython supports the
    usual syntax.

    http://docs.cython.org/src/userguide/limitations.html#behaviour-of-class-scopes
    """
    if isinstance(s, BitwiseOperator):
        s = s.value
    if isinstance(o, BitwiseOperator):
        o = o.value
    return (long(s), long(o))


cdef class BitwiseOperator (object):
    """General class for bitwise operations.

    This class allows chaining bitwise operations between
    `_NamedInt`\s and similar objects.

    Because flag values can be large, we cast all values to longs
    before performing any bitwise operations.  This avoids issues like

    >>> int.__or__(1073741824, 2147483648L)
    NotImplemented
    """

    def __init__(self, value):
        self.value = value

    def __str__(self):
        return self.__repr__()

    def __repr__(self):
        return '<%s %s>' % (self.__class__.__name__, self.value)

    _prepare_self_other = staticmethod(_pso)

    def __and__(self, other):
        "Bitwise and acts on `BitwiseOperator.value`."
        s,o = BitwiseOperator._prepare_self_other(self, other)
        return BitwiseOperator(int(long.__and__(s, o)))

    def __or__(self, other):
        "Bitwise or acts on `BitwiseOperator.value`."
        s,o = BitwiseOperator._prepare_self_other(self, other)
        return BitwiseOperator(int(long.__or__(s, o)))

    def __richcmp__(self, other, op):
        if other is None:
            other = self.value - 1
        s,o = BitwiseOperator._prepare_self_other(self, other)
        if op == 0:
            return s < o
        elif op == 1:
            return s <= o
        elif op == 2:
            return s == o
        elif op == 3:
            return s != o
        elif op == 4:
            return s > o
        elif op == 5:
            return s >= o
        else:
            raise ValueError(op)

    def __reduce__(self):
        return (BitwiseOperator, (self.value,))


class _NamedInt (BitwiseOperator):
    "A flag or enum item."
    def __init__(self, name, value, doc=None):
        super(_NamedInt, self).__init__(value)
        self.name = name
        self.doc = doc

    def __str__(self):
        return self.name

    def __repr__(self):
        return '<%s %s>' % (self.__class__.__name__, self.name)

    def __reduce__(self):
        return (_NamedInt, (self.name, self.value, self.doc))


class _Enum (list):
    "An enumerated list"
    def __init__(self, name, prefix='', blacklist=None, whitelist=None,
                 translation=None):
        super(_Enum, self).__init__()
        self.name = name
        if blacklist == None:
            blacklist = []
        if translation == None:
            translation = {}
        self._name_keys = {}
        self._value_keys = {}
        for attr in dir(_comedi):
            if attr.startswith(prefix):
                item_name = self._item_name(attr, prefix, translation)
                if self._is_ignored(item_name, blacklist, whitelist):
                    continue
                self._add_item(attr, item_name)
        self.sort(key=lambda item: item.value)

    def _item_name(self, attr, prefix, translation):
        item_name = attr[len(prefix):]
        if item_name in translation:
            return translation[item_name]
        else:
            return item_name.lower()

    def _is_ignored(self, item_name, blacklist, whitelist):
        return (item_name in blacklist
                or whitelist != None and item_name not in whitelist)

    def _add_item(self, attr, item_name):
        item_value = getattr(_comedi, attr)
        if item_value < 0:
            _LOG.debug('big value for {0:s}: {1:d} ({1:b}) converted to {2:d} ({2:b})'.format(
                    attr, item_value, (1<<32) + item_value))
            item_value = (1<<32) + item_value  # flags are unsigned 32 bit integers, but SWIG signs them
        item = _NamedInt(item_name, item_value, doc=attr)
        self.append(item)

    def append(self, item):
        super(_Enum, self).append(item)
        self._name_keys[item.name] = item
        if item.value in self._value_keys and item.name:
            raise ValueError('value collision in %s: %s = %s = %#x'
                             % (self.name, item.name,
                                self._value_keys[item.value], item.value))
        self._value_keys[item.value] = item
        setattr(self, item.name, item)

    def index_by_name(self, name):
        return self._name_keys[name]

    def index_by_value(self, value):
        return self._value_keys[value]


class _Flag (_Enum):
    "A flag"
    def __init__(self, *args, **kwargs):
        super(_Flag, self).__init__(*args, **kwargs)
        self._empty = None
        self._all = None
        for flag in self:
            if flag.value == 0:
                self._empty = flag
            elif flag.value < 0 or abs(_log(flag.value, 2)) % 1 > 1e-13:  # deal with rounding errors
                if self._all:
                    raise ValueError(
                        'mutliple multi-bit flags in %s: %s = %#x and %s = %#x'
                        % (self.name, self._all.name, self._all.value,
                           flag.name, flag.value))
                self._all = flag
        if self._empty:
            self.remove(self._empty)
        if self._all:
            self.remove(self._all)

    def get(self, value, name):
        flag = getattr(self, name)
        assert flag.value != 0, '%s: %s' % (self.name, flag)
        return value & flag.value == flag.value

    def set(self, value, name, status):
        flag = getattr(self, name)
        if status == True:
            return value | flag.value
        return (value | flag.value) - flag.value


class FlagValue (object):
    """A flag instance (flag + value)

    Examples
    --------

    >>> f = FlagValue(flag=TRIG_SRC, value=0, default='empty')
    >>> f.any
    False
    >>> print f
    empty
    >>> f.now = True
    >>> f.timer = True
    >>> f.int = True
    >>> print f
    now|timer|int
    """
    def __init__(self, flag, value, default='-'):
        self.flag = flag
        self._value = value
        self._default = default

    def __str__(self):
        flags = [f for f in self.flag if getattr(self, f.name)]
        if len(flags) == 0:
            return self._default
        return '|'.join([f.name for f in flags])

    def __getattr__(self, name):
        return self.flag.get(self._value, name)

    def __setattr__(self, name, value):
        if name != 'flag' and not name.startswith('_'):
            value = self.flag.set(self._value, name, value)
            name = '_value'
        super(FlagValue, self).__setattr__(name, value)


# blacklist deprecated values (and those belonging to other _Enums or _Flags)

CR = _Flag('ChanSpec flags', 'CR_', blacklist=['dither', 'deglitch'])
CR.alt_filter.doc += ' (can also mean "dither" or "deglitch")'

AREF = _Enum('analog_reference', 'AREF_')
AREF.diff.doc += ' (differential)'
AREF.other.doc += ' (other / undefined)'

#GPCT = _Flag('general_purpose_counter_timer', 'GPCT_')
# Two competing flag sets?  Need some documentation.

INSN_MASK = _Flag('instruction_mask', 'INSN_MASK_')

CONFIGURATION_IDS = _Enum('configuration_ids', 'INSN_CONFIG_', blacklist=[
        '8254_set_mode'])

INSN = _Enum('instruction', 'INSN_',
             blacklist=['mask_%s' % i.name for i in INSN_MASK] + [
        'config_%s' % i.name for i in CONFIGURATION_IDS])

TRIG = _Flag('trigger_flags', 'TRIG_', whitelist=[
        'bogus', 'dither', 'deglitch', 'config', 'wake_eos'])
TRIG.bogus.doc += ' (do the motions)'
TRIG.config.doc += ' (perform configuration, not triggering)'
TRIG.wake_eos.doc += ' (wake up on end-of-scan events)'

CMDF = _Flag('command_flags', 'CMDF_')
CMDF.priority.doc += (
    ' (try to use a real-time interrupt while performing command)')

EV = _Flag('??', 'COMEDI_EV_')

TRIG_ROUND = _Enum('trigger_round', 'TRIG_ROUND_', blacklist=['mask'])
TRIG_ROUND.mask = _comedi.TRIG_ROUND_MASK

TRIG_SRC = _Flag('trigger_source_flags', 'TRIG_',
                 blacklist=[i.name for i in TRIG] + [
            'round_%s' % i.name for i in TRIG_ROUND] + [
        'round_mask', 'rt', 'write'])
TRIG_SRC.none.doc += ' (never trigger)'
TRIG_SRC.now.doc += ' (trigger now + N ns)'
TRIG_SRC.follow.doc += ' (trigger on next lower level trig)'
TRIG_SRC.time.doc += ' (trigger at time N ns)'
TRIG_SRC.timer.doc += ' (trigger at rate N ns)'
TRIG_SRC.count.doc += ' (trigger when count reaches N)'
TRIG_SRC.ext.doc += ' (trigger on external signal N)'
TRIG_SRC.int.doc += ' (trigger on comedi-internal signal N)'
TRIG_SRC.other.doc += ' (driver defined)'

SDF_PWM = _Flag('pulse_width_modulation_subdevice_flags', 'SDF_PWM_')
SDF_PWM.counter.doc += ' (PWM can automatically switch off)'
SDF_PWM.hbridge.doc += ' (PWM is signed (H-bridge))'

SDF = _Flag('subdevice_flags', 'SDF_', blacklist=[
        'pwm_%s' % i.name for i in SDF_PWM] + [
        'cmd', 'writeable', 'rt'])
SDF.busy.doc += ' (device is busy)'
SDF.busy_owner.doc += ' (device is busy with your job)'
SDF.locked.doc += ' (subdevice is locked)'
SDF.lock_owner.doc += ' (you own lock)'
SDF.maxdata.doc += ' (maxdata depends on channel)'
SDF.flags.doc += ' (flags depend on channel (BROKEN))'
SDF.rangetype.doc += ' (range type depends on channel)'
SDF.soft_calibrated.doc += ' (subdevice uses software calibration)'
SDF.cmd_write.doc += ' (can do output commands)'
SDF.cmd_read.doc += ' (can to input commands)'
SDF.readable.doc += ' (subdevice can be read, e.g. analog input)'
SDF.writable.doc += ' (subdevice can be written, e.g. analog output)'
SDF.internal.doc += ' (subdevice does not have externally visible lines)'
SDF.ground.doc += ' (can do aref=ground)'
SDF.common.doc += ' (can do aref=common)'
SDF.diff.doc += ' (can do aref=diff)'
SDF.other.doc += ' (can do aref=other)'
SDF.dither.doc += ' (can do dithering)'
SDF.deglitch.doc += ' (can do deglitching)'
SDF.mmap.doc += ' (can do mmap())'
SDF.running.doc += ' (subdevice is acquiring data)'
SDF.lsampl.doc += ' (subdevice uses 32-bit samples)'
SDF.packed.doc += ' (subdevice can do packed DIO)'

SUBDEVICE_TYPE = _Enum('subdevice_type', 'COMEDI_SUBD_')
SUBDEVICE_TYPE.unused.doc += ' (unused by driver)'
SUBDEVICE_TYPE.ai.doc += ' (analog input)'
SUBDEVICE_TYPE.ao.doc += ' (analog output)'
SUBDEVICE_TYPE.di.doc += ' (digital input)'
SUBDEVICE_TYPE.do.doc += ' (digital output)'
SUBDEVICE_TYPE.dio.doc += ' (digital input/output)'
SUBDEVICE_TYPE.memory.doc += ' (memory, EEPROM, DPRAM)'
SUBDEVICE_TYPE.calib.doc += ' (calibration DACs)'
SUBDEVICE_TYPE.proc.doc += ' (processor, DSP)'
SUBDEVICE_TYPE.serial.doc += ' (serial IO)'
SUBDEVICE_TYPE.pwm.doc += ' (pulse-with modulation)'

IO_DIRECTION = _Enum('io_direction', 'COMEDI_', whitelist=[
        'input', 'output', 'opendrain'])

SUPPORT_LEVEL = _Enum('support_level', 'COMEDI_', whitelist=[
        'unknown_support', 'supported', 'unsupported'])

UNIT = _Enum('unit', 'UNIT_', translation={'mA':'mA'})
# The mA translation avoids lowercasing to 'ma'.
UNIT.append(_NamedInt(
        name='external',
        value=_comedi.RF_EXTERNAL, 
        doc=('RF_EXTERNAL (value unit is defined by an external reference '
             'channel)')))

CALLBACK = _Enum('callback_flags', 'COMEDI_CB_', blacklist=['block', 'eobuf'])
CALLBACK.eos.doc += ' (end of scan)'
CALLBACK.eoa.doc += ' (end of acquisition)'
CALLBACK.error.doc += ' (card error during acquisition)'
CALLBACK.overflow.doc += ' (buffer overflow/underflow)'

CONVERSION_DIRECTION = _Enum('conversion_direction', 'COMEDI_', whitelist=[
        'to_physical', 'from_physical'])

# The following constants aren't declared in comedi.h or comedilib.h,
# but they should be.

LOGLEVEL = _Enum('log level', '', whitelist=[''])
LOGLEVEL.append(_NamedInt('silent', 0, doc='Comedilib prints nothing.'))
LOGLEVEL.append(_NamedInt('bug', 1, doc=(
            'Comedilib prints error messages when there is a self-consistency '
            'error (i.e., an internal bug (default).')))
LOGLEVEL.append(_NamedInt('invalid', 2, doc=(
            'Comedilib prints an error message when an invalid parameter is '
            'passed.')))
LOGLEVEL.append(_NamedInt('error', 3, doc=(
            'Comedilib prints an error message whenever an error is generated '
            'in the Comedilib library or in the C library, when called by '
            'Comedilib.')))
LOGLEVEL.append(_NamedInt('debug', 4, doc='Comedilib prints a lot of junk.'))
