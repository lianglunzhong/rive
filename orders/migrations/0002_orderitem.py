# -*- coding: utf-8 -*-
# Generated by Django 1.9.4 on 2016-12-21 08:06
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion
import django_unixdatetimefield.fields


class Migration(migrations.Migration):

    dependencies = [
        ('products', '0002_auto_20161221_1412'),
        ('orders', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='Orderitem',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=250, verbose_name='Name')),
                ('sku', models.CharField(max_length=100, unique=True, verbose_name='Sku')),
                ('price', models.FloatField(blank=True, default=0.0, null=True, verbose_name='Price')),
                ('quantity', models.IntegerField(blank=True, default=0, null=True, verbose_name='Quantity')),
                ('created', django_unixdatetimefield.fields.UnixDateTimeField(auto_now_add=True, null=True, verbose_name='Create')),
                ('order', models.ForeignKey(default='', on_delete=django.db.models.deletion.CASCADE, to='orders.Order')),
                ('product', models.ForeignKey(blank=True, default='', null=True, on_delete=django.db.models.deletion.CASCADE, to='products.Product')),
            ],
            options={
                'verbose_name': 'Orderitem',
                'verbose_name_plural': 'Orderitem',
            },
        ),
    ]
