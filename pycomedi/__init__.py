# Copyright (C) 2008-2012 W. Trevor King <wking@drexel.edu>
#
# This file is part of pycomedi.
#
# pycomedi is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License as published by the
# Free Software Foundation, either version 2 of the License, or (at your
# option) any later version.
#
# pycomedi is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with pycomedi.  If not, see <http://www.gnu.org/licenses/>.

"A Pythonic wrapper around Comedilib"

import logging as _logging


__version__ = '0.3'


LOG = _logging.getLogger('pycomedi')
"Pycomedi logger"

LOG.setLevel(_logging.DEBUG)
h = _logging.StreamHandler()
h.setLevel(_logging.WARN)
f = _logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
h.setFormatter(f)
LOG.addHandler(h)
del h, f


class PyComediError (Exception):
    "Error in pycomedi"
    pass
