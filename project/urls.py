#-*- coding: utf-8 -*-
"""project URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/1.9/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  url(r'^$', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  url(r'^$', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.conf.urls import url, include
    2. Add a URL to urlpatterns:  url(r'^blog/', include('blog.urls'))
"""
from django.conf.urls import url, include
from django.contrib import admin
from django.views.generic import TemplateView
from accounts import views as accounts_views
from orders import views as orders_views
from products import views as products_views
from promotions import views as promotions_views
from django.conf import settings
from django.views import static
from products.views import ProductAutocomplete
from django.conf.urls import handler404, handler500


urlpatterns = [
    url(r'^$',accounts_views.index, name='index'),
    url(r'^product-autocomplete/$', ProductAutocomplete.as_view(), name='product-autocomplete'),
    url(r'^i18n/', include('django.conf.urls.i18n')),
    url(r'^admin/', admin.site.urls),
    url(r'^login/', accounts_views.login, name='login'),
    url(r'^template/', accounts_views.template, name='template'),
    url(r'^logout/', accounts_views.logout, name='logout'),
    #产品
    url(r'^products/', products_views.products, name='products'),
    #产品分页
    url(r'^products/page_(?P<page_id>[0-9]+)$', products_views.products, name='products_page'),
    #产品分类搜索分页
    # url(r'^products/page_(?P<page_id>[0-9]+)/(?P<category_id>[0-9]+)$', products_views.products, name='products_search_page'),
    url(r'^pagination/', products_views.pagination, name='pagination'),
    url(r'^order_list/', orders_views.order_list, name='order_list'),
    url(r'^order_history/', orders_views.order_history, name='order_history'),
    url(r'^order_history/page_(?P<page_id>[0-9]+)$', orders_views.order_history, name='order_history_page'),
    url(r'^order_detail/', orders_views.order_detail, name='order_detail'),
    url(r'^order_test/', orders_views.order_test, name='order_test'),
    url(r'^order_print/(?P<order_id>[0-9]+)$', orders_views.order_print, name='order_print'),
    url(r'^admin/products/', include('products.urls')),
    url(r'^admin/orders/', include('orders.urls')),
    url(r'^admin/accounts/', include('accounts.urls')),
    url(r'^about/$', TemplateView.as_view(template_name="about.html")),
    url(r'^site_media/(?P<path>[\S]+)$', static.serve,{'document_root': settings.STATIC_PATH}),
    url(r'^static/(?P<path>[\S]+)$', static.serve,{'document_root': settings.STATIC_ROOT }), 
    url(r'^upload_pic_order/', orders_views.upload_pic_order, name='upload_pic_order'),
    url(r'^upload_list_order/', orders_views.upload_list_order, name='upload_list_order'),
    url(r'^change_password_ajax/', accounts_views.change_password_ajax, name='change_password_ajax'),
    url(r'^add_to_order_ajax/', orders_views.add_to_order_ajax, name='add_to_order_ajax'),
    url(r'^delete_out_of_stock/', orders_views.delete_out_of_stock, name='delete_out_of_stock'),
    url(r'^currency_set/', products_views.currency_set, name='currency_set'),
    url(r'^currency_get/', products_views.currency_get, name='currency_get'),
    url(r'^order_address_delete/', orders_views.order_address_delete, name='order_address_delete'),
    url(r'^order_address_add/', orders_views.order_address_add, name='order_address_add'),
    url(r'^order_address_edit/', orders_views.order_address_edit, name='order_address_edit'),
    url(r'^order_address_set_default/', orders_views.order_address_set_default, name='order_address_set_default'),
    url(r'^ckeditor/', include('ckeditor_uploader.urls')),
    url(r'^promotion/', promotions_views.promotion, name='promotion'),
    url(r'^customer_address/', accounts_views.customer_address, name='customer_address'),
    url(r'^customer_address_handle/', accounts_views.customer_address_handle, name='customer_address_handle'),
    url(r'^customer_address_delete/(?P<address_id>[0-9]+)$', accounts_views.customer_address_delete, name='customer_address_delete'),
    url(r'^customer_address_setdefault/(?P<address_id>[0-9]+)/(?P<customer_id>[0-9]+)$', accounts_views.customer_address_setdefault, name='customer_address_setdefault'),
    url(r'^billing_address/', accounts_views.billing_address, name='billing_address'),
    url(r'^billing_address_handle/', accounts_views.billing_address_handle, name='billing_address_handle'),
    
]

#自定义前后台404/500页面，前后台分开
handler404 = "accounts.views.page_not_found"
handler500 = "accounts.views.page_error"