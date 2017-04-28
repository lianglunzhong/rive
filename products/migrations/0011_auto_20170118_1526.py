# -*- coding: utf-8 -*-
# Generated by Django 1.9.4 on 2017-01-18 07:26
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('products', '0010_product_expected_time'),
    ]

    operations = [
        migrations.AlterField(
            model_name='product',
            name='price',
            field=models.DecimalField(blank=True, decimal_places=2, default=0.0, max_digits=16, null=True, verbose_name='Price'),
        ),
    ]
