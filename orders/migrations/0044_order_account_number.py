# -*- coding: utf-8 -*-
# Generated by Django 1.9.4 on 2017-04-27 09:14
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('orders', '0043_auto_20170324_1648'),
    ]

    operations = [
        migrations.AddField(
            model_name='order',
            name='account_number',
            field=models.CharField(blank=True, default='', max_length=200, null=True, verbose_name='Account number'),
        ),
    ]
