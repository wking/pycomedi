# Use Comedi drivers for single-shot digital input/output
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
"""Use Comedi drivers for single-shot digital input/output

Being single-shot implementations, read/writes will be software timed,
so this module would not be a good choice if you need millisecond
resolution.  However, it does provide a simple and robust way to
generate/aquire signals at 1 second and greater timescales.
"""

import comedi as c
import common


class SngDioError (common.PycomediError):
    "Digital IO error"
    pass

class DIO_port (common.PyComediSingleIO) :
    def __init__(self, output=True, **kwargs) :
        """inputs:
          filename:  comedi device file for your device ["/dev/comedi0"].
          subdevice: the digital IO subdevice [-1 for autodetect]
          chan: an iterable of the channels you wish to control [(0,1,2,3)]
          aref: the analog references for these channels [(comedi.AREF_GROUND,)]
          range: the ranges for these channels [(0,)]
          output: whether to use the lines as output (vs input) (True)
        """
        common.PyComediSingleIO.__init__(self, devtype=c.COMEDI_SUBD_DIO, output=output, **kwargs)
        if self.output :
            self.set_to_output()
        else :
            self.set_to_input()
    def set_to_output(self) :
        "switch all the channels associated with this object to be outputs"
        for chan in self.chan :
            rc = c.comedi_dio_config(self.dev, self.subdev, chan, c.COMEDI_OUTPUT)
            if rc != 1 : # yes, comedi_dio_config returns 1 on success, -1 on failure, as of comedilib-0.8.1
                self._comedi.comedi_perror("comedi_dio_config")
                raise SngDioError, 'comedi_dio_config("%s", %d, %d, %d) returned %d' % (self.filename, self.subdev, chan, c.COMEDI_OUTPUT, rc)
        self.output = True
    def set_to_input(self) :
        "switch all the channels associated with this object to be inputs"
        for chan in self.chan :
            rc = c.comedi_dio_config(self.dev, self.subdev, chan, c.COMEDI_INPUT)
            if rc != 1 :
                self._comedi.comedi_perror("comedi_dio_config")
                raise SngDioError, 'comedi_dio_config("%s", %d, %d, %d) returned %d' % (self.filename, self.subdev, chan, c.COMEDI_INPUT, rc)
        self.output = False
    def write_port(self, data) :
        """inputs:
          data: decimal number representing data to write
        For example, setting data=6 will write
          0 to chan[0]
          1 to chan[1]
          1 to chan[2]
          0 to higher channels...
        """
        for i in range(self.nchan) :
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
        for i in range(self.nchan) :
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
    d.close()

def _test_DO_port() :
    p = DO_port()
    for data in [0, 1, 2, 3, 4, 5, 6, 7] :
        p(data)
    p.close()
    print "write_dig_port success"

def test() :
    _test_DIO_port()
    _test_DO_port()

if __name__ == "__main__" :
    test()
