# -*- coding: utf-8 -*-
# Generated by Django 1.9.4 on 2017-01-22 08:15
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('products', '0019_catalog_visibility'),
    ]

    operations = [
        migrations.AddField(
            model_name='productimage',
            name='title',
            field=models.CharField(blank=True, default='', max_length=200, null=True, verbose_name='Title'),
        ),
    ]
