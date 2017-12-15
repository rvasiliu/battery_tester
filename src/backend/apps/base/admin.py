from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.models import User

from .models import Battery, Inverter, InverterPool


class BatteryAdmin(admin.ModelAdmin):
    model = Battery
    list_display = ('serial_number', 'port')
    

class InverterAdmin(admin.ModelAdmin):
    model = Inverter
    list_display = ('setpoint','port',)


class InverterPoolAdmin(admin.ModelAdmin):
    model = InverterPool
    list_display = ('nr_available_inverters', 'available_inverters', 'inverters_state')


admin.site.register(Battery, BatteryAdmin)
admin.site.register(Inverter, InverterAdmin)
admin.site.register(InverterPool, InverterPoolAdmin)
# admin.site.register(Profile)