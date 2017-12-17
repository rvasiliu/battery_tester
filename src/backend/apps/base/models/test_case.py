import pandas as pd

from django.db import models
from django.dispatch import receiver
from django.db.models.signals import post_save
from django.conf import settings

from ..models import Inverter, InverterPool, Battery
from ..tasks import main_task, periodic_task_implement

from ..log import log_test_case


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
    config = models.(max_length=32, blank=True, null=True)
    state = models.CharField(max_length=32, choices=TEST_CASE_STATES, default='PENDING')

    def load_config(self):
        """
        Load csv config file with the steps of the test.
        :return:
        """
        pass

        df_recipe = pd.read_csv(settings.LOOKUP_TABLE)
        for i in range(0,len(df_recipe)):
            log_test_case.info('Proceeding to step %s in test case with ID: %s.', i, self.id)
            if df_recipe.step_type[i] == 'CC Charge':
                log_test_case.info('Attempting step type %s in test case with ID: %s', df_recipe.step_type[i], self.id)
                self.cc_charge()
                pass
            elif df_recipe.step_type[i] == 'CC Discharge':
                log_test_case.info('Attempting step type %s in test case with ID: %s', df_recipe.step_type[i], self.id)
                self.cc_discharge()
                pass
            
            elif df_recipe.step_type[i] == 'Rest':
                log_test_case.info('Attempting step type %s in test case with ID: %s', df_recipe.step_type[i], self.id)
                self.rest()
                pass
            
            else:
                log_test_case.info('Unrecognised Step Type in test case with ID: %s', self.id)
                pass

    def cc_charge(self):
        """
            Method encapsulates a cc_charge step
        """
        
        pass
    
    def cc_discharge(self):
        """
            Method encapsulates a cc_dischage step
        """
        pass
    
    def rest(self):
        """
            Method encapsulates a rest step
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
