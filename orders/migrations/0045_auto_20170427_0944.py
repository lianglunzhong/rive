# -*- coding: utf-8 -*-
# Generated by Django 1.9.4 on 2017-04-27 09:44
from __future__ import unicode_literals

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('orders', '0044_order_account_number'),
    ]

    operations = [
        migrations.RenameField(
            model_name='order',
            old_name='account_number',
            new_name='accountnumber',
        ),
    ]