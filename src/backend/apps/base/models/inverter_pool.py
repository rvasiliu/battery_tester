from django.db import models
from django.dispatch import receiver
from django.db.models.signals import pre_save, post_save

from ..models import Inverter
from ..log import log_inverter_pool as log


class InverterPool(models.Model):
    inverter = models.ForeignKey(Inverter, blank=True, null=True)
    available = models.IntegerField(blank=True, null=True)
    