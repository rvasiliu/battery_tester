# -*- coding: utf-8 -*-
# Generated by Django 1.11.1 on 2018-01-09 15:50
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('base', '0005_auto_20180108_1844'),
    ]

    operations = [
        migrations.AlterField(
            model_name='testcase',
            name='description',
            field=models.CharField(blank=True, max_length=256, null=True),
        ),
    ]