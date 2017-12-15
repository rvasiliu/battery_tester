from django.db import models
from django.dispatch import receiver
from django.db.models.signals import pre_save, post_save

from ..log import log_inverter as log
from ..tasks import add_inverter

import time
import ctypes

class Inverter(models.Model):
    
    port = models.CharField(max_length = 10, blank=True, null=True)
    ve_bus_address = models.CharField(max_length = 10, blank=True, null=True)
    
    dc_current = models.CharField(max_length = 10, blank=True, null=True)
    dc_voltage = models.CharField(max_length = 10, blank=True, null=True)
    ac_current = models.CharField(max_length = 10, blank=True, null=True)
    ac_voltage = models.CharField(max_length = 10, blank=True, null=True)
    
    setpoint = models.CharField(max_length = 10, blank=True, null=True)
    is_on = models.BooleanField(default = False)
    
    charging_setpoint = -500
    inverting_setpoint = 500
    
    #rx_thread
    #septpoint sending thread
    """
    Sugestions:
    1. setpoint has to be updated every 5 seconds or less. Should be running continuously.
    2. Readings from the inverter can be fetched with update_frames method. must be done periodically (2 seconds)
    
    3. - Start reading thread (poll get_info_frame_reply for each byte coming in) when AC/DC frames are requested
       - Stop the thread above when the update readings funtion is called.
       
       >>> Easier: start thread which continually reads the RX bytestream. Once a 
           Request Frame command is sent the thread will automatically chatch the replies and
           populated the frame attributes of the model 
    """
    
    def configure_ve_bus(self, comport_handle):
        """
        This method does the start-up procedure on the inverter (resets the Mk2 etc)
        """
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
        """
        This method sends the setpoint to the inverter (self.setpoint)
        """
        try:
            message_out = self.make_message_MK2();
            comport_handle.write(message_out)
            return True
        except:
            log.exception('Exception during sending power setpoint to the PU')
            return False
    
    def make_message_MK2(self):
        """
        This method return the setpoint command to send to the inverter. Uses self.setpoint.
        """
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
        """
        Sends request for a DC frame on the VE bus
        """
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
        """
        Sends request for AC frame on the VE bus
        """
        try:
            message = b'\x03\xffF\x01\xb7'
            comport_handle.write(message)
            log.info('AC frame Requested')
            return True
        except:
            log.exception('Exception when requesting the AC frame - serial timeout perhaps?')
            return False
    
    def update_DC_frame(self, message, comport_handle):
        """
        Updates the self.dc_current and self.dc_voltage variables.
        """
        #self.thread_RX.stop()
        try:
            self.dc_voltage = int.from_bytes(message[7:9], byteorder='little')
            self.dc_voltage = self.dc_voltage / 100
            charging_current = int.from_bytes(message[9:12], byteorder='little')
            discharging_current = int.from_bytes(message[12:15], byteorder='little')
            self.dc_current = charging_current + discharging_current
            self.dc_current = self.dc_current/10
            
            self.stop_RX_thread()
            return True
        except:
            log.exception('Could not update the DC frame.')
            return False
        
    
    def update_AC_frame(self, message, comport_handle):
        """
        Updates the self.ac_voltage and self.ac_current
        """
        try:
            self.ac_voltage = int.from_bytes(message[7:9], byteorder = 'little')/100
            self.ac_current = ctypes.c_int16(int.from_bytes(message[9:11], byteorder = 'little'))
            self.ac_current = self.ac_current.value/100
            
            self.stop_RX_thread()
            return True
        except Exception as err:
            log.exception('Could not update AC frame', err)
            return False
        
    def get_next_byte(self):
        """
        Use this function to read a single byte from the serial port
        """
        try:
            byte_in = self.ser_PU.read(1)
            return byte_in
        except Exception as err:
            log.exception('Unable to get next byte from the RS232 bus', err)
            return False
        
    def get_info_frame_reply(self):
        """
        This function should run continuously and run onto all the invoming bytestream after 'Get frame' Command
        The function will automatically call an update of the self.ac/dc-voltage/current variables if a suitable reply is detected.
        """
        message = b'\x0f\x20'
        r = 15
        byte = self.get_next_byte()
        #spare_byte = byte
        if(byte == b'\x0f'):
            new_byte = self.get_next_byte()
            if(new_byte == b' '):
                for i in range(r):
                    new_byte = self.get_next_byte()
                    message = message + new_byte

                if message[6] == 12:
                    print('DC message: ', message)
                    self.update_DC_frame(message)
                    
                elif message[6] == 8: # we have AC frame
                    print('AC message: ', message)
                    self.update_AC_frame(message)
                else:
                    print('Message not recognised')
            else:
                pass
         
        return True
    
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
            S = 0
            for b in reversed(range(len(message)-1)):
                S = S - message[b];    
            message_array[-1] = S%256
            return bytes(message_array)
        except Exception as err:
            log.exception('Cannot make state message', err)
            return False
        
    def send_state(self, state=0, comport_handle):
        """
        Method will send a state command to the inverter.
        Use state to choose state.
        """
        try:
            comport_handle.write(self.make_state_message(state))
            return True
        except Exception as err:
            log.exception('Cannot send state.', err)
            return False
        
    def charge(self, comport_handle):
        """
        Method can be called and it will automatically configure the inverter to charge with a set amount
        """    
        try:
            self.setpoint = self.charging_setpoint
            self.send_state(1, comport_handle)
            return True
        except Exception as err:
            log.exception('Cannot set charge mode.', err)
            return False
        
    def invert(self, comport_handle):
        """
        Method can be called and it will automatically configure the iverter to invert with a set amount
        """
        try:
            self.setpoint = self.inverting_setpoint
            self.send_state(1, comport_handle)
            return True
        except Exception as err:
            log.exception('Cannot set invert mode.', err)
            return False
        
    def rest(self, comport_handle):
        """
        Method will zero out the setpoint. The inverter will be kept on.
        """
        try:
            self.setpoint = 0
            self.send_state(1, comport_handle)
            return True
        except Exception as err:
            log.exception('Cannot set rest mode. The inverter is probably still running!', err)
            return False
        
    def stop(self, comport_handle):
        """
        Method will zero out the setpoint and it will switch the inverter power off.
        """
        try:
            self.setpoint = 0
            self.send_state(0, comport_handle)
            return True
        except Exception as err:
            log.exception('Cannot stop the inveter!', err)
            return False
        
    def update_frames(self, comport_handle):
        """
        Call this method periodically to update the readings from the Inverter
        """
        try:
            self.request_AC_frame(comport_handle) 
            self.time.sleep(0.1)
            self.request_DC_frame(comport_handle)
            self.time.sleep(0.1)
            return True
        except Exception as err:
            log.exception('Cannot update frames.', err)
            return False
            
        
    def start_RX_thread(self):
        """
        Would start the RX thread - would run self.get_info_frame_reply indefinitely.
        """
        
        pass
    
    def stop_RX_thread(self):
        """
        Would stop the RX thread
        """
        pass
        

@receiver(post_save, sender=Inverter, dispatch_uid="add_task_dispatch")
def add_task_dispatch(sender, instance, **kwargs):
    created = kwargs.get('created', False)
    if created:
        # dispatch add task
        log.info('dispatching add Inverter task for id: %s', instance.id)
        #add_battery.delay(instance.id)