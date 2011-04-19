# Copyright

"Useful error checking wrappers around Comedilib function calls"

# No relative imports in Cython yet, see
#   http://trac.cython.org/cython_trac/ticket/542
from pycomedi import LOG as _LOG
from pycomedi import PyComediError as _PyComediError

cimport _comedilib_h


def raise_error(function_name='', ret=None, error_msg=None):
    """Report an error while executing a comedilib function

    >>> raise_error(function_name='myfn', ret=-1)
    Traceback (most recent call last):
      ...
    PyComediError: myfn: Success (-1)
    >>> raise_error(function_name='myfn', ret=-1, error_msg='some error')
    Traceback (most recent call last):
      ...
    PyComediError: myfn (some error): Success (-1)
    """
    errno = _comedilib_h.comedi_errno()
    comedi_msg = _comedilib_h.comedi_strerror(errno)
    #_comedilib_h.comedi_perror(function_name)
    if error_msg:
        msg = '%s (%s): %s (%s)' % (function_name, error_msg, comedi_msg, ret)
    else:
        msg = '%s: %s (%s)' % (function_name, comedi_msg, ret)
    raise _PyComediError(msg)


def _comedi_getter(name, is_invalid):
    # Hmm, cannot get function by name, or pass differing function pointers...
    #def comedi_get(function_name, *args, **kwargs):
    def comedi_get(function, *args, **kwargs):
        if 'error_msg' in kwargs:
            error_msg = kwargs.pop('error_msg')
        else:
            error_msg = 'error while running %s with %s and %s' % (
                function_name, args, kwargs)
        #fn = getattr(_comedilib_h, function_name)
        fn = function  # workaround until I get getattr() working
        function_name = function.__name__

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
