# Simultaneous, finite, buffered analog inpout/output using comedi drivers
# Copyright (C) 2007,2008  W. Trevor King
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

import comedi as c
import common
from numpy import array, fromstring, float32, pi, sin
import int16_rw
import time

# imports for testing
from time import sleep
from scipy.stats import linregress
from os import system

VERSION = common.VERSION
#VERBOSE = True
VERBOSE = False
AO_TRIGGERS_OFF_AI_START = True
#AO_TRIGGERS_OFF_AI_START = False


# HACK! outputting last point can cause jumps to random positions
# This is probably due to some clocking issue when we trigger AO off of
# the AI Start signal.
DONT_OUTPUT_LAST_SAMPLE_HACK = True

class simAioError (Exception) :
    "Simultaneous Analog IO error"
    pass

_example_array = array([0], dtype=int16_rw.DATA_T) # for typing, since I don't know what type(array) should be

_cmdtest_message = ["success",
                     "invalid source",
                     "source conflict",
                     "invalid argument",
                     "argument conflict",
                     "invalid chanlist"]

class cmd (object) :
    """Wrap a comedi command in more Pythonic trappings.

    Due to my limited needs, this class currently only supports
    software triggered runs (possibly with output triggering off the
    input trigger) for a finite number of output samples where all of
    the scan and sample timing is internal and as fast as possible.

    See http://www.comedi.org/doc/x621.html#COMEDICMDSTRUCTURE
    for more details/possibilities.
    """
    def __init__(self, IO) :
        """input:
          IO : an initialized common.PyComediIO object
        """
        self.IO = IO
        if self.IO.output == True :
            self.cmdTypeString = "output"
        else :
            self.cmdTypeString = "input"
        self.generate_rough_command()
    def generate_rough_command(self) :
        if VERBOSE :
            print "generate rough %s command" % self.cmdTypeString
        cmd = self.IO._comedi.comedi_cmd_struct()
        cmd.subdev = self.IO.subdev
        if self.IO.output :
            cmd.flags = self.IO._comedi.CMDF_WRITE
        else :
            cmd.flags = 0
        # decide how to trigger a multi-scan run
        if self.IO.output and AO_TRIGGERS_OFF_AI_START :
            cmd.start_src = self.IO._comedi.TRIG_EXT
            cmd.start_arg = 18 # AI_START1 internal AI start signal
        else :
            cmd.start_src = self.IO._comedi.TRIG_INT
            cmd.start_arg = 0
        # decide how to trigger a multi-channel scan
        cmd.scan_begin_src = self.IO._comedi.TRIG_TIMER
        cmd.scan_begin_arg = 1 # temporary value for now
        # decide how to trigger a single channel's aquisition
        if self.IO.output : 
            cmd.convert_src = self.IO._comedi.TRIG_NOW # convert simultaneously (each output has it's own DAC)
            cmd.convert_arg = 0
        else :
            cmd.convert_src = self.IO._comedi.TRIG_TIMER # convert sequentially (all inputs share single ADC)
            cmd.convert_arg = 1 # time between channels in ns, 1 to convert ASAP
        # decide when a scan is complete
        cmd.scan_end_src = self.IO._comedi.TRIG_COUNT
        cmd.scan_end_arg = self.IO.nchan
        cmd.stop_src = self.IO._comedi.TRIG_COUNT
        cmd.stop_arg = 1 # temporary value for now
        cmd.chanlist = self.IO.cr_chan
        cmd.chanlist_len = self.IO.nchan
        self.cmd = cmd
        self.test_cmd(max_passes=3)
    def test_cmd(self, max_passes=1) :
        very_verbose = False
        i = 0
        rc = 0
        if  very_verbose : 
            print "Testing command:"
            print self
        while i < max_passes :
            rc = self.IO._comedi.comedi_command_test(self.IO.dev, self.cmd)
            if (rc == 0) :
                break
            if VERBOSE or very_verbose :
                print "test pass %d, %s" % (i, _cmdtest_message[rc])
            i += 1
        if (VERBOSE or very_verbose) and i < max_passes :
            print "Passing command:\n", self
        if i >= max_passes :
            print "Failing command (%d):\n" % rc, self
            raise simAioError, "Invalid command: %s" % _cmdtest_message[rc]
    def execute(self) :
        if VERBOSE :
            print "Loading %s command" % self.cmdTypeString
        rc = self.IO._comedi.comedi_command(self.IO.dev, self.cmd)
        if rc < 0 :
            self.IO._comedi.comedi_perror("comedi_command")
            raise simAioError, "Error executing %s command %d" % (self.cmdTypeString, rc)
    def _cmdsrc(self, source) :
        str = ""
        if source & c.TRIG_NONE   : str += "none|"
        if source & c.TRIG_NOW    : str += "now|"
        if source & c.TRIG_FOLLOW : str += "follow|"
        if source & c.TRIG_TIME   : str += "time|"
        if source & c.TRIG_TIMER  : str += "timer|"
        if source & c.TRIG_COUNT  : str += "count|"
        if source & c.TRIG_EXT    : str += "ext|"
        if source & c.TRIG_INT    : str += "int|"
        if source & c.TRIG_OTHER  : str += "other|"
        return str
    def __str__(self) :
        str = "Command on %s (%s):\n" % (self.IO, self.cmdTypeString)
        str += "subdevice: \t%d\n" % self.cmd.subdev
        str += "flags:     \t0x%x\n" % self.cmd.flags
        str += "start:     \t"
        str += self._cmdsrc(self.cmd.start_src)
        str += "\t%d\n" % self.cmd.start_arg
        str += "scan_begin:\t"
        str += self._cmdsrc(self.cmd.scan_begin_src)
        str += "\t%d\n" % self.cmd.scan_begin_arg
        str += "convert:   \t"
        str += self._cmdsrc(self.cmd.convert_src)
        str += "\t%d\n" % self.cmd.convert_arg
        str += "scan_end:  \t"
        str += self._cmdsrc(self.cmd.scan_end_src)
        str += "\t%d\n" % self.cmd.scan_end_arg
        str += "stop:      \t"
        str += self._cmdsrc(self.cmd.stop_src)
        str += "\t%d" % self.cmd.stop_arg
        return str

class AIO (object) :
    """Control a simultaneous analog input/output (AIO) device using
    Comedi drivers.
    
    The AIO device is modeled as being in one of the following states:

      Open         Device file has been opened, various one-off setup
                   tasks completed.
      Initialized  Any previous activity is complete, ready for a new
                   task
      Setup        New task assigned.
      Armed        The output task is "triggered" (see below)
      Read         The input task is triggered, and input read in
      Closed
    Transitions between these states may be achieved with class methods
      open, __init__ - through Open to Initialized
      close        Any to Closed
      setup        Initialized to Setup
      arm          Setup to Armed
      start_read   Armed to Read
      reset        Setup, Armed, or Read to Initialized

    There are two triggering methods set by the module global
      AO_TRIGGERS_OFF_AI_START
    When this global is true, the output and input will start on the
    exactly the same clock tick (in this case the output "trigger"
    when "Arming" just primes the output to start when the input start
    is signaled).  However, this functionality at the moment depends
    on your having a National Instruments card with a DAQ-STC module
    controling the timing (e.g. E series) and a patched version of
    ni_mio_common.c in your Comedi kernel.  If you do not have an
    appropriate card, you will either have to implement an appropriate
    method for your card, or set the global to false, in which case
    the IO synchronicity depends on the synchronicity of the AO and AI
    software triggers.
    """
    def __init__(self, filename="/dev/comedi0",
		 in_subdevice=-1, in_chan=(0,), in_aref=(0,), in_range=(0,),
		 out_subdevice=-1, out_chan=(0,), out_aref=(0,), out_range=(0,),
                 buffsize=32768) :
        """inputs:
          filename:  comedi device file for your device ("/dev/comedi0").
        And then for both input and output (in_* and out_*):
          subdevice: the analog output subdevice (-1 for autodetect)
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
        self._comedi = c
        self._filename = filename
        assert buffsize > 0
        assert buffsize % 2 == 0, "buffsize = %d is not even" % buffsize
        self.buffsize = buffsize
        # the next section is much like the open() method below,
        # but in this one we set up all the extra details associated
        # with the AO and AI structures
        self.dev = self._comedi.comedi_open(self._filename)
        self._fd = self._comedi.comedi_fileno(self.dev)
        if VERBOSE :
            print "Opened %s on fd %d" % (self._filename, self._fd)
        self.AI = common.PyComediIO(filename=self._filename, subdevice=in_subdevice, devtype=c.COMEDI_SUBD_AI, chan=in_chan, aref=in_aref, range=in_range, output=False, dev=self.dev)
        self.AO = common.PyComediIO(filename=self._filename, subdevice=out_subdevice, devtype=c.COMEDI_SUBD_AO, chan=out_chan, aref=out_aref, range=out_range, output=True, dev=self.dev)
        self.state = "Open"
        self._icmd = cmd(self.AI)
        self._ocmd = cmd(self.AO)
        self.state = "Initialized"
    def __del__(self) :
        self.close()
    def close(self) :
        if self.state != "Closed" :
            self.reset(force=True)
            rc = self._comedi.comedi_close(self.dev)
            if rc < 0 :
                self._comedi.comedi_perror("comedi_close")
                raise simAioError, "Cannot close %s" % self._filename
            if VERBOSE :
                print "Closed %s on fd %d" % (self._filename, self._fd)
            self.AI.fakeClose()
            self.AO.fakeClose()
            self.dev = None
            self._fd = None
            self.state = "Closed"
    def open(self) :
        if self.state != "Closed" :
            raise simAioError, "Invalid state %s" % self.state
        self.dev = self._comedi.comedi_open(self._filename)
        self._fd = self._comedi.comedi_fileno(self.dev)
        if VERBOSE :
            print "Opened %s on fd %d" % (self._filename, self._fd)
        self.AI.fakeOpen(self.dev)
        self.AO.fakeOpen(self.dev)
        self.state = "Open"
        self._icmd = cmd(self.AI)
        self._ocmd = cmd(self.AO)
        self.state = "Initialized"
    def genBuffer(self, nsamp, nchan=1, value=0) :
        return array([value]*nsamp*nchan, dtype=int16_rw.DATA_T)
    def setup(self, nsamps=None, freq=1.0, out_buffer=None) :
        if self.state != "Initialized" :
            raise simAioError, "Invalid state %s" % self.state
        if out_buffer == None : # read-only command
            assert self.AO == None
            assert nsamps > 1
        if nsamps == None :
            assert len(out_buffer) % self.AO.nchan == 0
            nsamps = int(len(out_buffer) / self.AO.nchan)
        if type(out_buffer) != type(_example_array) :
            raise simAioError, "out_buffer must be a numpy array, not a %s" % str(type(out_buffer))
        if DONT_OUTPUT_LAST_SAMPLE_HACK :
            for i in range(1, self.AO.nchan+1) : # i in [1, ... ,nchan]
                if out_buffer[-i] != out_buffer[-self.AO.nchan-i] :
                    raise simAioError, """To ensure that you are not suprised by the effects of the
DONT_OUTPUT_LAST_SAMPLE_HACK flag, please ensure that the last two
values samples output on each channel are the same."""
            onsamps = nsamps - 1
        else :
            onsamps = nsamps
        self._nsamps = nsamps
        self._ocmd.cmd.scan_begin_arg = int(1e9/freq)
        self._ocmd.cmd.stop_arg = onsamps
        if VERBOSE :
            print "Configure the board (%d ns per scan, %d samps, %g Hz)" % (self._icmd.cmd.scan_begin_arg, self._icmd.cmd.stop_arg, 1e9/self._ocmd.cmd.scan_begin_arg)
        self._obuffer = out_buffer
        self._onremain = nsamps
        self._ocmd.test_cmd(max_passes=2)
        self._ocmd.execute()
        self._icmd.cmd.scan_begin_arg = self._ocmd.cmd.scan_begin_arg
        self._icmd.cmd.stop_arg = nsamps
        self._icmd.test_cmd()
        self._inremain = nsamps
        self._icmd.execute()
        nsamps = min(self._onremain, self.buffsize)
        offset = 0
        if VERBOSE :
            print "Write %d output samples to the card" % (nsamps*self.AO.nchan)
        rc = int16_rw.write_samples(self._fd, out_buffer, offset, nsamps*self.AO.nchan, 1)
        if rc != nsamps*self.AO.nchan :
            raise simAioError, "Error %d writing output buffer\n" % rc
        self._onremain -= nsamps
        self.state = "Setup"
    def arm(self) :
        if self.state != "Setup" :
            raise simAioError, "Invalid state %s" % self.state 
        if VERBOSE :
            print "Arm the analog ouptut"
        self._comedi_internal_trigger(self.AO.subdev)
        self.state = "Armed"
    def start_read(self, in_buffer) :
        if self.state != "Armed" :
            raise simAioError, "Invalid state %s" % self.state
        if len(in_buffer) < self._nsamps * self.AI.nchan :
            raise simAioError, "in_buffer not long enough (size %d < required %d)" \
                % (len(in_buffer), self._nsamps * self.AI.nchan)

        if VERBOSE :
            print "Start the run"
        self._comedi_internal_trigger(self.AI.subdev)
        self.state = "Read"
        while self._inremain > 0 :
            # read half a buffer
            nsamps = min(self._inremain, self.buffsize/2)
            offset = (self._nsamps - self._inremain) * self.AI.nchan
            if VERBOSE :
                print "Read %d input samples from the card" % (nsamps*self.i_nchan)
            rc = int16_rw.read_samples(self._fd, in_buffer, offset, nsamps*self.AI.nchan, 20)
            if rc != nsamps*self.AI.nchan :
                raise simAioError, "Error %d reading input buffer\n" % rc
            self._inremain -= nsamps
            # write half a buffer
            nsamps = min(self._onremain, self.buffsize/2)
            if nsamps > 0 :
                offset = (self._nsamps - self._onremain) * self.AO.nchan
                if VERBOSE :
                    print "Write %d output samples to the card" % (nsamps*self.AO.nchan)
                rc = int16_rw.write_samples(self._fd, self._obuffer, offset, nsamps*self.AO.nchan, 20)
                if rc != nsamps*self.AO.nchan :
                    raise simAioError, "Error %d writing output buffer\n" % rc
                self._onremain -= nsamps
    def _comedi_internal_trigger(self, subdevice) :
        data = self._comedi.chanlist(1) # by luck, data is an array of lsampl_t (unsigned ints), as is chanlist
        insn = self._comedi.comedi_insn_struct()
        insn.insn = self._comedi.INSN_INTTRIG
        insn.subdev = subdevice
        insn.data = data
        insn.n = 1
        data[0] = 0
        rc = self._comedi.comedi_do_insn(self.dev, insn)
    def reset(self, force=False) :
        if VERBOSE :
            print "Reset the analog subdevices"
        # clean up after the read
        self.AO.updateFlags()
        self.AI.updateFlags()
        # I would expect self.AO.flags.busy() to be False by this point,
        # but after a write that does not seem to be the case.
        # It doesn't seem to cause any harm to cancel things anyway...
        rc = self._comedi.comedi_cancel(self.dev, self.AO.subdev)
        if rc < 0 :
            self._comedi.comedi_perror("comedi_cancel")
            raise simAioError, "Error cleaning up output command"
        rc = self._comedi.comedi_cancel(self.dev, self.AI.subdev)
        if rc < 0 :
            self._comedi.comedi_perror("comedi_cancel")
            raise simAioError, "Error cleaning up input command"
        self.state = "Initialized"


# define the test suite
# verbose
#  0 - no output
#  1 - print test names
#  2 - print test results
#  3 - print some details
#  4 - print lots of details

def _test_AIO(aio=None, start_wait=0, verbose=0) :
    if verbose >= 1 :
        print "_test_AIO(start_wait = %g)" % start_wait
    nsamps = 20
    out_data = aio.genBuffer(nsamps)
    in_data =  aio.genBuffer(nsamps)
    midpoint = int(aio.AO.maxdata[0]/2)
    bitrange = float(midpoint/2)
    for i in range(nsamps) :
        out_data[i] = int(midpoint+bitrange*sin(2*pi*i/float(nsamps)))
    out_data[-2] = out_data[-1] = midpoint
    aio.setup(freq=1000, out_buffer=out_data)
    aio.arm()
    sleep(start_wait)
    aio.start_read(in_data)
    aio.reset()
    if verbose >= 4 :
        print "out_data:\n", out_data
        print "in_data:\n", in_data
        print "residual:\n[",
        for i, o in zip(in_data, out_data) :
            print int(i)-int(o),
        print "]"
    return (out_data, in_data)

def _repeat_aio_test(aio=None, num_tests=100, start_wait=0, verbose=0) :
    if verbose >= 1 :
        print "_repeat_aio_test()"
    grads = array([0]*num_tests, dtype=float32) # test input with `wrong' type
    good = 0
    bad = 0
    good_run = 0
    good_run_arr = []
    for i in range(num_tests) :
        out_data, in_data = _test_AIO(aio, start_wait)
        gradient, intercept, r_value, p_value, std_err = linregress(out_data, in_data)
        grads[i] = gradient
        if verbose >= 4 :
            print "wait %2d, run %2d, gradient %g" % (start_wait, i, gradient)
        if gradient < .7 :
            bad += 1
            good_run_arr.append(good_run)
            good_run = 0
        else :
            good += 1
            good_run += 1
    good_run_arr.append(good_run)
    fail_rate = (float(bad)/float(good+bad))*100.0
    if verbose >= 2 :
        print "failure rate %g%% in %d runs" % (fail_rate, num_tests)
        call = 'echo "'
        for num in good_run_arr :
            call += "%d " % num
        call += '" | stem_leaf 2'
        print "good run stem and leaf:"
        system(call)
    return fail_rate

def _test_AIO_multi_chan(aio=None, start_wait=0, verbose=0) :
    from sys import stdout
    if verbose >= 1 :
        print "_test_AIO_multi_chan(start_wait = %g)" % start_wait
    nsamps = 100
    out_data = aio.genBuffer(nsamps, aio.AO.nchan)
    in_data =  aio.genBuffer(nsamps, aio.AI.nchan)
    # set up interleaved data
    midpoint = int(aio.AO.maxdata[0]/2)
    bitrange = float(midpoint/2)
    for i in range(nsamps) :
        out_data[i*aio.AO.nchan] = int(midpoint+bitrange*sin(2*pi*i/float(nsamps)))
        for j in range(1, aio.AO.nchan) :
            out_data[i*aio.AO.nchan + j] = 0
    if DONT_OUTPUT_LAST_SAMPLE_HACK :
        for ind in [-1,-1-aio.AO.nchan] :
            for chan in range(aio.AO.nchan) :
                out_data[ind-chan] = midpoint
    aio.setup(freq=1000, out_buffer=out_data)
    aio.arm()
    sleep(start_wait)
    aio.start_read(in_data)
    aio.reset()
    #fid = file('/tmp/comedi_test.o', 'w')
    fid = stdout
    if verbose >= 4 :
        print >> fid, "#",
        for j in range(aio.AO.nchan) :
            print >> fid, "%s\t" % aio.AO.chan[j],
        for j in range(aio.AI.nchan) :
            print >> fid, "%s\t" % aio.AI.chan[j],
        print ""
        for i in range(nsamps) :
            for j in range(aio.AO.nchan) :
                print >> fid, "%s\t" % out_data[i*aio.AO.nchan+j],
            for j in range(aio.AI.nchan) :
                print >> fid, "%s\t" % in_data[i*aio.AI.nchan+j],
            print >> fid, ""
    return (out_data, in_data)

def _test_big_bufs(aio=None, freq=100e3, verbose=False) :
    if verbose >= 1 :
        print "_test_big_bufs()"
    if aio == None :
        our_aio = True
        aio = AIO(in_chan=(1,), out_chan=(0,))
    else :
        our_aio = False
    nsamps = int(100e3)
    out_data = aio.genBuffer(nsamps, aio.AO.nchan)
    midpoint = int(aio.AO.maxdata[0]/2)
    bitrange = float(midpoint/2)
    for i in range(nsamps) :
        out_data[i] = int(sin(2*pi*i/float(nsamps))*bitrange) + midpoint
    if DONT_OUTPUT_LAST_SAMPLE_HACK :
        out_data[-2] = out_data[-1] = midpoint
    in_data = aio.genBuffer(nsamps, aio.AO.nchan)
    aio.setup(freq=freq, out_buffer=out_data)
    aio.arm()
    aio.start_read(in_data)
    aio.reset()
    if our_aio :
        aio.close()
        del(aio)

def _test_output_persistence(freq=100, verbose=False) :
    import single_aio
    if verbose >= 1 :
        print "_test_output_persistence()"
    aio = AIO(in_chan=(0,), out_chan=(0,))
    aio.close()
    ai = single_aio.AI(chan=(0,))
    ai.close()
    
    def simult_set_voltage(aio, range_fraction=None, physical_value=None, freq=freq, verbose=False) :
        "use either range_fraction or physical_value, not both."
        aio.open()
        if range_fraction != None :
            assert physical_value == None
            assert range_fraction >= 0 and range_fraction <= 1
            out_val = int(range_fraction*aio.AO.maxdata[0])
            physical_value = aio.AO.comedi_to_phys(chan_index=0, comedi=out_val, useNAN=False)
        else :
            assert physical_value != None
            out_val = aio.AO.phys_to_comedi(chan_index=0, phys=physical_value)
        if verbose >= 3 :
            print "Output : %d = %g V" % (out_val, physical_value)
        nsamps = int(int(freq))
        out_data = aio.genBuffer(nsamps, aio.AO.nchan, value=out_val)
        in_data = aio.genBuffer(nsamps, aio.AO.nchan)
        aio.setup(freq=freq, out_buffer=out_data)
        aio.arm()
        aio.start_read(in_data)
        aio.reset()
        # by this point the output returns to 0 V when 
        # DONT_OUTPUT_LATH_SAMPLE_HACK == False
        time.sleep(5)
        aio.close()
        if verbose >= 4 :
            print "Output complete"
            print in_data
        return physical_value
    def single_get_voltage(ai, verbose=False) :
        ai.open()
        in_val = ai.read()[0]
        ai.close()
        in_phys = ai.comedi_to_phys(chan_index=0, comedi=in_val, useNAN=False)
        if verbose >= 3 :
            print "Input  : %d = %g V" % (in_val, in_phys)
        return in_phys
    def tp(aio, ai, range_fraction, verbose=False) :
        out_phys = simult_set_voltage(aio, range_fraction=range_fraction, verbose=verbose)

        # It helps me to play a sound so I know where the test is
        # while confirming the output on an oscilliscope.
        #system("aplay /home/wking/Music/system/sonar.wav")

        time.sleep(1)
        in_phys = single_get_voltage(ai, verbose)
        assert abs((in_phys-out_phys)/out_phys) < 0.1, "Output %g V, but input %g V" % (out_phys, in_phys)
        
    tp(aio,ai,0,verbose)
    tp(aio,ai,1,verbose)
    simult_set_voltage(aio,physical_value=0.0,verbose=verbose)

def test(verbose=2) :
    aio = AIO(in_chan=(0,), out_chan=(0,))
    _test_AIO(aio, start_wait = 0, verbose=verbose)
    _test_AIO(aio, start_wait = 0.5, verbose=verbose)
    aio.close()
    aio.open()
    _repeat_aio_test(aio, num_tests=100, start_wait=0, verbose=verbose)
    _test_big_bufs(aio, verbose=verbose)
    aio.close()
    
    aiom = AIO(in_chan=(0,1,2,3), out_chan=(0,1))
    _test_AIO_multi_chan(aiom, start_wait = 0, verbose=verbose)
    del(aiom)
    _test_output_persistence(verbose=verbose)

if __name__ == "__main__" :
    test()
