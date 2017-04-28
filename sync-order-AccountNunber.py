# coding: utf-8

# 独立执行的django脚本, 需要添加这四行
import sys, os, django
sys.path.append(os.getcwd())
os.environ['DJANGO_SETTINGS_MODULE'] = 'project.settings'
django.setup()

from orders.models import Order

orders = Order.objects.all()

for order in orders:
	if order.customer:
		Order.objects.filter(id=order.id).update(accountnumber=order.customer.account_number)

print 'success'