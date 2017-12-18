from celery import shared_task
from celery.app.control import Control

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
    log_inv.info('Send inverter set point: %s', set_point)
    from .models import Inverter
    inverter = Inverter.object.get(id=inverter_id)
    victron_inv = inverter.inverter_utilities
    # victron_inv.send_setpoint(set_point)


@shared_task(bind=True)
def send_battery_keep_alive(self, battery_id, keep_alive):
    """
    This should be a periodic task that keeps the battery alive.
    Should be executed at 5 seconds interval.
    :param self:
    :param battery_id:
    :return:
    """
    log_bat.info('Send battery keep alive: %s', keep_alive)
    from .models import Battery
    battery = Battery.objects.get(id=battery_id)
    usbiss_bat = battery.battery_utilities
    # usbiss_bat.send_keep_alive()


@shared_task(bind=True)
def safety_check(self, battery_id, inverter_id, inv_periodic_task_id, bat_periodic_task_id, main_task_id):
    """
    This should check the battery parameters. It should detect a faulty state and stop the whole flow.
    :param self:
    :param battery_id:
    :param inv_periodic_task_id:
    :param bat_periodic_task_id:
    :param main_task_id:
    :return:
    """
    from .models import Battery, Inverter
    battery = Battery.objects.get(id=battery_id)
    inverter = Inverter.objects.get(id=inverter_id)
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

    if not battery.battery_utilities.check_safety_level_2():
        # stop rig here
        pass

    # stop the periodic tasks: bat and inv
    periodic_tasks = PeriodicTask.objects.filter(id__in=[inv_periodic_task_id, bat_periodic_task_id])
    log_bat.info('tasks that should be stopped: %s', periodic_tasks)
    # killing all the periodic tasks
    periodic_tasks.delete()

    # here you should send stop to inv and bat

    # setting test_case result
    test_case = battery.test_case.all()[0]
    test_case.state = 'FINISHED'
    test_case.result = 'ERROR'
    test_case.description = 'failed because of ...'
    test_case.save()

    # stop the main task
    Control.revoke(main_task_id, terminate=True)

    # stop the periodic tasks
    Control.revoke(inv_periodic_task_id, terminate=True)
    Control.revoke(bat_periodic_task_id, terminate=True)

    #stop inverter, stop battery
    battery.battery_utilities.stop_and_release()
    inverter.inverter_utilities.stop_and_release()
    
    # setting test_case result
    test_case = battery.test_case.all()[0]
    test_case.state = 'FINISHED'
    test_case.result = 'ERROR'
    test_case.description = 'failed because of ...'
    test_case.save()

    # stop the main task
    Control.revoke(main_task_id, terminate=True)


@shared_task(bind=True)
def main_task(self, test_case_id):
    from .models import TestCase
    test_case = TestCase.objects.get(id=test_case_id)
    battery = test_case.battery
    inverter = test_case.inverter

    # create django celery beat periodic task
    # they are like normal django objects with the same methods and query engine

    # create 5s period schedule. Use this for all the tasks that must run at every 5 seconds
    s5_schedule, created = IntervalSchedule.objects.get_or_create(every=5, period=IntervalSchedule.SECONDS)

    # create the send_inverter_setpoint periodic task
    inv_periodic_task = PeriodicTask.objects.create(
        interval=s5_schedule,  # we created this above.
        name='Send inverter set point',  # simply describes this periodic task.
        task="backend.apps.base.tasks.send_inverter_setpoint",  # name of task.
        args=[inverter.id, test_case.get_set_point()],
        queue='periodic_com_{}'.format(inverter.port)
    )
    log_main.info('periodic task send_inverter_setpoint scheduled')

    # create the send_inverter_setpoint periodic task
    bat_periodic_task = PeriodicTask.objects.create(
        interval=s5_schedule,  # we created this above.
        name='Send battery keep alive',  # simply describes this periodic task.
        task='backend.apps.base.tasks.send_battery_keep_alive',  # name of task.
        args=[battery.id, test_case.get_set_keep_alive()],
        queue='periodic_com_{}'.format(battery.port)
    )
    log_main.info('periodic task send_battery_keep_alive scheduled')

    # create the safety_check periodic task
    safety_check_periodic_task = PeriodicTask.objects.create(
        interval=s5_schedule,  # we created this above.
        name='Send battery keep alive',  # simply describes this periodic task.
        task='backend.apps.base.tasks.safety_check',  # name of task.
        args=[battery.id,
              inv_periodic_task.id,
              bat_periodic_task.id,
              self.request.id,
              ],
        queue='periodic_com_{}'.format(battery.port)
    )
    log_main.info('periodic task send_battery_keep_alive scheduled')

    # TODO
    # main logic
