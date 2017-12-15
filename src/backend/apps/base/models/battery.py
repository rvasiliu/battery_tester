from django.db import models
from django.dispatch import receiver
from django.db.models.signals import pre_save, post_save

from ..log import log_battery as log
from ..tasks import add_battery

import struct
import time

class Battery(models.Model):
    serial_number = models.CharField(max_length = 10, blank=True, null=True)
    port = models.CharField(max_length = 10, blank=True, null=True)
    i2c_address = models.CharField(max_length = 10, blank=True, null=True)

    firmware_version = models.IntegerField(max_length = 10, blank=True, null=True)
    
    dc_voltage = models.CharField(max_length = 10, blank=True, null=True)
    dc_current = models.CharField(max_length = 10, blank=True, null=True)
    
    cv_1 = models.CharField(max_length = 10, blank=True, null=True)
    cv_2 = models.CharField(max_length = 10, blank=True, null=True)
    cv_3 = models.CharField(max_length = 10, blank=True, null=True)
    cv_4 = models.CharField(max_length = 10, blank=True, null=True)
    cv_5 = models.CharField(max_length = 10, blank=True, null=True)
    cv_6 = models.CharField(max_length = 10, blank=True, null=True)
    cv_7 = models.CharField(max_length = 10, blank=True, null=True)
    cv_8 = models.CharField(max_length = 10, blank=True, null=True)
    cv_9 = models.CharField(max_length = 10, blank=True, null=True)
    
    cv_min = models.CharField(max_length = 10, blank=True, null=True)
    cv_max = models.CharField(max_length = 10, blank=True, null=True)
    
    mosfet_temp = models.CharField(max_length = 10, blank=True, null=True)
    pack_temp = models.CharField(max_length = 10, blank=True, null=True)
    
    cell_overvoltage_level_1 = models.CharField(max_length = 10, blank=True, null=True)
    cell_overvoltage_level_2 = models.CharField(max_length = 10, blank=True, null=True)
    cell_undervoltage_level_1 = models.CharField(max_length = 10, blank=True, null=True)
    cell_undervoltage_level_2 = models.CharField(max_length = 10, blank=True, null=True)
    pack_overcurrent = models.CharField(max_length = 10, blank=True, null=True)
    pack_overtemperature_mosfet = models.CharField(max_length = 10, blank=True, null=True)
    pack_overtemperature_cells = models.CharField(max_length = 10, blank=True, null=True)
    
    is_on = models.BooleanField(default=False)
    error_flag = models.BooleanField(default=False)
    
    status = []
    
    
    def initialise_comms(self):
        '''
        Function initialises comms. Maximum number of re-attempts: 5
        '''
        log.info('initialising COM port: %s', self.port )
       
        pass
    
    def close_comms(self):
        pass
    
    def update_values(self, comport_handle):
        '''
        Call this function to update all the model attributes that are read from the battery. 
        '''
        try:
            self.get_serial_number()
            self.get_pack_status(comport_handle)
            self.get_cell_voltages()
            self.get_pack_current()
            self.get_temperatures()
            log.info('Pack values updated. Pack serial number: %s', self.serial_number)
            log.ingo('Pack cell voltages: %s, %s, %s, %s, %s, %s, %s, %s, %s', self.cv_1,
                     self.cv_2, self.cv_3, self.cv_4, self.cv_5, self.cv_6, self.cv_7, self.cv_8, self.cv_9)
            return True
        except:
            log.exception('Error encountered while updating pack values')
            return False
        
    
    def turn_pack_on(self, comport_handle):
        '''
        This method turns the pack on. Note: function needs to be send every 10 sec minimum to maintain pack on.
        input: comport handler
        output: True if successful. False otherwise
        '''
        try:
            test = b'\x57\x01\x35\x40\x04\x01\x03\x00\x48\x03'
            comport_handle.write(test)
            #time.sleep(0.1)
            test = b'\x57\x01\x30\x41\x20\x03'
            comport_handle.write(test)
            #time.sleep(0.1)
            self.is_on = True
            log.info('Pack turned on. Pack serial number: %s', self.serial_number)
            return True
        except:
            log.info('Error when turning pack on. Pack serial number: %s', self.serial_number)
            return False
        
    def get_pack_status(self, comport_handle):
        '''
        Method gets the status message from the battery pack. It populates self.status with the reply
        '''
        try: 
            message = b'\x57\x01\x34\x40\x01\x00\x00\x41\x03'
            comport_handle.write(message)
            #time.sleep(0.1)
            reply = comport_handle.read(10)
            
            message = b'\x54\x41\x3E' #this matches the length of the message read
            comport_handle.reset_input_buffer()
            comport_handle.write(message)
            #time.sleep(0.5)
            self.status = self.USB_ISS.read(100)
            return True
        except:
            return False
        
    def get_pack_current(self):
        '''
        Extract the pack current out of the battery message reply (get_Status command). Updates self.dc_current
        input: none
        output: True if successful. False otherwise
        '''
        try:
            temp_variable = struct.unpack('<f', self.status[50:54])
            self.dc_current = "{0:.3f}".format(temp_variable[0])
            return True
        except:
            return False
    
    def get_cell_voltages(self):
        '''
        Function gets cell voltages out of self.status and populates cv1 -> cv9 as well as cv_max and cv_min
        '''
        try:
            data = self.status
            C1 = (struct.unpack('>f',struct.pack("B",data[17])+struct.pack("B", data[16]) + struct.pack("B", data[15])+struct.pack("B",data[14])))
            C2 = (struct.unpack('>f',struct.pack("B",data[21])+struct.pack("B", data[20]) + struct.pack("B", data[19])+struct.pack("B",data[18])))
            C3 = (struct.unpack('>f',struct.pack("B",data[25])+struct.pack("B", data[24]) + struct.pack("B", data[23])+struct.pack("B",data[22])))
            C4 = (struct.unpack('>f',struct.pack("B",data[29])+struct.pack("B", data[28]) + struct.pack("B", data[27])+struct.pack("B",data[26])))
            C5 = (struct.unpack('>f',struct.pack("B",data[33])+struct.pack("B", data[32]) + struct.pack("B", data[31])+struct.pack("B",data[30])))
            C6 = (struct.unpack('>f',struct.pack("B",data[37])+struct.pack("B", data[36]) + struct.pack("B", data[35])+struct.pack("B",data[34])))
            C7 = (struct.unpack('>f',struct.pack("B",data[41])+struct.pack("B", data[40]) + struct.pack("B", data[39])+struct.pack("B",data[38])))
            C8 = (struct.unpack('>f',struct.pack("B",data[45])+struct.pack("B", data[44]) + struct.pack("B", data[43])+struct.pack("B",data[42])))
            C9 = (struct.unpack('>f',struct.pack("B",data[49])+struct.pack("B", data[48]) + struct.pack("B", data[47])+struct.pack("B",data[46])))
    
            self.cv_1 = "{0:.3f}".format(C1[0])
            self.cv_2 = "{0:.3f}".format(C2[0])
            self.cv_3 = "{0:.3f}".format(C3[0])
            self.cv_4 = "{0:.3f}".format(C4[0])
            self.cv_5 = "{0:.3f}".format(C5[0])
            self.cv_6 = "{0:.3f}".format(C6[0])
            self.cv_7 = "{0:.3f}".format(C7[0])
            self.cv_8 = "{0:.3f}".format(C8[0])
            self.cv_9 = "{0:.3f}".format(C9[0])
            
            self.cv_min = min([self.cv_1, self.cv_2, self.cv_3, self.cv_4,
                               self.cv_5, self.cv_6, self.cv_7, self.cv_8,
                               self.cv_9])
            
            self.cv_max = max([self.cv_1, self.cv_2, self.cv_3, self.cv_4,
                               self.cv_5, self.cv_6, self.cv_7, self.cv_8,
                               self.cv_9])
            return True
        except:
            return False
        
    def get_serial_number(self):
        '''
        Method extract the serial number out of the status message. Populates self.serial_number
        '''
        try:
            self.serial_number = int.from_bytes(self.status[56:60], byteorder = 'little')
            return True
        except:
            return False
        
    def get_temperatures(self):
        '''
        methods extract the temperature readouts from self.status and populates mosfet and pack temperature readings
        '''
        try:
            self.mosfet_temp= struct.unpack('<f', self.status[6:10])
            self.pack_temp = struct.unpack('<f', self.status[10:14])
            
            self.mosfet_temp = "{0:.3f}".format(self.mosfet_temp[0])
            self.pack_temp = "{0:.3f}".format(self.pack_temp[0])
            return True
        except:
            return False
        
    def configure_thresholds(self):
        '''
        Method to configure the protection limits. Could be linked to a config file.
        '''
        self.cell_overvoltage_level_1 = 3.6
        self.cell_overvoltage_level_2 = 3.7
        self.cell_undervoltage_level_1 = 3
        self.cell_undervoltage_level_2 = 2.9
        self.pack_overcurrent = 35
        self.pack_overtemperature_cells = 50
        self.pack_overtemperature_mosfet = 80
        return True
        
    @property
    def port_handler(self):
        pass
    
    @property
    def elapsed_time(self):
        return self.timestamp_confirmation-self.timestamp_send


@receiver(post_save, sender=Battery, dispatch_uid="add_task_dispatch")
def add_task_dispatch(sender, instance, **kwargs):
    created = kwargs.get('created', False)
    if created:
        # dispatch add task
        log.info('dispatching add task for id: %s', instance.id)
        add_battery.delay(instance.id)