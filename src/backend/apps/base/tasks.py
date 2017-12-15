from celery import shared_task

from django.conf import settings
from django.db import transaction, IntegrityError
from .log import log_celery_task as log

class MaxRetriesExceededException(Exception):
    pass


@shared_task(bind=True, max_retries=10)
def add_socket(self, id):
    log.info('id: %s', id)
    from .models import Battery
    bat = Battery.objects.get(id=id)
    bat.serial_number = 'ce vrea VAS'
    bat.save()
    id += 30
    log.info('id: %s', id)
    
@shared_task(bind=True, max_retries=10)
def add_battery(self, id):
    log.info('Adding new battery... id: %s', id)
    from .models import Battery
    battery_instance = Battery.objects.get(id=id)
    log.info('Retrieved battery instance. Battery serial number: %s', battery_instance.serial_number)
    battery_instance.save()
    log.info('Battery saved to db. Serial nunmber is: %s', battery_instance.serial_number)
    battery_instance.initialise_comms()
    pass

@shared_task(bind=True, max_retries=10)
def add_inverter(self, id):
    log.info('Adding new inverter... id: %s', id)
    from .models import Inverter
    inverter_instance = Inverter.objects.get(id=id)
    #log.info('Retrieved Inverter instance. Battery serial number: %s', battery_instance.serial_number)
    inverter_instance.save()
    #log.info('Inverter saved to db. Serial nunmber is: %s', battery_instance.serial_number)
    #battery_instance.initialise_comms()
    pass


@shared_task(bind=True, max_retries=10)
def send_sms_via_sms_box1(self, id):
    log.info('SMSBox1 id: %s', id)
