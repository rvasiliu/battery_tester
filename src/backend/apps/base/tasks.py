from celery import shared_task
from celery.app.control import Control
from celery.task import periodic_task
from datetime import timedelta

from .log import log_celery_task as log


class MaxRetriesExceededException(Exception):
    pass


@periodic_task(run_every=timedelta(seconds=30))
def periodic_task_implement(self, id):
    log.info('periodic task printing with a 3 seconds period')


@shared_task(bind=True)
def send_inverter_setpoint(self, inverter_id, set_point):
    """
    This should be a periodic task that keeps the inverter alive.
    Should be executed at 5 seconds interval.
    :param self:
    :param inverter_id:
    :return:
    """
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
    from .models import Battery
    battery = Battery.objects.get(id=battery_id)
    usbiss_bat = battery.battery_utilities
    # usbiss_bat.send_keep_alive()


@shared_task(bind=True)
def safety_check(self, battery_id, inv_periodic_task_id, bat_periodic_task_id, main_task_id):
    from .models import Battery
    battery = Battery.objects.get(id=battery_id)
    # TODO
    # check battery parameters
    # if not ok:
    # 1. stop periodic tasks(inv, bat)
    # 2. send stop to inv
    # 3. send stop to bat
    # 4. set result on test_case = failed and reason/description
    # 5. stop main task

    # add code to check the battery parameter(or just call a method of the battery object

    # stop the periodic tasks
    Control.revoke(inv_periodic_task_id, terminate=True)
    Control.revoke(bat_periodic_task_id, terminate=True)

    # here you should send stop to inv and bat

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
    inv_periodic_task = send_inverter_setpoint.delay(inverter.id, test_case.get_set_point())
    bat_periodic_task = send_battery_keep_alive.delay(battery.id, test_case.get_keep_alive())
    safety_check.delay(battery.id, inv_periodic_task, bat_periodic_task, self.request.id)
    # TODO
    # main logic