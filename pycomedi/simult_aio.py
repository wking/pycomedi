# Simultaneous, finite, buffered analog inpout/output using comedi drivers

import comedi
from numpy import array, fromstring, uint16, float32, pi, sin
import int16_rw

# imports for testing
from time import sleep
from scipy.stats import linregress
from os import system

#VERBOSE = True
VERBOSE = False
AO_TRIGGERS_OFF_AI_START = True
#AO_TRIGGERS_OFF_AI_START = False

class simAioError (Exception) :
    "Simultaneous Analog IO error"
    pass

_example_array = array([0], dtype=uint16) # for typing, since I don't know what type(array) should be

_cmdtest_message = ["success",
                     "invalid source",
                     "source conflict",
                     "invalid argument",
                     "argument conflict",
                     "invalid chanlist"]

def _print_cmdsrc(source) :
    if source & comedi.TRIG_NONE : print "none|",
    if source & comedi.TRIG_NOW : print "now|",
    if source & comedi.TRIG_FOLLOW : print "follow|",
    if source & comedi.TRIG_TIME : print "time|",
    if source & comedi.TRIG_TIMER : print "timer|",
    if source & comedi.TRIG_COUNT : print "count|",
    if source & comedi.TRIG_EXT : print "ext|",
    if source & comedi.TRIG_INT : print "int|",
    if source & comedi.TRIG_OTHER : print "other|",

def _print_command(cmd) :
    print "subdevice: \t%d" % cmd.subdev
    print "flags:     \t0x%x" % cmd.flags
    print "start:     \t",
    _print_cmdsrc(cmd.start_src)
    print "\t%d" % cmd.start_arg
    print "scan_begin:\t",
    _print_cmdsrc(cmd.scan_begin_src)
    print "\t%d" % cmd.scan_begin_arg
    print "convert:   \t",
    _print_cmdsrc(cmd.convert_src)
    print "\t%d" % cmd.convert_arg
    print "scan_end:  \t",
    _print_cmdsrc(cmd.scan_end_src)
    print "\t%d" % cmd.scan_end_arg
    print "stop:      \t",
    _print_cmdsrc(cmd.stop_src)
    print "\t%d" % cmd.stop_arg

def _expand_tuple(tup, length) : 
    "Expand an iterable TUP to a tuple of LENGTH by repeating the last element"
    if len(tup) > length :
        raise simAioError, "Tuple too long."
    elif len(tup) < length :
        temp_tup = tup + tuple((tup[-1],)*(length-len(tup)))
        tup = temp_tup
    return tup

class aio_obj :
    def __init__(self, filename="/dev/comedi0",
		 in_subdevice=-1, in_chan=(0,), in_aref=(0,), in_range=(0,),
		 out_subdevice=-1, out_chan=(0,), out_aref=(0,), out_range=(0,)) :
        self._comedi = comedi
        self._filename = filename
        self.state = "Closed"
        self.open()

        self._iaref = _expand_tuple(in_aref, len(in_chan))
        self._irange = _expand_tuple(in_range, len(in_chan))
        temp = self._check_options(in_subdevice, in_chan, self._iaref, self._irange, output=False)
        self._isubdev = temp["subdevice"]
        self._ichan_params = temp["chan_params"]
        self._ichan = in_chan
        self.i_nchan = len(self._ichan)
        self._ichanlist = self._comedi.chanlist(self.i_nchan)
        for i in range(self.i_nchan) :
            self._ichanlist[i] = self._comedi.cr_pack(self._ichan[i], self._irange[i], self._iaref[i])

        self._oaref = _expand_tuple(out_aref, len(in_chan))
        self._orange = _expand_tuple(out_range, len(in_chan))
        temp = self._check_options(out_subdevice, out_chan, self._oaref, self._orange, output=True)
        self._osubdev = temp["subdevice"]
        self._ochan_params = temp["chan_params"]
        self._ochan = out_chan
        self.o_nchan = len(self._ochan)
        self._ochanlist = self._comedi.chanlist(self.o_nchan)
        for i in range(self.o_nchan) :
            self._ochanlist[i] = self._comedi.cr_pack(self._ochan[i], self._orange[i], self._oaref[i])

        self._gen_rough_output_cmd()
        self._gen_rough_input_cmd()
        self.state = "Initialized"
    def __del__(self) :
        self.close()
    def close(self) :
        if self.state != "Closed" :
            self.reset(force=True)
            rc = self._comedi.comedi_close(self._dev)
            if rc < 0 :
                self._comedi.comedi_perror("comedi_close")
                raise simAioError, "Cannot close %s" % self._filename
            if VERBOSE :
                print "Closed %s on fd %d" % (self._filename, self._fd)
            self.state = "Closed"
    def open(self) :
        if self.state != "Closed" :
            raise simAioError, "Invalid state %s" % self.state
        self._dev = self._comedi.comedi_open(self._filename)
        self._fd = self._comedi.comedi_fileno(self._dev)
        if VERBOSE :
            print "Opened %s on fd %d" % (self._filename, self._fd)
        self.state = "Initialized"
    def _check_options(self, subdevice, chan, aref, rnge, output=True) :
        subdevice = self._check_subdevice(subdevice, output=output)
        chan_params = []
        for i in range(len(chan)) :
            chan_params.append(self._check_chan(subdevice, chan[i], aref[i], rnge[i]))
        if VERBOSE :
            if output :
                print "Output",
            else :
                print "Input",
            print " subdevice with channels %s is valid" % (str(chan))
        return {"subdevice":subdevice,
                "chan_params":chan_params}
    def _check_subdevice(self, subdevice, output=True) :
        if output == True :
            target_type = self._comedi.COMEDI_SUBD_AO
        else :
            target_type = self._comedi.COMEDI_SUBD_AI
        if (subdevice < 0) : # autodetect an input device
            subdevice = self._comedi.comedi_find_subdevice_by_type(self._dev, target_type, 0) # 0 is starting subdevice
        else :
            type = self._comedi.comedi_get_subdevice_type(self._dev, subdevice)
            if type != target_type :
                raise simAioError, "Comedi subdevice %d has wrong type %d" % (subdevice, type)
        return subdevice
    def _check_chan(self, subdevice, chan, aref, range) :
        subdev_n_chan = self._comedi.comedi_get_n_channels(self._dev, subdevice)
        if chan >= subdev_n_chan :
            raise simAioError, "Channel %d > subdevice %d's largest chan %d" % (chan, subdevice, subdev_n_chan-1)
        n_range = self._comedi.comedi_get_n_ranges(self._dev, subdevice, chan)
        if range >= n_range :
            raise simAioError, "Range %d > subdevice %d, chan %d's largest range %d" % (range, subdevice, chan, n_range-1)
        maxdata = self._comedi.comedi_get_maxdata(self._dev, subdevice, chan)
        comrange = self._comedi.comedi_get_range(self._dev, subdevice, chan, range)
        return {"maxdata":maxdata, "comrange": comrange}
    def _gen_rough_output_cmd(self) :
        if VERBOSE :
            print "generate rough output command"
        cmd = self._comedi.comedi_cmd_struct()
        cmd.subdev = self._osubdev
        cmd.flags = self._comedi.CMDF_WRITE
        if AO_TRIGGERS_OFF_AI_START :
            cmd.start_src = self._comedi.TRIG_EXT
            cmd.start_arg = 18 # AI_START1 internal AI start signal
        else :
            cmd.start_src = self._comedi.TRIG_INT
            cmd.start_arg = 0
        cmd.scan_begin_src = self._comedi.TRIG_TIMER
        cmd.scan_begin_arg = 1 # temporary value for now
        cmd.convert_src = self._comedi.TRIG_NOW
        cmd.convert_arg = 0
        cmd.scan_end_src = self._comedi.TRIG_COUNT
        cmd.scan_end_arg = self.o_nchan
        cmd.stop_src = self._comedi.TRIG_COUNT
        cmd.stop_arg = 1 # temporary value for now
        cmd.chanlist = self._ochanlist
        cmd.chanlist_len = self.o_nchan
        self._test_cmd(cmd, max_passes=3)
        self._ocmd = cmd
    def _gen_rough_input_cmd(self) :
        if VERBOSE :
            print "generate rough input command"
        cmd = self._comedi.comedi_cmd_struct()
        cmd.subdev = self._isubdev
        cmd.flags = 0
        cmd.start_src = self._comedi.TRIG_INT
        cmd.start_arg = 0
        cmd.scan_begin_src = self._comedi.TRIG_TIMER
        cmd.scan_begin_arg = 1 # temporary value for now
        cmd.convert_src = self._comedi.TRIG_TIMER
        cmd.convert_arg = 1
        cmd.scan_end_src = self._comedi.TRIG_COUNT
        cmd.scan_end_arg = self.i_nchan
        cmd.stop_src = self._comedi.TRIG_COUNT
        cmd.stop_arg = 1 # temporary value for now
        cmd.chanlist = self._ichanlist
        cmd.chanlist_len = self.i_nchan
        self._test_cmd(cmd, max_passes=3)
        self._icmd = cmd
    def _test_cmd(self, cmd, max_passes=1) :
        very_verbose = False
        i = 0
        rc = 0
        if  very_verbose : 
            print "Testing command:"
            _print_command(cmd)
        while i < max_passes :
            rc = self._comedi.comedi_command_test(self._dev, cmd)
            if (rc == 0) :
                break
            if VERBOSE or very_verbose :
                print "test pass %d, %s" % (i, _cmdtest_message[rc])
            i += 1
        if (VERBOSE or very_verbose) and i < max_passes :
            print "Passing command:"
            _print_command(cmd)
        if i >= max_passes :
            print "Failing command:"
            _print_command(cmd)
            raise simAioError, "Invalid command: %s" % _cmdtest_message[rc]
    def setup(self, nsamps, freq, out_buffer) :
        if self.state != "Initialized" :
            raise simAioError, "Invalid state %s" % self.state
        if type(out_buffer) != type(_example_array) :
            raise simAioError, "out_buffer must be a numpy array, not a %s" % str(type(out_buffer))
        self._ocmd.scan_begin_arg = int(1e9/freq)
        self._ocmd.stop_arg = nsamps
        if VERBOSE :
            print "Configure the board (%d ns per scan, %d samps)" % (self._ocmd.scan_begin_arg, self._ocmd.stop_arg)
        self._onremain = nsamps
        self._test_cmd(self._ocmd)
        rc = self._comedi.comedi_command(self._dev, self._ocmd)
        if rc < 0 :
            self._comedi.comedi_perror("comedi_command")
            raise simAioError, "Error executing output command %d" % rc
        self._icmd.scan_begin_arg = int(1e9/freq)
        self._icmd.stop_arg = nsamps
        self._test_cmd(self._icmd)
        self._inremain = nsamps
        rc = self._comedi.comedi_command(self._dev, self._icmd)
        if rc < 0 :
            self._comedi.comedi_perror("comedi_command")
            raise simAioError, "Error executing input command"

        if VERBOSE :
            print "Write %d output samples to the card" % (nsamps*self.o_nchan)
        rc = int16_rw.write_samples(self._fd, nsamps*self.o_nchan, out_buffer, 1)
        if rc != nsamps*self.o_nchan :
            raise simAioError, "Error %d writing output buffer\n" % rc
        rc = int16_rw.write_samples(self._fd, self.o_nchan, out_buffer[-self.o_nchan:], 1) # HACK, add an extra sample for each channel to the output buffer
        if rc != self.o_nchan :
            raise simAioError, "Error %d writing hack output buffer\n" % rc
        # maybe will avoid resetting...
        self._nsamps = nsamps
        self.state = "Setup"
    def arm(self) :
        if self.state != "Setup" :
            raise simAioError, "Invalid state %s" % self.state 
        if VERBOSE :
            print "Arm the analog ouptut"
        self._comedi_internal_trigger(self._osubdev)
        self.state = "Armed"
    def start_read(self, in_buffer) :
        if self.state != "Armed" :
            raise simAioError, "Invalid state %s" % self.state
        if VERBOSE :
            print "Start the run"
        self._comedi_internal_trigger(self._isubdev)
        if VERBOSE :
            print "Read %d input samples from the card" % (self._nsamps*self.i_nchan)
        rc = int16_rw.read_samples(self._fd, self._nsamps*self.i_nchan, in_buffer, -1)
        if rc != self._nsamps*self.i_nchan :
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
        rc = self._comedi.comedi_do_insn(self._dev, insn)
    def reset(self, force=False) :
        if VERBOSE :
            print "Reset the analog subdevices"
        # clean up after the read
        rc = self._comedi.comedi_cancel(self._dev, self._osubdev)
        if rc < 0 :
            self._comedi.comedi_perror("comedi_cancel")
            raise simAioError, "Error cleaning up output command"
        rc = self._comedi.comedi_cancel(self._dev, self._isubdev)
        if rc < 0 :
            self._comedi.comedi_perror("comedi_cancel")
            raise simAioError, "Error cleaning up input command"
        self.state = "Initialized"


# define the test suite

def _test_aio_obj(aio=None, start_wait=0, verbose=False) :
    if (verbose) :
        print "_test_aio_obj(start_wait = %g)" % start_wait
    nsamps = 10
    out_data = array([0]*nsamps, dtype=uint16)
    in_data =  array([0]*nsamps, dtype=uint16)
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
        out_data, in_data = _test_aio_obj(aio, start_wait)
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

def _test_aio_obj_multi_chan(aio=None, start_wait=0, verbose=False) :
    if (verbose) :
        print "_test_aio_obj_multi_chan(start_wait = %g)" % start_wait
    nsamps = 10
    out_data = array([0]*nsamps*aio.o_nchan, dtype=uint16)
    in_data =  array([0]*nsamps*aio.i_nchan, dtype=uint16)
    # set up interleaved data
    for i in range(nsamps) :
        out_data[i*aio.o_nchan] = int(30000.0+3000.0*sin(2*pi*i/float(nsamps)))
        for j in range(1, aio.o_nchan) :
            out_data[i*aio.o_nchan + j] = 0
    aio.setup(10, 1000, out_data)
    aio.arm()
    sleep(start_wait)
    aio.start_read(in_data)
    aio.reset()
    if (verbose) :
        print "#",
        for j in range(aio.o_nchan) :
            print "%s\t" % aio._ochan[j],
        for j in range(aio.i_nchan) :
            print "%s\t" % aio._ichan[j],
        print ""
        for i in range(nsamps) :
            for j in range(aio.o_nchan) :
                print "%s\t" % out_data[i*aio.o_nchan+j],
            for j in range(aio.i_nchan) :
                print "%s\t" % in_data[i*aio.i_nchan+j],
            print ""
    return (out_data, in_data)



def test() :
    aio = aio_obj()
    _test_aio_obj(aio, start_wait = 0, verbose=True)
    _test_aio_obj(aio, start_wait = 0.5, verbose=True)
    aio.close()
    aio.open()
    #_repeat_aio_test(aio, num_tests=100, start_wait=0, verbose=False)
    aio.close()

    aiom = aio_obj(in_chan=(0,1,2,3), out_chan=(0,1))
    _test_aio_obj_multi_chan(aiom, start_wait = 0, verbose=True)

if __name__ == "__main__" :
    test()
