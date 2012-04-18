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

"An object-oriented interface for the Comedi drivers."

from distutils.core import setup
from distutils.extension import Extension
import os
import os.path

from Cython.Distutils import build_ext
import numpy

from pycomedi import __version__


package_name = 'pycomedi'
classifiers = """\
Development Status :: 2 - Pre-Alpha
Intended Audience :: Developers
Intended Audience :: Science/Research
Operating System :: POSIX
Operating System :: Unix
License :: OSI Approved :: GNU General Public License (GPL)
Programming Language :: Python
Topic :: Scientific/Engineering
Topic :: Software Development :: Libraries :: Python Modules
"""

_this_dir = os.path.dirname(__file__)

ext_modules = []
for filename in sorted(os.listdir(package_name)):
    basename,extension = os.path.splitext(filename)
    if extension == '.pyx':
        ext_modules.append(
            Extension(
                '%s.%s' % (package_name, basename),
                [os.path.join(package_name, filename)],
                libraries=['comedi'],
                include_dirs=[numpy.get_include()],
                ))

setup(name=package_name,
      version=__version__,
      maintainer='W. Trevor King',
      maintainer_email='wking@tremily.us',
      url='http://blog.tremily.us/posts/{}/'.format(package_name),
      download_url='http://git.tremily.us/?p={}.git;a=snapshot;h={};sf=tgz'.format(
        package_name, __version__),
      license='GNU General Public License (GPL)',
      platforms=['all'],
      description=__doc__,
      long_description=open(os.path.join(_this_dir, 'README'), 'r').read(),
      classifiers=filter(None, classifiers.split('\n')),
      packages=[package_name],
      provides=[package_name],
      cmdclass = {'build_ext': build_ext},
      ext_modules = ext_modules,
      )
