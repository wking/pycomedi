# Copyright (C) 2008-2012 W. Trevor King <wking@tremily.us>
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

"A Pythonic wrapper around Comedilib"

import logging as _logging


__version__ = '0.5'


LOG = _logging.getLogger('pycomedi')
"Pycomedi logger"

LOG.setLevel(_logging.WARN)
h = _logging.StreamHandler()
f = _logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
h.setFormatter(f)
LOG.addHandler(h)
del h, f


class PyComediError (Exception):
    "Error in pycomedi"
    def __init__(self, function_name=None, ret=None, comedi_msg=None,
                 error_msg=None):
        self.function_name = function_name
        self.ret = ret
        self.comedi_msg = comedi_msg
        self.error_msg = error_msg
        if error_msg:
            msg = '{0} ({1}): {2} ({3})'.format(
                function_name, error_msg, comedi_msg, ret)
        else:
            msg = '{0}: {1} ({2})'.format(function_name, comedi_msg, ret)
        super(PyComediError, self).__init__(msg)
