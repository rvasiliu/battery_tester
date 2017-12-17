from django.db import models
from django.dispatch import receiver
from django.db.models.signals import pre_save, post_save

from ..log import log_battery as log
from ..tasks import add_battery
from ..utils import UsbIssBattery

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

    @property
    def battery_utilities(self):
        return UsbIssBattery(self.port)   

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