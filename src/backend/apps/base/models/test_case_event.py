from django.db import models

from ..models import TestCase


class TestCaseEvent(models.Model):
    EVENT_NAME = (
        ('CHARGE', 'CHARGE'),
        ('REST', 'REST'),
        ('DISCHARGE', 'DISCHARGE'),
        ('STOP', 'STOP')
    )

    TRIGGERS = (
        ('RECIPE', 'RECIPE'),
        ('SAFETY_CHECK_L1', 'SAFETY_CHECK_L1'),
        ('SAFETY_CHECK_L2', 'SAFETY_CHECK_L2'),
        ('ERROR', 'ERROR'),
    )
    test_case = models.ForeignKey(TestCase, related_name='test_case_event')
    name = models.CharField(max_length=32, blank=True, null=True, choices=EVENT_NAME)
    trigger = models.CharField(max_length=128, blank=True, null=True, choices=TRIGGERS, help_text='safety_check_l1|safety_check_l2')
    message = models.CharField(max_length=128, blank=True, null=True, help_text='overvoltage on ...|undervoltage on ...')
    value = models.IntegerField(blank=True, null=True)
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return '{}_{}'.format(self.name, self.trigger)



