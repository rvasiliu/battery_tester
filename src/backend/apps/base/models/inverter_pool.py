from django.db import models

from ..log import log_inverter_pool as log


class InverterPool(models.Model):
    name = models.CharField(max_length=32, blank=True, null=True)

    def __str__(self):
        return self.name

    @property
    def nr_available_inverters(self):
        return len([inv for inv in self.inverters.all() if inv.state == 'FREE'])

    @property
    def available_inverters(self):
        """
        Property to get available inverters
        :return: a list of available inverters
        """
        return [inv for inv in self.inverters.all() if inv.state == 'FREE']

    @property
    def inverters_state(self):
        """
        get states for all the inverters in the pool
        :return: list of states
        """
        return [inv.state for inv in self.inverters.all()]
