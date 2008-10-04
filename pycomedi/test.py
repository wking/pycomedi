#!/usr/bin/python
#
# With analog output 0 cabled directly to analog input 0
# output a single period of a 1000kHz sine wave
# and perform a linear regression between the output and input data.
# If the input is closely correlated to the output (gradient > 0.7)
# consider the synchronized input/output a success.
# Prints the success rate for num_runs

from scipy.stats import linregress
from scipy.io import read_array, write_array
from os import system
from numpy import zeros

# I had been checking at different waits between AO arming and AI triggering,
# thinking that the problem might be due to my patch.
# But I get failure rates of ~ 20% regardless of the wait time (-t option)
# So currently only use waits of 0 seconds to get more data.

def test() :
    #waits = range(5, -1, -1)
    waits = [0]
    
    num_runs = 200
    runs  = range(0, num_runs)
    results = zeros((1, num_runs))
    good_run_arr = []

    fails = 0
    successes = 0
    good_run = 0
    for wait in waits :
        for run in runs :
            call = './simult_aio -n 50 -F 50000 -w 1000 -t%d' % wait
            if system(call) != 0 :
                return 1
            if system('int16s_to_ascii_array out in > data') != 0 :
                return 1
            data = read_array('data')
            gradient, intercept, r_value, p_value, std_err = linregress(data)
            results[wait,run] = gradient
            print "wait %2d, run %2d, gradient %g" % (wait, run, gradient)
            if gradient < .7 :
                fails += 1
                good_run_arr.append(good_run)
                good_run = 0
            else :
                successes += 1
                good_run += 1
    print "failure rate ", (float(fails)/float(fails+successes))
    call = 'echo "'
    for num in good_run_arr :
        call += "%d " % num
    call += '" | stem_leaf 2'
    print "good runs:"
    system(call)

if __name__ == "__main__" :
    test()
