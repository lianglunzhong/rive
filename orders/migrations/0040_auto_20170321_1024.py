# -*- coding: utf-8 -*-
# Generated by Django 1.9.4 on 2017-03-21 10:24
from __future__ import unicode_literals

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('orders', '0039_auto_20170321_0920'),
    ]

    operations = [
        migrations.AlterField(
            model_name='orderhistory',
            name='admin',
            field=models.ForeignKey(blank=True, default='', on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL, verbose_name='Admin'),
        ),
        migrations.AlterField(
            model_name='orderhistory',
            name='order',
            field=models.ForeignKey(blank=True, default='', on_delete=django.db.models.deletion.CASCADE, to='orders.Order'),
        ),
    ]