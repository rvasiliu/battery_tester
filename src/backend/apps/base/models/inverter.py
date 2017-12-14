from django.db import models
from django.dispatch import receiver
from django.db.models.signals import pre_save, post_save

from ..log import log_inverter as log
from ..tasks import add_inverter

class Inverter(models.Model):
    
    port = models.CharField(max_length = 10, blank=True, null=True)
    ve_bus_address = models.CharField(max_length = 10, blank=True, null=True)
    
    dc_current = models.CharField(max_length = 10, blank=True, null=True)
    dc_voltage = models.CharField(max_length = 10, blank=True, null=True)
    ac_current = models.CharField(max_length = 10, blank=True, null=True)
    ac_voltage = models.CharField(max_length = 10, blank=True, null=True)
    
    setpoint = models.CharField(max_length = 10, blank=True, null=True)
    is_on = models.BooleanField(default = False)
    

@receiver(post_save, sender=Inverter, dispatch_uid="add_task_dispatch")
def add_task_dispatch(sender, instance, **kwargs):
    created = kwargs.get('created', False)
    if created:
        # dispatch add task
        log.info('dispatching add Inverter task for id: %s', instance.id)
        #add_battery.delay(instance.id)