#-*- coding:utf-8 -*-
from django.conf.urls import url
from django.contrib import admin

from . import views

urlpatterns = [
	# url(r'^change_password_ajax/', views.change_password_ajax, name='change_password_ajax'),
	url(r'^upload_customers/', views.upload_customers, name='upload_customers'),
	url(r'^mail_ajax_test/', views.mail_ajax_test, name='mail_ajax_test'),
	url(r'^send_orderitem_shortage_mail/', views.send_orderitem_shortage_mail, name='send_orderitem_shortage_mail'),
	url(r'^send_orderitem_shortage_mail_test/', views.send_orderitem_shortage_mail_test, name='send_orderitem_shortage_mail_test'),
	url(r'^export_customers/', views.export_customers, name='export_customers'),
	url(r'^update_basic_shopkeepers/', views.update_basic_shopkeepers, name='update_basic_shopkeepers'),
]

