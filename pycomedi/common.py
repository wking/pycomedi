"""Some Comedi operations common to analog and digital IO"""

import comedi as c

VERSION = 0.1

class pycomediError (Exception) :
    "Error in pycomedi.common"
    pass

def _expand_tuple(tup, length) : 
    "Expand an iterable TUP to a tuple of LENGTH by repeating the last element"
    if len(tup) > length :
        raise simAioError, "Tuple too long."
    elif len(tup) < length :
        temp_tup = tup + tuple((tup[-1],)*(length-len(tup)))
        tup = temp_tup
    return tup

class PyComediIO (object) :
    "Base class for Comedi IO operations"
    def __init__(self, filename="/dev/comedi0", subdevice=-1, devtype=c.COMEDI_SUBD_AI, chan=(0,1,2,3), aref=(c.AREF_GROUND,), range=(0,), output=False, dev=None) :
        """inputs:
          filename:  comedi device file for your device ["/dev/comedi0"].
          subdevice: the IO subdevice [-1 for autodetect]
          devtype: the device type [c.COMEDI_SUBD_AI]
            values include
              comedi.COMEDI_SUBD_DI
              comedi.COMEDI_SUBD_DO
              comedi.COMEDI_SUBD_DIO
              comedi.COMEDI_SUBD_AI
              comedi.COMEDI_SUBD_AO
          chan: an iterable of the channels you wish to control [(0,1,2,3)]
          aref: the analog references for these channels [(comedi.AREF_GROUND,)]
            values include
              comedi.AREF_GROUND
              comedi.AREF_COMMON
              comedi.AREF_DIFF
              comedi.AREF_OTHER
          range: the ranges for these channels [(0,)]
          output: whether to use the lines as output (vs input) (False)
          dev: if you've already opened the device file, pass in the
               open device (None for internal open)
        Note that neither aref nor range need to be the same length as
        the channel tuple.  If they are shorter, their last entry will
        be repeated as needed.  If they are longer, pycomediError will
        be raised (was: their extra entries will not be used).
        """
        self.verbose = False
        self._comedi = c # keep a local copy around
        # sometimes I got errors on exitting python, which looked like
        # the imported comedi package was unset before my IO had a
        # chance to call comedi_close().  We avoid that by keeping a
        # local reference here.
        self.filename = filename
        self.state = "Closed"
        if dev == None :
            self.open()
        else :
            self.fakeOpen(dev)
        self._setup_device_type(subdevice, devtype)
        self._setup_channels(chan, aref, range)
        self.output = output
    def __del__(self) :
        self.close()
    def open(self) :
        if self.state == "Closed" :
            dev = self._comedi.comedi_open(self.filename)
            if dev < 0 :
                self._comedi.comedi_perror("comedi_open")
                raise pycomediError, "Cannot open %s" % self.filename
            self.fakeOpen(dev)
    def fakeOpen(self, dev):
        """fake open: if you open the comedi device file yourself, use this
        method to pass in the opened file descriptor and declare the
        port "Open".
        """
        if dev < 0 :
            raise pycomediError, "Invalid file descriptor %d" % dev
        self.dev = dev
        self.state = "Open"
    def close(self) :
        if self.state != "Closed" :
            rc = self._comedi.comedi_close(self.dev)
            if rc < 0 :
                self._comedi.comedi_perror("comedi_close")
                raise pycomediError, "Cannot close %s" % self.filename
            self.fakeClose()
    def fakeClose(self):
        """fake close: if you want to close the comedi device file yourself,
        use this method to let the port know it has been "Closed".
        """
        self.dev = None
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
            self.subdev = self._comedi.comedi_find_subdevice_by_type(self.dev, self._devtype, 0) # 0 is starting subdevice
            if self.subdev < 0 :
                self._comedi.comedi_perror("comedi_find_subdevice_by_type")
                raise pycomediError, "Could not find a %d device" % (self._devtype)
        else :
            self.subdev = subdevice
            type = self._comedi.comedi_get_subdevice_type(self.dev, self.subdev)
            if type != self._devtype :
                if type < 0 :
                    self._comedi.comedi_perror("comedi_get_subdevice_type")
                raise pycomediError, "Comedi subdevice %d has wrong type %d" % (self.subdev, type)
    def _setup_channels(self, chan, aref, rng) :
        """check that the specified channels exists, and that the arefs and
        ranges are legal for those channels.  Also allocate a range
        item for each channel, to allow converting between physical
        units and comedi units even when the device is not open.
        inputs:
          chan: an iterable of the channels you wish to control [(0,1,2,3)]
          aref: the analog references for these channels [(comedi.AREF_GROUND,)]
            values include
              comedi.AREF_GROUND
              comedi.AREF_COMMON
              comedi.AREF_DIFF
              comedi.AREF_OTHER
          rng: the ranges for these channels [(0,)]
        Note that neither aref nor rng need to be the same length as
        the channel tuple.  If they are shorter, their last entry will
        be repeated as needed.  If they are longer, pycomediError will
        be raised (was: their extra entries will not be used).
        """
        self.chan = chan
        self.nchan = len(self.chan)
        self._aref = _expand_tuple(aref, self.nchan)
        self._range = _expand_tuple(rng, self.nchan)
        self.maxdata = []
        self._comedi_range = []
        subdev_n_chan = self._comedi.comedi_get_n_channels(self.dev, self.subdev)
        self.cr_chan = self._comedi.chanlist(self.nchan)
        for i,chan,aref,rng in zip(range(self.nchan), self.chan, self._aref, self._range) :
            if int(chan) != chan :
                raise pycomediError, "Channels must be integers, not %s" % str(chan)
            if chan >= subdev_n_chan :
                raise pycomediError, "Channel %d > subdevice %d's largest chan %d" % (chan, self.subdev, subdev_n_chan-1)
            n_range = self._comedi.comedi_get_n_ranges(self.dev, self.subdev, chan)
            if rng > n_range :
                raise pycomediError, "Range %d > subdevice %d, chan %d's largest range %d" % (rng, subdev, chan, n_range-1)
            maxdata = self._comedi.comedi_get_maxdata(self.dev, self.subdev, chan)
            self.maxdata.append(maxdata)
            comrange = self._comedi.comedi_get_range(self.dev, self.subdev, chan, rng)
            # comrange becomes invalid if device is closed, so make a copy...
            comrange_copy = self._comedi.comedi_range()
            comrange_copy.min = comrange.min
            comrange_copy.max = comrange.max
            comrange_copy.unit = comrange.unit
            self._comedi_range.append(comrange_copy)
            self.cr_chan[i] = self._comedi.cr_pack(chan, rng, aref)
    def comedi_to_phys(self, chan_index, comedi) :
        phys = self._comedi.comedi_to_phys(comedi, self._comedi_range[chan_index], self.maxdata[chan_index])
        if self.verbose : 
            print "comedi %d = %g Volts on subdev %d, chan %d, range [%g, %g], max %d" % (comedi, phys, self.subdev, self.chan[chan_index], self._comedi_range[chan_index].max, self._comedi_range[chan_index].min, self.maxdata[chan_index])
        return phys
    def phys_to_comedi(self, chan_index, phys) :
        comedi = self._comedi.comedi_from_phys(phys, self._comedi_range[chan_index], self.maxdata[chan_index])
        if self.verbose : 
            print "%g Volts = comedi %d on subdev %d, chan %d, range [%g, %g], max %d" % (phys, comedi, self.subdev, self.chan[chan_index], self._comedi_range[chan_index].max, self._comedi_range[chan_index].min, self.maxdata[chan_index])
        return comedi

class PyComediSingleIO (PyComediIO) :
    "Software timed single-point input/ouput"
    def __init__(self, **kwargs) :
        """inputs:
          filename:  comedi device file for your device ["/dev/comedi0"].
          subdevice: the analog output subdevice [-1 for autodetect]
          devtype: the device type [c.COMEDI_SUBD_AI]
            values include
              comedi.COMEDI_SUBD_DI
              comedi.COMEDI_SUBD_DO
              comedi.COMEDI_SUBD_DIO
              comedi.COMEDI_SUBD_AI
              comedi.COMEDI_SUBD_AO
          chan: an iterable of the channels you wish to control [(0,1,2,3)]
          aref: the analog references for these channels [(comedi.AREF_GROUND,)]
            values include
              comedi.AREF_GROUND
              comedi.AREF_COMMON
              comedi.AREF_DIFF
              comedi.AREF_OTHER
          range: the ranges for these channels [(0,)]
          output: whether to use the lines as output (vs input) (False)
          dev: if you've already opened the device file, pass in the
               open device (None for internal open)
        Note that neither aref nor range need to be the same length as
        the channel tuple.  If they are shorter, their last entry will
        be repeated as needed.  If they are longer, pycomediError will
        be raised (was: their extra entries will not be used).
        """
        PyComediIO.__init__(self, **kwargs)
    def write_chan_index(self, chan_index, data) :
        """inputs:
          chan_index: the channel you wish to write to
          data: the value you wish to write to that channel
        """
        if self.output != True :
            raise pycomediError, "Must be an output to write"
        rc = c.comedi_data_write(self.dev, self.subdev, self.chan[chan_index], self._range[chan_index], self._aref[chan_index], data);
        if rc != 1 : # the number of samples written
            self._comedi.comedi_perror("comedi_data_write")
            raise pycomediError, "comedi_data_write returned %d" % rc
    def read_chan_index(self, chan_index) :
        """inputs:
          chan_index: the channel you wish to read from
        outputs:
          data: the value read from that channel
        """
        if self.output != False :
            raise pycomediError, "Must be an input to read"
        rc, data = c.comedi_data_read(self.dev, self.subdev, self.chan[chan_index], self._range[chan_index], self._aref[chan_index]);
        if rc != 1 : # the number of samples read
            self._comedi.comedi_perror("comedi_data_read")
            raise pycomediError, "comedi_data_read returned %d" % rc
        return data

