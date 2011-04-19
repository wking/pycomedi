# Copyright

"Wrap library-wide Comedi functions in a `Device` class"

import os as _os

cimport _comedilib_h
import constant as _constant


def set_loglevel(level):
    """Control the verbosity of Comedilib debugging and error messages

    This function affects the output of debugging and error messages
    from Comedilib. By increasing the loglevel, additional debugging
    information will be printed. Error and debugging messages are
    printed to the stream stderr.

    The default loglevel can be set by using the environment variable
    COMEDI_LOGLEVEL. The default loglevel is 1.

    In order to conserve resources, some debugging information is
    disabled by default when Comedilib is compiled.

    See `constants.LOGLEVEL` for a list of possible levels and their
    meanings.

    Return value
    ============

    This function returns the previous loglevel.

    >>> from constant import LOGLEVEL
    >>> level = set_loglevel(LOGLEVEL.error)
    >>> level
    <_NamedInt bug>
    >>> set_loglevel(level)
    <_NamedInt error>
    """
    ret = _comedilib_h.comedi_loglevel(_constant.bitwise_value(level))
    return _constant.LOGLEVEL.index_by_value(ret)
