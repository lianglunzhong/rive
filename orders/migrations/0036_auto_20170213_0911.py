# -*- coding: utf-8 -*-
# Generated by Django 1.9.4 on 2017-02-13 09:11
from __future__ import unicode_literals

from django.db import migrations
import django_unixdatetimefield.fields


class Migration(migrations.Migration):

    dependencies = [
        ('orders', '0035_auto_20170213_0850'),
    ]

    operations = [
        migrations.AlterField(
            model_name='order',
            name='expcted_shipping',
            field=django_unixdatetimefield.fields.UnixDateTimeField(blank=True, null=True, verbose_name='Expcted shipping date'),
        ),
    ]