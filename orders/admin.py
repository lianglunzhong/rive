#-*- coding:utf-8 -*-
from django.contrib import admin
from orders.models import *
from products.models import ProductImage
from accounts.models import *
from django.db.models.signals import post_save
from django.dispatch import receiver
from products.views import time_str2, write_csv
import csv
from accounts.models import Customer

from products.forms import OrderItemAdminForm
from django.contrib.auth.models import User,Group

class OrderItemInline(admin.TabularInline):
    model = OrderItem
    form = OrderItemAdminForm

    #保存时根据所选择的产品自动更新产品name、sku
    @receiver(post_save, sender=OrderItem, dispatch_uid="action")
    def action(sender, instance, **kwargs):
        instance.get_product()
        instance.get_price()

    #产品图片获取
    def product_image(self, obj):
        output = ""
        product = obj.product

        no_picture = "this.src='/static/assets/images/no_picture.png'"
        onerror = "onerror="+str(no_picture)

        if product:
            product_id = product.id
            image = ProductImage.objects.filter(product_id=product_id).order_by('id').first()
            if image:
                if image.image:
                    image_url = "/site_media/"+str(image.image)
                    output += "<a href='"
                    output += image_url
                    output += "' target='blank'><img src='"
                    output += image_url
                    output += "' height='80px' width='60px' "+str(onerror)+"></a>"
                else:
                    output += "<img src='/static/assets/images/no_picture.png' height='80px' width='60px'>"
            else:
                output += "<img src='/static/assets/images/no_picture.png' height='80px' width='60px'>"
        return output
    product_image.allow_tags = True
    product_image.short_description = 'Image'

    class Media:
        js = (
            # '/static/js/test.js',
            '/static/js/product_stock_limit.js',
        )

    #产品价格展示及判断能否修改(弃用)
    def product_price(self,obj):
        output = ''
        product_id = obj.product.id
        #下单时生成的 订单里面的价格
        price1 = obj.price
        #产品原来的价格
        price2 = obj.product.price
        #判断产品价格是否为净价,0：允许折扣和更改价格，1:不允许
        is_net_price = obj.product.is_net_price
        #允许更改价格的情况
        # if not is_net_price:
        #更改价格时的保存链接参数
        order_id = obj.order.id
        orderitem_id = obj.id
        product_id = obj.product.id
        output += "<div id='original_price"+str(product_id)+"'>"+str(price1)
        output += "&nbsp;&nbsp;"
        output += "<a href='javascript:void(0);' onclick='change_price("+str(product_id)+")' style='cursor:pointer;'>change price</a></div>"
        output += "<div id='change_price"+str(product_id)+"' style='display:none;'><input type='text' id='change_price_input"+str(product_id)+"' value='"+str(price1)+"'>&nbsp;&nbsp;&nbsp;&nbsp;<a id='price_save_"+str(product_id)+"' href='javascript:void(0);' style='cursor:pointer;' onclick='price_save("+str(order_id)+","+str(orderitem_id)+","+str(product_id)+");'>save</a></div>"
        # else:
        #   output += "<div>"+str(price1)+"</div>"
        return output
    product_price.allow_tags = True
    product_price.short_description = 'Price'


    #产品报缺勾选框
    def shortage_item(self,obj):
        output = ""
        if obj.id:
            order_id = obj.order.id
            email = ''
            if obj.order.customer:
                email = obj.order.customer.email
                
            orderitem = OrderItem.objects.filter(order_id=order_id).order_by('-id').first()
            if obj.id == orderitem.id:
                output += "<input type='checkbox' value='"+str(obj.id)+"' name='item_list'>"
                output += "<br><br><br><input type='hidden' id='customer_email' value='"+str(email)+"'><input type='hidden' id='order_id' value='"+str(order_id)+"'><input type='button' onclick='orderitem_shortage()' value='send shortage mail' class='default' style='padding:5px 8px'>"
            else:
                output += "<input type='checkbox' value='"+str(obj.id)+"' name='item_list'>"
        return output
    shortage_item.allow_tags = True
    shortage_item.short_description = 'selete'

    extra = 0
    max_num = 20
    can_delete = True
    fields = ('shortage_item','product_image','product','name','price','quantity','mark')
    readonly_fields = ('product_image','created','name','shortage_item')
        

class PackageInline(admin.StackedInline):

    model = Package

    #shipping_item添加按钮
    # def add_shippingitem(self,obj):
    #   package_id = str(obj.id)
    #   shipping = obj.order
    #   output = ""
    #   if shipping:
    #       output += "<div style='padding-left:10%;'><iframe frameBorder='0' scrolling='no' id='myiframe' style='width:100%;height:25px;' src='/orders/shipitem_add/"+package_id+"'></iframe></div>"
    #   return output   
    # add_shippingitem.allow_tags = True
    # add_shippingitem.short_description = u''

    class Media:
        js = (
            # '/static/js/test.js',
            '/static/js/product_stock_limit.js',
        )

    #shipping_item展示页面
    def show_shippingitem(self,obj):

        output = ""
        package_id = obj.id
        #qty输入框只能输入数字控制
        onkeyup = str("this.value=this.value.replace(/\D/g,'')")
        onafterpaste = str("this.value=this.value.replace(/\D/g,'')")
        input_contron = str("onkeyup=")+onkeyup+str("  ")+str("onafterpaste=")+onafterpaste
        print input_contron
        #查看包裹里的产品数据
        shippingitems = ShippingItem.objects.filter(package_id=package_id).all()
        if shippingitems:
            output += "<div id='sku_qty"+str(package_id)+"' style='margin-left:10%;padding:3px;'>"
            for shippingitem in shippingitems:
                output += "<br><br><div><div style='float:left;'><label for='sku'>Ref. :</label><input class='psku' type='text' name='"+str(package_id)+"sku[]' value='"+str(shippingitem.sku)+"'></div><div style='float:left;padding-left:20px;'> <label for='qty'>Qty :</label><input  type='text' name='"+str(package_id)+"qty[]' value='"+str(shippingitem.quantity)+"'"+input_contron+"></div></div><br>"
            output += "</div>"
        else:
            if package_id:
                output += "<br><br><div id='sku_qty"+str(package_id)+"' style='margin-left:10%;padding:3px;'><div style='float:left;'><label for='sku'>Ref. :</label><input class='psku' type='text' name='"+str(package_id)+"sku[]'></div><div style='float:left;padding-left:20px;'> <label for='qty'>Qty :</label><input type='text' name='"+str(package_id)+"qty[]'"+input_contron+"></div></div>"
            else:
                package_id = int(-99)
                output += "<br><br><div id='sku_qty"+str(package_id)+"' style='margin-left:10%;padding:3px;'><div style='float:left;'><label for='sku'>Ref. :</label><input class='psku' type='text' name='"+str(package_id)+"sku[]'></div><div style='float:left;padding-left:20px;'> <label for='qty'>Qty :</label><input type='text' name='"+str(package_id)+"qty[]'"+input_contron+"></div></div>"
        output += "<br><br><input onclick='add_new("+str(package_id)+")' type='button' style='margin-left:10%;padding:3px;' value='Add new'>"
        return output
    show_shippingitem.allow_tags = True
    show_shippingitem.short_description = 'Shiping Product'

    #保存时根据所选择的快递方式自动获取查询链接
    def get_track_link(self, obj):
        output = ''
        if obj.shipping:
            tracking_link = obj.shipping.tracking_link
        else:
            tracking_link = ''
        output += "<a target='blank' href='"+tracking_link+"'>"+tracking_link+"</a>"
        return output
    get_track_link.allow_tags = True
    get_track_link.short_description = 'Track link'

    extra = 0
    max_num = 10
    can_delete = True
    fields = (('shipping','get_track_link','tracking_number'),'show_shippingitem','note',)
    readonly_fields = ('get_track_link','show_shippingitem')


class OrderHistoryInline(admin.TabularInline):
    model = OrderHistory

    extra = 0
    can_delete = False
    fields = ('operation_type','operation_content','admin','created')
    readonly_fields = ('operation_type','operation_content','admin','created')

class OrderAdmin(admin.ModelAdmin):
    inlines = [OrderItemInline,PackageInline,OrderHistoryInline]
    #保存时根据所选择的用户自动更新用户地址
    @receiver(post_save, sender=Order, dispatch_uid="action")
    def action(sender, instance, **kwargs):
        instance.get_address()

    #inline保存方式
    def save_formset(self, request, form, formset, change):
        formset.save() # this will save the children
        form.instance.save()
        form.instance.package_products_save(request)
        #更改产品价格保存
        # form.instance.change_price_save(request)
        #根据当前产品价格及数量自动更新订单总价
        form.instance.get_order_amount(request)

    #取消订单时，发送邮件
    def save_model(self, request, obj, form, change):
        obj.sendOrderCancelEmail(change)

    #每个管理员只能看到属于他的客户的订单
    def get_queryset(self, request):
        if request.user.is_superuser:
            query_set = Order.objects.all()
        else:
            current_group_set = ''
            if request.user.is_authenticated():
                current_user_set = request.user
                try:
                    current_group_set = Group.objects.get(user=current_user_set)
                except Exception as e:
                    current_group_set = ''

            if str(current_group_set) == 'Super manager':
                query_set = Order.objects.all()
            else:
                admin_id = request.user.id
                customers = Customer.objects.filter(admin_id=admin_id).all()
                customer_ids = []
                for c in customers:
                    customer_ids.append(c.id)
                customer_ids = tuple(customer_ids)
                query_set = Order.objects.filter(customer_id__in=customer_ids).all()

        return query_set

    #前台用图片下单时后台图片展示
    def show_img(self,obj):
        output = ''
        img = obj.imgorder
        if img:
            #规定图片展示的大小
            output += "<a href='/site_media/"+str(img)+"' target='blank'><img style='max-width:40%;height:auto;' src='/site_media/"+str(img)+"'></a>"
        return output
    show_img.allow_tags = True
    show_img.short_description = 'Image'

    #期望下单时间展示
    def show_expcted_ship_date(self,obj):
        output = ''
        expcted_shipping = obj.expcted_shipping
        expcted_shipping = str(expcted_shipping)[0:11]
        return expcted_shipping
    show_expcted_ship_date.allow_tags = True
    show_expcted_ship_date.short_description = 'Expcted shipping date'

    #客户account_number展示
    def show_account_number(self,obj):
        output = ""
        if obj.customer:
            output += obj.customer.account_number
        return output
    show_account_number.allow_tags = True
    show_account_number.short_description = "Account number"

    #订单导出
    def export_selected_orders(modeladmin, request, queryset):
        response, writer = write_csv('export_orders')
        writer.writerow(['NO.','EPR NO.','Status','Stock-Mark','Amount','Currency','Created', 'Verified time','Shop keeper','Account number','Expcted shipping date','Comment','Ref.','Price','Quantity','Item-Mark','shipping_country','shipping_state','shipping_city','shipping_address','shipping_zip','shipping_phone','shipping_mobile','billing_country','billing_state','billing_city','billing_address','billing_zip','billing_phone','billing_mobile'])

        for order in queryset:
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
    export_selected_orders.short_description = 'Export selected Orders'


    save_as = True
    save_on_top = True
    search_fields = ['ordernum','customer__email','erp_num','accountnumber']
    actions = ['export_selected_orders']
    list_filter = ['status']
    list_display = ('id','ordernum','erp_num','customer','accountnumber','created','status','amount','currency','mark')
    # fields = (('ordernum','erp_num'),'status','mark',('currency','amount'),'customer','show_account_number','show_expcted_ship_date','verifued','message','show_img')

    fieldsets = (
        (u'Base',{
            'fields':(('ordernum','erp_num'),'status','mark',('currency','amount'),'customer','accountnumber','show_expcted_ship_date','verifued','message','show_img'),
        }),
        # ('Shop keeper address',{
        #     'fields':(('shipping_country','billing_country'),('shipping_state','billing_state'),('shipping_city','billing_city'),('shipping_address','billing_address'),('shipping_zip','billing_zip'),('shipping_phone','billing_phone'),('shipping_mobile','billing_mobile')),
        #     'classes': ('collapse',),
        # }),
        ('Shipping address',{
            'fields':('shipping_country','shipping_state','shipping_city','shipping_address','shipping_zip','shipping_phone','shipping_mobile'),
            'classes': ('collapse',),
        }),
        ('Billing address',{
            'fields':('billing_country','billing_state','billing_city','billing_address','billing_zip','billing_phone','billing_mobile'),
            'classes': ('collapse',),
        }),

    )

    readonly_fields = ('shipping_country','shipping_state','billing_state','shipping_mobile','billing_mobile','shipping_city','shipping_zip','shipping_phone','billing_phone','billing_zip','billing_city','billing_country','shipping_address','billing_address','message','show_img','amount','show_expcted_ship_date','ordernum','currency','customer','show_account_number','accountnumber')
admin.site.register(Order,OrderAdmin)


class ShippingAdmin(admin.ModelAdmin):
    save_as = True
    # save_on_top = True
    search_fields = ('ship_company',)
    list_display = ('id','ship_company','tracking_link')
    fields = ('ship_company','tracking_link')
admin.site.register(Shipping,ShippingAdmin)