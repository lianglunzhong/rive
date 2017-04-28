# -*- coding: utf-8 -*-
# Generated by Django 1.9.4 on 2017-02-06 02:08
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0010_currency'),
    ]

    operations = [
        migrations.AlterField(
            model_name='address',
            name='billing_mobile',
            field=models.CharField(blank=True, default='', max_length=100, null=True, verbose_name='Billing Mobile'),
        ),
        migrations.AlterField(
            model_name='customer',
            name='discount',
            field=models.FloatField(blank=True, default=1.0, null=True, verbose_name='discount'),
        ),
    ]
