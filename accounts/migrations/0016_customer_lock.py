# -*- coding: utf-8 -*-
# Generated by Django 1.9.4 on 2017-03-16 15:04
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0015_auto_20170213_0850'),
    ]

    operations = [
        migrations.AddField(
            model_name='customer',
            name='lock',
            field=models.IntegerField(blank=True, default=0, null=True, verbose_name='Lock ?'),
        ),
    ]
