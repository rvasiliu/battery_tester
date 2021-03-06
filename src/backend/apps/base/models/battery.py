from django.db import models
from ..utils import UsbIssBattery


class Battery(models.Model):
    BATTERY_STATES = (
        ('UNDER TEST', 'UNDER TEST'),
        ('FREE', 'FREE'),
        ('OFFLINE', 'OFFLINE')
    )
    name = models.CharField(max_length=32, blank=True, null=True)
    serial_number = models.CharField(max_length=10, blank=True, null=True)
    port = models.CharField(max_length=10, blank=True, null=True)
    i2c_address = models.CharField(max_length=10, blank=True, null=True)

    firmware_version = models.IntegerField(blank=True, null=True)
    
    dc_voltage = models.CharField(max_length=10, blank=True, null=True)
    dc_current = models.CharField(max_length=10, blank=True, null=True)
    
    cv_1 = models.CharField(max_length=10, blank=True, null=True)
    cv_2 = models.CharField(max_length=10, blank=True, null=True)
    cv_3 = models.CharField(max_length=10, blank=True, null=True)
    cv_4 = models.CharField(max_length=10, blank=True, null=True)
    cv_5 = models.CharField(max_length=10, blank=True, null=True)
    cv_6 = models.CharField(max_length=10, blank=True, null=True)
    cv_7 = models.CharField(max_length=10, blank=True, null=True)
    cv_8 = models.CharField(max_length=10, blank=True, null=True)
    cv_9 = models.CharField(max_length=10, blank=True, null=True)
    
    cv_min = models.CharField(max_length=10, blank=True, null=True)
    cv_max = models.CharField(max_length=10, blank=True, null=True)
    
    mosfet_temp = models.CharField(max_length=10, blank=True, null=True)
    pack_temp = models.CharField(max_length=10, blank=True, null=True)
    
    cell_overvoltage_level_1 = models.CharField(max_length=10, blank=True, null=True)
    cell_overvoltage_level_2 = models.CharField(max_length=10, blank=True, null=True)
    cell_undervoltage_level_1 = models.CharField(max_length=10, blank=True, null=True)
    cell_undervoltage_level_2 = models.CharField(max_length=10, blank=True, null=True)
    pack_overcurrent = models.CharField(max_length=10, blank=True, null=True)
    pack_overtemperature_mosfet = models.CharField(max_length=10, blank=True, null=True)
    pack_overtemperature_cells = models.CharField(max_length=10, blank=True, null=True)
    
    is_on = models.BooleanField(default=False)
    error_flag = models.BooleanField(default=False)

    state = models.CharField(max_length=32, choices=BATTERY_STATES, blank=True, null=True)

    def __str__(self):
        return '{}_{}'.format(self.name, self.port)

    @property
    def battery_utilities(self):
        # get the instance from the class attribute if it's already there
        if self.port in UsbIssBattery.battery_instances:
            return UsbIssBattery.battery_instances[self.port]
        # if not, create it and store it on the class attribute
        usbiss_instance = UsbIssBattery(self.port)
        UsbIssBattery.battery_instances[self.port] = usbiss_instance
        return usbiss_instance

