# -*- coding: utf-8 -*-
# Generated by Django 1.9.4 on 2016-12-29 02:11
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('orders', '0011_auto_20161229_0947'),
    ]

    operations = [
        migrations.AddField(
            model_name='ordermessage',
            name='shipping',
            field=models.ForeignKey(blank=True, default='', null=True, on_delete=django.db.models.deletion.CASCADE, to='orders.Shipping', verbose_name='Shipping method'),
        ),
    ]
