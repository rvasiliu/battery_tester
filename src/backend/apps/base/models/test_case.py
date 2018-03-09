import pandas as pd
import time

from django.db import models
from django.dispatch import receiver
from django.db.models.signals import post_save
from django.conf import settings
from django.utils import timezone

from ..models import Inverter, Battery
from ..tasks import main_task

from ..log import log_test_case


class TestCase(models.Model):
    TEST_CASE_STATES = (
        ('RUNNING', 'RUNNING'),
        ('STOPPED', 'STOPPED'),
        ('FAILED', 'FAILED'),
        ('FINISHED', 'FINISHED'),
        ('PENDING', 'PENDING')
    )
    name = models.CharField(max_length=32, blank=True, null=True)
    battery = models.ForeignKey(Battery, related_name='test_case', limit_choices_to={'state': 'FREE'})
    inverter = models.ForeignKey(Inverter, related_name='test_case', limit_choices_to={'state': 'FREE'})
    result = models.CharField(max_length=32, blank=True, null=True)
    description = models.CharField(max_length=256, blank=True, null=True)
    config = models.CharField(max_length=32, blank=True, null=True)
    state = models.CharField(max_length=32, choices=TEST_CASE_STATES, default='PENDING')
    graph = models.CharField(max_length=128, null=True, blank=True, default='#')
    created = models.DateTimeField(auto_now_add=True, null=True, blank=True)
    finished = models.DateTimeField(null=True, blank=True)
    recipe = models.CharField(max_length=128, default=settings.LOOKUP_TABLE)

    def __str__(self):
        return '{}'.format(self.name)

    def load_config(self):
        """
            Load csv config file with the steps of the test.
        """
        return pd.read_csv(self.recipe)

    def run_test(self):
        df_recipe = self.load_config()

        log_test_case.info('in run test: Battery instance ID is: %s', id(self.battery.battery_utilities))
        log_test_case.info('in run test: Inverter instance ID is %s', id(self.inverter.inverter_utilities))

        from ..models import TestCaseEvent
        for i in range(0, len(df_recipe)):
            log_test_case.info('TEST CASE ID: %s - Proceeding to step %s from the test RECIPE.', self.id, i)
            self.inverter.inverter_utilities.inverter_variables['dc_capacity'] = 0
            try:
                if df_recipe.step_type[i] == 'CC Charge':
                    log_test_case.info('TEST CASE ID: %s - Attempting step type %s.', self.id, df_recipe.step_type[i])
                    tce = TestCaseEvent.objects.create(
                        test_case=self,
                        name='CHARGE',
                        trigger='RECIPE',
                        message='set_point',
                        value=settings.CHARGING_SETPOINT,
                        timestamp=timezone.now(),
                    )
                    self.cc_charge(start_timestamp=time.time(),
                                   timeout_seconds=df_recipe.timeout_seconds[i],
                                   capacity_limit=df_recipe.capacity_limit[i])

                elif df_recipe.step_type[i] == 'CC Discharge':
                    log_test_case.info('TEST CASE ID: %s - Attempting step type %s', self.id, df_recipe.step_type[i])
                    tce = TestCaseEvent.objects.create(
                        test_case=self,
                        name='DISCHARGE',
                        trigger='RECIPE',
                        message='set_point',
                        value=settings.INVERTING_SETPOINT,
                        timestamp=timezone.now(),
                    )
                    self.cc_discharge(start_timestamp=time.time(),
                                      timeout_seconds=df_recipe.timeout_seconds[i])

                elif df_recipe.step_type[i] == 'Rest':
                    log_test_case.info('TEST CASE ID: %s - Attempting step type %s', self.id, df_recipe.step_type[i])
                    tce = TestCaseEvent.objects.create(
                        test_case=self,
                        name='REST',
                        trigger='RECIPE',
                        message='set_point',
                        value=0,
                        timestamp=timezone.now(),
                    )
                    self.rest(start_timestamp=time.time(),
                              timeout_seconds=df_recipe.timeout_seconds[i])
                else:
                    log_test_case.info('TEST CASE ID: %s - Unrecognised Step Type %s', self.id, i)
            except Exception as err:
                log_test_case.exception('TEST CASE ID: %s - Error on test step %s. Error is %s.', self.id, i, err)

    def cc_charge(self, start_timestamp=None, timeout_seconds=0, capacity_limit=0):
        """
            Method encapsulates a cc_charge step
        """
        #TODO
        #1. Place inverter in charge mode.
        #2. Every 2 seconds check for battery data and timeout.
        log_test_case.info('In Charge step: inverter instance ID is %s:', id(self.inverter.inverter_utilities))
        self.inverter.inverter_utilities.charge()
        log_test_case.info('TEST CASE ID: %s -Issued charge mode to inverter on port %s.', self.id, self.inverter.port)
        while (time.time() - start_timestamp) < timeout_seconds:
            if self.battery.battery_utilities.pack_variables['is_not_safe_level_1']:
                log_test_case.info('TEST CASE ID: %s - Reached level 1 limits during charging on battery on port: %s.', self.id, self.battery.port)
                break
            elif self.inverter.inverter_utilities.inverter_variables['dc_capacity'] > capacity_limit:
                log_test_case.info('TEST CASE ID: %s - Exceeded capacity limit in CC charge', self.id)
                break
            elif self.state == 'FINISHED':
                log_test_case.info('TEST CASE ID: %s - Encountered FINISHED command while doing CC Carge. Breaking.', self.id)
                break
            time.sleep(2)

        self.battery.battery_utilities.clear_level_1_error_flag()
        log_test_case.info('TEST CASE ID: %s - CC CHARGE mode on inverter on port %s finished.', self.id, self.inverter.port)
        return True

    def cc_discharge(self, start_timestamp, timeout_seconds=0):
        """
            Method encapsulates a cc_dischage step
        """
        self.inverter.inverter_utilities.invert()
        log_test_case.info('Issued invert mode to inverter on port %s.', self.inverter.port)
        inverter_instance.invert()
        log_test_case.info('Issued invert mode to inverter on port %s.', inverter_instance.com_port)

        while (time.time() - start_timestamp) < timeout_seconds:
            if self.battery.battery_utilities.pack_variables['is_not_safe_level_1']:
                log_test_case.info('Reached level 1 limits during inverting on battery on port: %s.', self.battery.port)
                break
            elif self.state == 'FINISHED':
                log_test_case.info('Encountered FINISHED command while doing CC Discharge. Breaking.')
                break
            time.sleep(2)

        self.battery.battery_utilities.clear_level_1_error_flag()
        log_test_case.info('CC DISCHARGE mode on inverter on port %s finished.', self.inverter.port)
        return True

    def rest(self, start_timestamp, timeout_seconds=0):
        """
            Method encapsulates a rest step
        """
        self.inverter.inverter_utilities.rest()
        log_test_case.info('Issued rest mode to inverter on port %s.', self.inverter.port)

        while (time.time() - start_timestamp) < timeout_seconds:
            if self.battery.battery_utilities.pack_variables['is_not_safe_level_1']:
                log_test_case.info('NO ACTION - Reached level 1 limits during resting battery on port: %s.', self.battery.port)
            elif self.state == 'FINISHED':
                log_test_case.info('Encountered FINISHED command while doing a Rest. Breaking.')
                break
            time.sleep(2)

        self.inverter.inverter_utilities.rest()
        self.battery.battery_utilities.clear_level_1_error_flag()
        log_test_case.info('REST mode on inverter on port %s finished.', self.inverter.port)
        return True


@receiver(post_save, sender=TestCase, dispatch_uid="start_test_task")
def start_test_task(sender, instance, **kwargs):
    created = kwargs.get('created', False)
    if created:
        # log.info('dispatching main task for test case id: %s', instance.id)
        main_task_id = main_task.apply_async((instance.id,), queue='main')
        log_test_case.info('main_task id: %s', main_task_id)

