import pandas as pd

from celery import shared_task
from celery.app.control import Control
from celery.task import periodic_task

from .log import log_celery_task as log
from .log import log_test_case
from backend.apps.base.models import inverter

from django.conf import settings

class MaxRetriesExceededException(Exception):
    pass

@periodic_task()


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
    #from .models import Inverter
    battery = Battery.objects.get(id=battery_id)
    
    # TODO
    # check battery parameter    
    # if not ok:
    # 1. stop periodic tasks(inv, bat)
    # 2. send stop to inv
    # 3. send stop to bat
    # 4. set result on test_case = failed and reason/description
    # 5. stop main task

    #add code to check battery parameter/safety flag
     
    if not battery.battery_utilities.check_safety_level_2():
        #stop rig here
        pass

    # stop the periodic tasks
    Control.revoke(inv_periodic_task_id, terminate=True)
    Control.revoke(bat_periodic_task_id, terminate=True)

    #stop inverter, stop battery
    battery.battery_utilities.stop_and_release()
    #inverter.inverter_utilities.stop_and_release()
    
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
    df_recipe = pd.read_csv(settings.LOOKUP_TABLE)
    for i in range(0,len(df_recipe)):
        log_test_case.info('Proceeding to step %s in test case with ID: %s.', i, test_case_id)
        if(df_recipe.step_type[i] == 'CC Charge'):
            log_test_case.info('Attempting step type %s in test case with ID: %s', df_recipe.step_type[i], test_case_id)
            test_case.cc_charge()
            pass

        elif(df_recipe.step_type[i] == 'CC Discharge'):
            log_test_case.info('Attempting step type %s in test case with ID: %s', df_recipe.step_type[i], test_case_id)
            test_case.cc_discharge()
            pass
        
        elif(df_recipe.step_type[i] == 'Rest'):
            log_test_case.info('Attempting step type %s in test case with ID: %s', df_recipe.step_type[i], test_case_id)
            test_case.rest()
            pass
        
        else:
            log_test_case.info('Unrecognised Step Type in test case with ID: %s', test_case_id)
            pass
        
        