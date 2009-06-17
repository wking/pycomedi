"""PyComedi: an object-oriented interface for the Comedi drivers.

Requires
  * Numpy  (http://numpy.scipy.org/)
  * Comedi (http://www.comedi.org/)
"""

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

# http://peak.telecommunity.com/DevCenter/setuptools#using-setuptools-without-bundling-it
import ez_setup
ez_setup.use_setuptools()

from setuptools import setup, find_packages

# patch distutils if it can't cope with the "classifiers" or
# "download_url" keywords
from sys import version
if version < '2.2.3':
    from distutils.dist import DistributionMetadata
    DistributionMetadata.classifiers = None
    DistributionMetadata.download_url = None

#from pycomedi import VERSION
VERSION = "0.2" # importing pycomedi requires comedi on this machine, so copy.

doclines = __doc__.split("\n")

setup(name="pycomedi",
      version=VERSION,
      maintainer="W. Trevor King",
      maintainer_email="wking@drexel.edu",
      url = "http://www.physics.drexel.edu/~wking/code/python/",
      download_url = "http://www.physics.drexel.edu/~wking/code/python/pycomedi-%s.tar.gz" % VERSION,
      license = "GNU General Public License (GPL)",
      platforms = ["all"],
      description = doclines[0],
      long_description = "\n".join(doclines[2:]),
      classifiers = filter(None, classifiers.split("\n")),
      py_modules = ['ez_setup'],
      packages = find_packages(),
      )

# use packages to include subdirectory packages
# use py_modules to include single-module packages
# use ext_modules to include extension modules
# see
#   http://www.python.org/doc/2.5.2/dist/listing-modules.html
#   http://www.python.org/doc/2.5.2/dist/describing-extensions.html
