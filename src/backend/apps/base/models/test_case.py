from django.db import models
from django.dispatch import receiver
from django.db.models.signals import pre_save, post_save

from ..models import Inverter, InverterPool, Battery
from ..tasks import main_task, periodic_task_implement


class TestCase(models.Model):
    TEST_CASE_STATES = (
        ('RUNNING', 'RUNNING'),
        ('STOPPED', 'STOPPED'),
        ('FAILED', 'FAILED'),
        ('FINISHED', 'FINISHED'),
        ('PENDING', 'PENDING')
    )
    battery = models.ForeignKey(Battery, related_name='test_case')
    inverter = models.ForeignKey(Inverter, related_name='test_case')
    result = models.CharField(max_length=32, blank=True, null=True)
    description = models.CharField(max_length=32, blank=True, null=True)
    config = models.CharField(max_length=32, blank=True, null=True)
    state = models.CharField(max_length=32, choices=TEST_CASE_STATES, default='PENDING')

    def load_config(self):
        """
        Load csv config file with the steps of the test.
        :return:
        """
        pass


@receiver(post_save, sender=TestCase, dispatch_uid="start_test_task")
def start_test_task(sender, instance, **kwargs):
    created = kwargs.get('created', False)
    if created:
        # dispatch add task
        # log.info('dispatching main task for test case id: %s', instance.id)
        # main_task.delay(instance.id)
        periodic_task_implement.delay(3)
