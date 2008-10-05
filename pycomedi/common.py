"""Some Comedi operations common to analog and digital IO"""

import comedi as c

VERSION = 0.1

class pycomediError (Exception) :
    "Error in pycomedi.common"
    pass

class PyComediIO (object) :
    "Base class for Comedi IO operations"
    def __init__(self, filename="/dev/comedi0", subdevice=-1, devtype=c.COMEDI_SUBD_AI, chan=(0,1,2,3), aref=c.AREF_GROUND, range=0, output=False) :
        """inputs:
          filename:  comedi device file for your device ("/dev/comedi0").
          subdevice: the analog output subdevice (-1 for autodetect)
          devtype: the devoce type (c.COMEDI_SUBD_AI)
            values include
              comedi.COMEDI_SUBD_DI
              comedi.COMEDI_SUBD_DO
              comedi.COMEDI_SUBD_DIO
              comedi.COMEDI_SUBD_AI
              comedi.COMEDI_SUBD_AO
          chan: an iterable of the channels you wish to control ((0,1,2,3))
          aref: the analog reference for these channels (comedi.AREF_GROUND)
            values include
              comedi.AREF_GROUND
              comedi.AREF_COMMON
              comedi.AREF_DIFF
              comedi.AREF_OTHER
          range: the range for these channels (0)
          output: whether to use the lines as output (vs input) (False)
        """
        self.verbose = False
        self._comedi = c # keep a local copy around
        # sometimes I got errors on exitting python, which looked like
        # the imported comedi package was unset before my IO had a
        # chance to call comedi_close().  We avoid that by keeping a
        # local reference here.
        self.filename = filename
        self.state = "Closed"
        self.open()
        self._setup_device_type(subdevice, devtype)
        self._setup_channels(chan, aref, range)
        self._output = output
    def __del__(self) :
        self.close()
    def open(self) :
        if self.state == "Closed" :
            self._dev = self._comedi.comedi_open(self.filename)
            if self.dev < 0 :
                self._comedi.comedi_perror("comedi_open")
                raise pycomediError, "Cannot open %s" % self.filename
            self.state = "Opened"
    def close(self) :
        if self.state != "Closed" :
            rc = self._comedi.comedi_close(self._dev)
            if rc < 0 :
                self._comedi.comedi_perror("comedi_close")
                raise pycomediError, "Cannot close %s" % self.filename
            self.state = "Closed"
    def _setup_device_type(self, subdevice, devtype) :
        """check that the specified subdevice exists,
        searching for an appropriate subdevice if subdevice == -1
        inputs:
          subdevice: the analog output subdevice (-1 for autodetect)
          devtype: the devoce type
            values include
              comedi.COMEDI_SUBD_DI
              comedi.COMEDI_SUBD_DO
              comedi.COMEDI_SUBD_DIO
              comedi.COMEDI_SUBD_AI
              comedi.COMEDI_SUBD_AO
        """
        self._devtype = devtype
        if (subdevice < 0) : # autodetect an output device
            self._subdev = self._comedi.comedi_find_subdevice_by_type(self._dev, self._devtype, 0) # 0 is starting subdevice
            if self._subdev < 0 :
                self._comedi.comedi_perror("comedi_find_subdevice_by_type")
                raise pycomediError, "Could not find a %d device" % (self._devtype)
        else :
            self._subdev = subdevice
            type = self._comedi.comedi_get_subdevice_type(self._dev, self._subdev)
            if type != self._devtype :
                if type < 0 :
                    self._comedi.comedi_perror("comedi_get_subdevice_type")
                raise pycomediError, "Comedi subdevice %d has wrong type %d" % (self._subdev, type)
    def _setup_channels(self, chan, aref, range) :
        """check that the specified channels exists, and that the arefs and
        ranges are legal for those channels.  Also allocate a range
        item for each channel, to allow converting between physical
        units and comedi units even when the device is not open.
        inputs:
          chan: an iterable of the channels you wish to control ((0,1,2,3))
          aref: the analog reference for these channels (comedi.AREF_GROUND)
            values include
              comedi.AREF_GROUND
              comedi.AREF_COMMON
              comedi.AREF_DIFF
              comedi.AREF_OTHER
          range: the range for these channels (0)
        """
        self._chan = chan
        self._aref = aref
        self._range = range
        subdev_n_chan = self._comedi.comedi_get_n_channels(self._dev, self._subdev)
        self._maxdata = []
        self._comedi_range = []
        for chan in self._chan :
            if int(chan) != chan :
                raise pycomediError, "Channels must be integers, not %s" % str(chan)
            if chan >= subdev_n_chan :
                raise pycomediError, "Channel %d > subdevice %d's largest chan %d" % (chan, self._subdev, subdev_n_chan-1)
            n_range = self._comedi.comedi_get_n_ranges(self._dev, self._subdev, chan)
            if range > n_range :
                raise pycomediError, "Range %d > subdevice %d, chan %d's largest range %d" % (range, subdev, chan, n_range-1)
            maxdata = self._comedi.comedi_get_maxdata(self._dev, self._subdev, chan)
            self._maxdata.append(maxdata)
            comrange = self._comedi.comedi_get_range(self._dev, self._subdev, chan, range)
            # comrange becomes invalid if device is closed, so make a copy...
            comrange_copy = self._comedi.comedi_range()
            comrange_copy.min = comrange.min
            comrange_copy.max = comrange.max
            comrange_copy.unit = comrange.unit
            self._comedi_range.append(comrange_copy)
    def comedi_to_phys(self, chan_index, comedi) :
        phys = self._comedi.comedi_to_phys(comedi, self._comedi_range[chan_index], self._maxdata[chan_index])
        if self.verbose : 
            print "comedi %d = %g Volts on subdev %d, chan %d, range [%g, %g], max %d" % (comedi, phys, self._subdev, self._chan[chan_index], self._comedi_range[chan_index].max, self._comedi_range[chan_index].min, self._maxdata[chan_index])
        return phys
    def phys_to_comedi(self, chan_index, phys) :
        comedi = self._comedi.comedi_from_phys(phys, self._comedi_range[chan_index], self._maxdata[chan_index])
        if self.verbose : 
            print "%g Volts = comedi %d on subdev %d, chan %d, range [%g, %g], max %d" % (phys, comedi, self._subdev, self._chan[chan_index], self._comedi_range[chan_index].max, self._comedi_range[chan_index].min, self._maxdata[chan_index])
        return comedi

class PyComediSingleIO (PyComediIO) :
    "Software timed single-point input/ouput"
    def __init__(self, **kwargs) :
        """inputs:
          filename:  comedi device file for your device ("/dev/comedi0").
          subdevice: the digital IO subdevice (-1 for autodetect)
          devtype: the devoce type
            values include
              comedi.COMEDI_SUBD_DI
              comedi.COMEDI_SUBD_DO
              comedi.COMEDI_SUBD_DIO
              comedi.COMEDI_SUBD_AI
              comedi.COMEDI_SUBD_AO
          chan: an iterable of the channels you wish to control ((0,1,2,3))
          aref: the analog reference for these channels (comedi.AREF_GROUND)
            values include
              comedi.AREF_GROUND
              comedi.AREF_COMMON
              comedi.AREF_DIFF
              comedi.AREF_OTHER
          range: the range for these channels (0)
        """
        common.PyComediIO.__init__(self, **kwargs)
    def write_chan_index(self, chan_index, data) :
        """inputs:
          chan_index: the channel you wish to write to
          data: the value you wish to write to that channel
        """
        if self._output != True :
            raise pycomediError, "Must be an output to write"
        rc = c.comedi_data_write(self.dev, self.subdev, self.chan[chan_index], self.range, self.aref, data);
        if rc != 1 : # the number of samples written
            self._comedi.comedi_perror("comedi_data_write")
            raise pycomediError, "comedi_data_write returned %d" % rc
    def read_chan_index(self, chan_index) :
        """inputs:
          chan_index: the channel you wish to read from
        outputs:
          data: the value read from that channel
        """
        if self._output == True :
            raise pycomediError, "Must be an input to read"
        rc, data = c.comedi_data_read(self.dev, self.subdev, self.chan[chan_index], self.range, self.aref);
        if rc != 1 : # the number of samples read
            self._comedi.comedi_perror("comedi_data_read")
            raise pycomediError, "comedi_data_read returned %d" % rc
        return data

