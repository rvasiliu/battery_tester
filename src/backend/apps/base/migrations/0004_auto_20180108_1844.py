# -*- coding: utf-8 -*-
# Generated by Django 1.11.1 on 2018-01-08 18:44
from __future__ import unicode_literals

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('base', '0003_auto_20180105_1720'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='battery',
            name='cell_overvoltage_level_1',
        ),
        migrations.RemoveField(
            model_name='battery',
            name='cell_overvoltage_level_2',
        ),
        migrations.RemoveField(
            model_name='battery',
            name='cell_undervoltage_level_1',
        ),
        migrations.RemoveField(
            model_name='battery',
            name='cell_undervoltage_level_2',
        ),
        migrations.RemoveField(
            model_name='battery',
            name='pack_overcurrent',
        ),
        migrations.RemoveField(
            model_name='battery',
            name='pack_overtemperature_cells',
        ),
        migrations.RemoveField(
            model_name='battery',
            name='pack_overtemperature_mosfet',
        ),
    ]
