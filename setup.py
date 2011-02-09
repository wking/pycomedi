# Copyright

"An object-oriented interface for the Comedi drivers."

from distutils.core import setup
import os.path

from pycomedi import __version__


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

setup(name='pycomedi',
      version=__version__,
      maintainer='W. Trevor King',
      maintainer_email='wking@drexel.edu',
      url='http://www.physics.drexel.edu/~wking/unfolding-disasters/posts/pycomedi/',
      download_url='http://www.physics.drexel.edu/~wking/code/python/pycomedi-%s.tar.gz' % __version__,
      license='GNU General Public License (GPL)',
      platforms=['all'],
      description=__doc__,
      long_description=open(os.path.join(_this_dir, 'README'), 'r').read(),
      classifiers=filter(None, classifiers.split('\n')),
      packages=['pycomedi'],
      provides=['pycomedi'],
      )
