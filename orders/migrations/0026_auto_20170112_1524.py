# -*- coding: utf-8 -*-
# Generated by Django 1.9.4 on 2017-01-12 07:24
from __future__ import unicode_literals

from django.db import migrations
import django_unixdatetimefield.fields


class Migration(migrations.Migration):

    dependencies = [
        ('orders', '0025_auto_20170111_1104'),
    ]

    operations = [
        migrations.AlterField(
            model_name='order',
            name='expcted_shipping',
            field=django_unixdatetimefield.fields.UnixDateTimeField(blank=True, null=True, verbose_name='Expcted shipping date'),
        ),
    ]