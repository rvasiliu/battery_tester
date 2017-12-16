'''
Created on 15 Dec 2017

@author: Vas
'''
from _overlapped import NULL
'''
Utils module. Contains object class for the VCP serial configuration (using python's serial library)
1. Victron Multiplus inverter with MK2b interface (tested for USB-RS232)
2. USB-ISS connected OnSystems 1st life battery pack
'''
from django.conf import settings

from .log import log_inverter as log_inverter
from .log import log_battery as log_battery

import serial
import time

class VictronMultiplusMK2VCP(object):
    '''
    Victron Multiplus inverter with MK2b interface (tested for USB-RS232)
    
    1. Call 'send setpoint' periodically (5 seconds)
    2. Call 'request_frames_update' periodically (5 seconds)
    
    '''
    
    setpoint = 0
    
    def __init__(self, COMPORT):
        self.COMPORT = COMPORT
        
        try:
            self.serial_handle = serial.Serial()
            self.serial_handle.port = self.COMPORT
            self.serial_handle.baudrate = 2400
            self.serial_handle.timeout = 0.1
            self.serial_handle.setDTR(True)
            self.serial_handle.bytesize = serial.EIGHTBITS
            self.serial_handle.stopbits = serial.STOPBITS_ONE
            self.serial_handle.open()
            log_inverter.info('Opened port to inverter on %s', self.COMPORT)
        except Exception as err:
            log_inverter.exception('Could not open port to inverter on %s. Error is: %s', self.COMPORT, err)
            
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
            log_inverter.info('VE Bus configure for inverter on port %s', self.COMPORT)
            return True            
        except Exception as err:
            log_inverter.exception('Initializing VE bus protocol failed on port %s because %s', self.COMPORT, err)
            return False
        
    def send_setpoint(self):
        """
            This method sends the setpoint to the inverter (self.setpoint)
        """
        try:
            message_out = self.make_message_MK2()
            self.serial_handle.write(message_out)
            return True
        except Exception as err:
            log_inverter.exception('Sending power setpoint to the PU failed on port %s because %s', self.COMPORT, err)
            return False
     
    def make_message_MK2(self, setpoint):
        """
            This method return the setpoint command to send to the inverter. Uses self.setpoint.
        """
        try:
            d0 = b'\x05\xFF\x57\x32\x81\x00\xF2\x05\xff\x57\x34\x00\x00\x00' 
            d1 = bytearray(d0)
            if setpoint < 0:
                setpoint = 65535 + self.setpoint

            d1[11] = int(setpoint) % 256
            d1[12] = int(setpoint) >> 8
            s = 0
            for b in reversed(range(7,13)):
                s = s - d1[b]
            d1[13] = s % 256
            return d1
        except Exception as err:
            log_inverter.exception('Setpoint message construction failed on port %s because %s', self.COMPORT, err)
            return False
        
    def request_DC_frame(self):
        """
            Sends request for a DC frame on the VE bus
            comport_handle:
        """
        try:
            #self.thread_RX.start()  #Start monitoring messages from Power Unit
            message = b'\x03\xffF\x00\xb8'
            self.serial_handle.write(message)
            log_inverter.info('DC frame Requested on port %s', self.COMPORT)
            return True
        except Exception as err:
            log_inverter.exception('Requesting the DC frame (maybe serial timeout?) failed on %s because %s', self.COMPORT, err)
            return False
    
    def request_AC_frame(self):
        """
            Sends request for AC frame on the VE bus
        """
        try:
            message = b'\x03\xffF\x01\xb7'
            self.serial_handle.write(message)
            log_inverter.info('AC frame Requested on port: %s', self.COMPORT)
            return True
        except Exception as err:
            log_inverter.exception('Requesting the AC frame (maybe serial timeout?) failed on %s because %s', self.COMPORT, err)
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
            message_array[-1] = S%256
            return bytes(message_array)
        except Exception as err:
            log_inverter.exception('Cannot make state message on port %s. Error is: %s', self.COMPORT, err)
            return False

    def send_state(self, state=0):
        """
            Method will send a state command to the inverter.
            Use state to choose state.
        """
        try:
            self.serial_handle.write(self.make_state_message(state))
            log_inverter.info('Switched to state %s the inverter on port %s.', state, self.COMPORT)
            return True
        except Exception as err:
            log_inverter.exception('Cannot send new state to inverter on port: %s. Error is: %s', self.COMPORT, err)
            return False   
        
    def get_next_byte(self):
        """
            Use this function to read a single byte from the serial port
        """
        try:
            byte_in = self.ser_PU.read(1)
            return byte_in
        except Exception as err:
            log_inverter.exception('Unable to get next byte from inverter on port: %s. Error is: %s', self.COMPORT, err)
            return False
        
    def request_frames_update(self):
        """
            Call this method periodically to update the readings from the Inverter
        """
        try:
            self.request_AC_frame() 
            self.time.sleep(0.1)
            self.request_DC_frame()
            self.time.sleep(0.1)
            return True
        except Exception as err:
            log_inverter.exception('Cannot update frames.', err)
            return False
     
    def charge(self):
        """
            Method can be called and it will automatically configure the inverter to charge with a set amount
        """
        try:
            self.setpoint = settings.CHARGING_SETPOINT
            self.send_state(1)
            return True
        except Exception as err:
            log_inverter.exception('Cannot set charge mode on port %s. Exception is: %s',self.COMPORT, err)
            return False

    def invert(self, comport_handle):
        """
            Method can be called and it will automatically configure the iverter to invert with a set amount
        """
        try:
            self.setpoint = settings.INVERTING_SETPOINT
            self.send_state(1)
            return True
        except Exception as err:
            log_inverter.exception('Cannot set invert mode on port %s. Exception is: %s',self.COMPORT, err)
            return False

    def rest(self, comport_handle):
        """
            Method will zero out the setpoint. The inverter will be kept on.
        """
        try:
            self.setpoint = 0
            self.send_state(1)
            return True
        except Exception as err:
            log_inverter.exception('Cannot set rest mode. The inverter on port %s ',
                                    'is still running? Exception is: %s', self.COMPORT, err)
            return False

    def stop(self, comport_handle):
        """
            Method will zero out the setpoint and it will switch the inverter power off.
        """
        try:
            self.setpoint = 0
            self.send_state(0)
            return True
        except Exception as err:
            log_inverter.exception('Cannot stop the inverter on port %s. Exception is: %s',self.COMPORT, err)
            return False 
     
     
        
class UsbIssBattery(object):
    '''
    USB-ISS connected OnSystems 1st life battery pack
    '''  
    def __init__(self, COMPORT):
        self.COMPORT = COMPORT

        try:
            self.serial_handle = serial.Serial()
            self.serial_handle.port = self.COMPORT
            self.serial_handle.baudrate = 19200
            self.serial_handle.timeout = 0.1
            self.serial_handle.parity = 'N'
            self.serial_handle.setDTR(False)
            self.serial_handle.bytesize = serial.EIGHTBITS
            self.serial_handle.stopbits = serial.STOPBITS_TWO
        except Exception as err:
            log_battery.exception('Cannot open comms to battery on port %s because of the following error: %s', self.COMPORT, err)

    def turn_pack_on(self, comport_handle):
        '''
            This method turns the pack on. Note: function needs to be send every 10 sec minimum to maintain pack on.
            input: comport handler
            output: True if successful. False otherwise
        '''
        try:
            test = b'\x57\x01\x35\x40\x04\x01\x03\x00\x48\x03'
            self.serial_handle.write(test)
            time.sleep(0.01)
            test = b'\x57\x01\x30\x41\x20\x03'
            self.serial_handle.write(test)
            time.sleep(0.01)
            log_battery.info('Pack on port %s has been turned on.', self.COMPORT)
            return True
        except Exception as err:
            log_battery.exception('Error when turning pack on port: %s. Pack serial number: %s', self.COMPORT, self.serial_number)
            return False


        
