# -*- coding: utf-8 -*-
# Generated by Django 1.9.4 on 2017-03-20 09:51
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('products', '0028_auto_20170320_0947'),
    ]

    operations = [
        migrations.AddField(
            model_name='product',
            name='mark',
            field=models.IntegerField(choices=[(1, 'Yes'), (0, 'No')], default=1, verbose_name='Special Mark'),
        ),
    ]