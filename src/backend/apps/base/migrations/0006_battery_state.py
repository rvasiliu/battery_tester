# -*- coding: utf-8 -*-
# Generated by Django 1.11.1 on 2017-12-17 23:23
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('base', '0005_auto_20171217_2341'),
    ]

    operations = [
        migrations.AddField(
            model_name='battery',
            name='state',
            field=models.CharField(blank=True, choices=[('UNDER TEST', 'UNDER TEST'), ('FREE', 'FREE'), ('OFFLINE', 'OFFLINE')], max_length=32, null=True),
        ),
    ]