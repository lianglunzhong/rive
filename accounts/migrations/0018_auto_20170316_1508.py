# -*- coding: utf-8 -*-
# Generated by Django 1.9.4 on 2017-03-16 15:08
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0017_auto_20170316_1507'),
    ]

    operations = [
        migrations.AlterField(
            model_name='customer',
            name='lock',
            field=models.IntegerField(choices=[('1', 'Yes'), ('0', 'No')], default=0, verbose_name='Lock ?'),
        ),
    ]
