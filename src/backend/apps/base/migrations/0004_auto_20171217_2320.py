# -*- coding: utf-8 -*-
# Generated by Django 1.11.1 on 2017-12-17 22:20
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('base', '0003_remove_inverterpool_nr_available_inverters'),
    ]

    operations = [
        migrations.CreateModel(
            name='TestCase',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('result', models.CharField(blank=True, max_length=32, null=True)),
                ('description', models.CharField(blank=True, max_length=32, null=True)),
                ('config', models.CharField(blank=True, max_length=32, null=True)),
                ('state', models.CharField(choices=[('RUNNING', 'RUNNING'), ('STOPPED', 'STOPPED'), ('FAILED', 'FAILED'), ('FINISHED', 'FINISHED'), ('PENDING', 'PENDING')], default='PENDING', max_length=32)),
            ],
        ),
        migrations.AlterField(
            model_name='battery',
            name='firmware_version',
            field=models.IntegerField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='testcase',
            name='battery',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='test_case', to='base.Battery'),
        ),
        migrations.AddField(
            model_name='testcase',
            name='inverter',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='test_case', to='base.Inverter'),
        ),
    ]