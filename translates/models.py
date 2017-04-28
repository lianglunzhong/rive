#-*- coding: utf-8 -*-
from __future__ import unicode_literals
from django.db import models
import os
from accounts.models import Customer, Currency
from django_unixdatetimefield import UnixDateTimeField
from products.models import Product


class ProductFr(models.Model):

	product = models.ForeignKey(Product)
	name = models.CharField(max_length=250,verbose_name="Name")
	description = models.TextField(default='',blank=True,null=True,verbose_name="Description")

	def __unicode__(self):
		return str(self.product)
	

