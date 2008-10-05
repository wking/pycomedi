"""Use Comedi drivers for single-shot analog input/output

Being single-shot implementations, read/writes will be software timed,
so this module would not be a good choice if you need millisecond
resolution.  However, it does provide a simple and robust way to
generate/aquire signals at 1 second and greater timescales.
"""

import comedi as c
import common

VERSION = common.VERSION
VERBOSE_DEBUG = True

class sngAioError (common.pycomediError) :
    "Single point Analog IO error"
    pass

class AI (common.PyComediSingleIO) :
    def __init__(self, **kwargs) :
        """inputs:
          filename:  comedi device file for your device ("/dev/comedi0").
          subdevice: the analog output subdevice (-1 for autodetect)
          chan: an iterable of the channels you wish to control ((0,1,2,3))
          aref: the analog reference for these channels (comedi.AREF_GROUND)
            values include:
              comedi.AREF_GROUND
              comedi.AREF_COMMON
              comedi.AREF_DIFF
              comedi.AREF_OTHER
          range: the range for these channels (0)
          output: whether to use the lines as output (vs input) (True)
        """
        common.PyComediIO.__init__(self, devtype=c.COMEDI_SUBD_AI, **kwargs)
    def read(self) :
        """outputs:
          data: a list of read data values in Comedi units
        """
        data = range(len(self.chan))
        for i in range(len(self.chan)) :
            data[i] = self.read_chan_index(i)
        #print "Read %s, got %s" % (str(self.chan), str(data))
        return data

def _test_ai_obj() :
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
          filename:  comedi device file for your device ("/dev/comedi0").
          subdevice: the analog output subdevice (-1 for autodetect)
          chan: an iterable of the channels you wish to control ((0,1,2,3))
          aref: the analog reference for these channels (comedi.AREF_GROUND)
            values include:
              comedi.AREF_GROUND
              comedi.AREF_COMMON
              comedi.AREF_DIFF
              comedi.AREF_OTHER
          range: the range for these channels (0)
          output: whether to use the lines as output (vs input) (True)
        """
        common.PyComediIO.__init__(self, devtype=c.COMEDI_SUBD_AO, **kwargs)
    def write(self, data) :
        if len(data) != len(self.chan) :
            raise sngAioError,  "data length %d != the number of channels (%d)" % (len(data), len(self.chan))
        for i in range(len(self.chan)) :
            self.write_chan_index(i, data[i])

def _test_ao_obj() :
    ao = AO()
    ao.write([0,0])
    ao.write([3000,3000])
    ao.write([0,0])
    ao.close()
    print "ao success"

def _fit_with_residual(out_data, in_data, channel) :
    "Fit in_data(out_data) to a straight line & return residual"
    from scipy.stats import linregress
    gradient, intercept, r_value, p_value, std_err = linregress(out_data, in_data)
    print "y = %g + %g x" % (intercept, gradient)
    print "r = ", r_value # correlation coefficient = covariance / (std_dev_x*std_dev_y)
    print "p = ", p_value # probablility of measuring this ?slope? for non-correlated, normally-distruibuted data
    print "err = ", std_err # root mean sqared error of best fit
    if gradient < .7 or p_value > 0.05 :
        raise sngAioError, "Out channel %d != in channel %d" % (channel, channel)
    residual = zeros((points,))
    for i in range(points) :
        pred_y = intercept + gradient * out_data[i]
        residual[i] = in_data[i] - pred_y
    return residual

def plot_data(out_data0, in_data0, residual0, out_data1, in_data1, residual1) :
    try :
        from pylab import plot, show, subplot
        subplot(311)
        plot(out_data0, in_data0, 'r.-', out_data1, in_data1, 'b.')
        subplot(312)
        plot(out_data0, residual0, 'r.', residual1, 'b.')
        subplot(313)
        plot(in_data0, 'r.', out_data1, 'b.')
        show() # if interactive mode is off...
        #raw_input("Press enter to continue") # otherwise, pause
    except ImportError :
        pass # ignore plot erros

def _test_aio() :
    "Test AO and AI by cabling AO0 into AI0 and sweeping voltage"
    from scipy.stats import linregress
    from numpy import linspace, zeros
    ao = ao_obj(chan=(0,1))
    ai = ai_obj(chan=(0,1))
    start = 0.1 * ao.maxdata[0]
    stop = 0.9 * ao.maxdata[0]
    points = 10
    out_data0 = linspace(start, stop, points)
    out_data1 = linspace(stop, start, points)
    in_data0 = zeros((points,))
    in_data1 = zeros((points,))
    for i in range(points) :
        ao.write([out_data0[i], out_data1[i]])
        id = ai.read()
        in_data0[i] = id[0]
        in_data1[i] = id[1]
    ai.close()
    ao.close()
    residual0 = _fit_with_residual(out_data0, in_data0, 0)
    residual1 = _fit_with_residual(out_data1, in_data1, 1)
    if VERBOSE_DEBUG :
        plot_data(out_data0, in_data0, residual0, out_data1, in_data1, residual1)
    for i in range(points) :
        if abs(residual0[i]) > 10 : # HACK, hardcoded maximum nonlinearity
            raise Exception, "Input 0, point %d (x %d), y-value %d has excessive residual %d" % (i, out_data0[i], in_data0[i], residual0[i])
        if abs(residual1[i]) > 10 : # HACK, hardcoded maximum nonlinearity
            raise Exception, "Input 1, point %d (x %d), y-value %d has excessive residual %d" % (i, out_data1[i], in_data1[i], residual1[i])
    print "_test_aio success"

def test() :
    _test_ai_obj()
    _test_ao_obj()
    _test_aio()

if __name__ == "__main__" :
    test()
