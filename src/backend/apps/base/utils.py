"""
Created on 15 Dec 2017

@author: Vas, Mihaido

Utils module. Contains object class for the VCP serial configuration (using python's serial library)
1. Victron Multiplus inverter with MK2b interface (tested for USB-RS232)
2. USB-ISS connected OnSystems 1st life battery pack
"""
import os
import serial
import time
import struct
import ctypes
import json
from random import randint, random, uniform

from django.conf import settings

from .log import log_battery, log_inverter

FAKE_STEP = 0

class VictronMultiplusMK2VCP(object):
    """
    Victron Multiplus inverter with MK2b interface (tested for USB-RS232)

    1. Call 'send setpoint' periodically (5 seconds)
    2. Call 'request_frames_update' periodically (5 seconds)
    3. Call '

    """

    inverter_instances = {}

    def __init__(self, com_port):
        self.set_point = 0
        self.set_point_timestamp = None
        self.last_values_update_timestamp = 0;
        self.inverter_variables = {
            'dc_current': 0,
            'dc_voltage': 0,
            'ac_current': 0,
            'ac_voltage': 0,
            'dc_capacity': 0, #Amps Hour (Ah)
            'dc_energy': 0 #Wh 
        }

        self.com_port = com_port

        try:
            self.serial_handle = serial.Serial()
            self.serial_handle.port = '{sep}{path}{sep}{com}'.format(sep=os.path.sep, path='dev', com=self.com_port)
            self.serial_handle.baudrate = 2400
            self.serial_handle.timeout = 0.5
            self.serial_handle.setDTR(True)
            self.serial_handle.bytesize = serial.EIGHTBITS
            self.serial_handle.stopbits = serial.STOPBITS_ONE
            self.serial_handle.open()
            log_inverter.info('Opened port to inverter on %s', self.com_port)
        except Exception as err:
            log_inverter.exception('Could not open port to inverter on %s. Error is: %s', self.com_port, err)

    def close_coms(self):
        """
            Closes the serial resource for the inverter
        """
        try:
            self.serial_handle.close()
            log_inverter.info('Closed port to inverter on %s', self.com_port)
            return True
        except Exception as err:
            log_inverter.exception('Could not close inverter port %s because %s', self.com_port, err)
            return False

    def prepare_inverter(self):
        """
            This method will ensure the inverter is in a state ready to be used during the test.
            1. It will configure the VE bus 
            2. It will verify that the comport is open and if it is not it will attempt to open it.
        """
        try:
            if self.serial_handle.is_open:
                self.configure_ve_bus()
                log_inverter.info('-PREPARE INVERTER- Configured VE bus for inverter on port: %s', self.com_port)
                return True
            else:
                self.serial_handle.open()
                self.configure_ve_bus()
                log_inverter.info('Configured VE bus for inverter on port: %s', self.com_port)
                return True
        except Exception as err:
            log_inverter.exception('Error encountered in preparing the inverter for test on port: %s. Error is: %s.', self.com_port, err)
            return False

    def configure_ve_bus(self):
        """
            This method does the start-up procedure on the inverter (resets the Mk2 etc)
        """
        A_command = b'\x04\xFF\x41\x01\x00\xBB'
        reset_command = b'\x02\xFF\x52\xAD'
        X53_command = b'\x09\xFF\x53\x03\x00\xFF\x01\x00\x00\x04\x9E'

        try:
            self.serial_handle.write(A_command)
            time.sleep(0.1)
            self.serial_handle.write(X53_command)
            time.sleep(0.1)
            self.serial_handle.write(reset_command)
            time.sleep(0.1)
            self.serial_handle.write(A_command)
            time.sleep(0.1)
            log_inverter.info('VE Bus configure for inverter on port %s', self.com_port)
            return True
        except Exception as err:
            log_inverter.exception('Initializing VE bus protocol failed on port %s because %s', self.com_port, err)
            return False

    def send_setpoint(self):
        """
            This method sends the setpoint to the inverter (self.setpoint)
        """
        try:
            message_out = self.make_message_MK2(self.set_point)
            self.serial_handle.write(message_out)
            time.sleep(0.1)
            log_inverter.info('Setpoint sent. Setpoint is: %s', self.set_point)
            return True
        except Exception as err:
            log_inverter.exception('Sending power setpoint to the PU failed on port %s because %s', self.com_port, err)
            return False

    def make_message_MK2(self, setpoint):
        """
            This method return the setpoint command to send to the inverter. Uses self.setpoint.
        """
        try:
            d0 = b'\x05\xFF\x57\x32\x81\x00\xF2\x05\xff\x57\x34\x00\x00\x00'
            d1 = bytearray(d0)
            if setpoint < 0:
                setpoint = 65535 + self.set_point

            d1[11] = int(setpoint) % 256
            d1[12] = int(setpoint) >> 8
            s = 0
            for b in reversed(range(7, 13)):
                s = s - d1[b]
            d1[13] = s % 256
            return d1
        except Exception as err:
            log_inverter.exception('Setpoint message construction failed on port %s because %s', self.com_port, err)
            return False

    def request_DC_frame(self):
        """
            Sends request for a DC frame on the VE bus
            com_port_handle:
        """
        try:
            #self.thread_RX.start()  #Start monitoring messages from Power Unit
            message = b'\x03\xffF\x00\xb8'
            self.serial_handle.write(message)
            log_inverter.info('DC frame Requested (message sent) on port %s', self.com_port)
            return True
        except Exception as err:
            log_inverter.exception('Requesting the DC frame (maybe serial timeout?) failed on %s because %s', self.com_port, err)
            return False

    def request_AC_frame(self):
        """
            Sends request for AC frame on the VE bus
        """
        try:
            message = b'\x03\xffF\x01\xb7'
            self.serial_handle.write(message)
            log_inverter.info('AC frame Requested (message sent) on port: %s', self.com_port)
            return True
        except Exception as err:
            log_inverter.exception('Requesting the AC frame (maybe serial timeout?) failed on %s because %s', self.com_port, err)
            return False

    def make_state_message(self, state=0):
        """
            Method will return the MK2 command for switching states.
            Select state = 0 for off. State = 1 for on.
        """
        #b'\x09\xFF\x53\x03\x00\xFF\x01\x00\x00\x04\x9E'
        try:
            if state == 0:
                switch_state = b'\x04'
            elif state == 1:
                switch_state = b'\x03'
            else:
                switch_state = b'\x04'

            message = b'\x09\xff\x53'
            message = message + switch_state
            message = message + b'\x00\xff'
            message = message + b'\x01'
            message = message + b'\x00\x00\x04'
            message = message + b'\xff'
            message_array = bytearray(message)
            s = 0
            for b in reversed(range(len(message)-1)):
                s = s - message[b];
            message_array[-1] = s % 256
            return bytes(message_array)
        except Exception as err:
            log_inverter.exception('Cannot make state message on port %s. Error is: %s', self.com_port, err)
            return False

    def send_state(self, state=0):
        """
            Method will send a state command to the inverter.
            Use state to choose state.
        """
        try:
            command = self.make_state_message(state = state)
            self.serial_handle.write(command)
            log_inverter.info('Switched to state %s the inverter on port %s. Used command: %s.', state, self.com_port, str(command))
            return True
        except Exception as err:
            log_inverter.exception('Cannot send new state to inverter on port: %s. Error is: %s', self.com_port, err)
            return False

    def get_next_byte(self):
        """
            Use this function to read a single byte from the serial port
        """
        try:
            byte_in = self.serial_handle.read(1)
            return byte_in
        except Exception as err:
            log_inverter.exception('Unable to get next byte from inverter on port: %s. Error is: %s', self.com_port, err)
            return False

    def request_frames_update(self):
        """
            Call this method periodically to update the readings from the Inverter
        """
        try:
            self.request_AC_frame()
            time.sleep(0.1)
            self.request_DC_frame()
            time.sleep(0.1)
            log_inverter.info('Requested DC and AC frames on inverter')
            return True
        except Exception as err:
            log_inverter.exception('Cannot update frames.', err)
            return False

    def charge(self):
        """
            Method can be called and it will automatically configure the inverter to charge with a set amount
        """
        try:
            self.set_point = settings.CHARGING_SETPOINT
            log_inverter.info('Setting setpoint to CHARGE setting on port: %s', self.com_port)
            return True
        except Exception as err:
            log_inverter.exception('Cannot set charge mode on port %s. Exception is: %s', self.com_port, err)
            return False

    def invert(self):
        """
            Method can be called and it will automatically configure the iverter to invert with a set amount
        """
        try:
            self.set_point = settings.INVERTING_SETPOINT
            log_inverter.info('Setting setpoint to DISCHARGE setting on port: %s, setpoint is: %s', self.com_port, self.set_point)
            return True
        except Exception as err:
            log_inverter.exception('Cannot set invert mode on port %s. Exception is: %s', self.com_port, err)
            return False

    def rest(self):
        """
            Method will zero out the setpoint. The inverter will be kept on.
        """
        try:
            self.set_point = 0
            log_inverter.info('Setting setpoint to REST setting on port: %s, setpoint is: %s', self.com_port, self.set_point)

            return True
        except Exception as err:
            msg = 'Cannot set rest mode. The inverter on port {} is still running? Exception is: {}'.format(
                self.com_port,
                err)
            log_inverter.exception(msg)
            return False

    def stop(self):
        """
            Method will zero out the setpoint and it will switch the inverter power off.
        """
        try:
            self.set_point = 0
            self.send_state(state=0)
            log_inverter.info('Issued a STOP command to inverter on port %s.', self.com_port)
            return True
        except Exception as err:
            log_inverter.exception('Cannot stop the inverter on port %s. Exception is: %s',self.com_port, err)
            return False

    def stop_and_release(self):
        """
            Use this method when the test case has ended
        """
        try:
            self.stop()
            self.close_coms()
            log_inverter.info('Stopped and released inverter on port %s.', self.com_port)
        except Exception as err:
            log_inverter.exception('Was unable to stop and release inverter on port %s. Reason: %s.', self.com_port, err)

    def update_DC_frame(self, message):
        """
            Updates the self.dc_current and self.dc_voltage variables.
        """
        try:
            self.inverter_variables['dc_voltage'] = int.from_bytes(message[7:9], byteorder='little') / 100
            charging_current = int.from_bytes(message[9:12], byteorder='little')
            discharging_current = int.from_bytes(message[12:15], byteorder='little')
            self.inverter_variables['dc_current'] = (discharging_current  - charging_current) / 10
            
            if self.last_values_update_timestamp == 0:
                #dc_capacity = format(abs(self.inverter_variables['dc_current']) * (time.time() - self.last_values_update_timestamp) / 3600, '.3f')
                #log_inverter.info('Capacity before converting to Float is: %s', dc_capacity)
                self.inverter_variables['dc_capacity'] = 0  # float(dc_capacity)
                log_inverter.info('Fist capacity measurement taken: %s', self.inverter_variables['dc_capacity'])
            else:
                self.inverter_variables['dc_capacity'] = float(format(self.inverter_variables['dc_capacity'] + (abs(self.inverter_variables['dc_current']) * (time.time() - self.last_values_update_timestamp) / 3600), '.3f'))
                log_inverter.info('Pack capacity measurement taken: %s', self.inverter_variables['dc_capacity'])

            self.last_values_update_timestamp = time.time()
            return True
        except Exception as err:
            log_inverter.exception('Could not update the DC frame because %s', err)
            return False

    def update_AC_frame(self, message):
        """
            Updates the self.ac_voltage and self.ac_current
        """
        try:
            self.inverter_variables['ac_voltage'] = int.from_bytes(message[7:9], byteorder='little') / 100
            self.inverter_variables['ac_current'] = ctypes.c_int16(int.from_bytes(message[9:11], byteorder='little')).value / 100

            return True
        except Exception as err:
            log_inverter.exception('Could not update AC frame', err)
            return False

    def get_info_frame_reply(self):
        """
            This function should run continuously and run onto all the incoming bytestream after 'Get frame' Command
            The function will automatically call an update of the self.ac/dc-voltage/current variables if a suitable reply is detected.
        """
        flag = 0
        r = 15
        frame = {}
        start = time.time()
        timeout = 2
        while 1:
            message = b'\x0f\x20'
            
            try:
                byte = self.get_next_byte()
                if byte == b'\x0f':
                    new_byte = self.get_next_byte()
                    if new_byte == b' ':
                        for i in range(r):
                            new_byte = self.get_next_byte()
                            message += new_byte
    
                        if message[6] == 12:
                            #log_inverter.info('DC message: ', str(message))
                            frame['DC'] = message
                            self.update_DC_frame(message)
                            flag += 1
                            log_inverter.warning('REceived DC frame, flag is: %s', flag)
    
                        elif message[6] == 8:  # we have AC
                            #log_inverter.info('AC message: ', str(message))
                            frame['AC'] = message
                            self.update_AC_frame(message)
                            flag += 1
                            log_inverter.warning('REceived AC frame, flag is: %s', flag)
                        else:
                            # TODO:
                            # replace this with a log msg
                            log_inverter.warning('Message not recognised')
                    else:
                        pass
                if time.time() > start + timeout:
                    frame['timeout'] = True
                    log_inverter.warning('Ended through timeout. Messages received: %s', frame)
                    return frame
    
                if flag == 2 or time.time() > start + timeout:
                    #log_inverter.info('Got both messages: %s', frame)
                    return frame
            except Exception as err:
                log_inverter.exception(err)
                return frame


class VictronMultiplusMK2VCPFake(object):
    """
    Victron Multiplus inverter with MK2b interface (tested for USB-RS232)

    1. Call 'send setpoint' periodically (5 seconds)
    2. Call 'request_frames_update' periodically (5 seconds)
    3. Call '

    """

    inverter_instances = {}

    def __init__(self, com_port):
        self.set_point = 0
        self.set_point_timestamp = None
        self.last_values_update_timestamp = 0;
        self.inverter_variables = {
            'dc_current': 0,
            'dc_voltage': 0,
            'ac_current': 0,
            'ac_voltage': 0,
            'dc_capacity': 0,  # Amps Hour (Ah)
            'dc_energy': 0  # Wh
        }

        self.com_port = com_port
        try:
            file_path = os.path.join(settings.BASE_DIR, self.com_port)
            self.serial_handle = open(file_path, 'a+')
            log_inverter.info('Opened inverter file %s', file_path)
        except Exception as err:
            log_inverter.exception('Could not open port to inverter on %s. Error is: %s', self.com_port, err)
        log_inverter.info('Opened port to inverter on %s', self.com_port)

    def close_coms(self):
        """
            Closes the serial resource for the inverter
        """
        self.serial_handle.close()
        log_inverter.info('Closed port to inverter on %s', self.com_port)
        return True

    def prepare_inverter(self):
        """
            This method will ensure the inverter is in a state ready to be used during the test.
            1. It will configure the VE bus
            2. It will verify that the comport is open and if it is not it will attempt to open it.
        """
        try:
            if self.serial_handle:
                self.configure_ve_bus()
                log_inverter.info('-PREPARE INVERTER- Configured VE bus for inverter on port: %s', self.com_port)
                return True
            else:
                file_path = os.path.join(settings.BASE_DIR, self.com_port)
                self.serial_handle = open(file_path, 'r+')
                self.configure_ve_bus()
                log_inverter.info('Configured VE bus for inverter on port: %s', self.com_port)
                return True
        except Exception as err:
            log_inverter.exception('Error encountered in preparing the inverter for test on port: %s. Error is: %s.',
                                   self.com_port, err)
            return False

    def configure_ve_bus(self):
        """
            This method does the start-up procedure on the inverter (resets the Mk2 etc)
        """
        try:
            time.sleep(0.4)
            self.serial_handle.write('VE Bus configure for inverter on port {}'.format(self.com_port))
            log_inverter.info('VE Bus configure for inverter on port %s', self.com_port)
            return True
        except Exception as err:
            log_inverter.exception('Initializing VE bus protocol failed on port %s because %s', self.com_port, err)
            return False

    def send_setpoint(self):
        """
            This method sends the setpoint to the inverter (self.setpoint)
        """
        try:
            time.sleep(0.5)
            self.serial_handle.write('Setpoint sent. Setpoint is: {}'.format(self.set_point))
            log_inverter.info('Setpoint sent. Setpoint is: %s', self.set_point)
            return True
        except Exception as err:
            log_inverter.exception('Sending power setpoint to the PU failed on port %s because %s', self.com_port, err)
            return False

    def request_DC_frame(self):
        """
            Sends request for a DC frame on the VE bus
            com_port_handle:
        """
        try:
            time.sleep(0.2)
            self.serial_handle.write('DC frame Requested (message sent) on port {}'.format(self.com_port))
            log_inverter.info('DC frame Requested (message sent) on port %s', self.com_port)
            return True
        except Exception as err:
            log_inverter.exception('Requesting the DC frame (maybe serial timeout?) failed on %s because %s',
                                   self.com_port, err)
            return False

    def request_AC_frame(self):
        """
            Sends request for AC frame on the VE bus
        """
        try:
            time.sleep(0.2)
            self.serial_handle.write('AC frame Requested (message sent) on port: {}'.format(self.com_port))
            log_inverter.info('AC frame Requested (message sent) on port: %s', self.com_port)
            return True
        except Exception as err:
            log_inverter.exception('Requesting the AC frame (maybe serial timeout?) failed on %s because %s',
                                   self.com_port, err)
            return False

    def make_state_message(self, state=0):
        """
            Method will return the MK2 command for switching states.
            Select state = 0 for off. State = 1 for on.
        """
        # b'\x09\xFF\x53\x03\x00\xFF\x01\x00\x00\x04\x9E'
        try:
            if state == 0:
                switch_state = b'\x04'
            elif state == 1:
                switch_state = b'\x03'
            else:
                switch_state = b'\x04'

            message = b'\x09\xff\x53'
            message = message + switch_state
            message = message + b'\x00\xff'
            message = message + b'\x01'
            message = message + b'\x00\x00\x04'
            message = message + b'\xff'
            message_array = bytearray(message)
            s = 0
            for b in reversed(range(len(message) - 1)):
                s = s - message[b];
            message_array[-1] = s % 256
            return bytes(message_array)
        except Exception as err:
            log_inverter.exception('Cannot make state message on port %s. Error is: %s', self.com_port, err)
            return False

    def send_state(self, state=0):
        """
            Method will send a state command to the inverter.
            Use state to choose state.
        """
        try:
            command = self.make_state_message(state=state)
            self.serial_handle.write('Switched to state {} the inverter on port {}.'.format(state, self.com_port))
            log_inverter.info('Switched to state %s the inverter on port %s. Used command: %s.', state, self.com_port,
                              str(command))
            return True
        except Exception as err:
            log_inverter.exception('Cannot send new state to inverter on port: %s. Error is: %s', self.com_port, err)
            return False

    def request_frames_update(self):
        """
            Call this method periodically to update the readings from the Inverter
        """
        try:
            self.request_AC_frame()
            time.sleep(0.1)
            self.request_DC_frame()
            time.sleep(0.1)
            log_inverter.info('Requested DC and AC frames on inverter')
            return True
        except Exception as err:
            log_inverter.exception('Cannot update frames.', err)
            return False

    def charge(self):
        """
            Method can be called and it will automatically configure the inverter to charge with a set amount
        """
        global FAKE_STEP
        FAKE_STEP = 'charge'
        try:
            self.set_point = settings.CHARGING_SETPOINT
            # self.send_state(1)
            log_inverter.info('Charge mode set on inverter.')
            return True
        except Exception as err:
            log_inverter.exception('Cannot set charge mode on port %s. Exception is: %s', self.com_port, err)
            return False

    def invert(self):
        """
            Method can be called and it will automatically configure the iverter to invert with a set amount
        """
        global FAKE_STEP
        FAKE_STEP = 'discharge'
        try:
            self.set_point = settings.INVERTING_SETPOINT
            # self.send_state(1)
            return True
        except Exception as err:
            log_inverter.exception('Cannot set invert mode on port %s. Exception is: %s', self.com_port, err)
            return False

    def rest(self):
        """
            Method will zero out the setpoint. The inverter will be kept on.
        """
        global FAKE_STEP
        FAKE_STEP = 'rest'
        try:
            self.set_point = 0
            self.set_point_timestamp = time.time()
            # self.send_state(1)
            return True
        except Exception as err:
            msg = 'Cannot set rest mode. The inverter on port {} is still running? Exception is: {}'.format(
                self.com_port, err)
            log_inverter.exception(msg)
            return False

    def stop(self):
        """
            Method will zero out the setpoint and it will switch the inverter power off.
        """
        try:
            self.set_point = 0
            self.send_state(state=0)
            log_inverter.info('Issued a STOP command to inverter on port %s.', self.com_port)
            return True
        except Exception as err:
            log_inverter.exception('Cannot stop the inverter on port %s. Exception is: %s', self.com_port, err)
            return False

    def stop_and_release(self):
        """
            Use this method when the test case has ended
        """
        try:
            self.stop()
            self.close_coms()
            log_inverter.info('Stopped and released inverter on port %s.', self.com_port)
        except Exception as err:
            log_inverter.exception('Was unable to stop and release inverter on port %s. Reason: %s.', self.com_port,
                                   err)

    def update_DC_frame(self, message=''):
        """
            Updates the self.dc_current and self.dc_voltage variables.
        """
        try:
            self.inverter_variables['dc_voltage'] = uniform(20, 40)
            if self.set_point:
                current = uniform(5, 10)
            else:
                current = uniform(10, 20) * (-1)
            self.inverter_variables['dc_current'] = current

            if self.last_values_update_timestamp == 0:
                self.inverter_variables['dc_capacity'] = float(format(
                    self.inverter_variables['dc_current'] * (time.time() - self.last_values_update_timestamp) / 3600,
                    '.5f'))
                log_inverter.info('Fist capacity measurement taken: %s', self.inverter_variables['dc_capacity'])
            else:
                self.inverter_variables['dc_capacity'] = float(format(self.inverter_variables['dc_capacity'] + (
                    self.inverter_variables['dc_current'] * (time.time() - self.last_values_update_timestamp) / 3600),
                                                                      '.5f'))
                log_inverter.info('Pack capacity measurement taken: %s', self.inverter_variables['dc_capacity'])

            self.last_values_update_timestamp = time.time()
            return True
        except Exception as err:
            log_inverter.exception('Could not update the DC frame because %s', err)
            return False

    def update_AC_frame(self, message=''):
        """
            Updates the self.ac_voltage and self.ac_current
        """
        try:
            self.inverter_variables['ac_voltage'] = uniform(230, 240)
            self.inverter_variables['ac_current'] = uniform(1, 5)

            return True
        except Exception as err:
            log_inverter.exception('Could not update AC frame', err)
            return False

    def get_info_frame_reply(self):
        """
            This function should run continuously and run onto all the incoming bytestream after 'Get frame' Command
            The function will automatically call an update of the self.ac/dc-voltage/current variables if a suitable reply is detected.
        """
        flag = 0
        frame = {}
        start = time.time()
        timeout = 2
        try:
            byte = self.serial_handle.read(2)
            frame['DC'] = 'Got DC data'
            self.update_DC_frame()
            flag += 1
            log_inverter.warning('REceived DC frame, flag is: %s', flag)
            # log_inverter.info('AC message: ', str(message))
            frame['AC'] = 'Got AC data'
            self.update_AC_frame()
            flag += 1
            log_inverter.warning('REceived AC frame, flag is: %s', flag)
            if time.time() > start + timeout:
                frame['timeout'] = True
                log_inverter.warning('Ended through timeout. Messages received: %s', frame)
                return frame

            if flag == 2 or time.time() > start + timeout:
                # log_inverter.info('Got both messages: %s', frame)
                return frame
        except Exception as err:
            log_inverter.exception(err)
            return frame


class UsbIssBattery(object):
    """
        USB-ISS connected OnSystems 1st life battery pack
    """
    battery_instances = {}

    def __init__(self, com_port):
        self.status_message = b''

        self.pack_variables = {'serial_number': 0,
                          'cv_1': 0, 'cv_2': 0,
                          'cv_3': 0, 'cv_4': 0,
                          'cv_5': 0, 'cv_6': 0,
                          'cv_7': 0, 'cv_8': 0,
                          'cv_9': 0, 'cv_max': 0,
                          'cv_min': 0,
                          'mosfet_temp': 0, 'pack_temp': 0,
                          'dc_current': 0,
                          'cell_overvoltage_level_1': False,
                          'cell_overvoltage_level_2': False,
                          'cell_undervoltage_level_1': False,
                          'cell_undervoltage_level_2': False,
                          'is_not_safe_level_1': False,
                          'is_not_safe_level_2': False,
                          'pack_overcurrent': False,
                          'pack_overtemperature_mosfets': False,
                          'pack_overtemperature_cells': False,
                          'is_on': False
                          }
        self.last_status_update = time.time()
        self.start_timestamp = time.time()

        self.com_port = com_port

        try:
            self.serial_handle = serial.Serial()
            self.serial_handle.port = '{sep}{path}{sep}{com}'.format(sep=os.path.sep, path='dev', com=self.com_port)
            self.serial_handle.baudrate = 19200
            self.serial_handle.timeout = 0.5
            self.serial_handle.parity = 'N'
            self.serial_handle.setDTR(False)
            self.serial_handle.bytesize = serial.EIGHTBITS
            self.serial_handle.stopbits = serial.STOPBITS_TWO
            self.serial_handle.open()
        except Exception as err:
            log_battery.exception('Cannot open comms to battery on port %s because of the following error: %s', self.com_port, err)

    def configure_USB_ISS(self):
        """
            This function will take care of configuring the USB-> I2C bridge.
        """
        try:
            message = b'\x5A\x01'
            self.serial_handle.write(message)
            time.sleep(0.5)
            self.serial_handle.read(10)

            # Setting the mode
            I2C_mode_message = b'\x5A\x02\x60\x04'
            self.serial_handle.write(I2C_mode_message)
            time.sleep(0.5)
            self.serial_handle.read(10)
            log_battery.info('Configure the ISS adapter for com: %s', self.com_port)
            return True
        except Exception as err:
            log_battery.exception('Error when configuring the USB ISS bridge on com %s. Error is: %s', self.com_port, err)
            return False

    def turn_pack_on(self):
        """
            This method turns the pack on. Note: function needs to be send every 10 sec minimum to maintain pack on.
            input: com_port handler
            output: True if successful. False otherwise
        """
        try:
            test = b'\x57\x01\x35\x40\x04\x01\x03\x00\x48\x03'
            self.serial_handle.write(test)
            time.sleep(0.1)
            test = b'\x57\x01\x30\x41\x20\x03'
            self.serial_handle.write(test)
            time.sleep(0.1)
            log_battery.info('Pack on port %s has been turned on.', self.com_port)
            return True
        except Exception as err:
            log_battery.exception('Error when turning pack on port: %s. Pack serial number: %s', self.com_port, self.serial_number)
            return False

    def close_coms(self):
        """
            Closes resources for battery serial
        """
        try:
            self.serial_handle.close()
            log_battery.info('Closed battery port %s.', self.com_port)
            return True
        except Exception as err:
            log_battery.exception('Could not close battery port %s because %s', self.com_port, err)

    def get_pack_status(self):
        """
            Method gets the status message from the battery pack. It populates self.status with the reply
        """
        try:
            message = b'\x57\x01\x34\x40\x01\x00\x00\x41\x03'
            self.serial_handle.write(message)
            time.sleep(0.2)
            reply = self.serial_handle.read(10)
            message = b'\x54\x41\x3E' #this matches the length of the message read
            self.serial_handle.reset_input_buffer()
            self.serial_handle.write(message)
            time.sleep(0.2)
            self.status_message = self.serial_handle.read(100)

            crc = 0
            # what is the hell? is that a dict or a list?
            crc_received = int.from_bytes({self.status_message[-2], self.status_message[-1]}, byteorder='little')
            for i in range(60):
                crc = crc + self.status_message[i]

            if crc == crc_received:
                return True
            else:
                log_battery.info('Status message CRC failed for battery on port %s.', self.com_port)
                return False
        except Exception as err:
            log_battery.exception('Could not refresh pack values on port %s. Reason: %s.', self.com_port, err)
            return False

    def update_values(self):
        """
            Call this function to update all the model attributes that are read from the battery.
        """
        try:
            if not self.get_pack_status():
                log_battery.info('Either CRC error or exception when reading from I2C - values discarded. Port: %s', self.com_port)
                return {}
            self.get_serial_number()
            self.get_pack_current()
            self.get_cell_voltages()
            self.get_temperatures()
            log_battery.info('Pack values updated')
#             log_battery.info('Pack cell voltages: %s, %s, %s, %s, %s, %s, %s, %s, %s', self.cv_1,
#                      self.cv_2, self.cv_3, self.cv_4, self.cv_5, self.cv_6, self.cv_7, self.cv_8, self.cv_9)
            self.last_status_update = time.time()
            return self.pack_variables
        except Exception as err:
            log_battery.exception('Error encountered while updating pack values. Exception is: %s', err)
            return {}

    def get_serial_number(self):
        """
            Method extract the serial number out of the status message. Populates self.serial_number
        """
        try:
            self.pack_variables['serial_number'] = int.from_bytes(self.status_message[56:60], byteorder='little')
            #log_battery.exception('Serial number of Battery on port %s is %s.', self.com_port, self.pack_variables['serial_number'])
            return True
        except Exception as err:
            log_battery.exception('Error encountered while updating the serial number on com: %s. Error is: %s', self.com_port, err)
            return False

    def get_pack_current(self):
        """
            Extract the pack current out of the battery message reply (get_Status command). Updates self.dc_current
            input: none
            output: True if successful. False otherwise
        """
        try:
            temp_variable = struct.unpack('<f', self.status_message[50:54])
            self.pack_variables['dc_current'] = "{0:.3f}".format(temp_variable[0])
            return True
        except Exception as err:
            log_battery.exception('Cannot refresh pack current value for batt on port %s. Reason is: %s.', self.com_port, err)
            return False

    def get_cell_voltages(self):
        """
            Function gets cell voltages out of self.status and populates cv1 -> cv9 as well as cv_max and cv_min
        """
        try:
            data = self.status_message
            C1 = (struct.unpack('>f',struct.pack("B",data[17])+struct.pack("B", data[16]) + struct.pack("B", data[15])+struct.pack("B",data[14])))
            C2 = (struct.unpack('>f',struct.pack("B",data[21])+struct.pack("B", data[20]) + struct.pack("B", data[19])+struct.pack("B",data[18])))
            C3 = (struct.unpack('>f',struct.pack("B",data[25])+struct.pack("B", data[24]) + struct.pack("B", data[23])+struct.pack("B",data[22])))
            C4 = (struct.unpack('>f',struct.pack("B",data[29])+struct.pack("B", data[28]) + struct.pack("B", data[27])+struct.pack("B",data[26])))
            C5 = (struct.unpack('>f',struct.pack("B",data[33])+struct.pack("B", data[32]) + struct.pack("B", data[31])+struct.pack("B",data[30])))
            C6 = (struct.unpack('>f',struct.pack("B",data[37])+struct.pack("B", data[36]) + struct.pack("B", data[35])+struct.pack("B",data[34])))
            C7 = (struct.unpack('>f',struct.pack("B",data[41])+struct.pack("B", data[40]) + struct.pack("B", data[39])+struct.pack("B",data[38])))
            C8 = (struct.unpack('>f',struct.pack("B",data[45])+struct.pack("B", data[44]) + struct.pack("B", data[43])+struct.pack("B",data[42])))
            C9 = (struct.unpack('>f',struct.pack("B",data[49])+struct.pack("B", data[48]) + struct.pack("B", data[47])+struct.pack("B",data[46])))

            self.pack_variables['cv_1'] = "{0:.3f}".format(C1[0])
            self.pack_variables['cv_2'] = "{0:.3f}".format(C2[0])
            self.pack_variables['cv_3'] = "{0:.3f}".format(C3[0])
            self.pack_variables['cv_4'] = "{0:.3f}".format(C4[0])
            self.pack_variables['cv_5'] = "{0:.3f}".format(C5[0])
            self.pack_variables['cv_6'] = "{0:.3f}".format(C6[0])
            self.pack_variables['cv_7'] = "{0:.3f}".format(C7[0])
            self.pack_variables['cv_8'] = "{0:.3f}".format(C8[0])
            self.pack_variables['cv_9'] = "{0:.3f}".format(C9[0])

            self.pack_variables['cv_min'] = min([self.pack_variables['cv_1'], self.pack_variables['cv_2'], self.pack_variables['cv_3'],
                               self.pack_variables['cv_4'], self.pack_variables['cv_5'], self.pack_variables['cv_6'],
                               self.pack_variables['cv_7'], self.pack_variables['cv_8'], self.pack_variables['cv_9'] ])

            self.pack_variables['cv_max'] = max([self.pack_variables['cv_1'], self.pack_variables['cv_2'], self.pack_variables['cv_3'],
                               self.pack_variables['cv_4'], self.pack_variables['cv_5'], self.pack_variables['cv_6'],
                               self.pack_variables['cv_7'], self.pack_variables['cv_8'], self.pack_variables['cv_9'] ])
            return True
        except Exception as err:
            log_battery.exception('Could not refresh cell voltages on port %s. Reason: %s.', self.com_port, err)
            return False

    def get_temperatures(self):
        """
            method extracts the temperature readouts from self.status and populates mosfet and pack temperature readings
        """
        try:
            mosfet_temp= struct.unpack('<f', self.status_message[6:10])
            pack_temp = struct.unpack('<f', self.status_message[10:14])

            self.pack_variables['mosfet_temp'] = "{0:.3f}".format(mosfet_temp[0])
            self.pack_variables['pack_temp'] = "{0:.3f}".format(pack_temp[0])
            return True
        except Exception as err:
            log_battery.exception('Could not refresh temperature values for pack on port %s. Exception is: %s.', self.com_port, err)
            return False

    def check_safety_level_1(self):
        """
            Method returns True if everything OK. False if the level 1 limits have been exceeded.
        """
        if self.last_status_update < self.start_timestamp + 10:
            #There has been no update of the cell readings since the start of the test. 
            log_battery.info('Attempted to run Safety Level 1 routine - battery data will not update in the first 10 seconds of the test.')
            return True 
        
        try:
            c_ovp = float(self.pack_variables['cv_max']) > settings.BATTERY_CELL_OVP_LEVEL_1
            c_uvp = float(self.pack_variables['cv_min']) < settings.BATTERY_CELL_UVP_LEVEL_1
            log_battery.info('Verified level 1 safety conditions on com %s. Max Cell is: %s, Min Cell is: %s.', 
                             self.com_port, 
                             self.pack_variables['cv_max'],
                             self.pack_variables['cv_min'])
                            
            if c_uvp:
                log_battery.info('Cell undervoltage detected, level 1 on port: %s', self.com_port)
                self.pack_variables['cell_undervoltage_level_1'] = True
                self.pack_variables['is_not_safe_level_1'] = True
                return  False
            elif c_ovp:
                log_battery.info('Cell overvoltage detected, level 1 on port: %s', self.com_port)
                self.pack_variables['cell_overvoltage_level_1'] = True
                self.pack_variables['is_not_safe_level_1'] = True
                return False
            else:
                log_battery.info('No level 1 protection triggered on port: %s.', self.com_port)
                return True
        except Exception as err:
            log_battery.exception('Exception in checking cell safety level 1 on port %s. Exception is: %s', self.com_port, err)
            return False

    def check_safety_level_2(self):
        """
            Method return True if everything OK. False if a test stop trigger should be issued.
        """
        
        if self.last_status_update < self.start_timestamp + 10:
            #There has been no update of the cell readings since the start of the test. 
            log_battery.info('Attempted to run Safety Level 2 routine - battery data will not update in the first 10 seconds of the test.')
            return True 
        
        try:
            c_ovp = float(self.pack_variables['cv_max']) > settings.BATTERY_CELL_OVP_LEVEL_2
            c_uvp = float(self.pack_variables['cv_min']) < settings.BATTERY_CELL_UVP_LEVEL_2
            ocp = float(self.pack_variables['dc_current']) > settings.BATTERY_OCP
            ovt_mosfet = float(self.pack_variables['mosfet_temp']) > settings.MOSFETS_OVERTEMPERATURE
            ovt_cells = float(self.pack_variables['pack_temp']) > settings.CELLS_OVERTEMPERATURE
            
            log_battery.info('Verified level 2 safety conditions on com %s. Max Cell is: %s, Min Cell is: %s.', 
                             self.com_port, 
                             self.pack_variables['cv_max'],
                             self.pack_variables['cv_min'])
            if c_ovp:
                log_battery.info('Cell over-voltage, level 2. Port: %s', self.com_port)
                self.pack_variables['cell_overvoltage_level_2'] = True
                self.pack_variables['is_not_safe_level_2'] = True
                return False
            elif c_uvp:
                log_battery.info('Cell under-voltage, level 2. Port: %s', self.com_port)
                self.pack_variables['cell_undervoltage_level_2'] = True
                self.pack_variables['is_not_safe_level_2'] = True
                return False
            elif ocp:
                log_battery.info('Battery over-current. Port: %s', self.com_port)
                self.pack_variables['pack_overcurrent'] = True
                self.pack_variables['is_not_safe_level_2'] = True
                return False
            elif ovt_mosfet:
                log_battery.info('Over-temperature (mosfets) on port: %s', self.com_port)
                self.pack_variables['pack_overtemperature_mosfets'] = True
                self.pack_variables['is_not_safe_level_2'] = True
                return False
            elif ovt_cells:
                log_battery.info('Over-temperature (mosfets) on port: %s', self.com_port)
                self.pack_variables['pack_overtemperature_cells'] = True
                self.pack_variables['is_not_safe_level_2'] = True
                return False
            else:
                log_battery.info('No level 2 protection triggered on port: %s', self.com_port)
                return True
        except Exception as err:
            log_battery.exception('Error in checking safety level 2 on port %s. Exception is: %s', self.com_port, err)
            return False

    def stop_and_release(self):
        """
            Method shuts down the mosfets and releases the serial port
        """
        #self.turn_pack_off()
        self.close_coms()
    
    def clear_level_1_error_flag(self):
        """
            Method clears the level_1_error_flag
        """
        try:
            self.pack_variables['is_not_safe_level_1'] = False
            log_battery.info('Cleared LEVEL 1 Safety flag')
            return True
        except Exception as err:
            log_battery.exception('Unable to clear error flag level 1 in batt on port %s. Reason is %s', self.com_port, err)
            return False


def random_with_n_digits(n):
    range_start = 10**(n-1)
    range_end = (10**n)-1
    return randint(range_start, range_end)


class UsbIssBatteryFake(object):
    """
        USB-ISS connected OnSystems 1st life battery pack
    """
    battery_instances = {}

    def __init__(self, com_port):
        self.status_message = b''

        self.pack_variables = {'serial_number': 0,
                               'cv_1': 0, 'cv_2': 0,
                               'cv_3': 0, 'cv_4': 0,
                               'cv_5': 0, 'cv_6': 0,
                               'cv_7': 0, 'cv_8': 0,
                               'cv_9': 0, 'cv_max': 0,
                               'cv_min': 0,
                               'mosfet_temp': 0, 'pack_temp': 0,
                               'dc_current': 0,
                               'cell_overvoltage_level_1': False,
                               'cell_overvoltage_level_2': False,
                               'cell_undervoltage_level_1': False,
                               'cell_undervoltage_level_2': False,
                               'is_not_safe_level_1': False,
                               'is_not_safe_level_2': False,
                               'pack_overcurrent': False,
                               'pack_overtemperature_mosfets': False,
                               'pack_overtemperature_cells': False,
                               'is_on': False
                               }
        self.last_status_update = time.time()
        self.start_timestamp = time.time()

        self.com_port = com_port
        try:
            file_path = os.path.join(settings.BASE_DIR, self.com_port)
            self.serial_handle = open(file_path, 'a+')
            log_battery.info('Opened battery file for read/write: %s', file_path)
        except Exception as err:
            log_battery.exception('Cannot open comms to battery on port %s because of the following error: %s', self.com_port, err)

        # fake data used to populate pack variables
        self.fake_charging_data = {}
        for cell in range(9):
            self.fake_charging_data['cv_{}'.format(cell + 1)] = []
            for i in range(100):
                self.fake_charging_data['cv_{}'.format(cell+1)].append(uniform(3, 4))
            self.fake_charging_data['cv_{}'.format(cell+1)].sort()
        self.fake_discharging_data = {}
        for cell in range(9):
            self.fake_discharging_data['cv_{}'.format(cell + 1)] = []
            for i in range(100):
                self.fake_discharging_data['cv_{}'.format(cell+1)].append(uniform(2.9, 3.7))
            self.fake_discharging_data['cv_{}'.format(cell+1)].sort(reverse=True)

    def configure_USB_ISS(self):
        """
            This function will take care of configuring the USB-> I2C bridge.
        """
        try:
            log_battery.info('Configure the ISS adapter for com: %s', self.com_port)
            self.serial_handle.write('Configure the ISS adapter for com: {}'.format(self.com_port))
            return True
        except Exception as err:
            log_battery.exception('Error when configuring the USB ISS bridge on com %s. Error is: %s', self.com_port,
                                  err)
            return False

    def turn_pack_on(self):
        """
            This method turns the pack on. Note: function needs to be send every 10 sec minimum to maintain pack on.
            input: com_port handler
            output: True if successful. False otherwise
        """
        try:
            time.sleep(0.5)
            self.serial_handle.write('Pack on port {} has been turned on.'.format(self.com_port))
            log_battery.info('Pack on port %s has been turned on.', self.com_port)
            return True
        except Exception as err:
            log_battery.exception('Error when turning pack on port: %s.', self.com_port)
            return False

    def close_coms(self):
        """
            Closes resources for battery serial
        """
        self.serial_handle.close()
        log_battery.info('Closed battery port %s.', self.com_port)
        return True

    def get_pack_status(self):
        """
            Method gets the status message from the battery pack. It populates self.status with the reply
        """
        try:
            self.serial_handle.write('get pack status')
            time.sleep(0.2)
            self.status_message = self.serial_handle.read(5)
        except Exception as err:
            log_battery.exception('failed to get pack status %s', self.com_port)
            return False
        return True

    def update_values(self):
        """
            Call this function to update all the model attributes that are read from the battery.
        """
        try:
            if not self.get_pack_status():
                log_battery.info('Either CRC error or exception when reading from I2C - values discarded. Port: %s',
                                 self.com_port)
                return {}
            self.get_serial_number()
            self.get_pack_current()
            self.get_cell_voltages()
            self.get_temperatures()
            log_battery.info('Pack values updated')
            log_battery.info('Pack cell voltages: %s', json.dumps(self.pack_variables, indent=2))
            self.last_status_update = time.time()
            return self.pack_variables
        except Exception as err:
            log_battery.exception('Error encountered while updating pack values. Exception is: %s', err)
            return {}

    def get_serial_number(self):
        """
            Method extract the serial number out of the status message. Populates self.serial_number
        """
        try:
            self.pack_variables['serial_number'] = random_with_n_digits(5)
            return True
        except Exception as err:
            log_battery.exception('Error encountered while updating the serial number on com: %s. Error is: %s',
                                  self.com_port, err)
            return False

    def get_pack_current(self):
        """
            Extract the pack current out of the battery message reply (get_Status command). Updates self.dc_current
            input: none
            output: True if successful. False otherwise
        """
        try:
            self.pack_variables['dc_current'] = random_with_n_digits(1)
            return True
        except Exception as err:
            log_battery.exception('Cannot refresh pack current value for batt on port %s. Reason is: %s.',
                                  self.com_port, err)
            return False

    def get_cell_voltages(self):
        """
            Function gets cell voltages out of self.status and populates cv1 -> cv9 as well as cv_max and cv_min
        """
        try:
            if FAKE_STEP == 'charge':
                for i in range(9):
                    self.pack_variables['cv_{}'.format(i+1)] = "{0:.3f}".format(self.fake_charging_data['cv_{}'.format(i + 1)].pop(0))
            elif FAKE_STEP == 'discharge':
                for i in range(9):
                    self.pack_variables['cv_{}'.format(i+1)] = "{0:.3f}".format(self.fake_discharging_data['cv_{}'.format(i + 1)].pop(0))
            else:
                for i in range(9):
                    self.pack_variables['cv_{}'.format(i+1)] = "{0:.3f}".format(3.70000)

            self.pack_variables['cv_min'] = min(
                [self.pack_variables['cv_1'], self.pack_variables['cv_2'], self.pack_variables['cv_3'],
                 self.pack_variables['cv_4'], self.pack_variables['cv_5'], self.pack_variables['cv_6'],
                 self.pack_variables['cv_7'], self.pack_variables['cv_8'], self.pack_variables['cv_9']])

            self.pack_variables['cv_max'] = max(
                [self.pack_variables['cv_1'], self.pack_variables['cv_2'], self.pack_variables['cv_3'],
                 self.pack_variables['cv_4'], self.pack_variables['cv_5'], self.pack_variables['cv_6'],
                 self.pack_variables['cv_7'], self.pack_variables['cv_8'], self.pack_variables['cv_9']])
            return True
        except Exception as err:
            log_battery.exception('Could not refresh cell voltages on port %s. Reason: %s.', self.com_port, err)
            return False

    def get_temperatures(self):
        """
            method extracts the temperature readouts from self.status and populates mosfet and pack temperature readings
        """
        try:
            mosfet_temp = uniform(30, 80)
            pack_temp = uniform(30, 80)

            self.pack_variables['mosfet_temp'] = "{0:.3f}".format(mosfet_temp)
            self.pack_variables['pack_temp'] = "{0:.3f}".format(pack_temp)
            return True
        except Exception as err:
            log_battery.exception('Could not refresh temperature values for pack on port %s. Exception is: %s.',
                                  self.com_port, err)
            return False

    def check_safety_level_1(self):
        """
            Method returns True if everything OK. False if the level 1 limits have been exceeded.
        """
        if self.last_status_update < self.start_timestamp + 10:
            # There has been no update of the cell readings since the start of the test.
            log_battery.info("""
            Attempted to run Safety Level 1 routine 
            - battery data will not update in the first 10 seconds of the test.""")
            return True

        try:
            c_ovp = float(self.pack_variables['cv_max']) > settings.BATTERY_CELL_OVP_LEVEL_1
            c_uvp = float(self.pack_variables['cv_min']) < settings.BATTERY_CELL_UVP_LEVEL_1
            log_battery.info('Verified level 1 safety conditions on com %s. Max Cell is: %s, Min Cell is: %s.',
                             self.com_port,
                             self.pack_variables['cv_max'],
                             self.pack_variables['cv_min'])

            if c_uvp:
                log_battery.info('Cell undervoltage detected, level 1 on port: %s', self.com_port)
                self.pack_variables['cell_undervoltage_level_1'] = True
                self.pack_variables['is_not_safe_level_1'] = True
                return False
            elif c_ovp:
                log_battery.info('Cell overvoltage detected, level 1 on port: %s', self.com_port)
                self.pack_variables['cell_overvoltage_level_1'] = True
                self.pack_variables['is_not_safe_level_1'] = True
                return False
            else:
                log_battery.info('No level 1 protection triggered on port: %s.', self.com_port)
                return True
        except Exception as err:
            log_battery.exception('Exception in checking cell safety level 1 on port %s. Exception is: %s',
                                  self.com_port, err)
            return False

    def check_safety_level_2(self):
        """
            Method return True if everything OK. False if a test stop trigger should be issued.
        """

        if self.last_status_update < self.start_timestamp + 10:
            # There has been no update of the cell readings since the start of the test.
            log_battery.info(
                'Attempted to run Safety Level 2 routine - battery data will not update in the first 10 seconds of the test.')
            return True

        try:
            c_ovp = float(self.pack_variables['cv_max']) > settings.BATTERY_CELL_OVP_LEVEL_2
            c_uvp = float(self.pack_variables['cv_min']) < settings.BATTERY_CELL_UVP_LEVEL_2
            ocp = float(self.pack_variables['dc_current']) > settings.BATTERY_OCP
            ovt_mosfet = float(self.pack_variables['mosfet_temp']) > settings.MOSFETS_OVERTEMPERATURE
            ovt_cells = float(self.pack_variables['pack_temp']) > settings.CELLS_OVERTEMPERATURE

            log_battery.info('Verified level 2 safety conditions on com %s. Max Cell is: %s, Min Cell is: %s.',
                             self.com_port,
                             self.pack_variables['cv_max'],
                             self.pack_variables['cv_min'])
            if c_ovp:
                log_battery.info('Cell over-voltage, level 2. Port: %s', self.com_port)
                self.pack_variables['cell_overvoltage_level_2'] = True
                self.pack_variables['is_not_safe_level_2'] = True
                return False
            elif c_uvp:
                log_battery.info('Cell under-voltage, level 2. Port: %s', self.com_port)
                self.pack_variables['cell_undervoltage_level_2'] = True
                self.pack_variables['is_not_safe_level_2'] = True
                return False
            elif ocp:
                log_battery.info('Battery over-current. Port: %s', self.com_port)
                self.pack_variables['pack_overcurrent'] = True
                self.pack_variables['is_not_safe_level_2'] = True
                return False
            elif ovt_mosfet:
                log_battery.info('Over-temperature (mosfets) on port: %s', self.com_port)
                self.pack_variables['pack_overtemperature_mosfets'] = True
                self.pack_variables['is_not_safe_level_2'] = True
                return False
            elif ovt_cells:
                log_battery.info('Over-temperature (mosfets) on port: %s', self.com_port)
                self.pack_variables['pack_overtemperature_cells'] = True
                self.pack_variables['is_not_safe_level_2'] = True
                return False
            else:
                log_battery.info('No level 2 protection triggered on port: %s', self.com_port)
                return True
        except Exception as err:
            log_battery.exception('Error in checking safety level 2 on port %s. Exception is: %s', self.com_port, err)
            return False

    def stop_and_release(self):
        """
            Method shuts down the mosfets and releases the serial port
        """
        self.close_coms()

    def clear_level_1_error_flag(self):
        """
            Method clears the level_1_error_flag
        """
        try:
            self.pack_variables['is_not_safe_level_1'] = False
            log_battery.info('Cleared LEVEL 1 Safety flag')
            return True
        except Exception as err:
            log_battery.exception('Unable to clear error flag level 1 in batt on port %s. Reason is %s', self.com_port,
                                  err)
            return False
