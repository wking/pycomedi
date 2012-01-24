# Copyright (C) 2011-2012 W. Trevor King <wking@drexel.edu>
#
# This file is part of pycomedi.
#
# pycomedi is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License as published by the
# Free Software Foundation, either version 2 of the License, or (at your
# option) any later version.
#
# pycomedi is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with pycomedi.  If not, see <http://www.gnu.org/licenses/>.

"Cython interface to comedilib.h"

from _comedi_h cimport *


cdef extern from 'comedilib.h':
    ctypedef struct comedi_t:
        pass

    ctypedef struct comedi_range:
        double min
        double max
        unsigned int unit

    comedi_t *comedi_open(char *fn)
    int comedi_close(comedi_t *it)

    # logging

    int comedi_loglevel(int loglevel)
    void comedi_perror(char *s)
    char *comedi_strerror(int errnum)
    int comedi_errno()
    int comedi_fileno(comedi_t *it)

    # device queries

    int comedi_get_n_subdevices(comedi_t *it)
    # COMEDI_VERSION_CODE handled by device.Device.get_version_code()
    int comedi_get_version_code(comedi_t *it)
    char *comedi_get_driver_name(comedi_t *it)
    char *comedi_get_board_name(comedi_t *it)
    int comedi_get_read_subdevice(comedi_t *dev)
    int comedi_get_write_subdevice(comedi_t *dev)

    # subdevice queries

    int comedi_get_subdevice_type(comedi_t *it,unsigned int subdevice)
    int comedi_find_subdevice_by_type(comedi_t *it,int type,unsigned int subd)
    int comedi_get_subdevice_flags(comedi_t *it,unsigned int subdevice)
    int comedi_get_n_channels(comedi_t *it,unsigned int subdevice)
    int comedi_range_is_chan_specific(comedi_t *it,unsigned int subdevice)
    int comedi_maxdata_is_chan_specific(comedi_t *it,unsigned int subdevice)

    # channel queries

    lsampl_t comedi_get_maxdata(comedi_t *it,unsigned int subdevice,
        unsigned int chan)
    int comedi_get_n_ranges(comedi_t *it,unsigned int subdevice,
        unsigned int chan)
    comedi_range * comedi_get_range(comedi_t *it,unsigned int subdevice,
        unsigned int chan,unsigned int range)
    int comedi_find_range(comedi_t *it,unsigned int subd,unsigned int chan,
        unsigned int unit,double min,double max)

    # buffer queries

    int comedi_get_buffer_size(comedi_t *it,unsigned int subdevice)
    int comedi_get_max_buffer_size(comedi_t *it,unsigned int subdevice)
    int comedi_set_buffer_size(comedi_t *it,unsigned int subdevice,
            unsigned int len)

    # low-level stuff

    int comedi_do_insnlist(comedi_t *it,comedi_insnlist *il)
    int comedi_do_insn(comedi_t *it,comedi_insn *insn)
    int comedi_lock(comedi_t *it,unsigned int subdevice)
    int comedi_unlock(comedi_t *it,unsigned int subdevice)

    # synchronous stuff

    int comedi_data_read(comedi_t *it,unsigned int subd,unsigned int chan,
        unsigned int range,unsigned int aref,lsampl_t *data)
    int comedi_data_read_n(comedi_t *it,unsigned int subd,unsigned int chan,
        unsigned int range,unsigned int aref,lsampl_t *data, unsigned int n)
    int comedi_data_read_hint(comedi_t *it,unsigned int subd,unsigned int chan,
        unsigned int range,unsigned int aref)
    int comedi_data_read_delayed(comedi_t *it,unsigned int subd,unsigned int chan,
        unsigned int range,unsigned int aref,lsampl_t *data, unsigned int nano_sec)
    int comedi_data_write(comedi_t *it,unsigned int subd,unsigned int chan,
        unsigned int range,unsigned int aref,lsampl_t data)
    int comedi_dio_config(comedi_t *it,unsigned int subd,unsigned int chan,
        unsigned int dir)
    int comedi_dio_get_config(comedi_t *it,unsigned int subd,unsigned int chan,
        unsigned int *dir)
    int comedi_dio_read(comedi_t *it,unsigned int subd,unsigned int chan,
        unsigned int *bit)
    int comedi_dio_write(comedi_t *it,unsigned int subd,unsigned int chan,
        unsigned int bit)
    int comedi_dio_bitfield2(comedi_t *it,unsigned int subd,
        unsigned int write_mask, unsigned int *bits, unsigned int base_channel)

    # streaming I/O (commands)

    int comedi_get_cmd_src_mask(comedi_t *dev,unsigned int subdevice,
            comedi_cmd *cmd)
    int comedi_get_cmd_generic_timed(comedi_t *dev,unsigned int subdevice,
            comedi_cmd *cmd, unsigned chanlist_len, unsigned scan_period_ns)
    int comedi_cancel(comedi_t *it,unsigned int subdevice)
    int comedi_command(comedi_t *it,comedi_cmd *cmd)
    int comedi_command_test(comedi_t *it,comedi_cmd *cmd)
    int comedi_poll(comedi_t *dev,unsigned int subdevice)

    # buffer control

    int comedi_set_max_buffer_size(comedi_t *it, unsigned int subdev,
            unsigned int max_size)
    int comedi_get_buffer_contents(comedi_t *it, unsigned int subdev)
    int comedi_mark_buffer_read(comedi_t *it, unsigned int subdev,
            unsigned int bytes)
    int comedi_mark_buffer_written(comedi_t *it, unsigned int subdev,
            unsigned int bytes)
    int comedi_get_buffer_offset(comedi_t *it, unsigned int subdev)

    # structs and functions used for parsing calibration files

    ctypedef struct comedi_caldac_t:
        unsigned int subdevice
        unsigned int channel
        unsigned int value

    enum: COMEDI_MAX_NUM_POLYNOMIAL_COEFFICIENTS

    ctypedef struct comedi_polynomial_t:
        double coefficients[COMEDI_MAX_NUM_POLYNOMIAL_COEFFICIENTS]
        double expansion_origin
        unsigned order

    ctypedef struct comedi_softcal_t:
        comedi_polynomial_t *to_phys
        comedi_polynomial_t *from_phys

    enum: CS_MAX_AREFS_LENGTH

    ctypedef struct comedi_calibration_setting_t:
        unsigned int subdevice
        unsigned int *channels
        unsigned int num_channels
        unsigned int *ranges
        unsigned int num_ranges
        unsigned int arefs[ CS_MAX_AREFS_LENGTH ]
        unsigned int num_arefs
        comedi_caldac_t *caldacs
        unsigned int num_caldacs
        comedi_softcal_t soft_calibration

    ctypedef struct comedi_calibration_t:
        char *driver_name
        char *board_name
        comedi_calibration_setting_t *settings
        unsigned int num_settings

    comedi_calibration_t* comedi_parse_calibration_file(
        char *cal_file_path )
    int comedi_apply_parsed_calibration( comedi_t *dev, unsigned int subdev,
        unsigned int channel, unsigned int range, unsigned int aref,
        comedi_calibration_t *calibration )
    char* comedi_get_default_calibration_path( comedi_t *dev )
    void comedi_cleanup_calibration( comedi_calibration_t *calibration )
    int comedi_apply_calibration( comedi_t *dev, unsigned int subdev,
        unsigned int channel, unsigned int range, unsigned int aref,
        char *cal_file_path)

    # New stuff to provide conversion between integers and physical values that
    # can support software calibrations.
    enum comedi_conversion_direction:
        COMEDI_TO_PHYSICAL,
        COMEDI_FROM_PHYSICAL
    int comedi_get_softcal_converter(
        unsigned subdevice, unsigned channel, unsigned range,
        comedi_conversion_direction direction,
        comedi_calibration_t *calibration,
        comedi_polynomial_t *polynomial)
    int comedi_get_hardcal_converter(
        comedi_t *dev, unsigned subdevice, unsigned channel, unsigned range,
        comedi_conversion_direction direction,
        comedi_polynomial_t *polynomial)
    double comedi_to_physical(lsampl_t data,
        comedi_polynomial_t *conversion_polynomial)
    lsampl_t comedi_from_physical(double data,
        comedi_polynomial_t *conversion_polynomial)
    #
    #int comedi_internal_trigger(comedi_t *dev, unsigned subd, unsigned trignum);
    #/* INSN_CONFIG wrappers */
    #int comedi_arm(comedi_t *device, unsigned subdevice, unsigned source);
    #int comedi_reset(comedi_t *device, unsigned subdevice);
    #int comedi_get_clock_source(comedi_t *device, unsigned subdevice, unsigned channel, unsigned *clock, unsigned *period_ns);
    #int comedi_get_gate_source(comedi_t *device, unsigned subdevice, unsigned channel,
    #        unsigned gate, unsigned *source);
    #int comedi_get_routing(comedi_t *device, unsigned subdevice, unsigned channel, unsigned *routing);
    #int comedi_set_counter_mode(comedi_t *device, unsigned subdevice, unsigned channel, unsigned mode_bits);
    #int comedi_set_clock_source(comedi_t *device, unsigned subdevice, unsigned channel, unsigned clock, unsigned period_ns);
    #int comedi_set_filter(comedi_t *device, unsigned subdevice, unsigned channel, unsigned filter);
    #int comedi_set_gate_source(comedi_t *device, unsigned subdevice, unsigned channel, unsigned gate_index, unsigned gate_source);
    #int comedi_set_other_source(comedi_t *device, unsigned subdevice, unsigned channel,
    #        unsigned other, unsigned source);
    #int comedi_set_routing(comedi_t *device, unsigned subdevice, unsigned channel, unsigned routing);
    #int comedi_get_hardware_buffer_size(comedi_t *device, unsigned subdevice, enum comedi_io_direction direction);
