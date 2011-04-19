# Copyright

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
      maintainer_email='wking@drexel.edu',
      url='http://www.physics.drexel.edu/~wking/unfolding-disasters/posts/%s/' % package_name,
      download_url='http://www.physics.drexel.edu/~wking/code/python/%s-%s.tar.gz' % (package_name, __version__),
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
