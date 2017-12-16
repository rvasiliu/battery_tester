'''
Created on 15 Dec 2017

@author: Vas
'''
'''
Utils module. Contains object class for the VCP serial configuration (using python's serial library)
1. Victron Multiplus inverter with MK2b interface (tested for USB-RS232)
2. USB-ISS connected OnSystems 1st life battery pack
'''
from .log import log_inverter as log_inverter
from .log import log_battery as log_battery


import serial
import time

class VictronMultiplusMK2VCP(object):
    '''
    Victron Multiplus inverter with MK2b interface (tested for USB-RS232)
    '''
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
            log.info('VE Bus configured.')
            return True            
        except Exception as err:
            log.exception('Initializing VE bus protocol failed because %s', err)
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
        except:
            pass
