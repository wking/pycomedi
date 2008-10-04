#!/usr/bin/python

from scipy.io import read_array, write_array
import sys

data = read_array(sys.argv[1]) #, atype='Integer' numpy.typecodes

start_vals = data[0]
for point in data :
    x = point-start_vals
    for val in x :
        print val, "\t",
    print ""

