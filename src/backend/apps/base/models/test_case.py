import pandas as pd
import time

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
    config = models.CharField(max_length=32, blank=True, null=True)
    state = models.CharField(max_length=32, choices=TEST_CASE_STATES, default='PENDING')

    def load_config(self):
        """
            Load csv config file with the steps of the test.
        """
        return pd.read_csv(settings.LOOKUP_TABLE)
        

    def run_test(self):
        df_recipe = self.load_config()
        battery_instance = self.battery.battery_utilities
        inverter_instance = self.inverter.inverter_utilities
        
        for i in range(0,len(df_recipe)):
            log_test_case.info('Proceeding to step %s in test case with ID: %s.', i, self.id)
            try:
                if df_recipe.step_type[i] == 'CC Charge':
                    log_test_case.info('Attempting step type %s in test case with ID: %s', df_recipe.step_type[i], self.id)
                    self.cc_charge(battery_instance=battery_instance, 
                                   inverter_instance=inverter_instance,
                                   start_timestamp=time.time(),
                                   timeout_seconds = df_recipe.timeout_seconds[i])
                
                elif df_recipe.step_type[i] == 'CC Discharge':
                    log_test_case.info('Attempting step type %s in test case with ID: %s', df_recipe.step_type[i], self.id)
                    self.cc_discharge(battery_instance=battery_instance, 
                                   inverter_instance=inverter_instance,
                                   start_timestamp=time.time(),
                                   timeout_seconds = df_recipe.timeout_seconds[i])
                    
                
                elif df_recipe.step_type[i] == 'Rest':
                    log_test_case.info('Attempting step type %s in test case with ID: %s', df_recipe.step_type[i], self.id)
                    self.rest(battery_instance=battery_instance, 
                                   inverter_instance=inverter_instance,
                                   start_timestamp=time.time(),
                                   timeout_seconds = df_recipe.timeout_seconds[i])
                    
                
                else:
                    log_test_case.info('Unrecognised Step Type in test case with ID: %s', self.id)
            except Exception as err:
                log_test_case.exception('Error while attempting to run test step %. Error is %s.', i, err)
                
                    

    def cc_charge(self, battery_instance=None, inverter_instance=None, start_timestamp=None, timeout_seconds = 0):
        """
            Method encapsulates a cc_charge step
        """
        #TODO
        #1. Place inverter in charge mode.
        #2. Every 2 seconds check for battery data and timeout.
        inverter_instance.charge()
        log_test_case.info('Issued charge mode to inverter on port %s.', inverter_instance.com_port)
        while (time.time()-start_timestamp)>timeout_seconds:
            if battery_instance.pack_variables['is_not_safe_level_1']:
                log_test_case.info('Reached level 1 limits during charging on battery on port: %s.', battery_instance.com_port)
                break
            
            time.sleep(2)
        
        inverter_instance.rest()
        battery_instance.clear_level_1_error_flag()
        log_test_case.info('CC charge mode on inverter on port %s finished.', inverter_instance.com_port)
        return True
    
    def cc_discharge(self, battery_instance=None, inverter_instance=None, start_timestamp=None, timeout_seconds = 0):
        """
            Method encapsulates a cc_dischage step
        """
        inverter_instance.invert()
        log_test_case.info('Issued invert mode to inverter on port %s.', inverter_instance.com_port)
        
        while (time.time()-start_timestamp)>timeout_seconds:
            if battery_instance.pack_variables['is_not_safe_level_1']:
                log_test_case.info('Reached level 1 limits during inverting on battery on port: %s.', battery_instance.com_port)
                break
            
            time.sleep(2)
        
        inverter_instance.rest()
        battery_instance.clear_level_1_error_flag()
        log_test_case.info('CC discharge mode on inverter on port %s finished.', inverter_instance.com_port)
        return True
    
    def rest(self, battery_instance=None, inverter_instance=None, start_timestamp=None, timeout_seconds = 0):
        """
            Method encapsulates a rest step
        """
        inverter_instance.rest()
        log_test_case.info('Issued rest mode to inverter on port %s.', inverter_instance.com_port)
        
        while (time.time()-start_timestamp)>timeout_seconds:
            if battery_instance.pack_variables['is_not_safe_level_1']:
                log_test_case.info('Reached level 1 limits during resting battery on port: %s.', battery_instance.com_port)
                break
            
            time.sleep(2)
        
        inverter_instance.rest()
        battery_instance.clear_level_1_error_flag()
        log_test_case.info('Rest mode on inverter on port %s finished.', inverter_instance.com_port)
        return True


@receiver(post_save, sender=TestCase, dispatch_uid="start_test_task")
def start_test_task(sender, instance, **kwargs):
    created = kwargs.get('created', False)
    if created:
        # dispatch add task
        # log.info('dispatching main task for test case id: %s', instance.id)

        # main_task.delay(instance.id)
        periodic_task_implement.delay(3)
