from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.models import User

from .models import Battery

class BatteryAdmin(admin.ModelAdmin):
    model = Battery
    list_display = ('serial_number', 'port')

admin.site.register(Battery, BatteryAdmin)
# admin.site.register(Profile)