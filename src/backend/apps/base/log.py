import logging
from celery.utils.log import get_task_logger

log_battery = logging.getLogger('battery')
log_celery_task = get_task_logger('celery_log')
log_inverter = logging.getLogger('inverter')
