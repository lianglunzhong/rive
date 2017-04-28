#-*- coding: utf-8 -*-
from __future__ import unicode_literals
from django.db import models
from accounts.models import *
from products.models import *
from django_unixdatetimefield import UnixDateTimeField
from library.views import sendEmail
from django.conf import settings
import thread 


class Order(models.Model):
    STATUS = (
            (0,u'new'),
            (1,u'processing'),
            (2,u'partical shipped'),
            (3,u'shipped'),
            (4,u'cancel'),
        )
    ordernum = models.CharField(max_length=100, default='', blank=True , null=True, verbose_name=u"Ordernum")
    erp_num = models.CharField(max_length=100, default='', blank=True , null=True, verbose_name=u"ERP_ordernum")
    status = models.IntegerField(choices=STATUS,default=0,blank=True,null=True,verbose_name="Order Status")
    customer = models.ForeignKey(Customer,default='', blank=True , null=True,verbose_name=u"Customer")
    accountnumber = models.CharField(max_length=200,default='',blank=True,null=True,verbose_name="Account number")
    address = models.ForeignKey(Address,default='', blank=True , null=True,verbose_name=u"Address")
    message = models.TextField(default='', blank=True , null=True, verbose_name=u"Comment")
    imgorder = models.CharField(max_length=200, default='', blank=True , null=True, verbose_name=u"Imgorder")
    amount = models.DecimalField(max_digits=16,default=0.0,decimal_places=2,blank=True,null=True,verbose_name="Amount")
    currency = models.CharField(max_length=100,default='',blank=True,null=True,verbose_name="Currency")
    created = UnixDateTimeField(auto_now_add=True, blank=True, null=True, verbose_name=u"Create")
    updated = UnixDateTimeField(auto_now=True,blank=True,null=True, verbose_name=u"Update")
    expcted_shipping = UnixDateTimeField(blank=True,null=True, verbose_name=u"Expcted shipping date")
    # expcted_shipping = models.IntegerField(blank=True,null=True, verbose_name=u"Expcted shipping date")
    verifued = UnixDateTimeField(blank=True,null=True, verbose_name=u"Verified Time")
    mark = models.CharField(max_length=100, default='', blank=True , null=True, verbose_name=u"Stock-Mark")

    shipping_country = models.CharField(max_length=100, default='', blank=True, null=True, verbose_name='Shipping Country')
    shipping_state = models.CharField(max_length=200, default='', blank=True, null=True, verbose_name='Shipping State/Province')
    shipping_city = models.CharField(max_length=200, default='', blank=True, null=True, verbose_name='Shipping City')
    shipping_address = models.CharField(max_length=500, default='',blank=True, null=True, verbose_name='Shipping Address')
    shipping_zip = models.CharField(max_length=100, default='', blank=True, null=True, verbose_name='Shipping Zip/Postal code')
    shipping_phone = models.CharField(max_length=100, default='', blank=True, null=True, verbose_name='Shipping Home Phone')
    shipping_mobile = models.CharField(max_length=100, default='', blank=True, null=True, verbose_name='Mobile')

    billing_country = models.CharField(max_length=100, default='', blank=True, null=True, verbose_name='Billing Country')
    billing_state = models.CharField(max_length=200, default='', blank=True, null=True, verbose_name='Billing State/Province')
    billing_city = models.CharField(max_length=200, default='', blank=True, null=True, verbose_name='Billing City')
    billing_address = models.CharField(max_length=500, default='', blank=True, null=True, verbose_name='Billing Address' )
    billing_zip = models.CharField(max_length=100, default='', blank=True, null=True, verbose_name='Billing Zip/Postal code')
    billing_phone = models.CharField(max_length=100, default='', blank=True, null=True, verbose_name='Billing Home Phone' )
    billing_mobile = models.CharField(max_length=100, default='', blank=True, null=True, verbose_name='Billing Mobile')

    class Meta:
        verbose_name = 'Order'
        verbose_name_plural = 'Orders'

    def __unicode__(self):
        return self.ordernum

    #根据当前选择的customer自动更新address
    def get_address(self):
        if self.customer:
            customer_id = self.customer.id
            if customer_id:
                address = Address.objects.filter(customer_id=customer_id).first()
                #更新当前订单的address
                if address:
                    order = Order.objects.filter(ordernum=self.ordernum).update(address=address.id)
        else:
            order = Order.objects.filter(ordernum=self.ordernum).update(address='')

    def change_price_save(self, request):
        #获取价格
        price = request.POST.get('change_price','')
        # if price:
        #   orderitem = OrderItem.objects.filter(order_id=self.id)

    #根据当前产品价格及数量自动更新订单总价
    def get_order_amount(self,request):
        orderitems = OrderItem.objects.filter(order_id=self.id)
        amount = 0.0
        for product in orderitems:
            amount += float(product.price) * product.quantity

        amount = round(amount,2)
        self.amount = amount
        self.save()

    #添加包裹产品保存
    def package_products_save(self,request):
        order_id = self.id
        #包裹
        packages = Package.objects.filter(order_id=order_id).all()
        if request.method == 'POST':
            for package in packages:
                skuname = str(package.id)+'sku[]'
                qtyname = str(package.id)+'qty[]'
                sku = request.POST.getlist(skuname)
                qty = request.POST.getlist(qtyname)
                products = zip(sku, qty)
                products = dict(products)
                # print products
                for sku,qty in products.items():
                    #验证sku是否正确
                    product = Product.objects.filter(sku=sku).first()
                    if product:
                        #查看包裹产品是否已存在
                        shippingitem = ShippingItem.objects.filter(package_id=package.id,sku=sku).first()
                        if shippingitem:
                            #查看数量是否存在,存在更新，不存在数据该条数据
                            if qty:
                                qty = int(qty)
                                query = ShippingItem.objects.filter(package_id=package.id,sku=sku).update(quantity=qty,name=product.name)
                            else:
                                query = ShippingItem.objects.filter(package_id=package.id,sku=sku).delete()
                        else:
                            if qty:
                                qty = int(qty)
                                query = ShippingItem.objects.create(package_id=package.id,sku=sku,quantity=qty,name=product.name)
            
            package1 = Package.objects.filter(order_id=order_id).order_by('-id').first()
            request_keys = []
            for key in request.POST:
                request_keys.append(key)

            if package1:
                new_key = str(package1.id)+'sku[]'
                if new_key not in request_keys:
                    package2 = Package.objects.filter(order_id=order_id).order_by('-id').first()
                    skunew = request.POST.getlist('-99sku[]')
                    qtynew = request.POST.getlist('-99qty[]')
                    newproducts = zip(skunew, qtynew)
                    newproducts = dict(newproducts)
                    
                    for sku,qty in newproducts.items():
                        #验证sku是否正确
                        product = Product.objects.filter(sku=sku).first()
                        if product:
                            #查看包裹产品是否已存在
                            shippingitem = ShippingItem.objects.filter(package_id=package2.id,sku=sku).first()
                            if shippingitem:
                                #查看数量是否存在,存在更新，不存在数据该条数据
                                if qty:
                                    qty = int(qty)
                                    query = ShippingItem.objects.filter(package_id=package2.id,sku=sku).update(quantity=qty,name=product.name)
                                else:
                                    query = ShippingItem.objects.filter(package_id=package2.id,sku=sku).delete()
                            else:
                                if qty:
                                    qty = int(qty)
                                    query = ShippingItem.objects.create(package_id=package2.id,sku=sku,quantity=qty,name=product.name)

    #取消订单时，发送邮件
    def sendOrderCancelEmail(self,change):
        if self.status == 4:
            order = Order.objects.filter(id=self.id).first()
            if order.status != 4:
                customer = Customer.objects.filter(id=self.customer_id).first()
                email = {}
                email['receiver'] = [customer.email]
                template = 'email_order_cancel.html'
                sendData = {}
                sendData['title'] = 'RIVE – B2B order cancelled'
                sendData['order_number'] = self.ordernum
                # sendEmail(email, template, sendData)
                thread.start_new_thread(sendEmail, (email,template,sendData))


class OrderItem(models.Model):
    order = models.ForeignKey(Order,default='')
    product = models.ForeignKey(Product,default='',blank=True,null=True)
    name = models.CharField(max_length=250,default='',blank=True,null=True,verbose_name="Name")
    sku = models.CharField(max_length=100,default='',blank=True,null=True,verbose_name="Sku")
    price = models.DecimalField(max_digits=16,default=0.0,decimal_places=2,blank=True,null=True,verbose_name="Price")
    quantity = models.IntegerField(default=0, blank=True, null=True, verbose_name=u"Quantity")
    created = UnixDateTimeField(auto_now_add=True, blank=True, null=True, verbose_name=u"Create")
    updated = UnixDateTimeField(auto_now=True,blank=True,null=True, verbose_name=u"Update")
    mark = models.CharField(max_length=100, default='', blank=True , null=True, verbose_name=u"Mark")

    class Meta:
        verbose_name = 'OrderItem'
        verbose_name_plural = 'OrderItems'

    def __unicode__(self):
        return str('')

    #保存时根据所选择的产品自动更新产品name、sku、price、quantity
    def get_product(self):
        if self.product:
            product = self.product
            quantity = self.quantity
            #新增时数量不填默认为1
            if not quantity:
                quantity = 1
            orderitem = OrderItem.objects.filter(id=self.id).update(name=product.name,sku=product.sku,quantity=quantity)

    #保存时根据所选产品限定产品价格的范围
    def get_price(self):
        product = self.product
        price = self.price
        order_id = self.order.id
        currency = self.order.currency
        customer_id = self.order.customer.id

        if product:
            final_price = product.final_price(customer_id,currency)
            #填入的价格不能大于用户享有的实际价格
            # if price > final_price:
            #   orderitem = OrderItem.objects.filter(id=self.id).update(price=final_price)
            #   return True

            #新增时候不填写，或者价格为0时，则选则默认价格
            if price == 0 or price == 0.0 or price == 0.00:
                orderitem = OrderItem.objects.filter(id=self.id).update(price=final_price)
                return True

            # min_price = float(final_price) * float(0.8)
            # min_price = round(min_price,2)
            # #价格小数部分如果是0也保留两位
            # min_price = '%.2f' % min_price
            # #填入的价格不能小于用户享有的实际价格的80%
            # if price < min_price:
            #   orderitem = OrderItem.objects.filter(id=self.id).update(price=min_price)
            #   return True


class Shipping(models.Model):
    ship_company = models.CharField(max_length=200,default='',verbose_name='Shipping Method')
    tracking_link = models.CharField(max_length=200,default='',blank=True,null=True,verbose_name="Tracing Link")
    created = UnixDateTimeField(auto_now_add=True, blank=True, null=True, verbose_name=u"Create")
    updated = UnixDateTimeField(auto_now=True,blank=True,null=True, verbose_name=u"Update")

    class Meta:
        verbose_name = 'Shipping'
        verbose_name_plural = 'Shippings'

    def __unicode__(self):
        return str(self.ship_company)


class Package(models.Model):
    order = models.ForeignKey(Order,default='')
    shipping = models.ForeignKey(Shipping,default='',verbose_name='Shipping method')
    # sku = models.CharField(max_length=100,default='',blank=True,null=True,verbose_name="Sku")
    # quantity = models.CharField(max_length=100,default='',blank=True,null=True,verbose_name="Qty")
    tracking_number = models.CharField(max_length=200,default='',verbose_name="Track Number")
    note = models.TextField(default='',blank=True,null=True,verbose_name="Note")
    created = UnixDateTimeField(auto_now_add=True, blank=True, null=True, verbose_name=u"Create")
    updated = UnixDateTimeField(auto_now=True,blank=True,null=True, verbose_name=u"Update")

    class Meta:
        verbose_name = 'Package'
        verbose_name_plural = 'Packages'

    def __unicode__(self):
        return str('')

    # #添加包裹产品保存
    # def package_products_save(self,request):
    #   if request.method == 'POST':
    #       print 2222



class CartItem(models.Model):
    customer = models.ForeignKey(Customer,default='', blank=True , null=True,verbose_name=u"Customer")
    product = models.ForeignKey(Product,default='',blank=True,null=True)
    quantity = models.IntegerField(default=0, blank=True, null=True, verbose_name=u"Quantity") 
    name = models.CharField(max_length=250,default='', blank=True , null=True,verbose_name="Name")
    sku = models.CharField(max_length=100,default='', blank=True , null=True,verbose_name="Ref")
    description = models.TextField(default='',blank=True,null=True,verbose_name="Description")
    price = models.DecimalField(max_digits=16,default=0.0,decimal_places=2,blank=True,null=True,verbose_name="Price")
    stock = models.IntegerField(default=1, blank=True, null=True, verbose_name=u"Stock")
    expected_time = UnixDateTimeField(blank=True,null=True, verbose_name=u"Expected in-stock time")


class ShippingItem(models.Model):
    package = models.ForeignKey(Package,default='')
    # product = models.ForeignKey(Product,default='',blank=True,null=True)
    name = models.CharField(max_length=100,default='',blank=True,null=True,verbose_name="Name")
    sku = models.CharField(max_length=100,default='',blank=True,null=True,verbose_name="Sku")
    quantity = models.IntegerField(default=0, blank=True, null=True, verbose_name=u"Quantity")
    created = UnixDateTimeField(auto_now_add=True, blank=True, null=True, verbose_name=u"Create")
    updated = UnixDateTimeField(auto_now=True,blank=True,null=True, verbose_name=u"Update")



class OrderHistory(models.Model):
    order = models.ForeignKey(Order,default='',)
    operation_type =models.CharField(max_length=200,default='', verbose_name=u"Operation-type")
    admin = models.ForeignKey(User,default='',verbose_name="Admin")
    operation_content = models.TextField(default='', blank=True, null=True, verbose_name=u"Operation-content")

    created = UnixDateTimeField(auto_now_add=True, blank=True, null=True, verbose_name=u"Created")
    updated = UnixDateTimeField(auto_now=True, blank=True, null=True, verbose_name=u"Updated")

    def __unicode__(self):
        return str('')