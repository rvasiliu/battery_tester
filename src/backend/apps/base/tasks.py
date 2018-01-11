import time
import json
import datetime

from celery import shared_task
from celery import current_app

from django.conf import settings

from django.utils import timezone
from django_celery_beat.models import PeriodicTask, IntervalSchedule

# log_main should be used in the main task
# log_bat should be used for the battery tasks
# log_inv should be used for the inverter tasks
from .log import log_inverter as log_inv, log_battery as log_bat
from .log import log_test_case as log_main


class MaxRetriesExceededException(Exception):
    pass

def calculate_graph_link(tc_id, start, stop='now'):
    if stop == 'now':
        refresh = '&refresh=5s'
    else:
        refresh = ''
    url_params = 'var-test_case_id={tc_id}&from={start_timestamp}&to={stop_timestamp}{refresh}'.format(
        tc_id=tc_id,
        start_timestamp=int(start.strftime('%s')) * 1000,
        stop_timestamp=stop if stop=='now' else int(stop.strftime('%s')) * 1000,
        refresh=refresh)
    return 'http://localhost:9000/dashboard/db/cells-voltage?{url_params}'.format(url_params)

@shared_task(bind=True)
def inverter_frame_read(self, inverter_id):
    from .models import Inverter
    inverter = Inverter.objects.get(id=inverter_id)
    victron_inv = inverter.inverter_utilities
    result = victron_inv.get_info_frame_reply()
    #log_main.info('Inverter frames read result is: %s', result)
    if result:
        inverter_variables = victron_inv.inverter_variables
        for field, value in inverter_variables.items():
            if hasattr(inverter, field):
                #log_main.info('Setting %s field on inverter to value: %s', field, value)
                setattr(inverter, field, value)
        inverter.save()
    return


@shared_task(bind=True)
def send_inverter_setpoint(self, inverter_id):
    """
    This should be a periodic task that keeps the inverter alive.
    Should be executed at 5 seconds interval.
    :param self:
    :param inverter_id:
    :return:
    """
    from .models import Inverter
    inverter = Inverter.objects.get(id=inverter_id)
    victron_inv = inverter.inverter_utilities
    #victron_inv.set_point = set_point
    victron_inv.send_setpoint()
    
    inverter_frame_read.apply_async((inverter_id,), queue='main_com_{}'.format(inverter.port))
    request = victron_inv.request_frames_update()
    log_inv.info('Request frame update has returned: %s', request)
    #if request:
        #inverter_frame_read.delay(inverter_id)
    #   inverter_frame_read.apply_async((inverter_id,), queue='main_com_{}'.format(inverter.port))
    return


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
                pass
                #log_bat.warning('Battery does not have attr: %s', key)
        battery.save()
        
    

@shared_task(bind=True)
def safety_check(self, battery_id, 
                inverter_id, 
                test_case_id,
                inv_periodic_task_id,
                bat_periodic_task_id, 
                populate_results_periodic_task_id,
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

    # add code to check the battery parameter(or just call a method of the battery object
    battery.battery_utilities.check_safety_level_1()
    # get periodic tasks that have to be deleted
    periodic_tasks = PeriodicTask.objects.filter(id__in=[inv_periodic_task_id,
                                                         bat_periodic_task_id,
                                                         populate_results_periodic_task_id])
    if not battery.battery_utilities.check_safety_level_2():
        # stop rig here
        log_main.info('TEST CASE ID: %s - Safety LEVEL 2 triggered in safety_check task.', test_case.id)
        inverter.inverter_utilities.stop()
        log_main.info('TEST CASE ID: %s - Stopped Inverter.', test_case.id)

        
        # stop the periodic tasks: bat and inv
        log_main.info('TEST CASE ID: %s - Following tasks will be stopped: %s', test_case.id, periodic_tasks)
        # killing all the periodic tasks
        periodic_tasks.delete()
        log_main.info('TEST CASE ID: %s - Stopped periodic tasks.', test_case.id)
        
        log_main.info('TEST CASE ID: %s - Setting statuses and result for test_case.', test_case_id)
        # setting test_case
        test_case.state = 'FINISHED'
        test_case.finished = timezone.now() + datetime.timedelta(seconds=60)
        test_case.graph = calculate_graph_link(test_case.id, test_case.created, test_case.finished)
        test_case.result = 'FAILED'
        test_case.description = 'The test failed in safety check LEVEL 2.'
        test_case.save()

        # stop inverter, stop battery
        # battery.battery_utilities.stop_and_release()
        # inverter.inverter_utilities.stop_and_release()
        log_bat.info('Removing safety_check task from the scheduler')
        try:
            safety_check_task = PeriodicTask.objects.get(name=name)
            safety_check_task.delete()
        except Exception as err:
            log_main.exception('TEST CASE ID: %s - Unable to delete the safety check task from the schedule. Error is: %s', test_case.id, err)

    #Check if test marked as FINISHED. 
    elif test_case.state == 'FINISHED':
        log_main.info('TEST CASE ID: %s - FINISHED condition has been detected in safety check. Shutting down.', test_case.id)
        try:
            periodic_tasks.delete()
            safety_check_task = PeriodicTask.objects.get(name=name)
            safety_check_task.delete()
        except Exception as err:
            log_main.exception('TEST CASE ID: %s - Unable to shut down the test: %s', test_case.id, err)

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
    timestamp = timezone.now()

    if not test_case.graph:
        test_case.graph = calculate_graph_link(test_case.id, test_case.created)
        test_case.save()
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
    #log_main.info('bat_field_values are: %s', bat_field_values)
    for field, value in bat_field_values:
        TestResult.objects.create(test_case=test_case,
                                  field='bat_{}'.format(field),
                                  value=value,
                                  timestamp=timestamp)
        
    #log_main.info('Pack values saved to db.')
    # inverter fields to save
    inverter_fields = [
        'dc_current',
        'dc_voltage',
        'ac_current',
        'ac_voltage',
        'dc_capacity',
        'dc_energy',
        'setpoint'
    ]
    inverter_field_values = [(field, getattr(inverter, field)) for field in inverter_fields if hasattr(inverter, field)]
    #log_main.info('inverter_field_values are: %s', inverter_field_values)
    for field, value in inverter_field_values:
        TestResult.objects.create(test_case=test_case,
                                  field='inv_{}'.format(field),
                                  value=value,
                                  timestamp=timestamp)
    #log_main.info('Inverter values saved to db.')
    return


@shared_task(bind=True)
def main_task(self, test_case_id):
    log_main.info('Waiting 25 Seconds...')
    time.sleep(5)
    log_main.info('Done.')
    from .models import TestCase

    test_case = TestCase.objects.get(id=test_case_id)
    battery = test_case.battery
    inverter = test_case.inverter
    
    # Inverter Setup
    victron_inv = inverter.inverter_utilities #local instance of the inv utilities for the inverter in use
    victron_inv.prepare_inverter()
    #victron_inv.rest()

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
        args=json.dumps([inverter.id]),
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
                        populate_results_periodic_task.id,
                        task_name]),
        queue='periodic_com_{}'.format(battery.port)
    )
    log_main.info('Periodic task - safety routine - scheduled')

    
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
    log_main.info('Attempting to run test_case.run_test() for test ID: %s', test_case.id)
    try:
        test_case.run_test()
    except Exception as err:
        log_main.exception('Error during running test ID %s. Error is: %s', test_case.id, err)
    log_main.info('Test_case.run_test() completed for test ID: %s', test_case.id)
    
    # stop inverter operation
    #victron_inv.stop()

    # stop all periodic tasks when the main finishes
    safety_check_periodic_task.delete()   
    inv_periodic_task.delete()
    bat_periodic_task.delete()
    populate_results_periodic_task.delete()

    test_case.state = 'FINISHED'
    test_case.finished = timezone.now() + datetime.timedelta(seconds=60)
    test_case.graph = calculate_graph_link(test_case.id, test_case.created, test_case.finished)
    test_case.result = 'Success'
    test_case.save()

    log_main.info('TEST CASE ID: %s - Main Task finished naturally. All tasks have been deleted.', test_case.id)

