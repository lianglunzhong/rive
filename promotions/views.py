#-*- coding:utf-8 -*-
from django.shortcuts import render
from django.http import HttpResponse, HttpResponseRedirect
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect
import time
from django.conf import settings
from django.views.decorators.csrf import csrf_protect
from .models import Promotion
from accounts.views import order_list_count
from accounts.models import Customer
from library.views import get_promotion

def promotion(request):
    data = {}

    has_promotion = get_promotion(request)
    data['has_promotion'] = has_promotion

    if not has_promotion:
        return redirect('products')

    #判断是否登陆，并把参数传递到模板页
    # customer = is_login(request)
    customer_id = request.session.get('customer_id', False)
    if not customer_id:
        return redirect('login')
    else:
        customer = Customer.objects.filter(id=customer_id).first()
        #判断用户是否被锁定
        if customer.locked:
            try:
                del request.session['customer_id']
            except KeyError:
                pass
            return redirect('login')

    data['customer'] = customer

    #order list数量显示
    data['number'] = order_list_count(request,customer.id)

    promotion = Promotion.objects.filter(visibility=1).order_by('-id').first()

    data['promotion'] = promotion

    #导航栏激活样式
    data['nav_products'] = ''
    data['nav_order_list'] = ''
    data['nav_order_history'] = ''
    data['nav_promotion'] = 'active'

    return render(request, 'promotion.html', data)
