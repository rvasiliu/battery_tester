from django.db import models
from django.dispatch import receiver
from django.db.models.signals import pre_save, post_save

from ..log import log_battery as log
from ..tasks import add_battery

class Battery(models.Model):
    serial_number = models.CharField(max_length = 10, blank=True, null=True)
    port = models.CharField(max_length = 10, blank=True, null=True)
    i2c_address = models.CharField(max_length = 10, blank=True, null=True)

    firmware_version = models.IntegerField(max_length = 10, blank=True, null=True)
    
    #port_handler = serial.Serial()
    
    def initialise_comms(self):
        '''
        Function initialises comms. Maximum number of re-attempts: 5
        '''
        log.info('initialising COM port: %s', self.port )
       
            
        
        pass
    
    def close_comms(self):
        pass
    
    def update_values(self):
        self.port_handler.read()
        pass
    
    @property
    def port_handler(self):
        return utils.port_battery
    
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