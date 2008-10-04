#!/usr/bin/python

from scipy.stats import linregress
from scipy.io import read_array, write_array
import sys

if __name__ == "__main__" :
    data = read_array(sys.argv[1]) #, atype='Integer' numpy.typecodes
    gradient, intercept, r_value, p_value, std_err = linregress(data)
    print "y = %g + %g x" % (intercept, gradient)
    print "r = ", r_value # correlation coefficient = covariance / (std_dev_x*std_dev_y)
    print "p = ", p_value # probablility of measuring this ?slope? for non-correlated, normally-distruibuted data
    print "err = ", std_err # root mean sqared error of best fit
    
