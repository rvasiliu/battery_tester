import datetime
from django.contrib import admin
from django.utils.safestring import mark_safe

from .models import Battery, Inverter, InverterPool, TestCase, TestResult


class BatteryAdmin(admin.ModelAdmin):
    model = Battery
    list_display = ('name', 'serial_number', 'port')


class InverterAdmin(admin.ModelAdmin):
    model = Inverter
    list_display = ('name', 'state', 'setpoint', 'port',)


class InverterPoolAdmin(admin.ModelAdmin):
    model = InverterPool
    list_display = ('name', 'nr_available_inverters', 'available_inverters', 'inverters_state')


class TestCaseAdmin(admin.ModelAdmin):
    model = TestCase
    list_display = ('id', 'name', 'get_battery', 'get_inverter', 'state', 'get_graph')
    list_filter = ('name',)

    def get_battery(self, instance):
        return instance.battery.name
    get_battery.short_description = 'Battery'

    def get_inverter(self, instance):
        return instance.inverter.name
    get_inverter.short_description = 'Inverter'

    def get_graph(self, instance):
        return mark_safe('<a href="{graph}">graph</a>'.format(graph=instance.graph))
    get_graph.short_description = 'Graph'


admin.site.register(Battery, BatteryAdmin)
admin.site.register(Inverter, InverterAdmin)
admin.site.register(InverterPool, InverterPoolAdmin)
admin.site.register(TestCase, TestCaseAdmin)
