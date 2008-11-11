.PHONY : all check dist clean

all : dummy_py

dummy_py : setup.py pycomedi/*.py
	python setup.py install --home=~
	echo "dummy for Makefile dependencies" > $@

check : all
	python pycomedi.py

dist :
	python setup.py sdist
	scp dist/pycomedi*tar.gz einstein:public_html/code/python/

clean :
	python setup.py clean
	rm -rf build dist pycomedi.egg-info
	rm -f dummy_py *.pyc
