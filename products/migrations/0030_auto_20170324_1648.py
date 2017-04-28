# -*- coding: utf-8 -*-
# Generated by Django 1.9.4 on 2017-03-24 16:48
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('products', '0029_product_mark'),
    ]

    operations = [
        migrations.AddField(
            model_name='product',
            name='rrp',
            field=models.DecimalField(blank=True, decimal_places=2, default=0.0, max_digits=16, null=True, verbose_name='RRP'),
        ),
        migrations.AddField(
            model_name='product',
            name='ssp',
            field=models.DecimalField(blank=True, decimal_places=2, default=0.0, max_digits=16, null=True, verbose_name='SSP'),
        ),
        migrations.AlterField(
            model_name='catalog',
            name='visibility',
            field=models.IntegerField(choices=[(1, 'visible'), (0, 'invisible')], default=1, verbose_name='Visibility'),
        ),
    ]