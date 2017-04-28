# -*- coding: utf-8 -*-
# Generated by Django 1.9.4 on 2017-03-24 16:48
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0020_customer_shop_name'),
    ]

    operations = [
        migrations.AddField(
            model_name='address',
            name='default',
            field=models.IntegerField(blank=True, choices=[(1, 'Yes'), (0, 'No')], default=0, null=True, verbose_name='Set default'),
        ),
    ]