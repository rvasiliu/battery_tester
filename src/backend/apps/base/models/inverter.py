import ctypes
import time

from django.db import models

from ..models import InverterPool
from ..log import log_inverter as log
from ..utils import VictronMultiplusMK2VCP


class Inverter(models.Model):
    INVERTER_STATES = (
        ('FREE', 'FREE'),
        ('BUSY', 'BUSY'),
        ('OFFLINE', 'OFFLINE')
    )
    name = models.CharField(max_length=32, blank=True, null=True)
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

    # rx_thread
    # septpoint sending thread
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

    def __str__(self):
        return '{}_{}'.format(self.name, self.port)

    @property
    def inverter_utilities(self):
        # get the instance from the class attribute if it's already there
        if self.port in VictronMultiplusMK2VCP.inverter_instances:
            return VictronMultiplusMK2VCP.inverter_instances[self.port]
        # if not, create it and store it on the class attribute
        victron_instance = VictronMultiplusMK2VCP(self.port)
        VictronMultiplusMK2VCP.inverter_instances[self.port] = victron_instance
        return victron_instance


