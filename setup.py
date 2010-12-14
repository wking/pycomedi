"""PyComedi: an object-oriented interface for the Comedi drivers.

Requires
  * Numpy  (http://numpy.scipy.org/)
  * Comedi (http://www.comedi.org/)
"""

from distutils.core import setup

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

doclines = __doc__.split('\n')


setup(name='pycomedi',
      version=__version__,
      maintainer='W. Trevor King',
      maintainer_email='wking@drexel.edu',
      url='http://www.physics.drexel.edu/~wking/unfolding-disasters/pycomedi/',
      download_url='http://www.physics.drexel.edu/~wking/code/python/pycomedi-%s.tar.gz' % __version__,
      license='GNU General Public License (GPL)',
      platforms=['all'],
      description=doclines[0],
      long_description='\n'.join(doclines[2:]),
      classifiers=filter(None, classifiers.split('\n')),
      packages=['pycomedi'],
      provides=['pycomedi'],
      )
