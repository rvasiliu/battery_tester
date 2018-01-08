from django.db import models
from ..models import TestCase


class TestResult(models.Model):
    test_case = models.ForeignKey(TestCase, related_name='test_result')
    field = models.CharField(max_length=32, blank=True, null=True)
    value = models.FloatField(blank=True, null=True)
    timestamp = models.DateTimeField()

    def __str__(self):
        return 'Test result for {}'.format(self.test_case.name)
