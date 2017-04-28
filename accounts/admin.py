#-*- coding: utf-8 -*-
from django.contrib import admin
from accounts.models import *
from django.utils.translation import ugettext_lazy as _
from django.contrib.admin import SimpleListFilter
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.models import User,Group
from django.db.models.signals import post_save
from django.dispatch import receiver
# from var_dump import var_dump

class AddressInline(admin.StackedInline):
    model = Address

    # @receiver(post_save, sender=Address, dispatch_uid="action")
    # def action(sender, instance, **kwargs):
    #     #保存时，如果billing信息为空，则复制shipping的信息
    #     # instance.get_billing_address()

    extra = 0
    max_num = 20
    can_delete = True
    fields = (('default'),('shipping_country','shipping_state','shipping_city'),('shipping_address','shipping_zip','shipping_phone','shipping_mobile'))

class BillingAddressInline(admin.StackedInline):
    model = BillingAddress

    extra = 0
    max_num = 1
    can_delete = False
    fields = (('billing_country','billing_state','billing_city'),('billing_address','billing_zip','billing_phone','billing_mobile'))


class CustomerAdmin(admin.ModelAdmin):

    class Media:
        js = (
            # '/static/js/test.js',
            '/static/js/product_stock_limit.js',
        )

    #customer密码展示与修改
    def change_password(self, obj):
        output = ''
        password = obj.password
        #新增用户时展示
        if not password:
            output += "<input class='vTextField' id='id_password' maxlength='100' name='password' type='text'>"
        #老用户给修改密码链接
        else:
            ch_pa = _('change password')
            output += "<a data-toggle='collapse' data-parent='#accordion' href='#change_password'>"+str(ch_pa)+"</a> "
            output += "<div id='change_password' class='panel-collapse collapse out'> "
            output += "<input class='vTextField' maxlength='100' name='change_password' type='text'>"
            output += "</div> "
        return output
    change_password.allow_tags = True
    change_password.short_description = _('Password')

    #用户折扣展示及保存
    def customer_discount(self, obj):
        output = ""
        #输入控制
        onkeyup = str("this.value=this.value.replace(/[^\d{1,}\.\d{1,}|\d{1,}]/g,'')")
        input_contron = str("onkeyup=")+onkeyup
        discount = obj.discount
        output += "<div style='margin-left:10%;padding:3px;><label for='customer_discount'></label><input type='text' name='customer_discount' value='"+str(discount)+"' "+str(input_contron)+" onchange='discount_change(this)' id='new_discount'></div>"
        return output
    customer_discount.allow_tags = True
    customer_discount.short_description = _('Discount')

    # def save_model(self, request, obj, form, change):
    #     try:
    #         super(CustomerAdmin, self).save_model(request, obj, form, change)
    #     except Exception as e:
    #         print e
    #     obj.encrypt_password(request)
    #     obj.discount_save(request)

    def save_formset(self, request, form, formset, change):
        formset.save()
        form.instance.save()
        form.instance.sendNewAccountsEmail(request)
        form.instance.encrypt_password(request)
        form.instance.discount_save(request)
    # def formfield_for_foreignkey(self, db_field, request, **kwargs):
    #   if not request.user.is_superuser:
    #       admin_id = request.user.id
    #       kwargs['queryset'] = Customer.objects.filter(admin_id=admin.id).all()
    #   else:
    #       kwargs['queryset'] = Customer.objects.all()
    #   return super(CustomerAdmin, self).formfield_for_foreignkey(db_field, request, **kwargs)

    #每个管理员只能看到属于他的客户
    def get_queryset(self, request):
        # if not request.user.is_superuser:
        #     admin_id = request.user.id
        #     query_set = Customer.objects.filter(admin_id=admin_id)
        # else:
        #     query_set = Customer.objects.all()
        # return query_set
        if request.user.is_superuser:
            query_set = Customer.objects.all()
        else:
            current_group_set = ''
            if request.user.is_authenticated():
                current_user_set = request.user
                try:
                    current_group_set = Group.objects.get(user=current_user_set)
                except Exception as e:
                    current_group_set = ''

            if str(current_group_set) == 'Super manager':
                query_set = Customer.objects.all()
            else:
                admin_id = request.user.id
                query_set = Customer.objects.filter(admin_id=admin_id)

        return query_set
        

    inlines = [AddressInline,BillingAddressInline]
    save_as = True
    save_on_top = True
    search_fields = ['email', 'firstname','lastname','account_number','shop_name','admin__username']
    list_display = ('id','email','firstname','lastname','account_number','shop_name','discount','locked','admin')
    fields = ('email','change_password','firstname','lastname','account_number','shop_name','customer_discount','locked','admin',)
    readonly_fields = ('change_password','customer_discount')
admin.site.register(Customer,CustomerAdmin) 


class CurrencyAdmin(admin.ModelAdmin):
    save_as = True
    # save_on_top = True
    # search_fields = ['name', 'code']
    list_display = ('id','name','rate','code')
    fields = ('name','rate','code')
admin.site.register(Currency,CurrencyAdmin)

