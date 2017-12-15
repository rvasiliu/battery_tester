'''
Created on 15 Dec 2017

@author: Vas
'''
'''
Utils module. Contains object class for the VCP serial configuration (using python's serial library)
1. Victron Multiplus inverter with MK2b interface (tested for USB-RS232)
2. USB-ISS connected OnSystems 1st life battery pack
'''

import serial

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
        except:
            pass
            
            
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
