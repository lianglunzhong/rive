# -*- coding: utf-8 -*-
# Generated by Django 1.9.4 on 2017-03-17 16:55
from __future__ import unicode_literals

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('translates', '0002_promotion'),
    ]

    operations = [
        migrations.DeleteModel(
            name='Promotion',
        ),
    ]
