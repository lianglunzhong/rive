# -*- coding: utf-8 -*-
# Generated by Django 1.9.4 on 2017-01-03 05:54
from __future__ import unicode_literals

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('orders', '0015_auto_20161229_1720'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='cartitem',
            name='created',
        ),
    ]
