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
        timestamps = None
        refresh = ''
        # get timestamp for test start
        try:
            tc = TestResult.objects.filter(test_case=instance.id)
            timestamps = set([int(t.timestamp.strftime("%s")) for t in tc])
        except Exception as err:
            print(err)
        print('################', instance.id)
        if timestamps:
            tc_start_timestamp = min(timestamps)*1000
            tc_stop_timestamp = max(timestamps)*1000
        else:
            tc_start_timestamp = 'now'
            tc_stop_timestamp = 'now'
        print('################', tc_start_timestamp)
        print('################', tc_stop_timestamp)
        if instance.state == 'RUNNING':
            tc_stop_timestamp = 'now'
            refresh = '&refresh=5s'
        url_params = 'var-test_case_id={tc_id}&from={start_timestamp}&to={stop_timestamp}{refresh}'.format(tc_id=instance.id,
                                                                                                           start_timestamp=tc_start_timestamp,
                                                                                                           stop_timestamp=tc_stop_timestamp,
                                                                                                           refresh=refresh)
        return mark_safe('<a href="http://localhost:9000/dashboard/db/cells-voltage?{url_params}">graph</a>'.format(url_params=url_params))
    get_graph.short_description = 'Graph'


admin.site.register(Battery, BatteryAdmin)
admin.site.register(Inverter, InverterAdmin)
admin.site.register(InverterPool, InverterPoolAdmin)
admin.site.register(TestCase, TestCaseAdmin)
