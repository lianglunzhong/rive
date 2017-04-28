from django.conf.urls import url
from django.contrib import admin

from . import views

urlpatterns = [
	url(r'^upload_products/', views.upload_products, name='upload_products'),
	# url(r'^currency_set/', views.currency_set, name='currency_set'),
    # url(r'^currency_get/', views.currency_get, name='currency_get'),
    url(r'^upload_catalogs/', views.upload_catalogs, name='upload_catalogs'),
    url(r'^update_stock/', views.update_stock, name='update_stock'),
    url(r'^update_basic_products/', views.update_basic_products, name='update_basic_products'),
    
]

