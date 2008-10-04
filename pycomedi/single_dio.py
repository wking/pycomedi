"""Use Comedi drivers for single-shot digital input/output

Being single-shot implementations, read/writes will be software timed,
so this module would not be a good choice if you need millisecond
resolution.  However, it does provide a simple and robust way to
generate/aquire signals at 1 second and greater timescales.
"""

import comedi as c

VERSION = 0.1

class dioError (Exception) :
    "Digital IO error"
    pass

class DIO_port :
    def __init__(self, filename="/dev/comedi0", subdevice=2, chan=(0,1,2,3), aref=0, range=0, output=True) :
        """inputs:
          filename:  comedi device file for your device ("/dev/comedi0").
          subdevice: the digital IO subdevice (2)
          chan: an iterable of the channels you wish to control ((0,1,2,3))
          aref: the analog reference for these channels (0)
          range: the range for these channels (0)
          output: whether to use the lines as output (vs input) (True)
        """
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
        "switch all the channels associated with this object to be outputs"
        for chan in self.chan :
            rc = c.comedi_dio_config(self.dev, self.subdev, chan, c.COMEDI_OUTPUT)
            if rc != 1 : # yes, comedi_dio_config returns 1 on success, -1 on failure, as of comedilib-0.8.1
                raise dioError, 'comedi_dio_config("%s", %d, %d, %d) returned %d' % (self.filename, self.subdev, chan, c.COMEDI_OUTPUT, rc)
        self.output = True
    def set_to_input(self) :
        "switch all the channels associated with this object to be inputs"
        for chan in self.chan :
            rc = c.comedi_dio_config(self.dev, self.subdev, chan, c.COMEDI_INPUT)
            if rc != 1 :
                raise dioError, 'comedi_dio_config("%s", %d, %d, %d) returned %d' % (self.filename, self.subdev, chan, c.COMEDI_INPUT, rc)
        self.output = False
    def write_chan_index(self, chan_index, data) :
        """inputs:
          chan_index: the channel you wish to write to
          data: the value you wish to write to that channel
        """
        if self.output != True :
            raise dioError, "Must be an output to write"
        rc = c.comedi_data_write(self.dev, self.subdev, self.chan[chan_index], self.range, self.aref, data);
        if rc != 1 : # the number of samples written
            raise dioError, "comedi_data_write returned %d" % rc
    def read_chan_index(self, chan_index) :
        """inputs:
          chan_index: the channel you wish to read from
        outputs:
          data: the value read from that channel
        """
        if self.output == True :
            raise dioError, "Must be an input to read"
        rc, data = c.comedi_data_read(self.dev, self.subdev, self.chan[chan_index], self.range, self.aref);
        if rc != 1 : # the number of samples read
            raise dioError, "comedi_data_read returned %d" % rc
        return data
    def write_port(self, data) :
        """inputs:
          data: decimal number representing data to write
        For example, setting data=6 will write
          0 to chan[0]
          1 to chan[1]
          1 to chan[2]
          0 to higher channels...
        """
        for i in range(len(self.chan)) :
            self.write_chan_index(i, (data >> i) % 2)
    def read_port(self) :
        """outputs:
          data: decimal number representing data read
        For example, data=6 represents
          0 on chan[0]
          1 on chan[1]
          1 on chan[2]
          0 on higher channels...
        """
        data = 0
        for i in range(len(self.chan)) :
            data += self.read_chan_index(i) << i
        return data

class DO_port (DIO_port) :
    "A simple wrapper on dio_obj to make writing easier"
    def __call__(self, data) :
        self.write_port(data)

def _test_DIO_port() :
    d = DIO_port()
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

def _test_DO_port() :
    p = DO_port
    for data in [0, 1, 2, 3, 4, 5, 6, 7] :
        p(data)
    print "write_dig_port success"

def test() :
    _test_DIO_port()
    _test_DO_port()

if __name__ == "__main__" :
    test()
