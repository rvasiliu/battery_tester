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
from .log import log_battery as logb, log_inverter as logi

class VictronMultiplusMK2VCP(object):
    """
    Victron Multiplus inverter with MK2b interface (tested for USB-RS232)
    """
    # the only chance to survive is to use class attributes
    invertor_instances = {}

    def __init__(self, com_port):
        self.com_port = com_port
        
        try:
            self.serial_handle = serial.Serial()
            self.serial_handle.port = self.com_port
            self.serial_handle.baudrate = 2400
            self.serial_handle.timeout = 0.1
            self.serial_handle.setDTR(True)
            self.serial_handle.bytesize = serial.EIGHTBITS
            self.serial_handle.stopbits = serial.STOPBITS_ONE
            self.serial_handle.open()
        except Exception as err:
            logi.exception('Unable to create inverter connection on port: %s because: %s', self.com_port, err)


class UsbIssBattery(object):
    """
    USB-ISS connected OnSystems 1st life battery pack
    """
    # the only chance to survive is to use class attributes
    battery_instances = {}

    def __init__(self, com_port):
        self.com_port = com_port

        try:
            self.serial_handle = serial.Serial()
            self.serial_handle.port = self.com_port
            self.serial_handle.baudrate = 19200
            self.serial_handle.timeout = 0.1
            self.serial_handle.parity = 'N'
            self.serial_handle.setDTR(False)
            self.serial_handle.bytesize = serial.EIGHTBITS
            self.serial_handle.stopbits = serial.STOPBITS_TWO
        except Exception as err:
            logb.exception('Unable to create battery connection on port %s because: %s', self.com_port, err)
