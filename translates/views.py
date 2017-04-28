#-*- coding:utf-8 -*-
from django.shortcuts import render
from products.models import Product
from django.db.models import Q
from translates.models import ProductFr

import re  
import urllib,urllib2 

