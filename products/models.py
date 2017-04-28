#-*- coding: utf-8 -*-
from __future__ import unicode_literals
from django.db import models
import os
from accounts.models import Customer, Currency
from django_unixdatetimefield import UnixDateTimeField


def get_product_image_upload_path(instance, filename):
    fn, ext = os.path.splitext(filename)
    if not ext:
        ext = '.jpg'
    name = str(fn)
    return os.path.join('pimg', name+ext)

class Catalog(models.Model):

    VISIBILITY = (
            (1,"visible"),
            (0,u"invisible"),
        )

    name = models.CharField(max_length=250,unique=True,verbose_name="Name")
    parent = models.ForeignKey("self",default='', blank=True, null=True,related_name="children", verbose_name="Parent catalog")
    discount = models.FloatField(default=1.0,blank=True,null=True, verbose_name=u"discount",help_text='From 0 to 1.0')
    description = models.TextField(default='',blank=True,null=True,verbose_name="Description")
    created = UnixDateTimeField(auto_now_add=True, blank=True, null=True, verbose_name=u"Create")
    updated = UnixDateTimeField(auto_now=True,blank=True,null=True, verbose_name=u"Update")
    visibility = models.IntegerField(choices=VISIBILITY, default=1, verbose_name=u"Visibility")

    class Meta:
        verbose_name = 'Category  '
        verbose_name_plural = 'Categories'

    def __unicode__(self):
        return self.name

    #折扣保存
    def discount_save(self, request):
        catalog_discount = request.POST.get('catalog_discount')
        catalog_discount = round(float(catalog_discount),2)
        if catalog_discount:
            if catalog_discount > 0 and catalog_discount <= 1:
                if catalog_discount != self.discount:
                    self.discount = catalog_discount
                    self.save()
        

class Product(models.Model):

    IS_NET_PRICE = (
            (1,'Yes'),
            (0,'No'),
        )

    STOCK = (
            (1,'In stock'),
            (2,'In stock(est)'),
            (0,'Limited or Out of stock'),
        )

    VISIBILITY = (
            (1,"visible"),
            (0,u"invisible"),
        )

    MARK = (
            (1,'Yes'),
            (0,'No'),
        )

    catalog = models.ForeignKey(Catalog, default='', blank=True,null=True,verbose_name='Category')
    name = models.CharField(max_length=250,verbose_name="Name")
    sku = models.CharField(max_length=100,unique=True,verbose_name="Ref")
    # stock = models.IntegerField(choices=STOCK,default=1,verbose_name="Stock")
    description = models.TextField(default='',blank=True,null=True,verbose_name="Description-en")
    price = models.DecimalField(max_digits=16,default=0.0,decimal_places=2,blank=True,null=True,verbose_name="Price")
    ssp = models.DecimalField(max_digits=16, default=0.0, decimal_places=2, blank=True, null=True, verbose_name="SSP")
    rrp = models.DecimalField(max_digits=16, default=0.0, decimal_places=2, blank=True, null=True, verbose_name="RRP")
    is_net_price = models.IntegerField(choices=IS_NET_PRICE,default=0,verbose_name="Is net price ?")
    created = UnixDateTimeField(auto_now_add=True, blank=True, null=True, verbose_name=u"Create")
    updated = UnixDateTimeField(auto_now=True,blank=True,null=True, verbose_name=u"Update")
    expected_time = UnixDateTimeField(blank=True,null=True, verbose_name=u"Expected in-stock time")
    visibility = models.IntegerField(choices=VISIBILITY, default=1, verbose_name=u"Visibility")
    # stock2 = models.IntegerField(choices=STOCK,default=1,verbose_name="CNL-Stock")
    qty = models.IntegerField(default=0,verbose_name="Public-qty")
    qty2 = models.IntegerField(default=0,verbose_name="CNL-qty")
    mark = models.IntegerField(choices=MARK,default=1,verbose_name="Special Mark")
    description_fr = models.TextField(default='',blank=True,null=True,verbose_name="Description-fr")
    description_de = models.TextField(default='',blank=True,null=True,verbose_name="Description-de")
    description_nl = models.TextField(default='',blank=True,null=True,verbose_name="Description-nl")
    
    class Meta:
        verbose_name = "Product"
        verbose_name_plural = "Products"

    def __unicode__(self):
        return self.sku


    #获取 用户--产品 对应价格公共方法
    def final_price(self,customer_id,currency):
        #获取货币汇率
        rate = 1.00
        currencys = Currency.objects.filter(name=currency).first()
        if currencys:
            rate = currencys.rate

        #判断产品是否是净价
        is_net_price = self.is_net_price
        if is_net_price:
            price = self.price
        else:
            catalog_discount = 1.0
            if self.catalog:
                catalog_discount = self.catalog.discount

            customer = Customer.objects.filter(id=customer_id).first()
            if customer:
                customer_discount = customer.discount
                price = float(self.price)*customer_discount*catalog_discount
            else:
                price = float(self.price)*catalog_discount

        #最终价格汇率转换
        #英镑四舍五入取整
        if currency == 'GBP':
            price = float(price)/float(rate)
            price = round(price)
            price = round(price,2)
        else:
            price = float(price)/float(rate)
            price = round(price,2)
        #价格小数部分如果是0也保留两位
        price = '%.2f' % price
        return price

    # 获取 用户--产品 对应价格公共方法
    def final_ssp_rrp(self, price, currency):
        # 获取货币汇率
        rate = 1.00
        currencys = Currency.objects.filter(name=currency).first()
        if currencys:
            rate = currencys.rate

        # 最终价格汇率转换
        # 英镑四舍五入取整
        if currency == 'GBP':
            price = float(price) / float(rate)
            price = round(price)
            price = round(price, 2)
        else:
            price = float(price) / float(rate)
            price = round(price, 2)
        # 价格小数部分如果是0也保留两位
        price = '%.2f' % price
        return price


    #获取 用户--产品 对应库存状态公共方法（结果返回三种状态 0:out-of-stock;1:in-stock;2:in-stock 14days later）
    def get_stock_type(self,stock_group):
        stock_type = 0
        #用户分组stock_group 0:公共组 1:荷兰组
        #获取用户分组对应的产品库存数量
        #荷兰组
        if int(stock_group) == 1:
            #先读荷兰组的库存
            quantity = self.qty2
            #荷兰组有库存，直接返回in-stock状态
            if quantity > 0:
                stock_type = 1
                return stock_type
            #荷兰组没有库存
            else:
                #读取公共组的库存
                quantity = self.qty
                #公共组有库存，直接返回in-stock状态
                if quantity > 0:
                    stock_type = 1
                    return stock_type
                #公共组也没有库存，则查看产品mark标记，Yes:返回2: in-stock 14days later; No:返回0: out-of-stock
                else:
                    mark = self.mark
                    if mark == 1:
                        stock_type = 2
                        return stock_type
                    else:
                        stock_type = 0
                        return stock_type
        #公共组
        else:
            #直接读取公共组库存数量
            quantity = self.qty
            #公共组有库存，直接返回in-stock状态
            if quantity > 0:
                stock_type = 1
                return stock_type
            #公共组没有库存，则查看产品mark标记，Yes:返回2: in-stock 14days later; No:返回0: out-of-stock
            else:
                mark = self.mark
                if mark == 1:
                    stock_type = 2
                    return stock_type
                else:
                    stock_type = 0
                    return stock_type


        return stock_type


    #获取 用户下单时候的产品数量对应库存状态公共方法（结果返回三种状态： H  B  A）
    def get_product_mark(self,stock_group,num):
        mark = 'A'
        num = int(num)
        #荷兰组
        if int(stock_group) == 1:
            #先读荷兰组的库存
            quantity = self.qty2
            #荷兰组满足当前需要库存，直接返回
            if quantity >= num:
                mark = 'H'
                return mark
            #荷兰组库存不满足
            else:
                #读取两个库存之和
                quantity = self.qty + self.qty2
                #满足，直接返回
                if quantity >= num:
                    mark = 'B'
                    return mark
                #库存之和都不满足
                else:
                    mark = 'A'
                    return mark
        
        #非荷兰组用户，直接返回
        return mark





class ProductImage(models.Model):
    product = models.ForeignKey(Product)
    title = models.CharField(max_length=200,default='',blank=True,null=True,verbose_name='Title')
    image = models.ImageField(upload_to=get_product_image_upload_path,verbose_name="Image")
    created = UnixDateTimeField(auto_now_add=True, blank=True, null=True, verbose_name=u"Create")
    updated = UnixDateTimeField(auto_now=True,blank=True,null=True, verbose_name=u"Update")

    class Meta:
        verbose_name = 'ProductImage'
        verbose_name_plural = 'ProductImages'

    def __unicode__(self):
        return str('')