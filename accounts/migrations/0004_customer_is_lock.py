# -*- coding: utf-8 -*-
# Generated by Django 1.9.4 on 2016-12-28 03:04
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0003_auto_20161221_1457'),
    ]

    operations = [
        migrations.AddField(
            model_name='customer',
            name='is_lock',
            field=models.IntegerField(blank=True, default=1, null=True, verbose_name='Is_lock ?'),
        ),
    ]