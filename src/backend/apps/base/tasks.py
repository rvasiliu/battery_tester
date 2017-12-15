from celery import shared_task

from django.conf import settings
from django.db import transaction, IntegrityError
from .log import log_celery_task as log

class MaxRetriesExceededException(Exception):
    pass

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
    inverter = Inverter.object.get(id=inverter_id)
    victron_inv = inverter
    pass

@shared_task(bind=True)
def send_battery_keep_alive(self, battery_id):
    """
    This should be a periodic task that keeps the battery alive.
    Should be executed at 5 seconds interval.
    :param self:
    :param battery_id:
    :return:
    """
    pass


@shared_task(bind=True)
def main_task(self, test_case_id):
    from .models import TestCase
    test_case = TestCase.objects.get(id=test_case_id)
    battery = test_case.battery
    inverter = test_case.inverter
