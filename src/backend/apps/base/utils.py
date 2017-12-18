"""
Created on 15 Dec 2017

@author: Vas

Utils module. Contains object class for the VCP serial configuration (using python's serial library)
1. Victron Multiplus inverter with MK2b interface (tested for USB-RS232)
2. USB-ISS connected OnSystems 1st life battery pack
"""
from django.conf import settings

from .log import log_inverter as log_inverter
from .log import log_battery as log_battery

import serial
import time
import struct
from backend.apps.base.log import log_test_case


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
        self.inverter_variables = {
            'dc_current': 0,
            'dc_voltage': 0,
            'ac_current': 0,
            'ac_voltage': 0
        }

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
                return True
            else:
                self.serial_handle.open()
                self.configure_ve_bus()
                return True
        except Exception as err:
            log_test_case.exception('Error encountered in preparing the inverter for tet on port: %s. Error is: %s.', self.com_port, err)
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
            log_inverter.info('DC frame Requested on port %s', self.com_port)
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
            log_inverter.info('AC frame Requested on port: %s', self.com_port)
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
            self.serial_handle.write(self.make_state_message(state))
            log_inverter.info('Switched to state %s the inverter on port %s.', state, self.com_port)
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
            self.set_point = settings.CHARGING_SETPOINT
            self.send_state(1)
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
            self.send_state(1)
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
            self.send_state(1)
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
            self.send_state(0)
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
            return True
        except Exception as err:
            log_inverter.exception('Was unable to stop and release inverter on port %s. Reason: %s.', self.com_port, err)
            return False


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
                          'is_cell_overvoltage_level_1': False,
                          'is_cell_overvoltage_level_2': False,
                          'is_cell_undervoltage_level_1': False,
                          'is_cell_undervoltage_level_2': False,
                          'is_not_safe_level_1': False,
                          'is_not_safe_level_2': False,
                          'is_pack_overcurrent': False,
                          'is_overtemperature_mosfets': False,
                          'is_overtemperature_cells': False,
                          'is_on': False,
                          'last_status_update': time.time()
                          }

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
            log_battery.exception('Cannot open comms to battery on port %s because of the following error: %s', self.com_port, err)


    def configure_USB_ISS(self):
        """
            This function will take care of configuring the USB-> I2C bridge.
        """
        try:
            pass
        except:
            pass

    def turn_pack_on(self, com_port_handle):
        """
            This method turns the pack on. Note: function needs to be send every 10 sec minimum to maintain pack on.
            input: com_port handler
            output: True if successful. False otherwise
        """
        try:
            test = b'\x57\x01\x35\x40\x04\x01\x03\x00\x48\x03'
            self.serial_handle.write(test)
            time.sleep(0.01)
            test = b'\x57\x01\x30\x41\x20\x03'
            self.serial_handle.write(test)
            time.sleep(0.01)
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
            time.sleep(0.1)
            reply = self.serial_handle.read(10)
            message = b'\x54\x41\x3E' #this matches the length of the message read
            self.serial_handle.reset_input_buffer()
            self.serial_handle.write(message)
            time.sleep(0.1)
            self.status_message = self.USB_ISS.read(100)

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

    def update_values(self, com_port_handle):
        """
            Call this function to update all the model attributes that are read from the battery.
        """
        try:
            if not self.get_pack_status():
                log_battery.info('Asked for new status but failed. Either CRC or exception. Port: %s', self.com_port)
                return False
            self.get_serial_number()
            self.get_pack_current()
            self.get_cell_voltages()
            self.get_temperatures()
            log_battery.info('Pack values updated. Pack serial number: %s', self.serial_number)
            log_battery.info('Pack cell voltages: %s, %s, %s, %s, %s, %s, %s, %s, %s', self.cv_1,
                     self.cv_2, self.cv_3, self.cv_4, self.cv_5, self.cv_6, self.cv_7, self.cv_8, self.cv_9)
            self.pack_variables['last_status_update'] = time.time()
            return True
        except Exception as err:
            log_battery.exception('Error encountered while updating pack values. Exception is: %s', err)
            return False

    def get_serial_number(self):
        """
            Method extract the serial number out of the status message. Populates self.serial_number
        """
        try:
            self.pack_variables['serial_number'] = int.from_bytes(self.status_message[56:60], byteorder = 'little')
            return True
        except Exception as err:
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
        try:
            c_ovp = self.pack_variables['cv_max'] > settings.BATTERY_CELL_OVP_LEVEL_1
            c_uvp = self.pack_variables['cv_min'] < settings.BATTERY_CELL_UVP_LEVEL_1

            if c_uvp:
                log_battery.info('Cell undervoltage, level 1 on port: %s', self.com_port)
                self.pack_variables['is_cell_undervoltage_level_1'] = True
                self.pack_variables['is_not_safe_level_1'] = True
                return  False
            elif c_ovp:
                log_battery.info('Cell overvoltage, level 1 on port: %s', self.com_port)
                self.pack_variables['is_cell_overvoltage_level_1'] = True
                self.pack_variables['is_not_safe_level_1'] = True
                return False
            else:
                return True
        except Exception as err:
            log_battery.exception('Exception in checking cell safety level 1 on port %s. Exception is: %s', self.com_port, err)
            return False

    def check_safety_level_2(self):
        """
            Method return True if everything OK. False if a test stop trigger should be issued.
        """
        try:
            c_ovp = self.pack_variables['cv_max'] > settings.BATTERY_CELL_OVP_LEVEL_2
            c_uvp = self.pack_variables['cv_min'] < settings.BATTERY_CELL_UVP_LEVEL_2
            ocp = self.pack_variables['dc_current'] > settings.BATTERY_OCP
            ovt_mosfet = self.pack_variables['mosfet_temp'] > settings.MOSFETS_OVERTEMPERATURE
            ovt_cells = self.pack_variables['pack_temp'] > settings.CELLS_OVERTEMPERATURE
            if c_ovp:
                log_battery.info('Cell over-voltage, level 2. Port: %s', self.com_port)
                self.pack_variables['is_cell_overvoltage_level_2'] = True
                self.pack_variables['is_not_safe_level_2'] = True
                return False
            elif c_uvp:
                log_battery.info('Cell under-voltage, level 2. Port: %s', self.com_port)
                self.pack_variables['is_cell_undervoltage_level_2'] = True
                self.pack_variables['is_not_safe_level_2'] = True
                return False
            elif ocp:
                log_battery.info('Battery over-current. Port: %s', self.com_port)
                self.pack_variables['is_pack_overcurrent'] = True
                self.pack_variables['is_not_safe_level_2'] = True
                return False
            elif ovt_mosfet:
                log_battery.info('Over-temperature (mosfets) on port: %s', self.com_port)
                self.pack_variables['is_overtemperature_mosfets'] = True
                self.pack_variables['is_not_safe_level_2'] = True
                return False
            elif ovt_cells:
                log_battery.info('Over-temperature (mosfets) on port: %s', self.com_port)
                self.pack_variables['is_overtemperature_cells'] = True
                self.pack_variables['is_not_safe_level_2'] = True
                return False
            else:
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
        pass
    
    def clear_level_1_error_flag(self):
        """
            Method clears the level_1_error_flag
        """
        try:
            self.pack_variables['is_not_safe_level_1'] = False
            return True
        except Exception as err:
            log_battery.exception('Unable to clear error fral level 1 in batt on port %s. Reason is %s', self.com_port, err)
            return False
    