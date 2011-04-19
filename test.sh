#!/bin/bash -e
# -e to abort script at first error

python setup.py build_ext --inplace
nosetests --with-doctest pycomedi
ls pycomedi | grep '.pyx$'| while read file; do
  mod="${file/.pyx/}"
  echo "$mod"
  python -c "import doctest, sys; import pycomedi.$mod as m; r = doctest.testmod(m); print r; sys.exit(r.failed)"
done
nosetests --with-doctest --doctest-extension=.txt doc
