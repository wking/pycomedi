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

"Useful error checking wrappers around Comedilib function calls"

# No relative imports in Cython yet, see
#   http://trac.cython.org/cython_trac/ticket/542
from pycomedi import LOG as _LOG
from pycomedi import PyComediError as _PyComediError

cimport _comedilib_h


def raise_error(function_name=None, ret=None, error_msg=None):
    """Report an error while executing a comedilib function

    >>> from pycomedi import PyComediError
    >>> raise_error(function_name='myfn', ret=-1)
    Traceback (most recent call last):
      ...
    PyComediError: myfn: Success (-1)
    >>> raise_error(function_name='myfn', ret=-1, error_msg='some error')
    Traceback (most recent call last):
      ...
    PyComediError: myfn (some error): Success (-1)
    >>> try:
    ...     raise_error(function_name='myfn', ret=-1)
    ... except PyComediError, e:
    ...     print(e.function_name)
    ...     print(e.ret)
    myfn
    -1
    """
    errno = _comedilib_h.comedi_errno()
    comedi_msg = _comedilib_h.comedi_strerror(errno)
    raise _PyComediError(
        function_name=function_name, ret=ret, comedi_msg=comedi_msg,
        error_msg=error_msg)


def _comedi_getter(name, is_invalid):
    # Hmm, cannot get function by name, or pass differing function pointers...
    #def comedi_get(function_name, *args, **kwargs):
    def comedi_get(function, *args, **kwargs):
        #fn = getattr(_comedilib_h, function_name)
        fn = function  # workaround until I get getattr() working
        function_name = function.__name__
        if 'error_msg' in kwargs:
            error_msg = kwargs.pop('error_msg')
        else:
            error_msg = 'error while running %s with %s and %s' % (
                function_name, args, kwargs)

        _LOG.debug('calling %s with %s %s' % (function_name, args, kwargs))

        ret = fn(*args, **kwargs)
        _LOG.debug('  call to %s returned %s' % (function_name, ret))
        if is_invalid(ret):
            raise_error(
                error_msg=error_msg, function_name=function_name, ret=ret)
        return ret
    #comedi_get.__name__ = name
    #comedi_get.__doc__ = (
    #    "Execute Comedilib's `<function_name>(*args, **kwargs)` safely.")
    return comedi_get

comedi_int = _comedi_getter('comedi_int', lambda ret: ret < 0)
comedi_ptr = _comedi_getter('comedi_ptr', lambda ret: ret == None)
comedi_tup = _comedi_getter('comedi_tup', lambda ret: ret[0] < 0)
