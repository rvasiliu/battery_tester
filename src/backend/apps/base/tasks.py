import time
import json

from celery import shared_task
from celery import current_app

from django_celery_beat.models import PeriodicTask, IntervalSchedule

# log_main should be used in the main task
# log_bat should be used for the battery tasks
# log_inv should be used for the inverter tasks
from .log import log_inverter as log_inv, log_battery as log_bat
from .log import log_test_case as log_main
from backend.apps.base.log import log_test_case


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
        log_bat.info('Pack values saved in db.')
    

@shared_task(bind=True)
def safety_check(self, battery_id, inverter_id, test_case_id,
                 inv_periodic_task_id, bat_periodic_task_id, main_task_id,
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
def main_task(self, test_case_id):
    time.sleep(1)
    from .models import TestCase
    from .models import Inverter
    from .models import Battery
    
    test_case = TestCase.objects.get(id=test_case_id)
    battery = test_case.battery
    inverter = test_case.inverter
    
    # Inverter Setup
    victron_inv = inverter.inverter_utilities #local instance of the inv utilities for the inverter in use
    victron_inv.prepare_inverter()

    # Battery Setup
    battery_instance = battery.battery_utilities
    battery_instance.configure_USB_ISS()
    battery_instance.turn_pack_on()
    battery_instance.update_values()
    
    # create django celery beat periodic task
    # they are like normal django objects with the same methods and query engine

    # create 5s period schedule. Use this for all the tasks that must run at every 5 seconds
    s5_schedule, created = IntervalSchedule.objects.get_or_create(every=5, period=IntervalSchedule.SECONDS)
    
    
    val = -200# inverter.inverter_utilities.send_setpoint()
    log_main.info('send_setpoint returns %s', val)
    # create the send_inverter_setpoint periodic task
    inv_periodic_task = PeriodicTask.objects.create(
        interval=s5_schedule,  # we created this above.
        name='InverterPT_{}'.format(int(time.time())),  # simply describes this periodic task.
        task="backend.apps.base.tasks.send_inverter_setpoint",  # name of task.
        args=json.dumps([inverter.id, val]),
        queue='periodic_com_{}'.format(inverter.port)
    )
    log_main.info('periodic task send_inverter_setpoint scheduled')

    val = 11#battery.battery_utilities.update_values()
    log_main.info('Update_values returns %s', val)
    # create the send_inverter_setpoint periodic task
    bat_periodic_task = PeriodicTask.objects.create( 
        interval=s5_schedule,  # we created this above.
        name='USBISSPT_{}'.format(int(time.time())),  # simply describes this periodic task.
        task='backend.apps.base.tasks.send_battery_keep_alive',  # name of task.
        args=json.dumps([battery.id, val]),
        queue='periodic_com_{}'.format(battery.port)
    )
    log_main.info('periodic task send_battery_keep_alive scheduled')
    # create the safety_check periodic task
    task_name = 'SafetyPT_{}'.format(int(time.time()))
    safety_check_periodic_task = PeriodicTask.objects.create(
        interval=s5_schedule,  # we created this above.
        name=task_name,  # simply describes this periodic task.
        task='backend.apps.base.tasks.safety_check',  # name of task.
        args=json.dumps([battery.id,
                        inverter.id,
                        test_case.id,
                        inv_periodic_task.id,
                        bat_periodic_task.id,
                        self.request.id,
                        task_name
                        ]),
        queue='periodic_com_{}'.format(battery.port)
    )
    log_main.info('periodic task send_battery_keep_alive scheduled')
        
    
    
    ### test the scheduler with the while loop below:
    while True:
        test_case = TestCase.objects.get(id=test_case_id)
        log_main.info('main_task logic %s', test_case.state)
        if test_case.state == 'FINISHED':
            break

        time.sleep(20)
    ### 
    
    safety_check_periodic_task.delete()   
    inv_periodic_task.delete()
    bat_periodic_task.delete()
    
    
    log_test_case.info('Main Task finished naturally. All tasks have been deleted.')
    # TODO
    # main logic
    
