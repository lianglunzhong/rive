# -*- coding: utf-8 -*-
# Generated by Django 1.9.4 on 2017-02-13 08:50
from __future__ import unicode_literals

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0014_remove_customer_cust_test'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='currency',
            options={'verbose_name': 'Currency', 'verbose_name_plural': 'Currency'},
        ),
    ]
