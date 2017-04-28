#-*- coding:utf-8 -*-
from __future__ import unicode_literals
from django.db import models
from django.contrib.auth.models import User
import hashlib,time
from django.contrib.auth.hashers import make_password, check_password
from django_unixdatetimefield import UnixDateTimeField
from django.utils.translation import ugettext_lazy as _
from library.views import sendEmail
from django.conf import settings
import thread 


class Customer(models.Model):

    LOCK = (
        (1,u'Yes'),
        (0,u'No'),
    )

    email = models.EmailField(default='',unique=True,verbose_name=_("Email"))
    password = models.CharField(max_length=100, default='',verbose_name=_("Password"))
    firstname = models.CharField(max_length=100, default='',blank=True,null=True,verbose_name=_("Firstname"))
    lastname = models.CharField(max_length=100, default='',blank=True,null=True,verbose_name=_("Lastname"))
    discount = models.FloatField(default=1.0,blank=True,null=True, verbose_name=_("discount"))
    #第一次登录需要修改密码的判断字段
    is_lock = models.IntegerField(default=1,blank=True,null=True,verbose_name="Is_lock ?")
    #后台锁定账号字段
    locked = models.IntegerField(choices=LOCK,default=0, verbose_name="Lock ?")
    admin = models.ForeignKey(User,default='',blank=True, null=True, verbose_name=_('Admin'))
    account_number = models.CharField(max_length=200,default='',blank=True,null=True,verbose_name="Account number")
    shop_name = models.CharField(max_length=200,default='',blank=True,null=True,verbose_name="Shop name")
    created = UnixDateTimeField(auto_now_add=True, blank=True, null=True, verbose_name=_("Create"))
    updated = UnixDateTimeField(auto_now=True,blank=True,null=True, verbose_name=_("Update"))
    emailed = models.BooleanField(default=False)

    class Meta:
        verbose_name = _('Shop keepers')
        verbose_name_plural = _('Shop keepers')

    def __unicode__(self):
        return self.email

    def save(self, *args, **kwargs):
        super(Customer, self).save(*args, **kwargs)

    #对用户密码保存及加密操作
    def encrypt_password(self,request):
        #新增用户时添加密码
        password = request.POST.get('password','')
        if password:
            password = make_password(password, 'a', 'pbkdf2_sha256')
            customer = Customer.objects.filter(id=self.id).update(password=password)
        #修改密码
        change_password = request.POST.get('change_password','')
        if change_password:
            change_password = make_password(change_password, 'a', 'pbkdf2_sha256')
            customer = Customer.objects.filter(id=self.id).update(password=change_password,is_lock=1)

    #折扣保存
    def discount_save(self, request):
        customer_discount = request.POST.get('customer_discount')
        customer_discount = round(float(customer_discount),2)
        if customer_discount:
            if customer_discount > 0 and customer_discount <= 1:
                if customer_discount != self.discount:
                    self.discount = customer_discount
                    self.save()

    #新建用户发送邮件
    #通过创建时间来判断是否是新用户
    def sendNewAccountsEmail(self,request):
        customer = Customer.objects.filter(id=self.id).first()
        if not customer.emailed:
            # 给管理员发邮件
            userEmails = settings.USEREMIAL1
            address = Address.objects.filter(customer_id=self.id).first()
            if address:
                n = 0
                for user in userEmails:
                    email = {}
                    email['receiver'] = [userEmails[user]]
                    template = 'email_new_shopkeeper.html'
                    sendData = {}
                    sendData['title'] = 'RIVE – B2B new shopkeeper'
                    sendData['shop_name'] = self.shop_name
                    sendData['rive_account_number'] = self.account_number
                    sendData['first_name'] = self.firstname
                    sendData['last_name'] = self.lastname
                    sendData['phone'] = address.shipping_phone
                    sendData['email'] = self.email
                    sendData['address'] = address.shipping_address
                    sendData['state'] = address.shipping_state
                    sendData['zip'] = address.shipping_zip
                    sendData['city'] = address.shipping_city
                    sendData['country'] = address.shipping_country
                    # res = sendEmail(email, template, sendData)
                    try:
                        thread.start_new_thread(sendEmail, (email,template,sendData))
                    except Exception:
                        pass
                    else:
                        n = 1
                if n:
                    self.emailed = True
                    self.save()



class Address(models.Model):

    DEFAULT = (
        (1,u'Yes'),
        (0,u'No'),
    )
    customer = models.ForeignKey(Customer,blank=True,null=True)

    shipping_country = models.CharField(max_length=100, default='', blank=True, null=True, verbose_name=_('Shipping Country'))
    shipping_state = models.CharField(max_length=200, default='', blank=True, null=True, verbose_name=_('Shipping State/Province'))
    shipping_city = models.CharField(max_length=200, default='', blank=True, null=True, verbose_name=_('Shipping City'))
    shipping_address = models.CharField(max_length=500, default='',blank=True, null=True, verbose_name=_('Shipping Address'))
    shipping_zip = models.CharField(max_length=100, default='', blank=True, null=True, verbose_name=_('Shipping Zip/Postal code'))
    shipping_phone = models.CharField(max_length=100, default='', blank=True, null=True, verbose_name=_('Shipping Home Phone'))
    shipping_mobile = models.CharField(max_length=100, default='', blank=True, null=True, verbose_name=_('Mobile'))


    # billing_country = models.CharField(max_length=100, default='', blank=True, null=True, verbose_name=_('Billing Country'))
    # billing_state = models.CharField(max_length=200, default='', blank=True, null=True, verbose_name=_('Billing State/Province'))
    # billing_city = models.CharField(max_length=200, default='', blank=True, null=True, verbose_name=_('Billing City'))
    # billing_address = models.CharField(max_length=500, default='', blank=True, null=True, verbose_name=_('Billing Address' ))
    # billing_zip = models.CharField(max_length=100, default='', blank=True, null=True, verbose_name=_('Billing Zip/Postal code'))
    # billing_phone = models.CharField(max_length=100, default='', blank=True, null=True, verbose_name=_('Billing Home Phone' ))
    # billing_mobile = models.CharField(max_length=100, default='', blank=True, null=True, verbose_name=_('Billing Mobile'))

    default = models.BooleanField(default=True, blank=True,verbose_name="Set default")

    created = UnixDateTimeField(auto_now_add=True, blank=True, null=True, verbose_name=_("Create"))
    updated = UnixDateTimeField(auto_now=True,blank=True,null=True, verbose_name=_("Update"))

    class Meta:
        verbose_name = _('Shipping Address')
        verbose_name_plural = _('Shipping Address')

    def __unicode__(self):
        return str('')

    def get_billing_address(self):
        if not self.billing_country:
            self.billing_country = self.shipping_country

        if not self.billing_state:
            self.billing_state = self.shipping_state

        if not self.billing_city:
            self.billing_city = self.shipping_city

        if not self.billing_address:
            self.billing_address = self.shipping_address

        if not self.billing_zip:
            self.billing_zip = self.shipping_zip

        if not self.billing_phone:
            self.billing_phone = self.shipping_phone

        if not self.billing_mobile:
            self.billing_mobile = self.shipping_mobile

        query_update = Address.objects.filter(id=self.id).update(
                billing_country=self.billing_country,
                billing_state=self.billing_state,
                billing_city=self.billing_city,
                billing_address=self.billing_address,
                billing_zip=self.billing_zip,
                billing_phone=self.billing_phone,
                billing_mobile=self.billing_mobile
            )


class BillingAddress(models.Model):

    customer = models.ForeignKey(Customer,default='')

    billing_country = models.CharField(max_length=100, default='', blank=True, null=True, verbose_name=_('Billing Country'))
    billing_state = models.CharField(max_length=200, default='', blank=True, null=True, verbose_name=_('Billing State/Province'))
    billing_city = models.CharField(max_length=200, default='', blank=True, null=True, verbose_name=_('Billing City'))
    billing_address = models.CharField(max_length=500, default='', blank=True, null=True, verbose_name=_('Billing Address' ))
    billing_zip = models.CharField(max_length=100, default='', blank=True, null=True, verbose_name=_('Billing Zip/Postal code'))
    billing_phone = models.CharField(max_length=100, default='', blank=True, null=True, verbose_name=_('Billing Home Phone' ))
    billing_mobile = models.CharField(max_length=100, default='', blank=True, null=True, verbose_name=_('Billing Mobile'))


    created = UnixDateTimeField(auto_now_add=True, blank=True, null=True, verbose_name=_("Create"))
    updated = UnixDateTimeField(auto_now=True,blank=True,null=True, verbose_name=_("Update"))

    class Meta:
        verbose_name = _('Billing Address')
        verbose_name_plural = _('Billing Address')

    def __unicode__(self):
        return str('')


class Currency(models.Model):
    name = models.CharField(max_length=50, verbose_name=_("Name"))
    code = models.CharField(max_length=50, verbose_name=_("Code"))
    rate = models.DecimalField(max_digits=12, decimal_places=4, verbose_name=_("Rate"))
    created = UnixDateTimeField(auto_now_add=True, blank=True, null=True, verbose_name=_("Create"))
    updated = UnixDateTimeField(auto_now=True,blank=True,null=True, verbose_name=_("Update"))

    class Meta:
        verbose_name = _('Currency')
        verbose_name_plural = _('Currency')

    def __unicode__(self):
        return str(self.name)