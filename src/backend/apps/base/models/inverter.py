from django.db import models
from django.dispatch import receiver
from django.db.models.signals import pre_save, post_save

from ..log import log_inverter as log
from ..tasks import add_inverter

import time

class Inverter(models.Model):
    
    port = models.CharField(max_length = 10, blank=True, null=True)
    ve_bus_address = models.CharField(max_length = 10, blank=True, null=True)
    
    dc_current = models.CharField(max_length = 10, blank=True, null=True)
    dc_voltage = models.CharField(max_length = 10, blank=True, null=True)
    ac_current = models.CharField(max_length = 10, blank=True, null=True)
    ac_voltage = models.CharField(max_length = 10, blank=True, null=True)
    
    setpoint = models.CharField(max_length = 10, blank=True, null=True)
    is_on = models.BooleanField(default = False)
    
    def configure_ve_bus(self, comport_handle):
        '''
        This method does the start-up procedure on the inverter (resets the Mk2 etc)
        '''
        A_command = b'\x04\xFF\x41\x01\x00\xBB'
        reset_command = b'\x02\xFF\x52\xAD'
        X53_command = b'\x09\xFF\x53\x03\x00\xFF\x01\x00\x00\x04\x9E'
        
        try:
            self.ser_PU.write(A_command)
            time.sleep(0.1)
            self.ser_PU.write(X53_command)
            time.sleep(0.1)
            self.ser_PU.write(reset_command)
            time.sleep(0.1)
            self.ser_PU.write(A_command)
            time.sleep(0.1) 
            log.info('VE Bus configured.')
            return True            
        except:
            log.exception('Exception encountered when initializing VE bus protocol')
            return False
        
    def send_setpoint(self, comport_handle):
        '''
        This method sends the setpoint to the inverter (self.setpoint)
        '''
        try:
            message_out = self.make_message_MK2();
            comport_handle.write(message_out)
            return True
        except:
            log.exception('Exception during sending power setpoint to the PU')
            return False
    
    def make_message_MK2(self):
        '''
        This method return the setpoint command to send to the inverter. Uses self.setpoint.
        '''
        try:
            d0 = b'\x05\xFF\x57\x32\x81\x00\xF2\x05\xff\x57\x34\x00\x00\x00' #need to add value and checksum
            d1 = bytearray(d0); 
            if (self.setpoint <0):
                self.setpoint = 65535 + self.setpoint;

            d1[11] = int(self.setpoint) % 256;
            d1[12] = int(self.setpoint) >> 8;
            S = 0
            for b in reversed(range(7,13)):
                S = S - d1[b];    
            d1[13] = S%256
            return d1
        except:
            log.exception('Exception raised in setpoint message construction')
            return False
        
    def request_DC_frame(self, comport_handle):
        '''
        Sends request for a DC frame on the VE bus
        '''
        try:
            #self.thread_RX.start()  #Start monitoring messages from Power Unit
            message = b'\x03\xffF\x00\xb8'
            comport_handle.write(message)
            log.info('DC frame Requested')
            return True
        except:
            log.exception('Exception when requesting the DC frame - serial timeout perhaps?')
            return False
    
    def request_AC_frame(self, comport_handle):
        '''
        Sends request for AC frame on the VE bus
        '''
        try:
            message = b'\x03\xffF\x01\xb7'
            comport_handle.write(message)
            log.info('AC frame Requested')
            return True
        except:
            log.exception('Exception when requesting the AC frame - serial timeout perhaps?')
            return False
    
    def update_DC_frame(self, message, comport_handle):
        '''
        Updates the self.dc_current and self.dc_voltage variables.
        '''
        #self.thread_RX.stop()
        try:
        self.dc_voltage = int.from_bytes(message[7:9], byteorder = 'little')
        self.dc_voltage = self.dc_voltage / 100
        
        charging_current = int.from_bytes(message[9:12], byteorder = 'little')
        discharging_current = int.from_bytes(message[12:15], byteorder = 'little')
        self.dc_current = charging_current + discharging_current
        self.dc_current = self.dc_current/10
        print(self.dc_voltage, self.dc_current)
        pass
    
    def update_AC_frame(self, message):
        self.ac_voltage = int.from_bytes(message[7:9], byteorder = 'little')/100
        self.ac_current = ctypes.c_int16(int.from_bytes(message[9:11], byteorder = 'little'))
        self.ac_current = self.ac_current.value/100
        
        print(self.ac_voltage, self.ac_current)
        pass

@receiver(post_save, sender=Inverter, dispatch_uid="add_task_dispatch")
def add_task_dispatch(sender, instance, **kwargs):
    created = kwargs.get('created', False)
    if created:
        # dispatch add task
        log.info('dispatching add Inverter task for id: %s', instance.id)
        #add_battery.delay(instance.id)