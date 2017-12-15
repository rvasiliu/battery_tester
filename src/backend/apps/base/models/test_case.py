from django.db import models
from django.dispatch import receiver
from django.db.models.signals import pre_save, post_save

from ..models import Inverter, InverterPool, Battery
from ..tasks import main_task

class TestCase(models.Model):
    battery = models.ForeignKey(Battery)
    inverter = models.ForeignKey(Inverter)



@receiver(post_save, sender=TestCase, dispatch_uid="start_test_task")
def start_test_task(sender, instance, **kwargs):
    created = kwargs.get('created', False)
    if created:
        # dispatch add task
        log.info('dispatching main task for test case id: %s', instance.id)
