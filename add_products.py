# coding: utf-8

# 独立执行的django脚本, 需要添加这四行
import sys, os, django
sys.path.append(os.getcwd())
os.environ['DJANGO_SETTINGS_MODULE'] = 'project.settings'
django.setup()

import time, datetime
import random
from products.models import Product
from Queue import Queue
from threading import Thread
import requests

i = 25
while i<1000:
    name = 'product' + str(i)
    sku = 'sku' + str(i)
    price = round(random.uniform(0,100),2)
    stock = random.randint(0,1)
    is_net_price = random.randint(0,1)
    description = name +' '+ sku +' '+ name +' '+ sku

    i += 1

    product = Product.objects.create(
            name=name,
            sku=sku,
            price=price,
            stock=stock,
            is_net_price=is_net_price,
            description=description,
        )
    print product
