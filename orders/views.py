#-*- coding:utf-8 -*-
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect,render_to_response
from django.http import HttpResponse, HttpResponseRedirect
from django.template import RequestContext
from .models import ShippingItem, OrderItem, CartItem, Order, Package, Shipping
import time
import demjson
from django.contrib import messages
from accounts.views import is_login, order_list_count,get_shipping_address,get_billing_address,get_stock_group,get_est_date
from accounts.models import Address, Customer, Currency,BillingAddress
from products.models import Product, ProductImage
from products.views import time_str, time_stamp, currency_get, get_currency_code, write_csv,eparse,time_stamp2,time_str2
import os
from django.conf import settings
import StringIO
import csv
from django.db import connection, transaction
# from reportlab.pdfgen import canvas
# from io import BytesIO
# import pdfcrowd
# from var_dump import var_dump
from django.contrib.auth.models import User,Group
import chardet
import sys
from library.views import sendEmail
from django.conf import settings
reload(sys)
sys.setdefaultencoding('utf8')
import thread
from library.views import getCookie, get_promotion



#订单详情页添加shipping_item页面及参数传递
@login_required
def shipitem_add(request,id):
    data = {}
    data['package_id'] = id
    return render(request,'shippingitem_add.html',data)

#上传csv文件，批量更新订单erpnumber
@login_required
def upload_erp_number(request):
    data = {}
    #获取上一个页面url，数据处理之后跳转回该页面
    referer_url = request.META['HTTP_REFERER']

    if request.method == 'POST':
        #上传csv批量更新订单的erpnum
        if request.POST['type'] == 'verify_orders_by_batch':

            #获取文件对象
            file_obj = request.FILES.get('verify_orders_by_batch', None)

            if file_obj == None:
                return redirect(referer_url)

            #文件内容
            file_content = file_obj.read()

            #格式转化
            try:
                reader = csv.reader(StringIO.StringIO(file_content),delimiter=';')
                header = next(reader)
            except Exception as e:
                return redirect(referer_url)

            std_header = [
                "Order_NO.","ERP_NO."
            ]
            field_header = [
                "ordernum",'erp_num'
            ]

            # 由于bom头的问题, 就不比较第一列的header了
            if header[1:] != std_header[1:]:
                messages.error(request, u"Please use the correct template and save as UTF-8 format.")
                return redirect(referer_url)

            #用于保存正确的订单号
            ordernum_right = {}
            #用于保存错误的订单号
            ordernum_error = []

            #获取csv表格每一行的值，i为行数，row该行对应的列的值
            for i, row in enumerate(reader,2):
                #将上传的每一行的值与改行的标题一一对应
                res = zip(field_header,row)
                #转为为字典，方便后面取值
                res = dict(res)
                
                res['erp_num'] = res['erp_num'].strip().decode('gbk').encode('utf-8')

                #判断输入的订单号是否有误
                order = Order.objects.filter(ordernum=res['ordernum']).first()
                if order:
                    if res['erp_num']:
                        ordernum_right[res['ordernum']] = res['erp_num']
                else:
                    ordernum_error.append(res['ordernum'])

            #更新
            data_error = []
            for key,value in ordernum_right.items():
                query = Order.objects.filter(ordernum=key).update(erp_num=value)
                if not query:
                    data_error.append(key)
                else:
                    # 给用户发送邮件
                    order = Order.objects.filter(ordernum=key).first()
                    customer = Customer.objects.filter(id=order.customer_id).first()
                    email = {}
                    email['receiver'] = [customer.email]
                    template = 'email_order_process.html'
                    sendData = {}
                    sendData['title'] = 'RIVE – B2B order status update'
                    sendData['order_number'] = key
                    # sendEmail(email, template, sendData)
                    thread.start_new_thread(sendEmail, (email,template,sendData))

            #上传错误的订单号提示
            if ordernum_error:
                ordernum_error = tuple(ordernum_error)
                messages.error(request,u"Order_NO.："+str(ordernum_error)+u"is(are) not accurate.")
                return redirect(referer_url)

            if data_error:
                data_error = tuple(data_error)
                messages.error(request,u"Order_NO.："+str(data_error)+u"updated falsed")
                return redirect(referer_url)
            else:
                messages.success(request,u"Order(s) has been verifyed successfully")
                return redirect(referer_url)

    return HttpResponse('111111111')

#上传csv文件，批量添加订单包裹产品
@login_required
def upload_package_items(request):
    data = {}
    #获取上一个页面url，数据处理之后跳转回该页面
    referer_url = request.META['HTTP_REFERER']

    if request.method == 'POST':
        #上传csv批量添加订单包裹产品
        if request.POST['type'] == 'upload_packageitems_by_batch':
            #获取文件对象
            file_obj = request.FILES.get('upload_packageitems_by_batch', None)

            if file_obj == None:
                return redirect(referer_url)

            #文件内容
            file_content = file_obj.read()

            #格式转化
            try:
                reader = csv.reader(StringIO.StringIO(file_content),delimiter=';')
                header = next(reader)
            except Exception as e:
                return redirect(referer_url)

            std_header = [
                "Order_NO.","Shiping_Method","Tracking_NO.","Ref.","QTY","Note",
            ]
            field_header = [
                "ordernum",'shipping_method','tracking_num','sku','qty','note'
            ]

            # 由于bom头的问题, 就不比较第一列的header了
            if header[1:] != std_header[1:]:
                messages.error(request, u"Please use the correct template and save as UTF-8 format.")
                return redirect(referer_url)

            #用于保存正确的订单号
            ordernum_right = {}
            #保存正确订单号的产品，用于判断该订单号下的产品是否正确，如果全都不正确，则不新增包裹
            ordernum_sku = {}
            #用于保存错误的订单号
            ordernum_error = []
            #用于保存所有上传每一行的数据
            upload_data = []

            #获取csv表格每一行的值，i为行数，row该行对应的列的值
            for i, row in enumerate(reader,2):
                #将上传的每一行的值与改行的标题一一对应
                res = zip(field_header,row)
                #转为为字典，方便后面取值
                res = dict(res)

                res['note'] = res['note'].strip().decode('gbk').encode('utf-8')
                res['shipping_method'] = res['shipping_method'].strip().decode('gbk').encode('utf-8')
                res['tracking_num'] = res['tracking_num'].strip().decode('gbk').encode('utf-8')

                upload_data.append(res)

                #判断输入的订单号是否有误
                order = Order.objects.filter(ordernum=res['ordernum']).first()
                if order:
                    if ordernum_sku.has_key(res['ordernum']):
                        ordernum_sku[res['ordernum']].append(res['sku'])
                    else:
                        ordernum_sku[res['ordernum']] = [res['sku']]
                    #先取出包含shipping_method 和 tracking_num的数据来创建一个新的包裹，没有的则跳过，所有的产品后面再加
                    if res['shipping_method']:
                        ordernum_right[res['ordernum']] = {'shipping_method':res['shipping_method'],'tracking_num':res['tracking_num'],'note':res['note']}
                else:
                    if res['ordernum']:
                        ordernum_error.append(res['ordernum'])

            #错误的发货方式保存
            shipping_error = []
            #错误的产品sku保存
            product_error = []
            #创建包裹并添加产品
            for key, value in ordernum_right.items():
                #先判断该订单号下的产品sku是否正确，如果产品全都不正确，则不创建包裹
                sku_lists = ordernum_sku[key]
                right_sku = 0
                for sku in sku_lists:
                    #判断sku是否输入正确
                    product = Product.objects.filter(sku=sku).first()
                    if product:
                        right_sku = 1
                        break
                #包含正确sku的情况下
                if right_sku:
                    #订单
                    order = Order.objects.filter(ordernum=key).first()
                    #发货方式
                    shipping_method = value['shipping_method']
                    #判断发货方式与后台保存的是否一致，不一致则跳过该订单不创建包裹
                    shipping = Shipping.objects.filter(ship_company=shipping_method).first()
                    if shipping:
                        tracking_num = value['tracking_num']
                        note = value['note']
                        #创建包裹
                        package = Package.objects.create(order_id=order.id,shipping_id=shipping.id,tracking_number=tracking_num,note=note)
                        if package:
                            for res in upload_data:
                                #获取每一个包裹订单对应的产品
                                if res['ordernum'] == key:
                                    if res['sku'] and res['qty']:
                                        #判断sku是否输入正确
                                        product = Product.objects.filter(sku=res['sku']).first()
                                        if product:
                                            #添加包裹产品
                                            shippingitem = ShippingItem.objects.create(package_id=package.id,sku=res['sku'],quantity=res['qty'],name=product.name)
                            #产品添加成功之后，获取订单产品发货数量，更新订单状态
                            #包含图片的订单不更新订单状态，需要手动更新
                            imgorder = order.imgorder
                            if not imgorder:
                                orderitem_products = {}
                                #订单产品及数量
                                orderitems = OrderItem.objects.filter(order_id=order.id).all()
                                for orderitem in orderitems:
                                    orderitem_products[orderitem.sku] = int(orderitem.quantity)
                                #该订单所有发货包裹中的产品及数量
                                #包裹
                                packages = Package.objects.filter(order_id=order.id).all()
                                package_ids = []
                                for p in packages:
                                    package_ids.append(p.id)
                                package_ids = tuple(package_ids)
                                #包裹产品
                                shippingitem_products = {}
                                shippingitems = ShippingItem.objects.filter(package_id__in=package_ids).all()
                                for shippingitem in shippingitems:
                                    if shippingitem_products.has_key(shippingitem.sku):
                                        shippingitem_products[shippingitem.sku] += int(shippingitem.quantity)
                                    else:
                                        shippingitem_products[shippingitem.sku] = int(shippingitem.quantity)
                                #字典比较
                                #1.比较字典长度，如果包裹中产品字典长度小于订单产品详情的长度，则改订单状态为部分发货
                                if len(shippingitem_products) < len(orderitem_products):
                                    order_update = Order.objects.filter(id=order.id).update(status=2)
                                else:
                                    #包裹中产品字典长度等于或大于订单产品详情的长度，比较键名，包裹中产品中如果不包含订单产品详情的键名，部分发货
                                    not_key = 0
                                    for key, value in orderitem_products.items():
                                        if shippingitem_products.has_key(key):
                                            pass
                                        else:
                                            not_key = 1
                                    if not_key:
                                        order_update = Order.objects.filter(id=order.id).update(status=2)
                                    else:
                                        #键都有的情况，比较键值的大小，如果包裹中产品小于订单产品，则部分发货
                                        is_partical = 0
                                        for key, value in orderitem_products.items():
                                            if shippingitem_products.has_key(key):
                                                if shippingitem_products[key] < value:
                                                    is_partical = 1
                                                    break
                                        if is_partical:
                                            order_update = Order.objects.filter(id=order.id).update(status=2)
                                        else:
                                            order_update = Order.objects.filter(id=order.id).update(status=3)

                                # 给用户发送邮件
                                customer = Customer.objects.filter(id=order.customer_id).first()
                                email = {}
                                email['receiver'] = [customer.email]
                                template = 'email_order_shipped.html'
                                sendData = {}
                                sendData['title'] = 'RIVE – B2B order status update'
                                sendData['order_number'] = order.ordernum
                                # sendEmail(email, template, sendData)
                                thread.start_new_thread(sendEmail, (email,template,sendData))

                    else:
                        shipping_error.append(shipping_method)

            #对错误数据的类型判断及结果反馈
            if ordernum_error and shipping_error:
                ordernum_error = tuple(ordernum_error)
                shipping_error = tuple(shipping_error)
                messages.error(request,u"Order_NO.："+str(ordernum_error)+",Shipping method："+str(shipping_error)+"is(are) not accurate.")
                return redirect(referer_url)
            elif ordernum_error:
                ordernum_error = tuple(ordernum_error)
                messages.error(request,u"Order_NO.:"+str(ordernum_error)+"is(are) not accurate.")
                return redirect(referer_url)
            elif shipping_error:
                shipping_error = tuple(shipping_error)
                messages.error(request,u"Shipping method："+str(shipping_error)+"is(are) not accurate.")
                return redirect(referer_url)
            else:
                messages.success(request,"Package item(s) has been added successfully")
                return redirect(referer_url)

    return HttpResponse('222222222')


#导出订单
@login_required
def export_orders(request):
    data = {}

    if request.method == 'POST':
        if request.POST['type'] == 'export_orders':
            from_time = request.POST['from']
            to_time = request.POST['to']

            try:
                from_time = from_time + " 00:00:00"
                from_time = time_stamp2(from_time)
                to_time = to_time + " 23:59:59"
                to_time = time_stamp2(to_time)
            except Exception,e:
                messages.error(request,u'Please enter the correct time format !')
                return redirect(referer_url)

            status = int(request.POST['status'])
            mark = str(request.POST['mark'])
            user_id = int(request.POST['user_id'])

            if user_id == 9999:
                customers = Customer.objects.all()
            else:
                customers = Customer.objects.filter(admin_id=user_id).all()

            customer_ids = []
            for c in customers:
                customer_ids.append(c.id)
            customer_ids = tuple(customer_ids)

            if mark == 'all':
                if from_time and to_time:
                    if status == 5:
                        orders = Order.objects.filter(created__gte=from_time,created__lt=to_time,customer_id__in=customer_ids).all().order_by('-id')
                    else:
                        orders = Order.objects.filter(created__gte=from_time,created__lt=to_time,status=status,customer_id__in=customer_ids).all().order_by('-id')
                elif from_time:
                    if status == 5:
                        orders = Order.objects.filter(created__gte=from_time,customer_id__in=customer_ids).all().order_by('-id')
                    else:
                        orders = Order.objects.filter(created__gte=from_time,status=status,customer_id__in=customer_ids).all().order_by('-id')
                elif to_time:
                    if status == 5:
                        orders = Order.objects.filter(created__lt=to_time,customer_id__in=customer_ids).all().order_by('-id')
                    else:
                        orders = Order.objects.filter(created__lt=to_time,status=status,customer_id__in=customer_ids).all().order_by('-id')
                else:
                    if status == 5:
                        orders = Order.objects.filter(customer_id__in=customer_ids).all().order_by('-id')
                    else:
                        orders = Order.objects.filter(status=status,customer_id__in=customer_ids).all().order_by('-id')
            else:
                if from_time and to_time:
                    if status == 5:
                        orders = Order.objects.filter(created__gte=from_time,created__lt=to_time,customer_id__in=customer_ids,mark=mark).all().order_by('-id')
                    else:
                        orders = Order.objects.filter(created__gte=from_time,created__lt=to_time,status=status,customer_id__in=customer_ids,mark=mark).all().order_by('-id')
                elif from_time:
                    if status == 5:
                        orders = Order.objects.filter(created__gte=from_time,customer_id__in=customer_ids,mark=mark).all().order_by('-id')
                    else:
                        orders = Order.objects.filter(created__gte=from_time,status=status,customer_id__in=customer_ids,mark=mark).all().order_by('-id')
                elif to_time:
                    if status == 5:
                        orders = Order.objects.filter(created__lt=to_time,customer_id__in=customer_ids,mark=mark).all().order_by('-id')
                    else:
                        orders = Order.objects.filter(created__lt=to_time,status=status,customer_id__in=customer_ids,mark=mark).all().order_by('-id')
                else:
                    if status == 5:
                        orders = Order.objects.filter(customer_id__in=customer_ids,mark=mark).all().order_by('-id')
                    else:
                        orders = Order.objects.filter(status=status,customer_id__in=customer_ids,mark=mark).all().order_by('-id')

                        
            #导出格式
            export_format = int(request.POST['export_format'])
            #CSV格式导出
            if export_format == 0:
                response, writer = write_csv('export_orders')
                writer.writerow(['NO.','EPR NO.','Status','Stock-Mark','Amount','Currency','Created', 'Verified time','Shop keeper','Account number','Expcted shipping date','Comment','Ref.','Price','Quantity','Item-Mark','shipping_country','shipping_state','shipping_city','shipping_address','shipping_zip','shipping_phone','shipping_mobile','billing_country','billing_state','billing_city','billing_address','billing_zip','billing_phone','billing_mobile'])

                for order in orders:
                    #订单状态
                    status = ''
                    if order.status == 0:
                        status = 'new'
                    elif order.status == 1:
                        status = 'processing'
                    elif order.status == 2:
                        status = 'partical shipped'
                    elif order.status == 3:
                        status = 'shipped'
                    elif order.status == 4:
                        status = 'cancel'

                    #期待发货时间
                    expcted_shipping = ''
                    if order.expcted_shipping and order.expcted_shipping != 'None':
                        try:
                            expcted_shipping = time_str2(order.expcted_shipping)
                        except Exception as e:
                            expcted_shipping = ''

                    #account_number
                    account_number = ''
                    if order.customer:
                        account_number = order.customer.account_number

                    #判断产品是否存在，存在的话取一个产品数据用作第一行导出
                    order_id = order.id
                    orderitem = OrderItem.objects.filter(order_id=order_id).order_by('id').first()
                    sku = ''
                    quantity = ''
                    price = ''
                    item_mark = ''
                    if orderitem and orderitem != 'None':
                        sku = orderitem.sku
                        quantity = orderitem.quantity
                        price = orderitem.price
                        item_mark = orderitem.mark
                    row = [
                        str(order.ordernum.encode('utf-8')),
                        str(order.erp_num.encode('utf-8')),
                        str(status),
                        str(order.mark),
                        str(order.amount),
                        str(order.currency),
                        str(order.created),
                        str(order.verifued),
                        str(order.customer),
                        str(account_number),
                        str(expcted_shipping),
                        str(order.message.encode('utf-8')),
                        str(sku),
                        str(price),
                        str(quantity),
                        str(item_mark),
                        str(order.shipping_country),
                        str(order.shipping_state),
                        str(order.shipping_city),
                        str(order.shipping_address),
                        str(order.shipping_zip),
                        str(order.shipping_phone),
                        str(order.shipping_mobile),
                        str(order.billing_country),
                        str(order.billing_state),
                        str(order.billing_city),
                        str(order.billing_address),
                        str(order.billing_zip),
                        str(order.billing_phone),
                        str(order.billing_mobile),
                    ]
                    writer.writerow(row)
                    #其余产品数据
                    orderitems = OrderItem.objects.filter(order_id=order_id).order_by('id').all()[1:]
                    for item in orderitems:
                        row = [
                            str(''),
                            str(''),
                            str(''),
                            str(''),
                            str(''),
                            str(''),
                            str(''),
                            str(''),
                            str(''),
                            str(''),
                            str(''),
                            str(''),
                            str(item.sku),
                            str(item.price),
                            str(item.quantity),
                            str(item.mark),
                            str(''),
                            str(''),
                            str(''),
                            str(''),
                            str(''),
                            str(''),
                            str(''),
                            str(''),
                            str(''),
                            str(''),
                            str(''),
                            str(''),
                            str(''),
                            str(''),
                        ]
                        writer.writerow(row)
                return response
            #PDF格式导出
            else:
                #所有订单
                data['orders'] = orders
                #币种符号
                currency_code = {}
                #用户信息
                customer_name = {}
                #地址
                shipping_address = {}
                billing_address = {}
                #期望发货时间页面展示（格式转化）
                expected_date = {}
                #产品信息
                products = {}
                #产品图片
                images = {}

                for order in orders:
                    #币种符号
                    currency = Currency.objects.filter(name=order.currency).first()
                    if currency:
                        currency_code[int(order.id)] = currency.code
                    else:
                        currency_code[int(order.id)] = '€'

                    #用户信息
                    customer = Customer.objects.filter(id=order.customer_id).first()
                    if customer:
                        fullname = customer.firstname + customer.lastname
                        customer_name[int(order.id)] = fullname
                    else:
                        customer_name[int(order.id)] = ''

                    #获取用户地址信息
                    s_address = customer.firstname +', '+ order.shipping_phone +', '+ order.shipping_mobile +' '+ order.shipping_address +' '+ order.shipping_city +', '+ order.shipping_zip +' '+ order.shipping_state +', '+ order.shipping_country

                    b_address =customer.firstname +', '+ order.billing_phone +', '+order.billing_mobile+' '+ order.billing_address +' '+ order.billing_city +', '+ order.billing_zip +' '+ order.billing_state +', '+ order.billing_country

                    shipping_address[int(order.id)] = s_address
                    billing_address[int(order.id)] = b_address

                    #期望发货时间页面展示（格式转化）
                    expcted_shipping = order.expcted_shipping
                    if expcted_shipping:
                        expected_date[int(order.id)] = str(expcted_shipping)[0:11]
                    else:
                        expected_date[int(order.id)] = ''

                    #产品信息
                    items = OrderItem.objects.filter(order_id=order.id).all()
                    if items:
                        products[int(order.id)] = items

                    #产品图片
                    for item in items:
                        product_id = item.product_id
                        pimage = ProductImage.objects.filter(product_id=product_id).order_by('id').first()
                        if pimage:
                            images[int(item.id)] = pimage.image
                        else:
                            images[int(item.id)] = ''

                data['currency_code'] = currency_code
                data['customer_name'] = customer_name
                data['shipping_address'] = shipping_address
                data['billing_address'] = billing_address
                data['expected_date'] = expected_date
                data['products'] = products
                data['images'] = images

                #订单状态
                status = {}
                status = {
                        0:'new',
                        1:'processing',
                        2:'artical shipped',
                        3:'shipped',
                        4:'cancel',
                    }
                data['status'] = status

                return render(request, 'export-order-pdf.html', data)
                
    return HttpResponse('1111')

#导出订单(弹窗形式导出，弃用)
@login_required
def export_orders1111(request):
    data = {}

    try:
        referer_url = request.META['HTTP_REFERER']
    except Exception as e:
        admin_url = str("http://") + request.META['HTTP_HOST'] +str("/admin/")
        print admin_url
        return redirect(admin_url)

    if request.user.is_superuser:
        customers = Customer.objects.all()
    else:
        current_group_set = ''
        if request.user.is_authenticated():
            current_user_set = request.user
            try:
                current_group_set = Group.objects.get(user=current_user_set)
            except Exception as e:
                current_group_set = ''
            
        if str(current_group_set) == 'Super manager':
            customers = Customer.objects.all()
        else:
            admin_id = request.user.id
            customers = Customer.objects.filter(admin_id=admin_id).all()

    # if not request.user.is_superuser:
    #     admin_id = request.user.id
    #     customers = Customer.objects.filter(admin_id=admin_id).all()
    # else:
    #     customers = Customer.objects.all()
    customer_ids = []
    for c in customers:
        customer_ids.append(c.id)
    customer_ids = tuple(customer_ids)

    if request.method == 'POST':
        if request.POST['type'] == 'export_orders':
            from_time = request.POST['from']
            to_time = request.POST['to']

            try:
                from_time = from_time + " 00:00:00"
                from_time = time_stamp2(from_time)
                to_time = to_time + " 23:59:59"
                to_time = time_stamp2(to_time)
            except Exception,e:
                messages.error(request,u'Please enter the correct time format !')
                return redirect(referer_url)

            status = int(request.POST['status'])

            if from_time and to_time:
                if status == 5:
                    orders = Order.objects.filter(created__gte=from_time,created__lt=to_time,customer_id__in=customer_ids).all().order_by('-id')
                else:
                    orders = Order.objects.filter(created__gte=from_time,created__lt=to_time,status=status,customer_id__in=customer_ids).all().order_by('-id')
            elif from_time:
                if status == 5:
                    orders = Order.objects.filter(created__gte=from_time,customer_id__in=customer_ids).all().order_by('-id')
                else:
                    orders = Order.objects.filter(created__gte=from_time,status=status,customer_id__in=customer_ids).all().order_by('-id')
            elif to_time:
                if status == 5:
                    orders = Order.objects.filter(created__lt=to_time,customer_id__in=customer_ids).all().order_by('-id')
                else:
                    orders = Order.objects.filter(created__lt=to_time,status=status,customer_id__in=customer_ids).all().order_by('-id')
            else:
                if status == 5:
                    orders = Order.objects.filter(customer_id__in=customer_ids).all().order_by('-id')
                else:
                    orders = Order.objects.filter(status=status,customer_id__in=customer_ids).all().order_by('-id')

            #导出格式
            export_format = int(request.POST['export_format'])
            #CSV格式导出
            if export_format == 0:
                response, writer = write_csv('export_orders')
                writer.writerow(['NO.','EPR NO.','Status','Stock-Mark','Amount','Currency','Created', 'Verified time','Shop keeper','Account number','Expcted shipping date','Comment','Ref.','Price','Quantity','Item-Mark'])

                for order in orders:
                    #订单状态
                    status = ''
                    if order.status == 0:
                        status = 'new'
                    elif order.status == 1:
                        status = 'processing'
                    elif order.status == 2:
                        status = 'partical shipped'
                    elif order.status == 3:
                        status = 'shipped'
                    elif order.status == 4:
                        status = 'cancel'

                    #期待发货时间
                    expcted_shipping = ''
                    if order.expcted_shipping and order.expcted_shipping != 'None':
                        try:
                            expcted_shipping = time_str2(order.expcted_shipping)
                        except Exception as e:
                            expcted_shipping = ''

                    #account_number
                    account_number = ''
                    if order.customer:
                        account_number = order.customer.account_number

                    #判断产品是否存在，存在的话取一个产品数据用作第一行导出
                    order_id = order.id
                    orderitem = OrderItem.objects.filter(order_id=order_id).order_by('id').first()
                    sku = ''
                    quantity = ''
                    price = ''
                    item_mark = ''
                    if orderitem and orderitem != 'None':
                        sku = orderitem.sku
                        quantity = orderitem.quantity
                        price = orderitem.price
                        item_mark = orderitem.mark
                    row = [
                        str(order.ordernum.encode('utf-8')),
                        str(order.erp_num.encode('utf-8')),
                        str(status),
                        str(order.mark),
                        str(order.amount),
                        str(order.currency),
                        str(order.created),
                        str(order.verifued),
                        str(order.customer),
                        str(account_number),
                        str(expcted_shipping),
                        # str(order.message.encode('utf-8')),
                        str(sku),
                        str(price),
                        str(quantity),
                        str(item_mark),
                    ]
                    writer.writerow(row)
                    #其余产品数据
                    orderitems = OrderItem.objects.filter(order_id=order_id).order_by('id').all()[1:]
                    for item in orderitems:
                        row = [
                            str(''),
                            str(''),
                            str(''),
                            str(''),
                            str(''),
                            str(''),
                            str(''),
                            str(''),
                            str(''),
                            str(''),
                            str(''),
                            # str(''),
                            str(item.sku),
                            str(item.price),
                            str(item.quantity),
                            str(item.mark),
                        ]
                        writer.writerow(row)
                return response
            #PDF格式导出
            else:
                #所有订单
                data['orders'] = orders
                #币种符号
                currency_code = {}
                #用户信息
                customer_name = {}
                #地址
                shipping_address = {}
                billing_address = {}
                #期望发货时间页面展示（格式转化）
                expected_date = {}
                #产品信息
                products = {}
                #产品图片
                images = {}

                for order in orders:
                    #币种符号
                    currency = Currency.objects.filter(name=order.currency).first()
                    if currency:
                        currency_code[int(order.id)] = currency.code
                    else:
                        currency_code[int(order.id)] = '€'

                    #用户信息
                    customer = Customer.objects.filter(id=order.customer_id).first()
                    if customer:
                        fullname = customer.firstname + customer.lastname
                        customer_name[int(order.id)] = fullname
                    else:
                        customer_name[int(order.id)] = ''

                    #获取用户地址信息
                    s_address = get_shipping_address(customer.id)
                    b_address = get_billing_address(customer.id)
                    shipping_address[int(order.id)] = s_address
                    billing_address[int(order.id)] = b_address

                    #期望发货时间页面展示（格式转化）
                    expcted_shipping = order.expcted_shipping
                    if expcted_shipping:
                        expected_date[int(order.id)] = str(expcted_shipping)[0:11]
                    else:
                        expected_date[int(order.id)] = ''

                    #产品信息
                    items = OrderItem.objects.filter(order_id=order.id).all()
                    if items:
                        products[int(order.id)] = items

                    #产品图片
                    for item in items:
                        product_id = item.product_id
                        pimage = ProductImage.objects.filter(product_id=product_id).order_by('id').first()
                        if pimage:
                            images[int(item.id)] = pimage.image
                        else:
                            images[int(item.id)] = ''

                data['currency_code'] = currency_code
                data['customer_name'] = customer_name
                data['shipping_address'] = shipping_address
                data['billing_address'] = billing_address
                data['expected_date'] = expected_date
                data['products'] = products
                data['images'] = images

                #订单状态
                status = {}
                status = {
                        0:'new',
                        1:'processing',
                        2:'artical shipped',
                        3:'shipped',
                        4:'cancel',
                    }
                data['status'] = status

                return render(request, 'export-order-pdf.html', data)
                
    return HttpResponse('1111')


def pdf_test(request):
    data = {}
    '''
    # Create the HttpResponse object with the appropriate PDF headers.
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = 'attachment; filename="somefilename.pdf"'

    buffer = BytesIO()

    # Create the PDF object, using the response object as its "file."
    p = canvas.Canvas(buffer)

    # Draw things on the PDF. Here's where the PDF generation happens.
    # See the ReportLab documentation for the full list of functionality.
    p.drawString(100,100,"Hello world.")

    # Close the PDF object cleanly, and we're done.
    p.showPage()
    p.save()

    pdf = buffer.getvalue()
    buffer.close()
    response.write(pdf)
    '''

    return render(request, "export-pdf-test.html", data)

    return response

def pdf_test2(request):
    username = 'lianglunzhong'  
    apikey = '3654a681292f4a6c490f6b11f0fde2cf'   
    try:  
        # create an API client instance  
        client = pdfcrowd.Client(username, apikey)  

        # convert a web page and store the generated PDF to a variable  
        pdf = client.convertURI("http://www.baidu.com")  
        # 或者根据Html或本地文件转换  
        # pdf = client.convertHtml('<head></head><body>My Page</body>')  
        # pdf = clent.convertFile('/var/www/xxx.html') # 必须是绝对路径  
        # set HTTP response headers  
        # response = HttpResponse(mimetype="application/pdf")  
        # 注意:新版本的django HttpResponse不支持mimetype,改成了content_type  
        response = HttpResponse(content_type="application/pdf")  
        response["Cache-Control"] = "max-age=0"   
        response["Accept-Ranges"] = "none"   
        response["Content-Disposition"] = "attachment; filename=xxx.pdf"   
        # send the generated PDF   
        response.write(pdf)   
    except pdfcrowd.Error, why:   
        response = HttpResponse(mimetype="text/plain")   
        response.write(why)   
    return response  

#订单详情页添加shipping_item删除操作
@login_required
def shipitem_delete(request,order_id,shipping_id):
    #删除后跳转到该订单详情页
    url = '/admin/orders/order/'+str(order_id)+'/change/'
    #删除shipping_item
    shippitem = ShippingItem.objects.filter(id=shipping_id).delete()
    if shippitem:
        messages.success(request,'Delete success !')
        return redirect(url)
    else:
        messages.error(request,'Delete false !')
        return redirect(url)


#订单详情页添加shipping_item的ajax操作  '''此方法已去除'''
@login_required
def shipitem_add_ajax(request):
    data = {}
    if request.method == 'POST':
        if request.POST['type'] == 'add_ship_product':
            sku = request.POST['sku']
            qty = request.POST['qty']
            package_id = request.POST['package_id']
            ship_item = ShippingItem.objects.create(package_id=package_id,sku=sku,quantity=qty)
            if ship_item:
                data['res'] = 'success'
                data = demjson.encode(data)
                return HttpResponse(data, content_type="application/json")

#订单详情页添加shipping_item产品时的save操作
@login_required
def shipitem_add_save(request,order_id,package_id,qty,sku):
    #添加产品后跳转到该订单详情页
    url = '/admin/orders/order/'+str(order_id)+'/change/'
    #判断sku是否正确
    product = Product.objects.filter(sku=sku).first()
    if not product:
        messages.error(request,'Please enter the correct sku and qty !')
        return redirect(url)

    name = product.name

    ship_item = ShippingItem.objects.create(package_id=package_id,sku=sku,quantity=qty,name=name)
    if ship_item:
        messages.success(request,'Add shipping product success !')
        return redirect(url)
    else:
        messages.error(request,'Add shipping product false !')
        return redirect(url)


#订单详情页更改产品价格保存操作
@login_required
def change_price_save(request,order_id,orderitem_id,product_id,price):
    #更新成功后跳转到该订单详情页
    url = '/admin/orders/order/'+str(order_id)+'/change/'
    orderitem = OrderItem.objects.filter(id=orderitem_id,product_id=product_id).update(price=price)
    if orderitem:
        messages.success(request,'Update price success !')
        return redirect(url)
    else:
        messages.error(request,'Update price false !')
        return redirect(url)


#前台添加产品到order list/从order list中删除产品或更改数量 ajax
def add_to_order_ajax(request):
    data = {}
    if request.method == 'POST':
        #产品页添加单个产品到order_list
        if request.POST['type'] == 'add_one_to_orderlist':
            product_id = int(request.POST['product_id'])
            product = Product.objects.filter(id=product_id).first()
            customer_id = int(request.POST['customer_id'])
            qty = int(request.POST['qty'])
            currency = currency_get(request)
            final_price = product.final_price(customer_id,currency)

            
            #用户所属库存组判断
            stock_group = get_stock_group(customer_id)
            #库存状态
            stock_type = product.get_stock_type(stock_group)

            #用于统计新增的数量
            number = 0
            #查看购物车是否已包含此产品
            cartitem , is_created = CartItem.objects.get_or_create(customer_id=customer_id,product_id=product_id)
            #不包含，新增，则插入数量
            if is_created:
                number += 1
                update = CartItem.objects.filter(customer_id=customer_id,product_id=product_id).update(quantity=qty,sku=product.sku,description=product.description,name=product.name,stock=stock_type,price=final_price,expected_time=product.expected_time)
            #已包含，则更新数量
            else:
                quantity = cartitem.quantity
                qty += quantity
                update = CartItem.objects.filter(customer_id=customer_id,product_id=product_id).update(quantity=qty,sku=product.sku,description=product.description,name=product.name,stock=stock_type,price=final_price,expected_time=product.expected_time)
            #成功添加到order_list,提示添加成功
            if update:
                data['result'] = 'success'
            else:
                data['result'] = 'false'

            data['number'] = number
            #根式转换
            data = demjson.encode(data)
            return HttpResponse(data, content_type='application/json')

        #产品页添加所有选中的产品到order_list
        if request.POST['type'] == 'add_all_to_orderlist':
            customer_id = int(request.POST['customer_id'])

            #获取产品数据
            products = request.POST['products']
            #转为为str
            products = products.encode("utf8")
            #转为为数组
            products = eval(products)

            #用户所属库存组判断
            stock_group = get_stock_group(customer_id)

            #用于统计新增的数量
            number = 0

            result = ''
            currency = currency_get(request)
            for k, v in products.items():
                product_id = int(k)
                product = Product.objects.filter(id=product_id).first()
                qty = int(v)
                final_price = product.final_price(customer_id,currency)

                #库存状态
                stock_type = product.get_stock_type(stock_group)

                #查看购物车是否已包含此产品
                cartitem , is_created = CartItem.objects.get_or_create(customer_id=customer_id,product_id=product_id)
                #不包含，新增，则插入数量
                if is_created:
                    number += 1
                    update = CartItem.objects.filter(customer_id=customer_id,product_id=product_id).update(quantity=qty,sku=product.sku,description=product.description,name=product.name,stock=stock_type,price=final_price,expected_time=product.expected_time)
                #已包含，则更新数量
                else:
                    quantity = cartitem.quantity
                    qty += quantity
                    update = CartItem.objects.filter(customer_id=customer_id,product_id=product_id).update(quantity=qty,sku=product.sku,description=product.description,name=product.name,stock=stock_type,price=final_price,expected_time=product.expected_time)

                if update:
                    continue
                else:
                    result = 'false'

            #成功添加到order_list,提示添加成功
            if result:
                data['result'] = 'false'
            else:
                data['result'] = 'success'

            data['number'] = number
            #根式转换
            data = demjson.encode(data)
            return HttpResponse(data, content_type='application/json')

        #order list页面删除单个产品
        if request.POST['type'] == 'delete_one_product':

            #需要删除的产品
            cartitem_id = request.POST['cartitem_id']

            #删除
            delete = CartItem.objects.filter(id=cartitem_id).delete()

            if delete:
                data['result'] = 'success'
            else:
                data['result'] = 'false'

            data = demjson.encode(data)
            return HttpResponse(data, content_type='application/json')

        #order list页面增加/减去产品数量
        if request.POST['type'] == 'order_list_plus':

            product_id = int(request.POST['product_id'])
            customer_id = int(request.POST['customer_id'])
            #获取的数量不能为0，js中已经判断
            qty = int(request.POST['num'])
            #更新对应的产品数量
            update = CartItem.objects.filter(customer_id=customer_id,product_id=product_id).update(quantity=qty)

            #成功添加到order_list,提示添加成功
            if update:
                data['result'] = 'success'
            else:
                data['result'] = 'false'

            #根式转换
            data = demjson.encode(data)
            return HttpResponse(data, content_type='application/json')

        #order list页面更改产品数量
        '''
        if request.POST['type'] == 'orderlist_change_product_qty':
            product_id = int(request.POST['product_id'])
            customer_id = int(request.POST['customer_id'])
            #获取的数量不能为0，js中已经判断
            qty = int(request.POST['qty'])
            #更新对应的产品数量
            update = CartItem.objects.filter(customer_id=customer_id,product_id=product_id).update(quantity=qty)

            #成功添加到order_list,提示添加成功
            if update:
                data['result'] = 'success'
            else:
                data['result'] = 'false'

            #根式转换
            data = demjson.encode(data)
            return HttpResponse(data, content_type='application/json')
        '''

        #order list页面删除勾选的产品
        if request.POST['type'] == 'delete_from_list':
            #获取所选的cartitem id
            cartitems = request.POST['cartitems']
            #字符串格式转换
            cartitems = cartitems.encode("utf8")
            #转化为数组
            cartitems = eval(cartitems)
            #转化为元组
            cartitems = tuple(cartitems)
            #删除
            delete = CartItem.objects.filter(id__in=cartitems).delete()

            if delete:
                data['result'] = 'success'
            else:
                data['result'] = 'false'

            data = demjson.encode(data)
            return HttpResponse(data, content_type='application/json')

        #order detail页面确认生成订单
        if request.POST['type'] == 'place_order':
            #用户id
            customer_id = request.POST['customer_id']

            customer = Customer.objects.filter(id=customer_id).first()
            accountnumber = customer.account_number

            address_id = request.POST['address_id']

            #用户所属库存组判断
            stock_group = get_stock_group(customer_id)

            #期望发货时间
            expcted_shipping = request.POST['expcted_shipping']
            #用户备注
            message = request.POST['message']
            #获取cartitem
            cartitem_ids = request.POST['cartitem_ids']
            #字符串格式转换
            cartitem_ids = cartitem_ids.encode("utf8")
            #转化为数组
            cartitem_ids = cartitem_ids.split(',')
            #转化为元组
            cartitem_ids = tuple(cartitem_ids)
            #获取cartitem中被选中的产品
            cartitem = CartItem.objects.filter(customer_id=customer_id,id__in=cartitem_ids).all()

            #订单总额
            amount = 0.0
            for c in cartitem:
                amount += float(c.price) * c.quantity
            amount = round(amount,2)

            #获取用户地址
            address = Address.objects.filter(id=address_id).first()
            if address:
                shipping_country = address.shipping_country
                shipping_state = address.shipping_state
                shipping_city = address.shipping_city
                shipping_address = address.shipping_address
                shipping_zip = address.shipping_zip
                shipping_phone = address.shipping_phone
                shipping_mobile = address.shipping_mobile
            else:
                shipping_country = ''
                shipping_state = ''
                shipping_city = ''
                shipping_address = ''
                shipping_zip = ''
                shipping_phone = ''
                shipping_mobile = ''

            baddress = ''
            billing_country = ''
            billing_state = ''
            billing_city = ''
            billing_address = ''
            billing_zip = ''
            billing_phone = ''
            billing_mobile = ''

            billingaddress = BillingAddress.objects.filter(customer_id=customer_id).first()
            if billingaddress:
                baddress = billingaddress

                billing_country = baddress.billing_country
                billing_state = baddress.billing_state
                billing_city = baddress.billing_city
                billing_address = baddress.billing_address
                billing_zip = baddress.billing_zip
                billing_phone = baddress.billing_phone
                billing_mobile = baddress.billing_mobile
            else:
                billingaddress = Address.objects.filter(customer_id=customer_id,default=1).first()
                if billingaddress:
                    baddress = billingaddress

                    billing_country = baddress.shipping_country
                    billing_state = baddress.shipping_state
                    billing_city = baddress.shipping_city
                    billing_address = baddress.shipping_address
                    billing_zip = baddress.shipping_zip
                    billing_phone = baddress.shipping_phone
                    billing_mobile = baddress.shipping_mobile
                else:
                    billingaddress = Address.objects.filter(customer_id=customer_id).first()
                    if billingaddress:
                        baddress = billingaddress

                        billing_country = baddress.shipping_country
                        billing_state = baddress.shipping_state
                        billing_city = baddress.shipping_city
                        billing_address = baddress.shipping_address
                        billing_zip = baddress.shipping_zip
                        billing_phone = baddress.shipping_phone
                        billing_mobile = baddress.shipping_mobile

            #当前货币
            currency = currency_get(request)
            #生成订单,因为订单的created字段，所以每次新增的时候一定不会重复
            order = Order.objects.create(
                    ordernum = '',
                    erp_num = '',
                    customer_id = customer_id,
                    accountnumber = accountnumber,
                    status = 0,
                    address_id = address_id,
                    message = message,
                    imgorder = '',
                    amount = amount,
                    currency = currency,
                    shipping_country = shipping_country,
                    shipping_state = shipping_state,
                    shipping_city = shipping_city,
                    shipping_address = shipping_address,
                    shipping_zip = shipping_zip,
                    shipping_phone = shipping_phone,
                    shipping_mobile = shipping_mobile,
                    billing_country = billing_country,
                    billing_state = billing_state,
                    billing_city = billing_city,
                    billing_address = billing_address,
                    billing_zip = billing_zip,
                    billing_phone = billing_phone,
                    billing_mobile = billing_mobile,
                )
            #订单更新成功，
            if order:
                #更新订单号：日期+order id
                now = int(time.time())
                now_str = time_str(now)
                order_id = str(order.id)
                if len(order_id) < 6:
                    num = 6 - len(order_id)
                    i = 1
                    p = '0'
                    while i < num:
                        p += '0'
                        i += 1
                    ordernum = str('R')+str(now_str)+str(p)+str(order.id)+'ive'
                else:
                    ordernum = str('R')+str(now_str)+str(order.id)+'ive'

                #更新期望发货日期
                if expcted_shipping:
                    try:
                        expcted_date = time_stamp(expcted_shipping)
                    except Exception as e:
                        expcted_date = ''
                else:
                    expcted_date = ''

                # if expcted_date:
                #   order_update = Order.objects.filter(id=order.id).update(ordernum=ordernum,expcted_shipping=expcted_date)
                # else:
                #   order_update = Order.objects.filter(id=order.id).update(ordernum=ordernum)
                if expcted_date:
                    sql = "UPDATE orders_order SET ordernum='"+str(ordernum)+"', expcted_shipping='"+str(expcted_date)+"'  WHERE id='"+str(order.id)+"'"
                else:
                    sql = "UPDATE orders_order SET ordernum='"+str(ordernum)+"' WHERE id='"+str(order.id)+"'"

                cursor = connection.cursor()
                cursor.execute(sql)

                order_mark = []
                #添加相应的信息的order_item表
                for c in cartitem:
                    #库存数量标记
                    product = Product.objects.filter(id=c.product_id).first()
                    mark = product.get_product_mark(stock_group,c.quantity)

                    if mark not in order_mark:
                        order_mark.append(mark)

                    orderitem = OrderItem.objects.create(
                            order_id=order.id,
                            product_id=c.product_id,
                            name = c.name,
                            sku = c.sku,
                            price = c.price,
                            quantity = c.quantity,
                            mark = mark
                        )

                if len(order_mark) > 0:
                    if len(order_mark) == 1:
                        order_update = Order.objects.filter(id=order.id).update(mark=order_mark[0])
                    else:
                        order_update = Order.objects.filter(id=order.id).update(mark='A')

                #删除cartitem中对应的产品
                cartitem = CartItem.objects.filter(customer_id=customer_id,id__in=cartitem_ids).delete()

                #给用户发送邮件
                customer = Customer.objects.filter(id=customer_id).first()
                email = {}
                email['receiver'] = [customer.email ]
                template = 'email_new_order.html'
                sendData = {}
                sendData['title'] = 'RIVE – B2B UPDATE'
                # sendEmail(email,template,sendData)
                thread.start_new_thread(sendEmail, (email,template,sendData))

                # 给管理员发邮件
                userEmails = settings.USEREMIAL

                for key in userEmails:
                    email = {}
                    email['receiver'] = [userEmails[key]]
                    template = 'email_new_order_user.html'
                    sendData = {}
                    sendData['title'] = 'RIVE – B2B ORDER'
                    sendData['salesman_name'] = key
                    sendData['rive_account_number'] = customer.account_number
                    sendData['firstname'] = customer.firstname
                    sendData['order_number'] = order.ordernum
                    # sendEmail(email, template, sendData)
                    thread.start_new_thread(sendEmail, (email,template,sendData))


                data['result'] = 'success'
                data = demjson.encode(data)
                return HttpResponse(data, content_type='application/json')

        #order detail 图片 生成订单
        if request.POST['type'] == 'place_pic_order':
            #用户id
            customer_id = request.POST['customer_id']

            customer = Customer.objects.filter(id=customer_id).first()
            accountnumber = customer.account_number

            address_id = request.POST['address_id']
            
            #期望发货时间
            expcted_shipping = request.POST['expcted_shipping']
            #用户备注
            message = request.POST['message']
            #图片
            image_name = request.POST['image_name']

            #获取用户地址
            address = Address.objects.filter(id=address_id).first()
            if address:
                shipping_country = address.shipping_country
                shipping_state = address.shipping_state
                shipping_city = address.shipping_city
                shipping_address = address.shipping_address
                shipping_zip = address.shipping_zip
                shipping_phone = address.shipping_phone
                shipping_mobile = address.shipping_mobile
            else:
                shipping_country = ''
                shipping_state = ''
                shipping_city = ''
                shipping_address = ''
                shipping_zip = ''
                shipping_phone = ''
                shipping_mobile = ''

            
            baddress = ''

            billing_country = ''
            billing_state = ''
            billing_city = ''
            billing_address = ''
            billing_zip = ''
            billing_phone = ''
            billing_mobile = ''

            billingaddress = BillingAddress.objects.filter(customer_id=customer_id).first()
            if billingaddress:
                baddress = billingaddress

                billing_country = baddress.billing_country
                billing_state = baddress.billing_state
                billing_city = baddress.billing_city
                billing_address = baddress.billing_address
                billing_zip = baddress.billing_zip
                billing_phone = baddress.billing_phone
                billing_mobile = baddress.billing_mobile
            else:
                billingaddress = Address.objects.filter(customer_id=customer_id,default=1).first()
                if billingaddress:
                    baddress = billingaddress

                    billing_country = baddress.shipping_country
                    billing_state = baddress.shipping_state
                    billing_city = baddress.shipping_city
                    billing_address = baddress.shipping_address
                    billing_zip = baddress.shipping_zip
                    billing_phone = baddress.shipping_phone
                    billing_mobile = baddress.shipping_mobile
                else:
                    billingaddress = Address.objects.filter(customer_id=customer_id).first()
                    if billingaddress:
                        baddress = billingaddress

                        billing_country = baddress.shipping_country
                        billing_state = baddress.shipping_state
                        billing_city = baddress.shipping_city
                        billing_address = baddress.shipping_address
                        billing_zip = baddress.shipping_zip
                        billing_phone = baddress.shipping_phone
                        billing_mobile = baddress.shipping_mobile

            #生成订单,因为订单的created字段，所以每次新增的时候一定不会重复
            order = Order.objects.create(
                    ordernum = '',
                    erp_num = '',
                    customer_id = customer_id,
                    accountnumber = accountnumber,
                    status = 0,
                    address_id = address_id,
                    message = message,
                    imgorder = image_name,
                    amount = 0.0,
                    currency = 'EUR',
                    shipping_country = shipping_country,
                    shipping_state = shipping_state,
                    shipping_city = shipping_city,
                    shipping_address = shipping_address,
                    shipping_zip = shipping_zip,
                    shipping_phone = shipping_phone,
                    shipping_mobile = shipping_mobile,
                    billing_country = billing_country,
                    billing_state = billing_state,
                    billing_city = billing_city,
                    billing_address = billing_address,
                    billing_zip = billing_zip,
                    billing_phone = billing_phone,
                    billing_mobile = billing_mobile,
                )
            #订单更新成功，
            if order:
                #更新订单号：日期+order id
                now = int(time.time())
                now_str = time_str(now)
                order_id = str(order.id)
                if len(order_id) < 6:
                    num = 6 - len(order_id)
                    i = 1
                    p = '0'
                    while i < num:
                        p += '0'
                        i += 1
                    ordernum = str('R')+str(now_str)+str(p)+str(order.id)+'ive'
                else:
                    ordernum = str('R')+str(now_str)+str(order.id)+'ive'

                #更新期望发货日期
                if expcted_shipping:
                    expcted_date = time_stamp(expcted_shipping)
                else:
                    expcted_date = ''

                # if expcted_date:
                #   order_update = Order.objects.filter(id=order.id).update(ordernum=ordernum,expcted_shipping=expcted_date)
                # else:
                #   order_update = Order.objects.filter(id=order.id).update(ordernum=ordernum)

                if expcted_date:
                    sql = "UPDATE orders_order SET ordernum='"+str(ordernum)+"',expcted_shipping='"+str(expcted_date)+"' WHERE id='"+str(order.id)+"'"
                else:
                    sql = "UPDATE orders_order SET ordernum='"+str(ordernum)+"' WHERE id='"+str(order.id)+"'"

                cursor = connection.cursor()
                order_update = cursor.execute(sql)


                if order_update:

                    # 发送邮件
                    customer = Customer.objects.filter(id=customer_id).first()
                    email = {}
                    email['receiver'] = [customer.email]
                    template = 'email_new_order.html'
                    sendData = {}
                    sendData['title'] = 'RIVE – B2B UPDATE'
                    # sendEmail(email, template, sendData)
                    thread.start_new_thread(sendEmail, (email,template,sendData))

                    # 给管理员发邮件
                    userEmails = settings.USEREMIAL

                    for key in userEmails:
                        email = {}
                        email['receiver'] = [userEmails[key]]
                        template = 'email_new_order_user.html'
                        sendData = {}
                        sendData['title'] = 'RIVE – B2B ORDER'
                        sendData['salesman_name'] = key
                        sendData['rive_account_number'] = customer.account_number
                        sendData['firstname'] = customer.firstname
                        sendData['order_number'] = order.ordernum
                        # sendEmail(email, template, sendData)
                        thread.start_new_thread(sendEmail, (email,template,sendData))
                    data['result'] = 'success'
                else:
                    data['result'] = 'error'

                data = demjson.encode(data)
                return HttpResponse(data, content_type='application/json')


        #order history页面查看包裹详情ajax
        if request.POST['type'] == 'package_detail':

            package_id = request.POST['package_id']

            #tracking number comment
            package = Package.objects.filter(id=package_id).first()
            tracking_num = package.tracking_number
            tracking_note = package.note
            data['tracking_num'] = tracking_num
            data['tracking_note'] = tracking_note

            tracking_method = package.shipping.ship_company
            tracking_link = package.shipping.tracking_link

            data['tracking_method'] = tracking_method
            data['tracking_link'] = tracking_link

            #查询该包裹发货的产品，即orders_shippingitem表
            shippingitems = ShippingItem.objects.filter(package_id=package_id).all()
            #把obj的值转为为字典形式，在用json传递
            products = {}
            for s in shippingitems:
                products[str(s.id)] = {'name':s.name,'sku':s.sku,'qty':int(s.quantity)}

            data['products'] = products

            data = demjson.encode(data)
            return HttpResponse(data, content_type='application/json')

        #产品页点击图片预览 ajax
        if request.POST['type'] == 'product_image_view':
            lang = getCookie(request)

            product_id = request.POST['product_id']
            customer_id = request.POST['customer_id']
            #查询产品图片
            productimages = ProductImage.objects.filter(product_id=product_id).order_by('id').all()
            #把图片的值保存到数组，然后返回json格式
            images = []
            images_info = ''
            image_count = productimages.count()

            code = get_currency_code(request)
            currency = currency_get(request)
            
            if image_count:
                uwidth = str(100*image_count)+str('%')
                lwidth = str(100/image_count)+str('%')
            else:
                uwidth = str('100%')
                lwidth = str('100%')

            images_info += '<ul class="slides clearfix" style="position: relative;width:'+uwidth+';">'

            onerror="this.src='/static/assets/images/no_picture.png'"

            for pi in productimages:
                price = pi.product.final_price(customer_id, currency)
                if lang == 'fr':
                    description = pi.product.description_fr
                    if not description:
                        description = pi.product.description
                    images_info += '<li style="width:'+lwidth+';float:left;"><img class="responsive" src="/site_media/'+str(pi.image)+'" onerror="'+onerror+'"><div class="m-info"><div class="row"><div class="col-xs-6">Ref.: <span>'+str(pi.product.sku)+'</span></div><div class="col-xs-6">Prix:<span>'+str(price)+str(code)+'</span></div><div class="col-xs-12">Nom du produits:<span>'+str(pi.product.name)+'</span></div><div class="col-xs-12">Détails:<span>'+str(description)+'</span></div></div></div></li>'
                elif lang == 'de':
                    description = pi.product.description_de
                    if not description:
                        description = pi.product.description
                    images_info += '<li style="width:'+lwidth+';float:left;"><img class="responsive" src="/site_media/'+str(pi.image)+'" onerror="'+onerror+'"><div class="m-info"><div class="row"><div class="col-xs-6">Ref.: <span>'+str(pi.product.sku)+'</span></div><div class="col-xs-6">Preis:<span>'+str(price)+str(code)+'</span></div><div class="col-xs-12">Produktname:<span>'+str(pi.product.name)+'</span></div><div class="col-xs-12">Details:<span>'+str(description)+'</span></div></div></div></li>'
                elif lang == 'nl':
                    description = pi.product.description_nl
                    if not description:
                        description = pi.product.description
                    images_info += '<li style="width:'+lwidth+';float:left;"><img class="responsive" src="/site_media/'+str(pi.image)+'" onerror="'+onerror+'"><div class="m-info"><div class="row"><div class="col-xs-6">Ref.: <span>'+str(pi.product.sku)+'</span></div><div class="col-xs-6">Price:<span>'+str(price)+str(code)+'</span></div><div class="col-xs-12">Product Name:<span>'+str(pi.product.name)+'</span></div><div class="col-xs-12">Details:<span>'+str(description)+'</span></div></div></div></li>'
                else:
                    description = pi.product.description
                    images_info += '<li style="width:'+lwidth+';float:left;"><img class="responsive" src="/site_media/'+str(pi.image)+'" onerror="'+onerror+'"><div class="m-info"><div class="row"><div class="col-xs-6">Ref.: <span>'+str(pi.product.sku)+'</span></div><div class="col-xs-6">Price:<span>'+str(price)+str(code)+'</span></div><div class="col-xs-12">Product Name:<span>'+str(pi.product.name)+'</span></div><div class="col-xs-12">Details:<span>'+str(description)+'</span></div></div></div></li>'
                images.append(str(pi.image))

            images_info += '</ul>'

            #单张图片不显示左右切换按钮
            images_count = productimages.count()

            data['images'] = images
            
            data['images_count'] = images_count

            data['images_info'] = images_info.decode('utf-8')

            data = demjson.encode(data)
            return HttpResponse(data, content_type="application/json")

    return HttpResponse(1111)


#前台订单列表页order list
def order_list(request):
    data = {}

    lang = getCookie(request)
    data['lang'] = lang

    has_promotion = get_promotion(request)
    data['has_promotion'] = has_promotion

    lang = getCookie(request)

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

    #用户所属库存组判断
    stock_group = get_stock_group(customer.id)
    #前台显示时间：当前时间+14天
    est_date = get_est_date()
    
    data['est_date'] = est_date
    data['customer'] = customer

    #查询当前用户购物车产品
    cartitems = CartItem.objects.filter(customer_id=customer.id).all().order_by('-id')
    #获取当前选择的货币，用于计算产品最终价格
    currency = currency_get(request)
    #去除购物车产品中不可见的产品/以及更新购物车产品参数
    for citem in cartitems:
        pro = Product.objects.filter(id=citem.product_id).first()
        if pro:
            #该产品已经不可见，删除购物车中该产品
            if pro.visibility == 0:
                citem.delete()
            #更新产品价格，库存，到货时间等
            final_price = pro.final_price(customer_id,currency)
            #产品库存状态
            stock_type = pro.get_stock_type(stock_group)
            #产品描述翻译
            description = ''
            if lang == 'fr':
                description = pro.description_fr
            elif lang == 'de':
                description = pro.description_de
            elif lang == 'nl':
                description = pro.description_nl
            else:
                description = pro.description

            if description == '':
                description = pro.description

            query_update = CartItem.objects.filter(id=citem.id).update(sku=pro.sku,description=description,name=pro.name,stock=stock_type,price=final_price,expected_time=pro.expected_time)

    #前台价格不同货币对应的符号展示
    data['code'] = get_currency_code(request)
    #前台展示时判断当前选择的货币
    data['current_currency'] = currency

                
    #重新获取用户当前购物车产品数据
    cartitems = CartItem.objects.filter(customer_id=customer.id).all().order_by('-id')


    #产品图片图片，默认展示第一张
    images = {}
    #库存限制的产品id,用于用户选择生成订单时候判断
    stock_id = []
    #用于页面展示时判断产品描述字符数
    product_ids = []
    # 合计金额
    total_amount = 0
    #产品到货时间格式转化
    expected_times = {}

    for c in cartitems:

        #产品到货时间格式转化
        expected_time = c.expected_time
        if expected_time:
            expected_time = time_stamp2(expected_time)
            expected_time = time_str2(expected_time)
            expected_times[int(c.id)] = expected_time

        product_ids.append(str(c.product_id))
        image = ProductImage.objects.filter(product_id=c.product_id).order_by('id').first()
        total_amount += c.price * c.quantity
        if image:
            images[int(c.product_id)] = image.image
        else:
            images[int(c.product_id)] = ''
        if c.stock == 0:
            stock_id.append(str(c.id))

    stock_id = ','.join(stock_id)

    product_ids = ','.join(product_ids)

    data['expected_times'] = expected_times
    data['number'] = cartitems.count()
    data['total_amount'] = total_amount
    data['stock_id'] = stock_id
    data['product_ids'] = product_ids
    data['cartitems'] = cartitems
    data['images'] = images

    #导航栏激活样式
    data['nav_products'] = ''
    data['nav_order_list'] = 'active'
    data['nav_order_history'] = ''
    data['nav_promotion'] = ''

    #前台币种选择
    currencies = Currency.objects.all()
    data['currencies'] = currencies
    
    return render(request, 'order-list.html', data)

#前台order list页删除库存限制产品
def delete_out_of_stock(request):
    data = {}
    #判断是否登陆，并把参数传递到模板页
    # customer = is_login(request)
    customer_id = request.session.get('customer_id', False)
    if not customer_id:
        return redirect('login')
    else:
        customer = Customer.objects.filter(id=customer_id).first()

    data['customer'] = customer

    #删除当前用户购物车有库存限制的产品
    delete = CartItem.objects.filter(customer_id=customer.id,stock=0).delete()

    #跳转到order_list页面
    return redirect('order_list')

#前台order_history页面
def order_history(request,page_id='1'):
    data = {}

    lang = getCookie(request)
    data['lang'] = lang 

    has_promotion = get_promotion(request)
    data['has_promotion'] = has_promotion

    page_id = ''

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

    #查询当前用户购物车产品
    data['number'] = order_list_count(request,customer.id)

    #通过url获取page_id
    current_url = request.get_full_path()
    current_url = current_url.strip().split('/')
    print current_url
    page = current_url[2]
    if page and page.startswith('page_'):
        page_id = int(page.strip('page_'))

    '''用户订单查询'''
    #分页订单数据
    if page_id and page_id > 1:
        order_start = (page_id - 1) * 10
        order_end = order_start + 10
        orders = Order.objects.filter(customer_id=customer.id).order_by('-id')[order_start:order_end]
    #正常打开页面或者点击第一页订单数据
    else:
        orders = Order.objects.filter(customer_id=customer.id).order_by('-id')[0:10]

    #当前页订单数
    current_orders = orders.count()
    data['current_orders'] =current_orders

    #订单状态
    status = {}
    status = {
            0:'new',
            1:'shipping',
            2:'verify',
        }

    #订单id
    order_id = []
    #订单id,用于前台coment字符长度判断
    order_ids = []
    #通过订单结算时的币种分别获取币种符号
    currency_codes = {}
    #期望发货时间前台展示格式转化
    except_date = {}
    #用户地址
    saddresses = {}
    baddresses = {}
    #订单新增时间和确认时间
    order_create = {}
    order_verify = {}

    for order in orders:
        order_id.append(int(order.id))
        order_ids.append(str(order.id))
        currency = Currency.objects.filter(name=order.currency).first()
        if currency:
            currency_codes[int(order.id)] = currency.code
        else:
            currency_codes[int(order.id)] = '€'
        if order.expcted_shipping:
            expcted_shipping = str(order.expcted_shipping)[0:11]
            except_date[int(order.id)] = expcted_shipping

        saddresses[int(order.id)] = customer.firstname +', '+ order.shipping_phone +', '+ order.shipping_mobile +' '+ order.shipping_address +' '+ order.shipping_city +', '+ order.shipping_zip +' '+ order.shipping_state +', '+ order.shipping_country

        baddresses[int(order.id)] =customer.firstname +', '+ order.billing_phone +', '+order.billing_mobile+' '+ order.billing_address +' '+ order.billing_city +', '+ order.billing_zip +' '+ order.billing_state +', '+ order.billing_country

        if order.created:
            try:
                created = time_stamp2(order.created)
                created = time_str2(created)
                order_create[int(order.id)] = created
            except Exception as e:
                order_create[int(order.id)] = ''
        else:
            order_create[int(order.id)] = ''

        if order.verifued:
            try:
                verify = time_stamp2(order.verifued)
                verify = time_str2(verify)
                order_verify[int(order.id)] = verify
            except Exception as e:
                order_verify[int(order.id)] = ''
        else:
            order_verify[int(order.id)] = ''



    data['saddresses'] = saddresses
    data['baddresses'] = baddresses
    
    data['order_create'] = order_create
    data['order_verify'] = order_verify

    data['except_date'] = except_date

    print currency_codes
    data['currency_codes'] = currency_codes

    order_id = tuple(order_id)

    order_ids = ','.join(order_ids)

    #订单产品
    orderitems = OrderItem.objects.filter(order_id__in=order_id).all()

    #产品图片
    images = {}
    for orderitem in orderitems:
        product_id = orderitem.product_id
        pimage = ProductImage.objects.filter(product_id=product_id).order_by('id').first()
        if pimage:
            images[int(orderitem.id)] = pimage.image
        else:
            images[int(orderitem.id)] = ''

    #订单发货信息
    packages = Package.objects.filter(order_id__in=order_id).all()

    data['status'] = status
    data['orderitems'] = orderitems
    data['packages'] = packages
    data['orders'] = orders
    data['images'] = images
    data['order_ids'] = order_ids

    '''分页数据展示'''
    #订单总数
    order_total = orders = Order.objects.filter(customer_id=customer.id).all().count()
    data['order_total'] = order_total

    #当前分页数
    if page_id and page_id >= 1:
            data['page_id'] = page_id
    else:
        data['page_id'] = 1

    #导航栏激活样式
    data['nav_products'] = ''
    data['nav_order_list'] = ''
    data['nav_order_history'] = 'active'
    data['nav_promotion'] = ''

    #当前页订单数显示
    if page_id and page_id >= 1:
            start_order = (int(page_id) - 1) * 10 + 1
            end_order = start_order + current_orders - 1
    else:
        page_id = 1
        if current_orders:
            start_order = (int(page_id) - 1) * 10 + 1
        else:
            start_order = 0
        end_order = start_order + current_orders - 1

    data['start_order'] = start_order
    data['end_order'] = end_order

    return render(request, 'order-history.html', data)

#前台order_detail页面
def order_detail(request):
    data = {}

    has_promotion = get_promotion(request)
    data['has_promotion'] = has_promotion

    #判断是否登录
    customer_id = request.session.get('customer_id', False)
    if not customer_id:
        return redirect('login')
    else:
        #判断用户是否被锁定
        customer = Customer.objects.filter(id=customer_id).first()
        if customer.locked:
            try:
                del request.session['customer_id']
            except KeyError:
                pass
            return redirect('login')

    if request.POST.get('type') == 'order_detail':
        customerid = request.POST.get('customerid')
        cartitemid = request.POST.get('cartitemid')
        #字符串格式转换
        cartitemid = cartitemid.encode("utf8")
        #转化为数组
        cartitemid = eval(cartitemid)
        cartitem_id = []
        for c in cartitemid:
            cartitem_id.append(int(c))
        #转化为元组,用于查询cartitem产品
        cartitem_id = tuple(cartitem_id)

        customer = Customer.objects.filter(id=customerid).first()
        data['customer'] = customer

        #前台显示时间：当前时间+14天
        est_date = get_est_date()
        
        data['est_date'] = est_date

        #获取用户地址信息

        shipping_addresses = {}
        default_address = {}
        addresses = Address.objects.filter(customer_id=customer.id).all()
        for address in addresses:
            default_address[int(address.id)] = address.default
            shipping_addresses[int(address.id)] = customer.firstname +', '+ address.shipping_phone +', '+ address.shipping_mobile +' '+ address.shipping_address +' '+ address.shipping_city +', '+ address.shipping_zip +' '+ address.shipping_state +', '+ address.shipping_country

        data['shipping_addresses'] = shipping_addresses
        data['default_address'] = default_address

        billing_address = ''

        baddress = BillingAddress.objects.filter(customer_id=customer.id).first()
        if baddress:
            billing_address = customer.firstname +', '+ baddress.billing_phone +', '+baddress.billing_mobile+' '+ baddress.billing_address +' '+ baddress.billing_city +', '+ baddress.billing_zip +' '+ baddress.billing_state +', '+ baddress.billing_country
        else:
            baddress = Address.objects.filter(customer_id=customer.id,default=1).first()
            if baddress:
                billing_address = customer.firstname +', '+ baddress.shipping_phone +', '+ baddress.shipping_mobile +' '+ baddress.shipping_address +' '+ baddress.shipping_city +', '+ baddress.shipping_zip +' '+ baddress.shipping_state +', '+ baddress.shipping_country
            else:
                baddress = Address.objects.filter(customer_id=customer.id).first()
                if baddress:
                    billing_address = customer.firstname +', '+ baddress.shipping_phone +', '+ baddress.shipping_mobile +' '+ baddress.shipping_address +' '+ baddress.shipping_city +', '+ baddress.shipping_zip +' '+ baddress.shipping_state +', '+ baddress.shipping_country

        data['billing_address'] = billing_address


        #获取cartitem已经选择的产品
        cartitems = CartItem.objects.filter(customer_id=customer.id,id__in=cartitem_id).all()
        data['cartitems'] = cartitems

        #判断选择的产品中是否有库存限制的产品
        stock_limit = ''
        #订单总额
        amount = 0.0
        #获取cartitem已经选择的产品id,用于生成订单时的产品数据
        cartitem_ids = []
        #获取产品图片
        images = {}
        for c in cartitems:
            stock = c.stock
            if stock == 0:
                stock_limit = 1
                
            amount += float(c.price) * c.quantity
            cartitem_ids.append(str(c.id))

            product_id = c.product_id
            pimage = ProductImage.objects.filter(product_id=product_id).order_by('id').first()
            if pimage:
                images[int(c.id)] = pimage.image
            else:
                images[int(c.id)] = ''

        cartitem_ids = ','.join(cartitem_ids)
        amount = round(amount,2)

        data['amount'] = amount
        data['images'] = images
        data['cartitem_ids'] = cartitem_ids
        data['stock_limit'] = stock_limit

        #查询当前用户购物车产品
        data['number'] = order_list_count(request,customer.id)

        #order-detail不显示底部的切换语言及货币
        data['hidden_footer'] = 1
        #前台产品价格后面的货币符号展示
        data['code'] = get_currency_code(request)

        return render(request, 'order-detail.html', data)
    else:
        return redirect('products')

#测试
def order_test(request):
    data = {}
    if request.POST.get('type') == 'order_test':
        print 'order_test'
        customerid = request.POST.get('customerid')
        cartitemid = request.POST.get('cartitemid')
        #字符串格式转换
        cartitemid = cartitemid.encode("utf8")
        #转化为数组
        cartitemid = eval(cartitemid)
        #转化为元组
        cartitemid = tuple(cartitemid)
        print customerid
        print cartitemid
    return HttpResponse('2222')

#上传图片生成订单
def upload_pic_order(request):
    data = {}

    has_promotion = get_promotion(request)
    data['has_promotion'] = has_promotion

    #判断是否登陆，并把参数传递到模板页
    # customer = is_login(request)
    customer_id = request.session.get('customer_id', False)
    if not customer_id:
        return redirect('login')
    else:
        customer = Customer.objects.filter(id=customer_id).first()

    #上传图片生成订单
    if request.POST:
        if request.POST['type'] == 'upload_pic_order':

            #获取图片
            file_obj = request.FILES.get('upload_image',None)

            if file_obj == None:
                return redirect('products')

            '''把图片保存到服务器'''
            #获取文件名称
            file_name = file_obj.name
            #更改文件名称，防止有重复的文件名
            fn, ext = os.path.splitext(file_name)
            if not ext:
                ext = '.jpg'
            now = int(time.time())
            fn = str(now)

            file_name = fn + ext

            #定义文件保存路径及名称
            file_full_path = os.path.join(settings.UPLOAD_PIC, file_name)
            #以读写的方式打开该文件
            dest = open(file_full_path, 'wb+')
            #写入内容，file_obj.read()方法获取上次的文件内容  
            result = dest.write(file_obj.read())
            dest.close()

            '''跳转到order-detail页面'''
            data['upload_pic_order'] = "upload_pic/" + file_name

            data['customer'] = customer

            #获取用户地址信息
            shipping_addresses = {}
            default_address = {}
            addresses = Address.objects.filter(customer_id=customer.id).all()
            for address in addresses:
                default_address[int(address.id)] = address.default
                shipping_addresses[int(address.id)] = customer.firstname +', '+ address.shipping_phone +', '+ address.shipping_mobile +' '+ address.shipping_address +' '+ address.shipping_city +', '+ address.shipping_zip +' '+ address.shipping_state +', '+ address.shipping_country

            data['shipping_addresses'] = shipping_addresses
            data['default_address'] = default_address

            billing_address = ''

            baddress = BillingAddress.objects.filter(customer_id=customer.id).first()
            if baddress:
                billing_address = customer.firstname +', '+ baddress.billing_phone +', '+baddress.billing_mobile+' '+ baddress.billing_address +' '+ baddress.billing_city +', '+ baddress.billing_zip +' '+ baddress.billing_state +', '+ baddress.billing_country
            else:
                baddress = Address.objects.filter(customer_id=customer.id,default=1).first()
                if baddress:
                    billing_address = customer.firstname +', '+ baddress.shipping_phone +', '+ baddress.shipping_mobile +' '+ baddress.shipping_address +' '+ baddress.shipping_city +', '+ baddress.shipping_zip +' '+ baddress.shipping_state +', '+ baddress.shipping_country
                else:
                    baddress = Address.objects.filter(customer_id=customer.id).first()
                    if baddress:
                        billing_address = customer.firstname +', '+ baddress.shipping_phone +', '+ baddress.shipping_mobile +' '+ baddress.shipping_address +' '+ baddress.shipping_city +', '+ baddress.shipping_zip +' '+ baddress.shipping_state +', '+ baddress.shipping_country

            data['billing_address'] = billing_address

            #查询当前用户购物车产品
            data['number'] = order_list_count(request,customer.id)

            #order-detail不显示底部的切换语言及货币
            data['hidden_footer'] = 1

            return render(request, 'order-detail.html', data)
     
    return redirect('products')

#上传csv文件生成订单
def upload_list_order(request):
    data = {}

    has_promotion = get_promotion(request)
    data['has_promotion'] = has_promotion

    #判断是否登陆，并把参数传递到模板页
    # customer = is_login(request)
    customer_id = request.session.get('customer_id', False)
    if not customer_id:
        return redirect('login')
    else:
        customer = Customer.objects.filter(id=customer_id).first()

    if request.POST:
        #上传csv文件生成订单
        if request.POST['type'] == 'upload_list_order':

            #获取文件对象
            file_obj = request.FILES.get('upload_list', None)

            if file_obj == None:
                return redirect('products')

            #文件内容
            file_content = file_obj.read()

            #格式转化
            try:
                reader = csv.reader(StringIO.StringIO(file_content),delimiter=';')
                header = next(reader)
            except Exception as e:
                return redirect('products')

            std_header = [
                "Ref.","QTY"
            ]
            field_header = [
                "sku",'qty'
            ]

            # 由于bom头的问题, 就不比较第一列的header了
            if header[1:] != std_header[1:]:
                # messages.error(request, u"请使用正确的模板, 并另存为utf-8格式")
                return redirect('products')

            #用于保存正确的sku产品和数量
            product_right = {}

            #获取csv表格每一行的值，i为行数，row该行对应的列的值
            for i, row in enumerate(reader,2):
                #将上传的每一行的值与改行的标题一一对应，及(sku,sku值)，(qyt,qty值)
                res = zip(field_header,row)
                #转为为字典，方便后面取值
                res = dict(res)

                try:
                    #sku格式转化
                    is_start_zero = res['sku'].startswith('0')
                    res['sku'] = int(res['sku'])

                    if is_start_zero:
                        res['sku'] = str('0') + str(res['sku'])
                    else:
                        res['sku'] = str(res['sku'])

                    #拆分数字
                    sku_str = ''
                    i = 0
                    while i < len(res['sku']):
                        sku_str += str(res['sku'][i:i+2]) + str(' ')
                        i += 2
                
                    #去掉最后一个空格
                    sku_str = sku_str.strip()

                    res['sku'] = sku_str
                except Exception as e:
                    print e
                    pass

                #判断输入的sku是否有误
                product = Product.objects.filter(sku=res['sku'],visibility=1).first()
                #产品存在，保存产品及对应的数量
                if product:
                    if res['qty']:
                        product_right[res['sku']] = res['qty']
                    # else:
                    #   product_right[res['sku']] = 0

            '''跳转到order-detail页面，传递的参数与def order_detail(request)方法传递的参数及名称相同'''

            data['customer'] = customer
            customer_id = customer.id

            #用户所属库存组判断
            stock_group = get_stock_group(customer.id)

            #获取用户地址信息
            shipping_addresses = {}
            default_address = {}
            addresses = Address.objects.filter(customer_id=customer.id).all()
            for address in addresses:
                default_address[int(address.id)] = address.default
                shipping_addresses[int(address.id)] = customer.firstname +', '+ address.shipping_phone +', '+ address.shipping_mobile +' '+ address.shipping_address +' '+ address.shipping_city +', '+ address.shipping_zip +' '+ address.shipping_state +', '+ address.shipping_country

            data['shipping_addresses'] = shipping_addresses
            data['default_address'] = default_address

            billing_address = ''

            baddress = BillingAddress.objects.filter(customer_id=customer.id).first()
            if baddress:
                billing_address = customer.firstname +', '+ baddress.billing_phone +', '+baddress.billing_mobile+' '+ baddress.billing_address +' '+ baddress.billing_city +', '+ baddress.billing_zip +' '+ baddress.billing_state +', '+ baddress.billing_country
            else:
                baddress = Address.objects.filter(customer_id=customer.id,default=1).first()
                if baddress:
                    billing_address = customer.firstname +', '+ baddress.shipping_phone +', '+ baddress.shipping_mobile +' '+ baddress.shipping_address +' '+ baddress.shipping_city +', '+ baddress.shipping_zip +' '+ baddress.shipping_state +', '+ baddress.shipping_country
                else:
                    baddress = Address.objects.filter(customer_id=customer.id).first()
                    if baddress:
                        billing_address = customer.firstname +', '+ baddress.shipping_phone +', '+ baddress.shipping_mobile +' '+ baddress.shipping_address +' '+ baddress.shipping_city +', '+ baddress.shipping_zip +' '+ baddress.shipping_state +', '+ baddress.shipping_country

            data['billing_address'] = billing_address


            currency = currency_get(request)
            #产品数据
            cartitem_id = []
            for sku, qty in product_right.items():
                product = Product.objects.filter(sku=sku,visibility=1).first()
                price = product.final_price(customer.id,currency)
                quantity = int(qty)

                #产品库存状态
                stock_type = product.get_stock_type(stock_group)
                
                '''把产品数据保存到购物车'''
                #查看购物车是否已包含此产品,存在的情况，返回对象，不存在则创建对象再返回，然后可以直接更新产品其他数据
                cartitem , is_created = CartItem.objects.get_or_create(customer_id=customer_id,product_id=product.id)

                #更新数据
                update = CartItem.objects.filter(customer_id=customer_id,product_id=product.id).update(quantity=quantity,sku=product.sku,description=product.description,name=product.name,stock=stock_type,price=price,expected_time=product.expected_time)

                if update:
                    cartitem_id.append(cartitem.id)

            #获取cartitem中刚上传的产品
            cartitem_id = tuple(cartitem_id)
            cartitems = CartItem.objects.filter(customer_id=customer.id,id__in=cartitem_id).all()
            data['cartitems'] = cartitems

            #判断选择的产品中是否有库存限制的产品
            stock_limit = ''
            #订单总额
            amount = 0.0
            #获取cartitem已经选择的产品id,用于生成订单时的产品数据
            cartitem_ids = []
            #获取产品图片
            images = {}
            for c in cartitems:
                stock = c.stock
                if stock == 0:
                    stock_limit = 1
                    
                amount += float(c.price) * c.quantity
                cartitem_ids.append(str(c.id))

                product_id = c.product_id
                pimage = ProductImage.objects.filter(product_id=product_id).order_by('id').first()
                if pimage:
                    images[int(c.id)] = pimage.image
                else:
                    images[int(c.id)] = ''

            cartitem_ids = ','.join(cartitem_ids)
            amount = round(amount,2)
            
            data['amount'] = amount
            data['images'] = images
            data['cartitem_ids'] = cartitem_ids
            data['stock_limit'] = stock_limit

            #查询当前用户购物车产品
            data['number'] = order_list_count(request,customer.id)

            #order-detail不显示底部的切换语言及货币
            data['hidden_footer'] = 1
            #前台产品价格后面的货币符号展示
            data['code'] = get_currency_code(request)

            #前台显示时间：当前时间+14天
            est_date = get_est_date()
        
            data['est_date'] = est_date

            return render(request, 'order-detail.html', data)

    return redirect('products')

#打印订单
def order_print(request,order_id):
    data = {}

    has_promotion = get_promotion(request)
    data['has_promotion'] = has_promotion

    #订单信息
    order = Order.objects.filter(id=order_id).first()
    data['order'] = order 

    #币种符号
    currency = Currency.objects.filter(name=order.currency).first()
    if currency:
        data['code'] = currency.code
    else:
        data['code'] = '€'

    #订单状态
    status = {}
    status = {
            0:'new',
            1:'processing',
            2:'artical shipped',
            3:'shipped',
            4:'cancel',
        }
    data['status'] = status

    #用户信息
    customer = Customer.objects.filter(id=order.customer_id).first()
    customer_name = customer.firstname + customer.lastname
    data['customer_name'] = customer_name

    #获取用户地址信息
    shipping_address = customer.firstname +', '+ order.shipping_phone +', '+ order.shipping_mobile +' '+ order.shipping_address +' '+ order.shipping_city +', '+ order.shipping_zip +' '+ order.shipping_state +', '+ order.shipping_country

    billing_address =customer.firstname +', '+ order.billing_phone +', '+order.billing_mobile+' '+ order.billing_address +' '+ order.billing_city +', '+ order.billing_zip +' '+ order.billing_state +', '+ order.billing_country

    data['shipping_address'] = shipping_address
    data['billing_address'] = billing_address

    #期望发货时间页面展示（格式转化）
    expcted_shipping = order.expcted_shipping
    if expcted_shipping:
        expcted_shipping = str(expcted_shipping)[0:11]
    data['expcted_shipping'] = expcted_shipping


    #产品信息
    orderitems = OrderItem.objects.filter(order_id=order_id).all()
    data['orderitems'] = orderitems

    #产品图片
    images = {}
    for orderitem in orderitems:
        product_id = orderitem.product_id
        pimage = ProductImage.objects.filter(product_id=product_id).order_by('id').first()
        if pimage:
            images[int(orderitem.id)] = pimage.image
        else:
            images[int(orderitem.id)] = ''
    data['images'] = images


    return render(request, 'print-order.html', data)


#前台order-detail页面地址删除操作ajax
def order_address_delete(request):

    data = {}
    if request.method == 'POST':
        if request.POST['type'] == 'shipping_address_delete':

            customer_id = request.POST['customer_id']
            address_id = request.POST['address_id']
            #判断地址数量，最后一个地址不允许删除
            address_count = Address.objects.filter(customer_id=customer_id).all().count()
            if address_count == 1:
                data['result'] = 1
                data = demjson.encode(data)
                return HttpResponse(data, content_type='application/json')
            else:
                Address.objects.filter(id=address_id,customer_id=customer_id).delete()

                data['result'] = 2
                data = demjson.encode(data)
                return HttpResponse(data, content_type='application/json')

    return HttpResponse('111111')


#前台order-detail页面地址新增操作ajax
def order_address_add(request):

    data = {}
    if request.method == 'POST':
        if request.POST['type'] == 'shipping_address_add':

            customer_id = request.POST['customer_id']
            customer = Customer.objects.filter(id=customer_id).first()

            shipping_country = request.POST['shipping_country']
            shipping_state = request.POST['shipping_state']
            shipping_city = request.POST['shipping_city']
            shipping_address = request.POST['shipping_address']
            shipping_zip = request.POST['shipping_zip']
            shipping_phone = request.POST['shipping_phone']
            shipping_mobile = request.POST['shipping_mobile']

            lang = request.POST['lang']

            #如果都为空，则不允许新增
            if shipping_country == shipping_state == shipping_city == shipping_address == shipping_zip == shipping_phone == shipping_mobile == '':
                data['result'] = 3
                data = demjson.encode(data)
                return HttpResponse(data, content_type='application/json')

            address = Address.objects.create(
                    customer_id = customer_id,
                    shipping_country = shipping_country,
                    shipping_state = shipping_state,
                    shipping_city = shipping_city,
                    shipping_address = shipping_address,
                    shipping_zip = shipping_zip,
                    shipping_phone = shipping_phone,
                    shipping_mobile = shipping_mobile,
                    default = 0,
                )

            if address:
                data['result'] = 1

                ship_address = customer.firstname +', '+ address.shipping_phone +', '+ address.shipping_mobile +' '+ address.shipping_address +' '+ address.shipping_city +', '+ address.shipping_zip +' '+ address.shipping_state +', '+ address.shipping_country

                set_default = "Set Default"
                if lang == 'fr':
                    set_default = u'Par Défaut'
                    add = u'Ajouter'
                    edit = u'Editer'
                    delete = u'SUPPRIMER'
                elif lang == 'de':
                    set_default = u'Betriebsart'
                    add = u'Hinzufügen'
                    edit = u'Editieren'
                    delete = u'Löschen'
                elif lang == 'nl':
                    set_default = 'Set Default'
                    add = 'Add'
                    edit = 'Edit'
                    delete = 'Delete'
                else:
                    set_default = "Set Default"
                    add = 'Add'
                    edit = 'Edit'
                    delete = 'Delete'

                data['address_add'] = "<div class='col-xs-11 addressrow'><div class='col-xs-1'><input type='radio' name='select_shipping_address' value='"+str(address.id)+"'/></div><p class='form-control-static' id='shipping_address_detail_"+str(address.id)+"'>"+str(ship_address)+"</p><div class='row'><div class='col-xs-2' style='width: 25%;'><a href='javascript:void(0);' data-toggle='modal' data-target='#myModal-rec-add'><i class='fa fa-plus mr10' aria-hidden='true'></i>"+add+"</a></div><div class='col-xs-2' style='width: 25%;'><a href='javascript:void(0);' onclick='shipping_address_edit_show("+str(address.id)+")'><i class='fa fa-pencil-square-o mr10' aria-hidden='true'></i>"+edit+"</a></div><div class='col-xs-3' style='width: 25%;'><a href='javascript:void(0);' onclick='shipping_address_delete("+str(address.id)+", this)'><i class='fa fa-trash-o mr10' aria-hidden='true'></i>"+delete+"</a></div><div class='col-xs-offset-1 col-xs-3' id='dafault_"+str(address.id)+"' style='margin-left:0px;'><a href='javascript:void(0);' onclick='address_set_dafault("+str(address.id)+", this)'>"+set_default+"</a></div>  </div></div>"
                data = demjson.encode(data)
                return HttpResponse(data, content_type='application/json')
            else:
                data['result'] = 2
                data = demjson.encode(data)
                return HttpResponse(data, content_type='application/json')


    return HttpResponse('111111')

#前台order-detail页面地址编辑操作ajax
def order_address_edit(request):
    data = {}
    if request.method == 'POST':
        #打开页面时获取数据填充表单
        if request.POST['type'] == 'shipping_address_edit_show':
            address_id = request.POST['address_id']

            address = Address.objects.filter(id=address_id).first()
            
            if address:

                data['result'] = 1

                data['shipping_country'] = address.shipping_country
                data['shipping_state'] = address.shipping_state
                data['shipping_city'] = address.shipping_city
                data['shipping_address'] = address.shipping_address
                data['shipping_zip'] = address.shipping_zip
                data['shipping_phone'] = address.shipping_phone
                data['shipping_mobile'] = address.shipping_mobile

                data = demjson.encode(data)
                return HttpResponse(data, content_type='application/json')
            else:
                data['result'] = 2
                data = demjson.encode(data)
                return HttpResponse(data, content_type='application/json')

        #編輯頁面提交數據
        if request.POST['type'] == 'shipping_address_edit_submit':

            address_id = request.POST['address_id']

            customer_id = request.POST['customer_id']
            customer = Customer.objects.filter(id=customer_id).first()

            shipping_country = request.POST['shipping_country']
            shipping_state = request.POST['shipping_state']
            shipping_city = request.POST['shipping_city']
            shipping_address = request.POST['shipping_address']
            shipping_zip = request.POST['shipping_zip']
            shipping_phone = request.POST['shipping_phone']
            shipping_mobile = request.POST['shipping_mobile']

            #如果都为空，则不允许编辑
            if shipping_country == shipping_state == shipping_city == shipping_address == shipping_zip == shipping_phone == shipping_mobile == '':
                data['result'] = 3
                data = demjson.encode(data)
                return HttpResponse(data, content_type='application/json')


            address = Address.objects.filter(id=address_id).update(
                    customer_id = customer_id,
                    shipping_country = shipping_country,
                    shipping_state = shipping_state,
                    shipping_city = shipping_city,
                    shipping_address = shipping_address,
                    shipping_zip = shipping_zip,
                    shipping_phone = shipping_phone,
                    shipping_mobile = shipping_mobile,
                )

            if address:
                address = Address.objects.filter(id=address_id).first()

                data['result'] = 1

                ship_address = customer.firstname +', '+ address.shipping_phone +', '+ address.shipping_mobile +' '+ address.shipping_address +' '+ address.shipping_city +', '+ address.shipping_zip +' '+ address.shipping_state +', '+ address.shipping_country

                data['ship_address'] = ship_address
                data = demjson.encode(data)
                return HttpResponse(data, content_type='application/json')
            else:
                data['result'] = 2
                data = demjson.encode(data)
                return HttpResponse(data, content_type='application/json')

    return HttpResponse('11111')


#前台order-detail页面设置shipping address 为默认ajax
def order_address_set_default(request):
    data = {}
    if request.method == 'POST':
        if request.POST['type'] == 'address_set_dafault':

            customer_id = request.POST['customer_id']

            address_id = request.POST['address_id']

            if address_id:
                address_ids = []
                addresses = Address.objects.filter(customer_id=customer_id).all()
                for address in addresses:
                    if address.id == int(address_id):
                        Address.objects.filter(id=address.id).update(default=1)
                    else:
                        address_ids.append(address.id)
                        Address.objects.filter(id=address.id).update(default=0)

                data['address_ids'] = address_ids
                data['result'] = 1
                data = demjson.encode(data)
                return HttpResponse(data, content_type='application/json')
            else:
                data['result'] = 2
                data = demjson.encode(data)
                return HttpResponse(data, content_type='application/json')

    return HttpResponse('11111')

