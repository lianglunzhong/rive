#-*- coding:utf-8 -*-
from __future__ import unicode_literals
from django.shortcuts import render, render_to_response
from django.http import HttpResponse, HttpResponseRedirect
from django.conf.urls import url
from accounts.models import Customer, Address,BillingAddress
from django.contrib.auth.hashers import make_password, check_password
from django.shortcuts import get_object_or_404, redirect
from accounts.forms import LoginForm
from orders.models import CartItem, Order, OrderItem, OrderHistory
import demjson
from django.contrib.auth.decorators import login_required
import StringIO
import csv
from django.contrib import messages
from django.contrib.auth.models import User,Group
from django.db.models import Q
from django.views.decorators.csrf import csrf_protect
from django.views.decorators.csrf import csrf_exempt
import time,thread
import chardet
import sys
from library.views import sendEmail
reload(sys)
sys.setdefaultencoding('utf8')

from django.conf import settings
from django.core.mail import send_mail,send_mass_mail,EmailMultiAlternatives
from django.template import loader
from django.db import connection, transaction
from library.views import getCookie, get_promotion



def index(request):
    data = {}
    print request.path
    return render(request, 'index.html', data)

#导出公用方法
def write_csv(filename):
    response = HttpResponse(content_type='text/csv')
    # response.write('\xEF\xBB\xBF')
    response['Content-Disposition'] = 'attachment; filename="%s.csv"' % filename
    writer = csv.writer(response, delimiter=b";")
    return response, writer

#登录
@csrf_exempt
def login(request):

    lang = getCookie(request)

    data = {}

    has_promotion = get_promotion(request)

    customer_id = request.session.get('customer_id', False)
    if customer_id:
        #判断用户是否被锁定
        customer = Customer.objects.filter(id=customer_id).first()
        if customer.locked:
            try:
                del request.session['customer_id']
            except KeyError:
                pass
            return redirect('login')
        else:
            if has_promotion:
                return redirect('promotion')
            else:
                return redirect('products')
            
    if request.POST:
        #判断是否为第一次登陆修改密码操作
        if request.POST.get('type') == 'first_login_change_password':
            email = request.POST.get('email', '')
            if not email:
                if lang == 'fr':
                    data['error'] = "<i class='fa fa-warning' style='color:#f00;'></i> Renseignez votre compte !"
                elif lang == 'de':
                    data['error'] = "<i class='fa fa-warning' style='color:#f00;'></i> Füllen Sie Ihr Konto aus !"
                elif lang == 'nl':
                    data['error'] = "<i class='fa fa-warning' style='color:#f00;'></i> Account can not be empty !"
                else:
                    data['error'] = "<i class='fa fa-warning' style='color:#f00;'></i> Account can not be empty !"
                return render(request, 'login.html', data)
            password = request.POST.get('password', '')
            cpassword = request.POST.get('cpassword', '')
            if not password or not cpassword:
                data['change_password'] = 1
                data['email'] = email
                if lang == 'fr':
                    data['error'] = "<i class='fa fa-warning' style='color:#f00;'></i> Renseigner votre mot de passe !"
                elif lang == 'de':
                    data['error'] = "<i class='fa fa-warning' style='color:#f00;'></i> Geben Sie auf der Bildschirmtastatur Ihr Passwort ein !"
                elif lang == 'nl':
                    data['error'] = "<i class='fa fa-warning' style='color:#f00;'></i> Password can not be empty !"
                else:
                    data['error'] = "<i class='fa fa-warning' style='color:#f00;'></i> Password can not be empty !"
                return render(request, 'login.html', data)
            #判断密码长度及格式
            password = str(password)
            length = len(password)
            if length < 6:
                data['change_password'] = 1
                data['email'] = email
                if lang == 'fr':
                    data['error'] = "<i class='fa fa-warning' style='color:#f00;'></i> Votre mot de passe doit contenir 6 caractères minimum et 20 caractèrse maximum."
                elif lang == 'de':
                    data['error'] = "<i class='fa fa-warning' style='color:#f00;'></i> Das Passwort soll mindestens 6 Buchstaben und höchstens 20 Buchstaben enthalten."
                elif lang == 'nl':
                    data['error'] = "<i class='fa fa-warning' style='color:#f00;'></i> Password must be at least 6 characters long and not exceeds maximum length of 20 characters."
                else:
                    data['error'] = "<i class='fa fa-warning' style='color:#f00;'></i> Password must be at least 6 characters long and not exceeds maximum length of 20 characters."

                return render(request, 'login.html', data)
            if length > 20:
                data['change_password'] = 1
                data['email'] = email

                if lang == 'fr':
                    data['error'] = "<i class='fa fa-warning' style='color:#f00;'></i> Votre mot de passe doit contenir 6 caractères minimum et 20 caractèrse maximum."
                elif lang == 'de':
                    data['error'] = "<i class='fa fa-warning' style='color:#f00;'></i> Das Passwort soll mindestens 6 Buchstaben und höchstens 20 Buchstaben enthalten."
                elif lang == 'nl':
                    data['error'] = "<i class='fa fa-warning' style='color:#f00;'></i> Password must be at least 6 characters long and not exceeds maximum length of 20 characters."
                else:
                    data['error'] = "<i class='fa fa-warning' style='color:#f00;'></i> Password must be at least 6 characters long and not exceeds maximum length of 20 characters."

                return render(request, 'login.html', data)
            #判断两次输入的密码是否一致
            if password != cpassword:
                data['change_password'] = 1
                data['email'] = email
                if lang == 'fr':
                    data['error'] = "<i class='fa fa-warning' style='color:#f00;'></i> Votre nouveau mot de passe et le mot de passe confirmé sont différents."
                elif lang == 'de':
                    data['error'] = "<i class='fa fa-warning' style='color:#f00;'></i> Das neue Passwort und die Kontrolle stimmen nicht überein."
                elif lang == 'nl':
                    data['error'] = "<i class='fa fa-warning' style='color:#f00;'></i> Your new and confirm password are different."
                else:
                    data['error'] = "<i class='fa fa-warning' style='color:#f00;'></i> Your new and confirm password are different."

                return render(request, 'login.html', data)
            customer = Customer.objects.filter(email=email).order_by('-id').first()
            pw = customer.password
            password = make_password(password, 'a', 'pbkdf2_sha256')
            #判断新密码与旧密码是否相同
            if password == pw:
                data['change_password'] = 1
                data['email'] = email
                if lang == 'fr':
                    data['error'] = "<i class='fa fa-warning' style='color:#f00;'></i> Votre nouveau mot de passe doit être différent de l'ancien."
                elif lang == 'de':
                    data['error'] = "<i class='fa fa-warning' style='color:#f00;'></i> Ihr neues Passwort soll von dem letzes unterschiedlich sein."
                elif lang == 'nl':
                    data['error'] = "<i class='fa fa-warning' style='color:#f00;'></i> Your new password must be different with your current password."
                else:
                    data['error'] = "<i class='fa fa-warning' style='color:#f00;'></i> Your new password must be different with your current password."

                return render(request, 'login.html', data)
            #更新密码,更新customer表的is_lock字段
            customer = Customer.objects.filter(email=email).order_by('-id')
            query = customer.update(password=password,is_lock=0)
            if query:
                data['email'] = email
                data['change_success'] = 1
                if lang == 'fr':
                    data['error'] = "<i class='fa fa-info-circle' style='color:#3f575b;'></i> Votre mot de passe a bien été mis à jour."
                elif lang == 'de':
                    data['error'] = "<i class='fa fa-info-circle' style='color:#3f575b;'></i> Ihr Passwort wurde generiert. "
                elif lang == 'nl':
                    data['error'] = "<i class='fa fa-info-circle' style='color:#3f575b;'></i> Your password has been changed successfully."
                else:
                    data['error'] = "<i class='fa fa-info-circle' style='color:#3f575b;'></i> Your password has been changed successfully."
                #验证成功，设置session
                customer = Customer.objects.filter(email=email).order_by('-id').first()
                customer_id = customer.id
                request.session['customer_id'] = customer_id
                return render(request, 'login.html', data)
            else:
                data['change_password'] = 1
                data['email'] = email
                if lang == 'fr':
                    data['error'] = "<i class='fa fa-warning' style='color:#f00;'></i> Erreur de modification de mot de passe ! "
                elif lang == 'de':
                    data['error'] = "<i class='fa fa-warning' style='color:#f00;'></i> Passwortänderung Fehler ! "
                elif lang == 'nl':
                    data['error'] = "<i class='fa fa-warning' style='color:#f00;'></i> Password change error !"
                else:
                    data['error'] = "<i class='fa fa-warning' style='color:#f00;'></i> Password change error !"
                return render(request, 'login.html', data)
        #正常登陆的情况下
        else:
            email = request.POST.get('email', '')
            if not email:
                if lang == 'fr':
                    data['error'] = "<i class='fa fa-warning' style='color:#f00;'></i> Renseignez votre compte ! "
                elif lang == 'de':
                    data['error'] = "<i class='fa fa-warning' style='color:#f00;'></i> Füllen Sie Ihr Konto aus ! "
                elif lang == 'nl':
                    data['error'] = "<i class='fa fa-warning' style='color:#f00;'></i> Account can not be empty !"
                else:
                    data['error'] = "<i class='fa fa-warning' style='color:#f00;'></i> Account can not be empty !"
                return render(request, 'login.html', data)
            password = request.POST.get('password', '')
            if not password:
                if lang == 'fr':
                    data['error'] = "<i class='fa fa-warning' style='color:#f00;'></i> Renseigner votre mot de passe ! "
                elif lang == 'de':
                    data['error'] = "<i class='fa fa-warning' style='color:#f00;'></i> Geben Sie auf der Bildschirmtastatur Ihr Passwort ein ! "
                elif lang == 'nl':
                    data['error'] = "<i class='fa fa-warning' style='color:#f00;'></i> Password can not be empty !"
                else:
                    data['error'] = "<i class='fa fa-warning' style='color:#f00;'></i> Password can not be empty !"
                return render(request, 'login.html', data)
            customer = Customer.objects.filter(email=str(email)).order_by('-id').first()
            if not customer:
                if lang == 'fr':
                    data['error'] = "<i class='fa fa-warning' style='color:#f00;'></i> Votre e-mail ou votre mot de passe n'est pas correct. Veuillez réessayer."
                elif lang == 'de':
                    data['error'] = "<i class='fa fa-warning' style='color:#f00;'></i> Ihr E-mail oder Ihr Passwort ist fehlerhaft. Bitte nochmal."
                elif lang == 'nl':
                    data['error'] = "<i class='fa fa-warning' style='color:#f00;'></i> Your user name/password combination was not correct. Please try again."
                else:
                    data['error'] = "<i class='fa fa-warning' style='color:#f00;'></i> Your user name/password combination was not correct. Please try again."
                return render(request, 'login.html', data)
            #正常登录的情况下，判断账号是否被锁定
            locked = customer.locked
            if locked:
                if lang == 'fr':
                    data['error'] = "<i class='fa fa-warning' style='color:#f00;'></i> Votre compte a été bloqué, merci de contacter votre représentant afin de vérifier le statut de votre compte."
                elif lang == 'de':
                    data['error'] = "<i class='fa fa-warning' style='color:#f00;'></i> Ihr Konto wurde gesperrt. Bitte kontaktieren Sie Ihrem Repräsentant um Ihr Konto den Status zu überprüfen.."
                elif lang == 'nl':
                    data['error'] = "<i class='fa fa-warning' style='color:#f00;'></i> Your account has been blocked, please contact your saleman to check your account status."
                else:
                    data['error'] = "<i class='fa fa-warning' style='color:#f00;'></i> Your account has been blocked, please contact your saleman to check your account status."
                return render(request, 'login.html', data)

            #正常登录的情况下，判断密码是否正确
            pw = customer.password
            password = make_password(password, 'a', 'pbkdf2_sha256')
            if password != pw:
                data['email'] = email
                if lang == 'fr':
                    data['error'] = "<i class='fa fa-warning' style='color:#f00;'></i> Votre e-mail ou votre mot de passe n'est pas correct. Veuillez réessayer."
                elif lang == 'de':
                    data['error'] = "<i class='fa fa-warning' style='color:#f00;'></i> Ihr E-mail oder Ihr Passwort ist fehlerhaft. Bitte nochmal."
                elif lang == 'nl':
                    data['error'] = "<i class='fa fa-warning' style='color:#f00;'></i> Your user name/password combination was not correct. Please try again."
                else:
                    data['error'] = "<i class='fa fa-warning' style='color:#f00;'></i> Your user name/password combination was not correct. Please try again."
                return render(request, 'login.html', data)
            #判断是否是第一次登录，第一次登录需要修改密码
            is_lock = customer.is_lock
            if is_lock:
                #返回页面，并显示更改密码输入框
                data['change_password'] = 1
                data['email'] = email
                if lang == 'fr':
                    data['error'] = "<i class='fa fa-info-circle' style='color:#3f575b;'></i> Le mot de passe doit-être modifié lors de votre première connection."
                elif lang == 'de':
                    data['error'] = "<i class='fa fa-info-circle' style='color:#3f575b;'></i> Das Passwort muss bei der ersten Anmeldung geändert werden."
                elif lang == 'nl':
                    data['error'] = "<i class='fa fa-info-circle' style='color:#3f575b;'></i> The user's password must be changed before logging on for the first time."
                else:
                    data['error'] = "<i class='fa fa-info-circle' style='color:#3f575b;'></i> The user's password must be changed before logging on for the first time."
                return render(request, 'login.html', data)
            #验证成功，设置session
            customer_id = customer.id
            request.session['customer_id'] = customer_id
            #跳转到模板页
            if has_promotion:
                return redirect('promotion')
            else:
                return redirect('products')

    return render(request,'login.html',data)


def template(request):
    data = {}
    customer_id = request.session.get('customer_id', False)
    if not customer_id:
        return redirect('login')
    customer = Customer.objects.filter(id=customer_id).first()
    data['email'] = customer.email
    data['firstname'] = customer.firstname
    return render(request, 'template.html', data)

#退出
def logout(request):
    data = {}
    try:
        del request.session['customer_id']
    except KeyError:
        pass
    return redirect('login')

def logintest(request):
    data = {}
    if request.POST:
        form = LoginForm(request.POST)
        ret = objPost.is_valid()
        if ret:
            email = form.cleaned_data['email']
            password = form.cleaned_data('password')
            print email
            print password


    return render(request, 'login_test.html',data)

#判断用户是否登录通用方法（弃用）
def is_login(request):
    customer_id = request.session.get('customer_id', False)
    if not customer_id:
        return redirect('login')
    else:
        customer = Customer.objects.filter(id=customer_id).first()
        return customer

#查询当前用户购物车产品数公共方法
def order_list_count(request,customer_id):
    # customer = is_login(request)
    cartitems = CartItem.objects.filter(customer_id=customer_id).all()
    count = cartitems.count()
    return int(count)


#获取用户shipping address公共方法(页面展示)
def get_shipping_address(customer_id):
    customer = Customer.objects.filter(id=customer_id).first()
    shipping_address = ''
    address = Address.objects.filter(customer_id=customer_id).first()
    if address:
        shipping_address += customer.firstname +', '+ address.shipping_phone +' '+ address.shipping_address +' '+ address.shipping_city +', '+ address.shipping_zip +' '+ address.shipping_state +', '+ address.shipping_country
    return shipping_address

#获取用户billing address公共方法(页面展示)
def get_billing_address(customer_id):
    customer = Customer.objects.filter(id=customer_id).first()
    billing_address = ''
    address = Address.objects.filter(customer_id=customer_id).first()
    if address:
        billing_address += customer.firstname +', '+ address.billing_phone +' '+ address.billing_address +' '+ address.billing_city +', '+ address.billing_zip +' '+ address.billing_state +', '+ address.billing_country
    return billing_address


#获取用户shipping address公共方法(导出)
def get_shipping_address2(customer_id):
    customer = Customer.objects.filter(id=customer_id).first()
    shipping_address = ''
    address = Address.objects.filter(customer_id=customer_id).first()
    if address:
        shipping_address += customer.firstname +' '+ address.shipping_phone +' '+ address.shipping_address +' '+ address.shipping_city +' '+ address.shipping_zip +' '+ address.shipping_state +' '+ address.shipping_country
    return shipping_address

#获取用户billing address公共方法(导出)
def get_billing_address2(customer_id):
    customer = Customer.objects.filter(id=customer_id).first()
    billing_address = ''
    address = Address.objects.filter(customer_id=customer_id).first()
    if address:
        billing_address += customer.firstname +' '+ address.billing_phone +' '+ address.billing_address +' '+ address.billing_city +' '+ address.billing_zip +' '+ address.billing_state +' '+ address.billing_country
    return billing_address

#用户登录之后修改密码ajax数据操作
def change_password_ajax(request):

    lang = getCookie(request)

    data = {}
    if request.method == 'POST':
        if request.POST['type'] == 'change_password':
            old_password = request.POST['old_password']
            new_password = request.POST['new_password']
            comfirm_password = request.POST['comfirm_password']
            #密码不能为空
            if not old_password or not new_password or not comfirm_password:
                if lang == 'fr':
                    data['error'] = 'Current and new passwords can not be empty.'
                elif lang == 'de':
                    data['error'] = 'Current and new passwords can not be empty.'
                elif lang == 'nl':
                    data['error'] = 'Current and new passwords can not be empty.'
                else:
                    data['error'] = 'Current and new passwords can not be empty.'
                data = demjson.encode(data)
                return HttpResponse(data, content_type='application/json')
            #获取用户信息
            customer_id = request.session.get('customer_id', False)
            customer = Customer.objects.filter(id=customer_id).first()

            #验证旧密码是否正确
            password = customer.password
            old_password = make_password(old_password, 'a', 'pbkdf2_sha256')
            if old_password != password:
                if lang == 'fr':
                    data['error'] = "Current password is not correct."
                elif lang == 'de':
                    data['error'] = "Current password is not correct."
                elif lang == 'nl':
                    data['error'] = "Current password is not correct."
                else:
                    data['error'] = "Current password is not correct."
                data = demjson.encode(data)
                return HttpResponse(data, content_type='application/json')
            #判断密码长度及格式
            new_password = str(new_password)
            length = len(new_password)
            if length < 6 or length > 20:
                if lang == 'fr':
                    data['error'] = "Votre mot de passe doit contenir 6 caractères minimum et 20 caractèrse maximum."
                elif lang == 'de':
                    data['error'] = "Das Passwort soll mindestens 6 Buchstaben und höchstens 20 Buchstaben enthalten."
                elif lang == 'nl':
                    data['error'] = "New password must be at least 6 characters long and not exceeds maximum length of 20 characters."
                else:
                    data['error'] = "New password must be at least 6 characters long and not exceeds maximum length of 20 characters."
                data = demjson.encode(data)
                return HttpResponse(data, content_type='application/json')
            #判断两次输入的密码是否一致
            if new_password != comfirm_password:
                if lang == 'fr':
                    data['error'] = "Votre nouveau mot de passe et le mot de passe confirmé sont différents."
                elif lang == 'de':
                    data['error'] = "Das neue Passwort und die Kontrolle stimmen nicht überein."
                elif lang == 'nl':
                    data['error'] = "New and confirm password are different."
                else:
                    data['error'] = "New and confirm password are different."
                data = demjson.encode(data)
                return HttpResponse(data, content_type='application/json')
            #判断新密码与旧密码是否相同
            new_password = make_password(new_password, 'a', 'pbkdf2_sha256')
            if password == new_password:
                if lang == 'fr':
                    data['error'] = "Votre nouveau mot de passe doit être différent de l'ancien"
                elif lang == 'de':
                    data['error'] = "Ihr neues Passwort soll von dem letzes unterschiedlich sein."
                elif lang == 'nl':
                    data['error'] = "New password must be different with your current password."
                else:
                    data['error'] = "New password must be different with your current password."
                data = demjson.encode(data)
                return HttpResponse(data, content_type='application/json')
            #更新密码
            customer = Customer.objects.filter(id=customer_id).update(password=new_password)
            if customer:
                data['success'] = 1
                data = demjson.encode(data)
                return HttpResponse(data, content_type='application/json')
            else:
                data['error'] = "Change password false."
                data = demjson.encode(data)
                return HttpResponse(data, content_type='application/json')

    return HttpResponse('11111')

#csv批量上传用户
@login_required
def upload_customers(request):
    data = {}
    #获取上一个页面url，数据处理之后跳转回该页面
    referer_url = request.META['HTTP_REFERER']

    if request.method == 'POST':
        if request.POST['type'] == 'upload_customers':

            #获取文件对象
            file_obj = request.FILES.get('upload_customers_file',None)

            if file_obj == None:
                return redirect(referer_url)

            #获取文件内容
            file_content = file_obj.read()

            #格式转化
            try:
                reader = csv.reader(StringIO.StringIO(file_content),delimiter=str(';'))
                header = next(reader)
            except Exception as e:
                print e
                return redirect(referer_url)

            std_header = [
                'Email','Firstname','Lastname','Discount','Lock','Admin_username/email','Account_number','Shop_name','Country','State/Province','City','Zip','Phone','Mobile','Address'
            ]
            field_header = [
                'email','firstname','lastname','discount','locked','admin','account_number','shop_name','country','state','city','zip','phone','mobile','address'
            ]

            #由于bom头的问题, 就不比较第一列的header了
            if header[1:] != std_header[1:]:
                messages.error(request,"Please use the correct template and save as UTF-8 format.")
                return redirect(referer_url)

            #用于保存已经存在的用户email
            email_error = []

            #获取csv表格每一行的值，i为行数，row该行对应的列的值
            for i, row in enumerate(reader,2):
                #将上传的每一行的值与该行的标题一一对应
                res = zip(field_header,row)
                #转为为字典，方便后面取值
                res = dict(res)

                if res['email']:
                    print res['email']
                    res['email'] = res['email'].strip().decode('gbk').encode('utf-8')
                    res['firstname'] = res['firstname'].strip().decode('gbk').encode('utf-8')
                    res['lastname'] = res['lastname'].strip().decode('gbk').encode('utf-8')
                    res['admin'] = res['admin'].strip().decode('gbk').encode('utf-8')
                    res['account_number'] = res['account_number'].strip().decode('gbk').encode('utf-8')
                    res['country'] = res['country'].strip().decode('gbk').encode('utf-8')
                    res['city'] = res['city'].strip().decode('gbk').encode('utf-8')
                    res['phone'] = res['phone'].strip().decode('gbk').encode('utf-8')
                    res['address'] = res['address'].strip().decode('gbk').encode('utf-8')
                    res['state'] = res['state'].strip().decode('gbk').encode('utf-8')
                    res['shop_name'] = res['shop_name'].strip().decode('gbk').encode('utf-8')
                    #判断用户email是否已经存在
                    customer = Customer.objects.filter(email=res['email']).first()
                    if customer:
                        # email_error.append(res['email'])
                        #如果已经存在则更新

                        #折扣
                        discount = 1.0
                        if res['discount']:
                            try:
                                discount = round(float(res['discount']),2)
                            except Exception as e:
                                discount = 1.0
                        if discount<=0 or discount>1.0:
                            discount = 1.0

                        #lock
                        locked = 0
                        if res['locked']:
                            try:
                                locked = int(locked)
                            except Exception as e:
                                discount = 0
                        if locked != 0 and locked != 1:
                            locked = 0

                        #admin
                        if res['admin']:
                            user = User.objects.filter(Q(username=res['admin'])|Q(email=res['admin'])).first()
                            if user:
                                admin_id = user.id
                            else:
                                admin_id = ''
                        else:
                            admin_id = ''

                        #更新
                        customer_updated = Customer.objects.filter(id=customer.id).update(
                                # email = res['email'],
                                # password = 'pbkdf2_sha256$24000$a$gx0SVXPywuw1WsH2Y009UGxRwdfJhkwpM4Og7x7bI7Y=',
                                firstname = res['firstname'],
                                lastname = res['lastname'],
                                discount = discount,
                                locked = locked,
                                admin_id = admin_id,
                                account_number = res['account_number'],
                                shop_name = res['shop_name'],
                            )
                        #客户更新成功，更新对应的地址
                        if customer_updated:
                            ship_address = Address.objects.filter(customer_id=customer.id).first()
                            if ship_address:
                                address_updated = Address.objects.filter(customer_id=customer.id).update(
                                        shipping_country = res['country'],
                                        shipping_state = res['state'],
                                        shipping_city = res['city'],
                                        shipping_address = res['address'],
                                        shipping_zip = res['zip'],
                                        shipping_phone = res['phone'],
                                        shipping_mobile = res['mobile'],
                                        default = 1,
                                    )
                            else:
                                address_create = Address.objects.create(
                                        customer_id = customer.id,
                                        shipping_country = res['country'],
                                        shipping_state = res['state'],
                                        shipping_city = res['city'],
                                        shipping_address = res['address'],
                                        shipping_zip = res['zip'],
                                        shipping_phone = res['phone'],
                                        shipping_mobile = res['mobile'],
                                        default = 1,
                                    )
                            bill_address = BillingAddress.objects.filter(customer_id=customer.id).first()
                            if bill_address:
                                address_updated2 = BillingAddress.objects.filter(customer_id=customer.id).update(
                                        billing_country = res['country'],
                                        billing_state = res['state'],
                                        billing_city = res['city'],
                                        billing_address = res['address'],
                                        billing_zip = res['zip'],
                                        billing_phone = res['phone'],
                                        billing_mobile = res['mobile'],
                                    )
                            else:
                                address_create2 = BillingAddress.objects.create(
                                        customer_id = customer.id,
                                        billing_country = res['country'],
                                        billing_state = res['state'],
                                        billing_city = res['city'],
                                        billing_address = res['address'],
                                        billing_zip = res['zip'],
                                        billing_phone = res['phone'],
                                        billing_mobile = res['mobile'],
                                    )

                    #新增客户
                    else:
                        #折扣
                        discount = 1.0
                        if res['discount']:
                            try:
                                discount = round(float(res['discount']),2)
                            except Exception as e:
                                discount = 1.0
                        if discount<=0 or discount>1.0:
                            discount = 1.0

                        #lock
                        locked = 0
                        if res['locked']:
                            try:
                                locked = int(locked)
                            except Exception as e:
                                discount = 0
                        if locked != 0 and locked != 1:
                            locked = 0

                        #admin
                        if res['admin']:
                            user = User.objects.filter(Q(username=res['admin'])|Q(email=res['admin'])).first()
                            if user:
                                admin_id = user.id
                            else:
                                admin_id = ''
                        else:
                            admin_id = ''

                        #新增
                        customer_create = Customer.objects.create(
                                email = res['email'],
                                password = 'pbkdf2_sha256$24000$a$gx0SVXPywuw1WsH2Y009UGxRwdfJhkwpM4Og7x7bI7Y=',
                                firstname = res['firstname'],
                                lastname = res['lastname'],
                                discount = discount,
                                locked = locked,
                                admin_id = admin_id,
                                account_number = res['account_number'],
                                shop_name = res['shop_name'],
                            )
                        #客户添加成功，添加对应的地址
                        if customer_create:
                            address_create = Address.objects.create(
                                    customer_id = customer_create.id,
                                    shipping_country = res['country'],
                                    shipping_state = res['state'],
                                    shipping_city = res['city'],
                                    shipping_address = res['address'],
                                    shipping_zip = res['zip'],
                                    shipping_phone = res['phone'],
                                    shipping_mobile = res['mobile'],
                                    default = 1,

                                    # billing_country = res['country'],
                                    # billing_state = res['state'],
                                    # billing_city = res['city'],
                                    # billing_address = res['address'],
                                    # billing_zip = res['zip'],
                                    # billing_phone = res['phone'],
                                    # billing_mobile = res['mobile'],
                                )
                            address_create2 = BillingAddress.objects.create(
                                    customer_id = customer_create.id,

                                    billing_country = res['country'],
                                    billing_state = res['state'],
                                    billing_city = res['city'],
                                    billing_address = res['address'],
                                    billing_zip = res['zip'],
                                    billing_phone = res['phone'],
                                    billing_mobile = res['mobile'],
                                )

            if email_error:
                email_error = tuple(email_error)
                messages.error(request,"Email(s):"+str(email_error)+" has existed.")
                return redirect(referer_url)
            else:
                messages.success(request,"Shop keeper(s) add success.")
                return redirect(referer_url)

    return HttpResponse('1111111')

#csv导出用户
@login_required
def export_customers(request):
    data = {}
    #导出用户
    if request.POST.get('type','') == 'export_customers':
        user_id = request.POST.get('user_id','')
        account_number = request.POST.get('account_number','')
        if user_id:
            response, writer = write_csv('export_customers')
            writer.writerow(['Email','Firstname','Lastname','Discount','Admin username','Account number','Shop name','Lock','shipping_country','shipping_state','shipping_city','shipping_address','shipping_zip','shipping_phone','shipping_mobile','billing_country','billing_state','billing_city','billing_address','billing_zip','billing_phone','billing_mobile'])

            if int(user_id) == 9999:
                if account_number:
                    customers = Customer.objects.filter(account_number__istartswith=account_number).all()
                else:
                    customers = Customer.objects.all()
            else:
                if account_number:
                    customers = Customer.objects.filter(admin_id=int(user_id),account_number__istartswith=account_number).all()
                else:
                    customers = Customer.objects.filter(admin_id=int(user_id)).all()

            for customer in customers:
                lock = int(customer.locked)
                if lock == 1:
                    locked = 'Yes'
                else:
                    locked = 'No'

                #获取用户地址
                address = Address.objects.filter(customer_id=customer.id,default=1).first()
                if not address:
                    address = Address.objects.filter(customer_id=customer.id).first()
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

                billingaddress = BillingAddress.objects.filter(customer_id=customer.id).first()
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
                    billingaddress = Address.objects.filter(customer_id=customer.id,default=1).first()
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
                        billingaddress = Address.objects.filter(customer_id=customer.id).first()
                        if billingaddress:
                            baddress = billingaddress

                            billing_country = baddress.shipping_country
                            billing_state = baddress.shipping_state
                            billing_city = baddress.shipping_city
                            billing_address = baddress.shipping_address
                            billing_zip = baddress.shipping_zip
                            billing_phone = baddress.shipping_phone
                            billing_mobile = baddress.shipping_mobile


                admin_usrname = ''
                if customer.admin:
                    admin_usrname = customer.admin.username.encode('utf-8')

                row = [
                    str(customer.email.encode('utf-8')),
                    str(customer.firstname.encode('utf-8')),
                    str(customer.lastname.encode('utf-8')),
                    str(customer.discount),
                    str(admin_usrname),
                    str(customer.account_number.encode('utf-8')),
                    str(customer.shop_name.encode('utf-8')),
                    str(locked),
                    str(shipping_country),
                    str(shipping_state),
                    str(shipping_city),
                    str(shipping_address),
                    str(shipping_zip),
                    str(shipping_phone),
                    str(shipping_mobile),
                    str(billing_country),
                    str(billing_state),
                    str(billing_city),
                    str(billing_address),
                    str(billing_zip),
                    str(billing_phone),
                    str(billing_mobile),
                ]
                writer.writerow(row)
            return response
        else:
            messages.error(request, u"Please chose Admin.")
            return redirect('export_customers')
    #默认打开页面
    else:
        super_user = 0
        if request.user.is_superuser:
            users = User.objects.all()
            super_user = 1
        else:
            current_group_set = ''
            if request.user.is_authenticated():
                current_user_set = request.user
                try:
                    current_group_set = Group.objects.get(user=current_user_set)
                except Exception as e:
                    current_group_set = ''

            if str(current_group_set) == 'Super manager':
                users = User.objects.all()
                super_user = 1
            else:
                user_id = request.user.id
                users = User.objects.filter(id=user_id)

        data['users'] = users
        data['super_user'] = super_user

    data['title'] = ''
    return render(request, 'export_customer.html', data)


#订单详情页产品报却发送邮件
@login_required
def send_orderitem_shortage_mail(request):
    data = {}
    if request.method == 'POST':
        order_id = request.POST['order_id']
        customer_email = request.POST['customer_email']
        item_list = request.POST['item_list']
        item_list = demjson.decode(item_list)

        item_ids = []
        for item in item_list:
            if item != None:
                item_ids.append(item)

        item_ids = tuple(item_ids)

        customer = Customer.objects.filter(email=customer_email).first()
        if not customer:
            data['result'] = u'shop keeper email does not existed.'
            data = demjson.encode(data)
            return HttpResponse(data, content_type='application/json')

        orderitems = OrderItem.objects.filter(id__in=item_ids).all()
        if not orderitems:
            data['result'] = u'product(s) does not existed.'
            data = demjson.encode(data)
            return HttpResponse(data, content_type='application/json')

        order = Order.objects.filter(id=order_id).first()
        if not order:
            data['result'] = u'order does not existed.'
            data = demjson.encode(data)
            return HttpResponse(data, content_type='application/json')


        from_email = settings.DEFAULT_FROM_EMAIL
        to_email = customer_email
        # to_email = '2546763702@qq.com'

        # cc_email = '424063857@qq.com'

        subject = 'RIVE – B2B UPDATE'

        title = 'RIVE – B2B UPDATE'

        text_content = 'test test test test test test test test test test test test'

        html_content = loader.render_to_string(
                            'shortage-mail.html',              #需要渲染的html模板
                            {
                                'title' : title,
                                'orderitems'  : orderitems,   #参数
                                'ordernum' : order.ordernum,
                                'customer_name' : customer.firstname+customer.lastname,
                            }
                       )

        try:
            msg = EmailMultiAlternatives(subject, html_content, from_email, [to_email])
            msg.content_subtype = "html"
            msg.send()
        except Exception as e:
            data['result'] = u'send mail failed.'
            data = demjson.encode(data)
            return HttpResponse(data, content_type='application/json')
        #shortage email to salesmen
        if customer.admin:
            email = {}
            email['receiver'] = [customer.admin.email]
            template = 'email_shortage_salesmen.html'
            sendData = {}
            sendData['title'] = 'RIVE – B2B ORDER SHORTAGE'
            sendData['rive_account_number'] = customer.account_number
            sendData['salesman_name'] = customer.admin.username
            sendData['firstname'] = customer.firstname
            sendData['orderitems'] = orderitems
            sendData['order_number'] = order.ordernum
            thread.start_new_thread(sendEmail, (email, template, sendData))

        #邮件发送成功，把结果记录到订单历史中
        operation_type = 'Send Shortage email'
        admin_id = request.user.id

        skus = []
        for orderitem in orderitems:
            skus.append(orderitem.sku)
        
        skuarr = ''
        for sku in skus:
            skuarr += sku+' ; '
        operation_content = 'Product(s): '+str(skuarr)

        query_create = OrderHistory.objects.create(order_id=order.id,admin_id=admin_id,operation_type=operation_type,operation_content=operation_content)


        data['result'] = u'send mail success.'
        data = demjson.encode(data)
        return HttpResponse(data, content_type='application/json')

    return HttpResponse('11111111')
    # return redirect(referer_url)


@login_required
def send_orderitem_shortage_mail_test(request):
    data = {}
    order_id = 141
    customer_email = '2546763702@qq.com'
    order = Order.objects.filter(id=order_id).first()
    orderitems = OrderItem.objects.filter(id__in=(268,267)).all()
    customer = Customer.objects.filter(email=customer_email).first()

    from_email = settings.DEFAULT_FROM_EMAIL
    to_email = customer_email
    # to_email = '2546763702@qq.com'

    # cc_email = '424063857@qq.com'

    subject = 'RIVE – B2B ORDER SHORTAGE'

    title = 'RIVE – B2B ORDER SHORTAGE'

    admin_id = request.user.id
    admin_email = request.user.email
    admin_username = request.user.username

    data['title'] = title
    data['admin_username'] = admin_username
    data['orderitems'] = orderitems
    data['ordernum'] = order.ordernum
    data['account_number'] = customer.account_number
    data['firstname'] = customer.firstname

    return render(request, 'shortage-mail-to-salesmen.html', data)


@login_required
def mail_ajax_test(request):
    data = {}
    if request.method == 'POST':
        print 1111111111111111111

    return HttpResponse('11111')


#用户所属库存组判断公用方法
def get_stock_group(customer_id):
    customer = Customer.objects.filter(id=customer_id).first()
    stock_group = 0
    if customer:
        try:
            account_number = customer.account_number
            if account_number[0:3] == "CNL":
                stock_group = 1
            else:
                stock_group = 0
        except Exception as e:
            stock_group = 0

    return stock_group


def time_str2s(timestamp):
    try:
        t = int(timestamp)
        t = time.localtime(t)
        t = time.strftime("%Y-%m-%d",t)
    except Exception,e:
        print e
    return t

#获取库存状态为2的发货日期
def get_est_date():
    now = int(time.time())
    est_date = now + 14*86400
    est_date = time_str2s(est_date)
    return est_date

#自定义前后台404页面
def page_not_found(request):
    path = request.path
    if path.startswith('/admin/'):
        return render_to_response('admin/404.html')
    else:
        return render_to_response('404.html')

#自定义前后台500页面
def page_error(request):
    path = request.path
    if path.startswith('/admin/'):
        return render_to_response('admin/500.html')
    else:
        return render_to_response('500.html')



#前台个人中心shipping address地址 增 删 改 页面
def customer_address(request):
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

    data['customer'] = customer

    #查询当前用户购物车产品
    data['number'] = order_list_count(request,customer.id)


    #获取用户地址信息
    shipping_addresses = {}
    default_address = {}
    addresses = Address.objects.filter(customer_id=customer.id).all()
    for address in addresses:
        default_address[int(address.id)] = address.default
        shipping_addresses[int(address.id)] = customer.firstname +', '+ address.shipping_phone +', '+ address.shipping_mobile +' '+ address.shipping_address +' '+ address.shipping_city +', '+ address.shipping_zip +' '+ address.shipping_state +', '+ address.shipping_country

    #最后一个地址不允许删除
    print addresses.count()
    data['address_count'] = addresses.count()

    data['shipping_addresses'] = shipping_addresses
    data['default_address'] = default_address

    # billing_address = ''

    # baddress = BillingAddress.objects.filter(customer_id=customer.id).first()
    # if baddress:
    #     billing_address = customer.firstname +', '+ baddress.billing_phone +', '+baddress.billing_mobile+' '+ baddress.billing_address +' '+ baddress.billing_city +', '+ baddress.billing_zip +' '+ baddress.billing_state +', '+ baddress.billing_country
    # else:
    #     baddress = Address.objects.filter(customer_id=customer.id,default=1).first()
    #     if baddress:
    #         billing_address = customer.firstname +', '+ baddress.shipping_phone +', '+ baddress.shipping_mobile +' '+ baddress.shipping_address +' '+ baddress.shipping_city +', '+ baddress.shipping_zip +' '+ baddress.shipping_state +', '+ baddress.shipping_country
    #     else:
    #         baddress = Address.objects.filter(customer_id=customer.id).first()
    #         if baddress:
    #             billing_address = customer.firstname +', '+ baddress.shipping_phone +', '+ baddress.shipping_mobile +' '+ baddress.shipping_address +' '+ baddress.shipping_city +', '+ baddress.shipping_zip +' '+ baddress.shipping_state +', '+ baddress.shipping_country

    # data['billing_address'] = billing_address

    return render(request, 'shippingaddress.html', data)


#前台个人中心shipping address 增 改 数据操作
def customer_address_handle(request):

    data = {}

    if request.method == 'POST':
        if request.POST['type'] == 'customer_address_add':
            customer_id = request.POST['customer_id']

            country = request.POST['country']
            state = request.POST['state']
            city = request.POST['city']
            address = request.POST['address']
            czip = request.POST['czip']
            phone = request.POST['phone']
            mobile = request.POST['mobile']

            #如果都为空，则不新增
            if country == state == city == address == czip == phone == mobile == '':
                return redirect('customer_address')
            #新增地址
            address_create = Address.objects.create(
                    customer_id = customer_id,
                    shipping_country = country,
                    shipping_state = state,
                    shipping_city = city,
                    shipping_address = address,
                    shipping_zip = czip,
                    shipping_phone = phone,
                    shipping_mobile = mobile,
                    default = 0,
                )
            #新增成功，直接返回刷新该页面
            return redirect('customer_address')

        if request.POST['type'] == 'customer_address_edit':
            address_id = request.POST['address_id']

            country = request.POST['country']
            state = request.POST['state']
            city = request.POST['city']
            address = request.POST['address']
            czip = request.POST['czip']
            phone = request.POST['phone']
            mobile = request.POST['mobile']
            #如果都为空，则不更新
            if country == state == city == address == czip == phone == mobile == '':
                return redirect('customer_address')
            #更新地址
            address_create = Address.objects.filter(id=address_id).update(
                    shipping_country = country,
                    shipping_state = state,
                    shipping_city = city,
                    shipping_address = address,
                    shipping_zip = czip,
                    shipping_phone = phone,
                    shipping_mobile = mobile,
                )
            #更新成功，直接返回刷新该页面
            return redirect('customer_address')


    return redirect('customer_address')


#前台个人中心shipping address 删除 数据操作
def customer_address_delete(request, address_id):
    data = {}

    try:
        address_delete = Address.objects.filter(id=address_id).delete()
    except Exception as e:
        print e

    return redirect('customer_address')


#前台个人中心shipping address 设置为默认 数据操作
def customer_address_setdefault(request, address_id,customer_id):
    data = {}

    try:
        address_update1 = Address.objects.filter(customer_id=customer_id).update(default=0)
        address_update2 = Address.objects.filter(id=address_id).update(default=1)
        
    except Exception as e:
        print e

    return redirect('customer_address')


#前台个人中心billing address地址 增 改 页面
def billing_address(request):
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

    data['customer'] = customer

    #查询当前用户购物车产品
    data['number'] = order_list_count(request,customer.id)

    address = BillingAddress.objects.filter(customer_id=customer.id).first()

    data['address'] = address

    return render(request, 'billingaddress.html', data)


#前台个人中心billing address地址 增 改 数据操作
def billing_address_handle(request):
    data = {}

    if request.method == 'POST':
        if request.POST['type'] == 'billing_address_handle':
            customer_id = request.POST['customer_id']

            country = request.POST['country']
            state = request.POST['state']
            city = request.POST['city']
            address = request.POST['address']
            czip = request.POST['czip']
            phone = request.POST['phone']
            mobile = request.POST['mobile']

            #如果都为空，则删除该条数据
            if country == state == city == address == czip == phone == mobile == '':
                BillingAddress.objects.filter(customer_id=customer_id).delete()
            else:
                baddress = BillingAddress.objects.filter(customer_id=customer_id).first()

                if baddress:
                    BillingAddress.objects.filter(customer_id=customer_id).update(
                            billing_country = country,
                            billing_state = state,
                            billing_city = city,
                            billing_address = address,
                            billing_zip = czip,
                            billing_phone = phone,
                            billing_mobile = mobile,
                        )
                else:
                    #新增地址
                    BillingAddress.objects.create(
                            customer_id = customer_id,
                            billing_country = country,
                            billing_state = state,
                            billing_city = city,
                            billing_address = address,
                            billing_zip = czip,
                            billing_phone = phone,
                            billing_mobile = mobile,
                        )

                return redirect('billing_address')

    return redirect('billing_address')


#update_basic_shopkeepers
@login_required
def update_basic_shopkeepers(request):
    data = {}
    #获取上一个页面url，数据处理之后跳转回该页面
    referer_url = request.META['HTTP_REFERER']

    if request.method == 'POST':
        if request.POST['type'] == 'update_basic_shopkeepers':

            #获取文件对象
            file_obj = request.FILES.get('update_basic_shopkeepers_file', None)

            if file_obj == None:
                messages.error(request, u'Please upload a valid CSV file.')
                return redirect(referer_url)

            #文件内容
            file_content = file_obj.read()

            #格式转化
            try:
                reader = csv.reader(StringIO.StringIO(file_content),delimiter=str(';'))
                header = next(reader)
            except Exception as e:
                messages.error(request, u'Please upload a valid CSV file.')
                return redirect(referer_url)

            std_header = [
                'Email','Firstname','Lastname','Discount','Lock','Admin_email','Account_number','Shop_name'
            ]
            field_header = [
                'email','firstname','lastname','discount','locked','admin_id','account_number','shop_name'
            ]

            #由于bom头的问题, 就不比较第一列的header了
            if header[1:] != std_header[1:]:
                messages.error(request,"Please use the correct template and save as UTF-8 format.")
                return redirect(referer_url)

            #用于保存不存在的用户email
            email_error = []

            #获取csv表格每一行的值，i为行数，row该行对应的列的值
            for i, row in enumerate(reader,2):
                #将上传的每一行的值与该行的标题一一对应
                res = zip(field_header,row)
                #转为为字典，方便后面取值
                res = dict(res)

                if res['email']:
                    res['email'] = res['email'].strip().decode('gbk').encode('utf-8')
                    res['firstname'] = res['firstname'].strip().decode('gbk').encode('utf-8')
                    res['lastname'] = res['lastname'].strip().decode('gbk').encode('utf-8')
                    res['admin_id'] = res['admin_id'].strip().decode('gbk').encode('utf-8')
                    res['account_number'] = res['account_number'].strip().decode('gbk').encode('utf-8')
                    res['shop_name'] = res['shop_name'].strip().decode('gbk').encode('utf-8')

                    #去除字典里面的空值
                    res2 = {}
                    for key, value in res.items():
                        if value:
                            res2[key] = value

                    if res2['email']:
                        customer = Customer.objects.filter(email=res2['email']).first()
                        if customer:
                            
                            sql = ""
                            for key, value in res2.items():
                                #折扣
                                if key == 'discount':
                                    try:
                                        value = round(float(value),2)
                                    except Exception as e:
                                        value = 1.0
                                    if value<=0 or value>1.0:
                                        value = 1.0

                                #locked
                                if key == 'locked':
                                    try:
                                        value = int(value)
                                    except Exception as e:
                                        value = 0
                                    if value != 0 and value != 1:
                                        value = 0

                                #admin
                                if key == 'admin_id':
                                    user = User.objects.filter(email=value).first()
                                    if user:
                                        value = user.id
                                    else:
                                        value = ''

                                #更新字段拼接
                                sql += key + " = '" + str(value) + "',"

                            #去掉最后一个','
                            sql = sql.strip(',')

                            sql_update = "UPDATE accounts_customer SET " + sql + "  WHERE id=" + str(customer.id)

                            try:
                                cursor = connection.cursor()
                                cursor.execute(sql_update)
                            except Exception as e:
                                print e

                        else:
                            email_error.append(res2['email'])

            if email_error:
                email_error = tuple(email_error)
                messages.error(request,"Email(s):"+str(email_error)+" has not existed.")
                return redirect(referer_url)
            else:
                messages.success(request,"Shop keeper(s) update success.")
                return redirect(referer_url)

    return redirect(referer_url)
