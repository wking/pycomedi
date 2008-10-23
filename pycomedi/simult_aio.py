# Simultaneous, finite, buffered analog inpout/output using comedi drivers

import comedi as c
import common
from numpy import array, fromstring, float32, pi, sin
import int16_rw

# imports for testing
from time import sleep
from scipy.stats import linregress
from os import system

VERSION = common.VERSION
#VERBOSE = True
VERBOSE = False
AO_TRIGGERS_OFF_AI_START = True
#AO_TRIGGERS_OFF_AI_START = False

class simAioError (common.pycomediError) :
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
            _print_command(self.cmd)
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
		 out_subdevice=-1, out_chan=(0,), out_aref=(0,), out_range=(0,)) :
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
    def setup(self, nsamps, freq, out_buffer) :
        if self.state != "Initialized" :
            raise simAioError, "Invalid state %s" % self.state
        if type(out_buffer) != type(_example_array) :
            raise simAioError, "out_buffer must be a numpy array, not a %s" % str(type(out_buffer))
        self._ocmd.cmd.scan_begin_arg = int(1e9/freq)
        self._ocmd.cmd.stop_arg = nsamps
        if VERBOSE :
            print "Configure the board (%d ns per scan, %d samps)" % (self._ocmd.cmd.scan_begin_arg, self._ocmd.cmd.stop_arg)
        self._onremain = nsamps
        self._ocmd.test_cmd()
        self._ocmd.execute()
        self._icmd.cmd.scan_begin_arg = int(1e9/freq)
        self._icmd.cmd.stop_arg = nsamps
        self._icmd.test_cmd()
        self._inremain = nsamps
        self._icmd.execute()
        if VERBOSE :
            print "Write %d output samples to the card" % (nsamps*self.AO.nchan)
        rc = int16_rw.write_samples(self._fd, out_buffer, 0, nsamps*self.AO.nchan, 1)
        if rc != nsamps*self.AO.nchan :
            raise simAioError, "Error %d writing output buffer\n" % rc
        if VERBOSE :
            print "Writing extra output"
        rc = int16_rw.write_samples(self._fd, out_buffer, (nsamps-1)*self.AO.nchan, self.AO.nchan, 1) # HACK, add an extra sample for each channel to the output buffer
        if rc != self.AO.nchan :
            raise simAioError, "Error %d writing hack output buffer\n" % rc
        # Without the hack, output jumps back to 0V after the command completes
        self._nsamps = nsamps
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
        if VERBOSE :
            print "Start the run"
        self._comedi_internal_trigger(self.AI.subdev)
        if VERBOSE :
            print "Read %d input samples from the card" % (self._nsamps*self.AI.nchan)
        rc = int16_rw.read_samples(self._fd, in_buffer, 0, self._nsamps*self.AI.nchan, -1)
        if rc != self._nsamps*self.AI.nchan :
            raise simAioError, "Error %d reading input buffer\n" % rc
        self.state = "Read"
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

def _test_AIO(aio=None, start_wait=0, verbose=False) :
    if (verbose) :
        print "_test_AIO(start_wait = %g)" % start_wait
    nsamps = 10
    out_data = array([0]*nsamps, dtype=int16_rw.DATA_T)
    in_data =  array([0]*nsamps, dtype=int16_rw.DATA_T)
    for i in range(nsamps) :
        out_data[i] = int(30000.0+3000.0*sin(2*pi*i/float(nsamps)))
    aio.setup(10, 1000, out_data)
    aio.arm()
    sleep(start_wait)
    aio.start_read(in_data)
    aio.reset()
    if (verbose) :
        print "out_data:\n", out_data
        print "in_data:\n", in_data
        print "residual:\n[",
        for i, o in zip(in_data, out_data) :
            print int(i)-int(o),
        print "]"
    return (out_data, in_data)

def _repeat_aio_test(aio=None, num_tests=100, start_wait=0, verbose=False) :
    print "_repeat_aio_test()"
    grads = array([0]*num_tests, dtype=float32)
    good = 0
    bad = 0
    good_run = 0
    good_run_arr = []
    for i in range(num_tests) :
        out_data, in_data = _test_AIO(aio, start_wait)
        gradient, intercept, r_value, p_value, std_err = linregress(out_data, in_data)
        grads[i] = gradient
        if verbose :
            print "wait %2d, run %2d, gradient %g" % (start_wait, i, gradient)
        if gradient < .7 :
            bad += 1
            good_run_arr.append(good_run)
            good_run = 0
        else :
            good += 1
            good_run += 1
    good_run_arr.append(good_run)
    print "failure rate %g%% in %d runs" % ((float(bad)/float(good+bad))*100.0, num_tests)
    call = 'echo "'
    for num in good_run_arr :
        call += "%d " % num
    call += '" | stem_leaf 2'
    print "good run stem and leaf:"
    system(call)

def _test_AIO_multi_chan(aio=None, start_wait=0, verbose=False) :
    if (verbose) :
        print "_test_AIO_multi_chan(start_wait = %g)" % start_wait
    nsamps = 10
    out_data = array([0]*nsamps*aio.AO.nchan, dtype=int16_rw.DATA_T)
    in_data =  array([0]*nsamps*aio.AI.nchan, dtype=int16_rw.DATA_T)
    # set up interleaved data
    for i in range(nsamps) :
        out_data[i*aio.AO.nchan] = int(30000.0+3000.0*sin(2*pi*i/float(nsamps)))
        for j in range(1, aio.AO.nchan) :
            out_data[i*aio.AO.nchan + j] = 0
    aio.setup(10, 1000, out_data)
    aio.arm()
    sleep(start_wait)
    aio.start_read(in_data)
    aio.reset()
    if (verbose) :
        print "#",
        for j in range(aio.AO.nchan) :
            print "%s\t" % aio.AO.chan[j],
        for j in range(aio.AI.nchan) :
            print "%s\t" % aio.AI.chan[j],
        print ""
        for i in range(nsamps) :
            for j in range(aio.AO.nchan) :
                print "%s\t" % out_data[i*aio.AO.nchan+j],
            for j in range(aio.AI.nchan) :
                print "%s\t" % in_data[i*aio.AI.nchan+j],
            print ""
    return (out_data, in_data)



def test() :
    aio = AIO(in_chan=(0,), out_chan=(0,))
    _test_AIO(aio, start_wait = 0, verbose=True)
    _test_AIO(aio, start_wait = 0.5, verbose=True)
    aio.close()
    aio.open()
    _repeat_aio_test(aio, num_tests=500, start_wait=0, verbose=False)
    aio.close()

    aiom = AIO(in_chan=(0,1,2,3), out_chan=(0,1))
    _test_AIO_multi_chan(aiom, start_wait = 0, verbose=True)

if __name__ == "__main__" :
    test()
