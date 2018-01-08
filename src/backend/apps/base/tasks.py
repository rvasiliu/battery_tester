import time
import json
import datetime
import pandas as pd

from celery import shared_task
from celery import current_app

from django.conf import settings

from django_celery_beat.models import PeriodicTask, IntervalSchedule

# log_main should be used in the main task
# log_bat should be used for the battery tasks
# log_inv should be used for the inverter tasks
from .log import log_inverter as log_inv, log_battery as log_bat
from .log import log_test_case as log_main


class MaxRetriesExceededException(Exception):
    pass


@shared_task(bind=True)
def send_inverter_setpoint(self, inverter_id, set_point):
    """
    This should be a periodic task that keeps the inverter alive.
    Should be executed at 5 seconds interval.
    :param self:
    :param inverter_id:
    :return:
    """
    log_inv.info('In inverter set point: %s', set_point)
    from .models import Inverter
    inverter = Inverter.objects.get(id=inverter_id)
    victron_inv = inverter.inverter_utilities
    victron_inv.set_point = set_point
    victron_inv.send_setpoint()
    


@shared_task(bind=True)
def send_battery_keep_alive(self, battery_id, keep_alive):
    """
    This should be a periodic task that keeps the battery alive.
    Should be executed at 5 seconds interval.
    :param self:
    :param battery_id:
    :return:
    """
    log_bat.info('In battery keep alive: %s', keep_alive)
    from .models import Battery
    battery = Battery.objects.get(id=battery_id)
    usbiss_bat = battery.battery_utilities
    pack_values = usbiss_bat.update_values()
    if pack_values:
        for key in pack_values:
            if hasattr(battery, key):
                setattr(battery, key, pack_values[key])
            else:
                log_bat.warning('Battery does not have attr: %s', key)
        battery.save()
        
    

@shared_task(bind=True)
def safety_check(self, battery_id, inverter_id, test_case_id,
                 inv_periodic_task_id, bat_periodic_task_id,
                 name):
    """
    This should check the battery parameters. It should detect a faulty state and stop the whole flow.
    :param self:
    :param battery_id:
    :param inv_periodic_task_id:
    :param bat_periodic_task_id:
    :param main_task_id:
    :return:
    """
    from .models import Battery, Inverter, TestCase
    battery = Battery.objects.get(id=battery_id)
    inverter = Inverter.objects.get(id=inverter_id)
    test_case = TestCase.objects.get(id=test_case_id)
    log_bat.info('Safety check for battery: %s on port: %s', battery.name, battery.port)

    # TODO
    # check battery parameters
    # if not ok:
    # 1. stop periodic tasks(inv, bat)
    # 2. send stop to inv
    # 3. send stop to bat
    # 4. set result on test_case = failed and reason/description
    # 5. stop main task

    # add code to check the battery parameter(or just call a method of the battery object
    log_bat.info('before parameters check')
    if not battery.battery_utilities.check_safety_level_2():
        # stop rig here
        log_bat.info('battery params failed')
        # stop the periodic tasks: bat and inv
        periodic_tasks = PeriodicTask.objects.filter(id__in=[inv_periodic_task_id, bat_periodic_task_id])
        log_bat.info('tasks that should be stopped: %s', periodic_tasks)
        # killing all the periodic tasks
        periodic_tasks.delete()
        log_bat.info('stopped periodic tasks')
        
        log_bat.info('setting statuses and result for test_case')
        # setting test_case
        test_case.state = 'FINISHED'
        test_case.result = 'ERROR'
        test_case.description = 'failed because of ...'
        test_case.save()

        #stop inverter, stop battery
#         battery.battery_utilities.stop_and_release()
#         inverter.inverter_utilities.stop_and_release()
        log_bat.info('removing safety_check task from the scheduler')
        try:
            safety_check_task = PeriodicTask.objects.get(name=name)
            safety_check_task.delete()
        except Exception as err:
            log_bat.exception('unable to get the safety check task')

@shared_task(bind=True)
def populate_result(self, battery_id, inverter_id, test_case_id):
    """
    Executes every X seconds and populates the test_result table.
    battery and inverter models are used for temporary storage of values.
    :param battery_id:
    :param inverter_id:
    :param test_case_id:
    :return:
    """
    from .models import TestCase, TestResult
    test_case = TestCase.objects.get(id=test_case_id)
    battery = test_case.battery
    inverter = test_case.inverter
    timestamp = datetime.datetime.now()

    # battery fields to save
    battery_fields = [
        'dc_voltage',
        'dc_current',
        'cv_1',
        'cv_2',
        'cv_3',
        'cv_4',
        'cv_5',
        'cv_6',
        'cv_7',
        'cv_8',
        'cv_9',
        'cv_min',
        'cv_max',
        'mosfet_temp',
        'pack_temp',
        'cell_overvoltage_level_1',
        'cell_overvoltage_level_2',
        'cell_undervoltage_level_1',
        'cell_undervoltage_level_2',
        'pack_overcurrent',
        'pack_overtemperature_mosfet',
        'pack_overtemperature_cells',
        'error_flag'
    ]
    bat_field_values = [(field, getattr(battery, field)) for field in battery_fields if hasattr(battery, field)]
    log_main.info('bat_field_values are: %s', bat_field_values)
    for field, value in bat_field_values:
        TestResult.objects.create(test_case=test_case,
                                  field='bat_{}'.format(field),
                                  value=value,
                                  timestamp=timestamp)
        
    log_main.info('Pack values saved to db.')
    # inverter fields to save
    inverter_fields = [
        'dc_current',
        'dc_voltage',
        'ac_current',
        'ac_voltage',
        'setpoint'
    ]
    inverter_field_values = [(field, getattr(inverter, field)) for field in inverter_fields if hasattr(inverter, field)]
    log_main.info('inverter_field_values are: %s', inverter_field_values)
    for field, value in inverter_field_values:
        TestResult.objects.create(test_case=test_case,
                                  field='inv_{}'.format(field),
                                  value=value,
                                  timestamp=timestamp)
    log_main.info('Inverter values saved to db.')

@shared_task(bind=True)
def main_task(self, test_case_id):
    time.sleep(1)
    from .models import TestCase

    test_case = TestCase.objects.get(id=test_case_id)
    battery = test_case.battery
    inverter = test_case.inverter
    
    # Inverter Setup
    victron_inv = inverter.inverter_utilities #local instance of the inv utilities for the inverter in use
    victron_inv.prepare_inverter()
    victron_inv.rest()

    # Battery Setup
    battery_instance = battery.battery_utilities
    battery_instance.configure_USB_ISS()
    battery_instance.turn_pack_on()
    battery_instance.update_values()
    
    # create django celery beat periodic task
    # they are like normal django objects with the same methods and query engine

    # create 5s period schedule. Use this for all the tasks that must run at every 5 seconds
    s5_schedule, created = IntervalSchedule.objects.get_or_create(every=5, period=IntervalSchedule.SECONDS)
    s10_schedule, created = IntervalSchedule.objects.get_or_create(every=10, period=IntervalSchedule.SECONDS)
    s60_schedule, created = IntervalSchedule.objects.get_or_create(every=60, period=IntervalSchedule.SECONDS)
    
    val = -200  # inverter.inverter_utilities.send_setpoint()
    log_main.info('send_setpoint returns %s', val)
    # create the send_inverter_setpoint periodic task
    inv_periodic_task = PeriodicTask.objects.create(
        interval=s5_schedule,  # we created this above.
        name='InverterPT_{}'.format(test_case.name),
        task="backend.apps.base.tasks.send_inverter_setpoint",  # name of task.
        args=json.dumps([inverter.id, val]),
        queue='periodic_com_{}'.format(inverter.port)
    )
    log_main.info('periodic task send_inverter_setpoint scheduled')

    val = 11    #battery.battery_utilities.update_values()
    log_main.info('Update_values returns %s', val)
    # create the send_inverter_setpoint periodic task
    bat_periodic_task = PeriodicTask.objects.create( 
        interval=s5_schedule,  # we created this above.
        name='USBISSPT_{}'.format(test_case.name),
        task='backend.apps.base.tasks.send_battery_keep_alive',  # name of task.
        args=json.dumps([battery.id, val]),
        queue='periodic_com_{}'.format(battery.port)
    )
    log_main.info('periodic task send_battery_keep_alive scheduled')
    # create the safety_check periodic task
    task_name = 'SafetyPT_{}'.format(test_case.name)
    safety_check_periodic_task = PeriodicTask.objects.create(
        interval=s5_schedule,  # we created this above.
        name=task_name,  # simply describes this periodic task.
        task='backend.apps.base.tasks.safety_check',  # name of task.
        args=json.dumps([battery.id,
                        inverter.id,
                        test_case.id,
                        inv_periodic_task.id,
                        bat_periodic_task.id,
                        task_name]),
        queue='periodic_com_{}'.format(battery.port)
    )
    log_main.info('periodic task send_battery_keep_alive scheduled')

    task_name = 'Populate_results_{}'.format(test_case.name)
    populate_results_periodic_task = PeriodicTask.objects.create(
        interval=s10_schedule,  # we created this above.
        name=task_name,  # simply describes this periodic task.
        task='backend.apps.base.tasks.populate_result',  # name of task.
        args=json.dumps([battery.id,
                        inverter.id,
                        test_case.id]),
        queue='periodic_com_{}'.format(battery.port)
    )

    # save the headers in the result table
    inverter_header = [
        'name',
        'port',
        've_bus_address',
    ]
    battery_header = [
        'serial_number',
        '',
        '',
    ]
    
    ### Main Logic - use test_case model 
    log_main.info('Attempting to run test_case.run_test() now...')
    try:
        test_case.run_test()
    except Exception as err:
        log_main.exception('Error during running test %s', err)
    log_main.info('Test_case.run_test() completed')
    


    ### test the scheduler with the while loop below:
    while True:
        test_case = TestCase.objects.get(id=test_case_id)
        log_main.info('main_task logic %s', test_case.state)
        if test_case.state == 'FINISHED':
            break

        time.sleep(20)

    # stop inverter operation
    victron_inv.stop()
    
    # stop all periodic tasks when the main finishes
    safety_check_periodic_task.delete()   
    inv_periodic_task.delete()
    bat_periodic_task.delete()
    populate_results_periodic_task.delete()

    log_main.info('Main Task finished naturally. All tasks have been deleted.')

