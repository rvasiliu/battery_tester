import ctypes

from django.db import models
from django.dispatch import receiver
from django.db.models.signals import post_save
from django.conf import settings

from ..models import InverterPool

from ..log import log_inverter as log
from ..tasks import add_inverter
from ..utils import VictronMultiplusMK2VCP

import time


class Inverter(models.Model):
    INVERTER_STATES = (
        ('FREE', 'FREE'),
        ('BUSY', 'BUSY'),
        ('OFFLINE', 'OFFLINE')
    )
    port = models.CharField(max_length=10, blank=True, null=True)
    ve_bus_address = models.CharField(max_length=10, blank=True, null=True)
    
    dc_current = models.CharField(max_length=10, blank=True, null=True)
    dc_voltage = models.CharField(max_length=10, blank=True, null=True)
    ac_current = models.CharField(max_length=10, blank=True, null=True)
    ac_voltage = models.CharField(max_length=10, blank=True, null=True)
    
    setpoint = models.CharField(max_length=10, blank=True, null=True)
    is_on = models.BooleanField(default=False)

    inverter_pool = models.ForeignKey(InverterPool, related_name='inverters', related_query_name='inverters')
    state = models.CharField(choices=INVERTER_STATES, max_length=32, default='OFFLINE')

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
    @property
    def inverter_utilities(self):
        return VictronMultiplusMK2VCP(self.port)

    def update_DC_frame(self, message, comport_handle):
        """
            Updates the self.dc_current and self.dc_voltage variables.
        """
        try:
            self.dc_voltage = int.from_bytes(message[7:9], byteorder='little')
            self.dc_voltage = self.dc_voltage / 100
            charging_current = int.from_bytes(message[9:12], byteorder='little')
            discharging_current = int.from_bytes(message[12:15], byteorder='little')
            self.dc_current = charging_current + discharging_current
            self.dc_current = self.dc_current / 10

            self.stop_RX_thread()
            return True
        except Exception as err:
            log.exception('Could not update the DC frame because %s', err)
            return False

    def update_AC_frame(self, message, comport_handle):
        """
            Updates the self.ac_voltage and self.ac_current
        """
        try:
            self.ac_voltage = int.from_bytes(message[7:9], byteorder='little') / 100
            self.ac_current = ctypes.c_int16(int.from_bytes(message[9:11], byteorder='little'))
            self.ac_current = self.ac_current.value / 100

            self.stop_RX_thread()
            return True
        except Exception as err:
            log.exception('Could not update AC frame', err)
            return False


        
    def get_info_frame_reply(self):
        """
            This function should run continuously and run onto all the incoming bytestream after 'Get frame' Command
            The function will automatically call an update of the self.ac/dc-voltage/current variables if a suitable reply is detected.
        """
        message = b'\x0f\x20'
        r = 15
        byte = self.get_next_byte()
        if byte == b'\x0f':
            new_byte = self.get_next_byte()
            if new_byte == b' ':
                for i in range(r):
                    new_byte = self.get_next_byte()
                    message = message + new_byte

                if message[6] == 12:
                    print('DC message: ', message)
                    frame = {'type':'DC', 
                            'message':message}
                    return frame
                    self.update_DC_frame(message)
                    
                elif message[6] == 8: # we have AC frame
                    print('AC message: ', message)
                    frame = {'type':'AC', 
                            'message':message}
                    return frame
                    self.update_AC_frame(message)
                else:
                    print('Message not recognised')
                    frame = {'type':'Unknown', 
                            'message':message}
            else:
                return None
        return None

    

    
            
        
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
    """

    :param sender:
    :param instance:
    :param kwargs:
    :return:
    """
    created = kwargs.get('created', False)
    if created:
        # dispatch add task
        log.info('dispatching add Inverter task for id: %s', instance.id)
        #add_battery.delay(instance.id)