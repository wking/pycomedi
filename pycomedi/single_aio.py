# Use Comedi drivers for single-shot analog input/output
# Copyright (C) 2007-2010  W. Trevor King
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

"""Use Comedi drivers for single-shot analog input/output

Being single-shot implementations, read/writes will be software timed,
so this module would not be a good choice if you need millisecond
resolution.  However, it does provide a simple and robust way to
generate/aquire signals at 1 second and greater timescales.
"""

import comedi as c
import common

VERBOSE_DEBUG = False

class sngAioError (common.PycomediError) :
    "Single point Analog IO error"
    pass

class AI (common.PyComediSingleIO) :
    def __init__(self, **kwargs) :
        """inputs:
          filename:  comedi device file for your device ["/dev/comedi0"].
          subdevice: the analog input subdevice (-1 for autodetect)
          chan: an iterable of the channels you wish to control [(0,1,2,3)]
          aref: the analog references for these channels [(comedi.AREF_GROUND,)]
            values include:
              comedi.AREF_GROUND
              comedi.AREF_COMMON
              comedi.AREF_DIFF
              comedi.AREF_OTHER
          range: the ranges for these channels [(0,)]
        """
        common.PyComediIO.__init__(self, devtype=c.COMEDI_SUBD_AI, output=False, **kwargs)
    def read(self) :
        """outputs:
          data: a list of read data values in Comedi units
        """
        data = range(self.nchan)
        for i in range(self.nchan) :
            data[i] = self.read_chan_index(i)
        #print "Read %s, got %s" % (str(self.chan), str(data))
        return data

def _test_AI() :
    ai = AI()
    print "read ", ai.read()
    print "read ", ai.read()
    print "read ", ai.read()
    print "read ", ai.read()
    ai.close()
    print "ai success"

class AO (common.PyComediSingleIO) :
    def __init__(self, **kwargs) :
        """inputs:
          filename:  comedi device file for your device ["/dev/comedi0"].
          subdevice: the analog output subdevice [-1 for autodetect]
          chan: an iterable of the channels you wish to control [(0,1,2,3)]
          aref: the analog references for these channels [(comedi.AREF_GROUND,)]
            values include:
              comedi.AREF_GROUND
              comedi.AREF_COMMON
              comedi.AREF_DIFF
              comedi.AREF_OTHER
          range: the ranges for these channels [(0,)]
        """
        common.PyComediIO.__init__(self, devtype=c.COMEDI_SUBD_AO, output=True, **kwargs)
    def write(self, data) :
        if len(data) != self.nchan :
            raise sngAioError,  "data length %d != the number of channels (%d)" % (len(data), self.nchan)
        for i in range(self.nchan) :
            self.write_chan_index(i, data[i])

def _test_AO() :
    ao = AO(chan=(0,1))
    ao.write([0,0])
    ao.write([3000,3000])
    ao.write([0,0])
    ao.close()
    print "ao success"

def _fit_with_residual(out_data, in_data, channel) :
    "Fit in_data(out_data) to a straight line & return residual"
    from scipy.stats import linregress
    from numpy import zeros
    gradient, intercept, r_value, p_value, std_err = linregress(out_data, in_data)
    print "y = %g + %g x" % (intercept, gradient)
    print "r = ", r_value # correlation coefficient = covariance / (std_dev_x*std_dev_y)
    print "p = ", p_value # probablility of measuring this ?slope? for non-correlated, normally-distruibuted data
    print "err = ", std_err # root mean sqared error of best fit
    if gradient < .7 or p_value > 0.05 :
        raise sngAioError, "Out channel %d != in channel %d" % (channel, channel)
    residual = zeros((len(out_data),))
    for i in range(len(out_data)) :
        pred_y = intercept + gradient * out_data[i]
        residual[i] = in_data[i] - pred_y
    return residual

def plot_data(out_data0, in_data0, residual0, out_data1, in_data1, residual1) :
    try :
        from pylab import plot, show, subplot, xlabel, ylabel
        subplot(311)
        plot(out_data0, in_data0, 'r.-', out_data1, in_data1, 'b.')
        ylabel("Read")
        xlabel("Wrote")
        if residual0 != None and residual1 != None:
            subplot(312)
            plot(out_data0, residual0, 'r.', out_data1, residual1, 'b.')
            ylabel("Residual")
            xlabel("Wrote")
        subplot(313)
        plot(in_data0, 'r.', in_data1, 'b.')
        xlabel("Read")
        show() # if interactive mode is off...
        #raw_input("Press enter to continue") # otherwise, pause
    except ImportError :
        pass # ignore plot erros

def _test_AIO() :
    "Test AO and AI by cabling AO0 into AI0 and sweeping voltage"
    from scipy.stats import linregress
    from numpy import linspace, zeros
    ao = AO(chan=(0,1))
    ai = AI(chan=(0,1))
    start = 0.1 * ao.maxdata[0]
    stop = 0.9 * ao.maxdata[0]
    points = 10
    out_data0 = linspace(start, stop, points)
    out_data1 = linspace(stop, start, points)
    in_data0 = zeros((points,))
    in_data1 = zeros((points,))
    for i in range(points) :
        ao.write([int(out_data0[i]), int(out_data1[i])])
        id = ai.read()
        in_data0[i] = id[0]
        in_data1[i] = id[1]
    ai.close()
    ao.close()
    if VERBOSE_DEBUG :
        plot_data(out_data0, in_data0, None, out_data1, in_data1, None)
    residual0 = _fit_with_residual(out_data0, in_data0, 0)
    residual1 = _fit_with_residual(out_data1, in_data1, 1)
    if VERBOSE_DEBUG :
        plot_data(out_data0, in_data0, residual0, out_data1, in_data1, residual1)
    for i in range(points) :
        if abs(residual0[i]) > 10 : # HACK, hardcoded maximum nonlinearity
            raise Exception, "Input 0, point %d (x %d), y-value %d has excessive residual %d" % (i, out_data0[i], in_data0[i], residual0[i])
        if abs(residual1[i]) > 10 : # HACK, hardcoded maximum nonlinearity
            raise Exception, "Input 1, point %d (x %d), y-value %d has excessive residual %d" % (i, out_data1[i], in_data1[i], residual1[i])
    print "aio success"

def test() :
    _test_AI()
    _test_AO()
    _test_AIO()

if __name__ == "__main__" :
    test()
