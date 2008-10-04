# Use Comedi drivers for single-shot analog input/output

import comedi

VERSION = 0.0
VERBOSE_DEBUG = True

class sngAioError (Exception) :
    "Single point Analog IO error"
    pass

class ai_obj :
    def __init__(self, filename="/dev/comedi0", subdevice=-1, chan=(0,1,2,3), aref=0, range=0) :
        self.verbose = False
        self.comedi = comedi
        self.filename = filename
        self.state = "Closed"
        self.open()
        if (subdevice < 0) : # autodetect an output device
            self.subdev = self.comedi.comedi_find_subdevice_by_type(self.dev, self.comedi.COMEDI_SUBD_AI, 0) # 0 is starting subdevice
        else :
            self.subdev = subdevice
            type = self.comedi.comedi_get_subdevice_type(self.dev, self.subdev)
            if type != self.comedi.COMEDI_SUBD_AI :
                raise sngAioError, "Comedi subdevice %d has wrong type %d" % (self.subdev, type)
        self.chan = chan
        self.aref = aref
        self.range = range
        subdev_n_chan = self.comedi.comedi_get_n_channels(self.dev, self.subdev)
        self.maxdata = []
        self.comedi_range = []
        for chan in self.chan :
            if int(chan) != chan :
                raise sngAioError, "Channels must be integers, not %s" % str(chan)
            if chan >= subdev_n_chan :
                raise sngAioError, "Channel %d > subdevice %d's largest chan %d" % (chan, self.subdev, subdev_n_chan-1)
            n_range = self.comedi.comedi_get_n_ranges(self.dev, self.subdev, chan)
            if range > n_range :
                raise sngAioError, "Range %d > subdevice %d, chan %d's largest range %d" % (range, subdev, chan, n_range-1)
            maxdata = self.comedi.comedi_get_maxdata(self.dev, self.subdev, chan)
            self.maxdata.append(maxdata)
            comrange = self.comedi.comedi_get_range(self.dev, self.subdev, chan, range)
            # comrange becomes invalid if device is closed, so make a copy...
            comrange_copy = self.comedi.comedi_range()
            comrange_copy.min = comrange.min
            comrange_copy.max = comrange.max
            comrange_copy.unit = comrange.unit
            self.comedi_range.append(comrange_copy)
    def __del__(self) :
        self.close()
    def open(self) :
        if self.state == "Closed" :
            self.dev = self.comedi.comedi_open(self.filename)
            self.state = "Opened"
    def close(self) :
        if self.state != "Closed" :
            rc = self.comedi.comedi_close(self.dev)
            if rc < 0 :
                self.comedi.comedi_perror("comedi_close")
                raise sngAioError, "Cannot close %s" % self.filename
            self.state = "Closed"
    def comedi_to_phys(self, chan_index, comedi) :
        phys = self.comedi.comedi_to_phys(comedi, self.comedi_range[chan_index], self.maxdata[chan_index])
        if self.verbose : 
            print "comedi %d = %g Volts on subdev %d, chan %d, range [%g, %g], max %d" % (comedi, phys, self.subdev, self.chan[chan_index], self.comedi_range[chan_index].max, self.comedi_range[chan_index].min, self.maxdata[chan_index])
        return phys
    def phys_to_comedi(self, chan_index, phys) :
        comedi = self.comedi.comedi_from_phys(phys, self.comedi_range[chan_index], self.maxdata[chan_index])
        if self.verbose : 
            print "%g Volts = comedi %d on subdev %d, chan %d, range [%g, %g], max %d" % (phys, comedi, self.subdev, self.chan[chan_index], self.comedi_range[chan_index].max, self.comedi_range[chan_index].min, self.maxdata[chan_index])
        return comedi
    def read_chan_index(self, chan_index) :
        rc, data = self.comedi.comedi_data_read(self.dev, self.subdev, self.chan[chan_index], self.range, self.aref);
        if rc != 1 : # the number of samples read
            raise sngAioError, "comedi_data_read returned %d" % rc
        return data
    def read(self) :
        out = range(len(self.chan))
        for i in range(len(self.chan)) :
            out[i] = self.read_chan_index(i)
        #print "Read %s, got %s" % (str(self.chan), str(out))
        return out

def _test_ai_obj() :
    ai = ai_obj()
    print "read ", ai.read()
    print "read ", ai.read()
    print "read ", ai.read()
    print "read ", ai.read()
    ai.close()
    print "ai success"

class ao_obj :
    def __init__(self, filename="/dev/comedi0", subdevice=-1, chan=(0,1), aref=0, range=0) :
        self.verbose = False
        self.comedi = comedi
        self.filename = filename
        self.state = "Closed"
        self.open()
        if (subdevice < 0) : # autodetect an output device
            self.subdev = self.comedi.comedi_find_subdevice_by_type(self.dev, self.comedi.COMEDI_SUBD_AO, 0) # 0 is starting subdevice
        else :
            self.subdev = subdevice
            type = self.comedi.comedi_get_subdevice_type(self.dev, self.subdev)
            if type != self.comedi.COMEDI_SUBD_AO :
                raise sngAioError, "Comedi subdevice %d has wrong type %d" % (self.subdev, type)
        self.chan = chan
        self.aref = aref
        self.range = range
        subdev_n_chan = self.comedi.comedi_get_n_channels(self.dev, self.subdev)
        self.maxdata = []
        self.comedi_range = []
        for chan in self.chan :
            if chan >= subdev_n_chan :
                raise sngAioError, "Channel %d > subdevice %d's largest chan %d" % (chan, self.subdev, subdev_n_chan-1)
            n_range = self.comedi.comedi_get_n_ranges(self.dev, self.subdev, chan)
            if range > n_range :
                raise sngAioError, "Range %d > subdevice %d, chan %d's largest range %d" % (range, subdev, chan, n_range-1)
            maxdata = self.comedi.comedi_get_maxdata(self.dev, self.subdev, chan)
            self.maxdata.append(maxdata)
            comrange = self.comedi.comedi_get_range(self.dev, self.subdev, chan, range)
            # comrange becomes invalid if device is closed, so make a copy...
            comrange_copy = self.comedi.comedi_range()
            comrange_copy.min = comrange.min
            comrange_copy.max = comrange.max
            comrange_copy.unit = comrange.unit
            self.comedi_range.append(comrange_copy)
    def __del__(self) :
        self.close()
    def open(self) :
        if self.state != "Closed" :
            raise sngAioError, "Invalid state %s" % self.state
        self.dev = self.comedi.comedi_open(self.filename)
        self.state = "Opened"
    def close(self) :
        if self.state != "Closed" :
            for i in range(len(self.chan)) : 
                self.write_chan_index(i, self.phys_to_comedi(i, 0))
            rc = self.comedi.comedi_close(self.dev)
            if rc < 0 :
                self.comedi.comedi_perror("comedi_close")
                raise sngAioError, "Cannot close %s" % self.filename
            self.state = "Closed"
    def comedi_to_phys(self, chan_index, comedi) :
        phys = self.comedi.comedi_to_phys(int(comedi), self.comedi_range[chan_index], self.maxdata[chan_index])
        if self.verbose : 
            print "comedi %d = %g Volts on subdev %d, chan %d, range [%g, %g], max %d" % (comedi, phys, self.subdev, self.chan[chan_index], self.comedi_range[chan_index].max, self.comedi_range[chan_index].min, self.maxdata[chan_index])
        return phys
    def phys_to_comedi(self, chan_index, phys) :
        comedi = self.comedi.comedi_from_phys(phys, self.comedi_range[chan_index], self.maxdata[chan_index])
        if self.verbose : 
            print "%g Volts = comedi %d on subdev %d, chan %d, range [%g, %g], max %d" % (phys, comedi, self.subdev, self.chan[chan_index], self.comedi_range[chan_index].max, self.comedi_range[chan_index].min, self.maxdata[chan_index])
        return comedi
    def write_chan_index(self, chan_index, data) :
        #print "set output on chan %d to %d" % (chan_index, data)
        rc = self.comedi.comedi_data_write(self.dev, self.subdev, self.chan[chan_index], self.range, self.aref, int(data));
        if rc != 1 : # the number of samples written
            raise sngAioError, 'comedi_data_write returned %d' % rc
    def write(self, data) :
        if len(data) != len(self.chan) :
            raise sngAioError,  "data length %d != the number of channels (%d)" % (len(data), len(self.chan))
        for i in range(len(self.chan)) :
            self.write_chan_index(i, data[i])

def _test_ao_obj() :
    ao = ao_obj()
    ao.write([0,0])
    ao.write([3000,3000])
    ao.write([0,0])
    ao.close()
    print "ao success"

def _fit_with_residual(out_data, in_data) :
    from scipy.stats import linregress
    gradient, intercept, r_value, p_value, std_err = linregress(out_data, in_data)
    print "y = %g + %g x" % (intercept, gradient)
    print "r = ", r_value # correlation coefficient = covariance / (std_dev_x*std_dev_y)
    print "p = ", p_value # probablility of measuring this ?slope? for non-correlated, normally-distruibuted data
    print "err = ", std_err # root mean sqared error of best fit
    if gradient < .7 or p_value > 0.05 :
        raise sngAioError, "Out channel 0 != in channel 0"
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
    residual0 = _fit_with_residual(out_data0, in_data0)
    residual1 = _fit_with_residual(out_data1, in_data1)
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
