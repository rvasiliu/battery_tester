import logging
from celery.utils.log import get_task_logger

log_battery = logging.getLogger('battery')
log_celery_task = get_task_logger('celery_log')
log_inverter = logging.getLogger('inverter')
log_inverter_pool = logging.getLogger('inverter_pool')
log_test_case = logging.getLogger('test_case')

