from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.models import User

from .models import Battery, Inverter

class BatteryAdmin(admin.ModelAdmin):
    model = Battery
    list_display = ('serial_number', 'port')
    
class InverterAdmin(admin.ModelAdmin):
    model = Inverter
    list_display = ('setpoint','port',)

admin.site.register(Battery, BatteryAdmin)
admin.site.register(Inverter, InverterAdmin)
# admin.site.register(Profile)