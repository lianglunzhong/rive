#-*- coding:utf-8 -*-
from django.conf.urls import url
from django.contrib import admin

from . import views

urlpatterns = [
	url(r'^shipitem_add/(?P<id>[0-9]+)$', views.shipitem_add, name='shipitem_add'),
	url(r'^shipitem_delete/(?P<order_id>[0-9]+)/(?P<shipping_id>[0-9]+)$', views.shipitem_delete, name='shipitem_delete'),
	url(r'^change_price_save/(?P<order_id>[0-9]+)/(?P<orderitem_id>[0-9]+)/(?P<product_id>[0-9]+)/(?P<price>[\S]+)$', views.change_price_save, name='change_price_save'),
	url(r'^shipitem_add_save/(?P<order_id>[0-9]+)/(?P<package_id>[0-9]+)/(?P<qty>[0-9]+)/(?P<sku>[\S]+)$', views.shipitem_add_save, name='shipitem_add_save'),
	url(r'^shipitem_add_ajax/', views.shipitem_add_ajax, name='shipitem_add_ajax'),
	#前台添加产品到order_list ajax
	# url(r'^add_to_order_ajax/', views.add_to_order_ajax, name='add_to_order_ajax'),
	#前台order_list页面删除库存限制的产品
	# url(r'^delete_out_of_stock/', views.delete_out_of_stock, name='delete_out_of_stock'),
	url(r'^upload_erp_number/', views.upload_erp_number, name='upload_erp_number'),
	url(r'^upload_package_items/', views.upload_package_items, name='upload_package_items'),
	url(r'^export_orders/', views.export_orders, name='export_orders'),
	url(r'^pdf_test/', views.pdf_test, name='pdf_test'),
	url(r'^pdf_test2/', views.pdf_test2, name='pdf_test2'),
]

