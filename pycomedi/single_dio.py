"""Use Comedi drivers for single-shot digital input/output

Being single-shot implementations, read/writes will be software timed,
so this module would not be a good choice if you need millisecond
resolution.  However, it does provide a simple and robust way to
generate/aquire signals at 1 second and greater timescales.
"""

import comedi as c

VERSION = 0.0

class dioError (Exception) :
    "Digital IO error"
    pass

class dio_obj :
    def __init__(self, filename="/dev/comedi0", subdevice=2, chan=(0,1,2,3), aref=0, range=0, output=True) :
        self.filename = filename
        self.subdev = subdevice
        self.chan = chan
        self.aref = aref
        self.range = range
        self.output = output
        self.dev = c.comedi_open(filename)
        if self.dev < 0 :
            raise dioError, "Cannot open %s" % self.filename
        type = c.comedi_get_subdevice_type(self.dev, self.subdev)
        if type != c.COMEDI_SUBD_DIO :
            raise dioError, "Comedi subdevice %d has wrong type %d" % (self.subdev, type)
        if self.output :
            self.set_to_output()
        else :
            self.set_to_input()
    def set_to_output(self) :
        for chan in self.chan :
            rc = c.comedi_dio_config(self.dev, self.subdev, chan, c.COMEDI_OUTPUT)
            if rc != 1 : # yes, comedi_dio_config returns 1 on success, -1 on failure, as of comedilib-0.8.1
                raise dioError, 'comedi_dio_config("%s", %d, %d, %d) returned %d' % (self.filename, self.subdev, chan, c.COMEDI_OUTPUT, rc)
        self.output = True
    def set_to_input(self) :
        for chan in self.chan :
            rc = c.comedi_dio_config(self.dev, self.subdev, chan, c.COMEDI_INPUT)
            if rc != 1 :
                raise dioError, 'comedi_dio_config("%s", %d, %d, %d) returned %d' % (self.filename, self.subdev, chan, c.COMEDI_INPUT, rc)
        self.output = False
    def write_chan_index(self, chan_index, data) :
        if self.output != True :
            raise dioError, "Must be an output to write"
        rc = c.comedi_data_write(self.dev, self.subdev, self.chan[chan_index], self.range, self.aref, data);
        if rc != 1 : # the number of samples written
            raise dioError, "comedi_data_write returned %d" % rc
    def read_chan_index(self, chan_index) :
        if self.output == True :
            raise dioError, "Must be an input to read"
        rc, data = c.comedi_data_read(self.dev, self.subdev, self.chan[chan_index], self.range, self.aref);
        if rc != 1 : # the number of samples read
            raise dioError, "comedi_data_read returned %d" % rc
        return data
    def write_port(self, data) :
        "Channel significance increases with array index"
        for i in range(len(self.chan)) :
            self.write_chan_index(i, (data >> i) % 2)
    def read_port(self) :
        data = 0
        for i in range(len(self.chan)) :
            data += self.read_chan_index(i) << i
        return data

class write_dig_port (dio_obj) :
    def __call__(self, data) :
        self.write_port(data)

def _test_dio_obj() :
    d = dio_obj()
    d.set_to_output()
    d.write_chan_index(0, 1)
    d.write_chan_index(0, 0)
    d.write_port(7)
    d.set_to_input()
    data = d.read_chan_index(0)
    print "channel %d is %d" % (d.chan[0], data)
    data = d.read_port()
    print "port value is %d" % data
    print "dio_obj success"

def _test_write_dig_port() :
    p = write_dig_port()
    for data in [0, 1, 2, 3, 4, 5, 6, 7] :
        p(data)
    print "write_dig_port success"

def test() :
    _test_dio_obj()
    _test_write_dig_port()

if __name__ == "__main__" :
    test()
