#-*- coding: utf-8 -*-
from django.contrib import admin
from products.models import *
from django.db.models import Q
from django.contrib.admin import SimpleListFilter

# class ProductNetpriceManagerFilter(SimpleListFilter):
#     print 22222
#     title = 'By Is net price ?'
#     parameter_name = 'is_net_price'

#     def lookups(self, request, model_admin):
#         type_list = []  
#         type_list.append([0,u'No'])
#         type_list.append([1,'Yes'])
#         return type_list

#     def queryset(self, request, queryset):
#         if self.value() == '0':
#             return queryset.filter(is_net_price=0)
#         elif self.value() == '1':
#             return queryset.filter(is_net_price=1)
#         else:
#             return queryset.all()


class CatalogAdmin(admin.ModelAdmin):

    class Media:
        js = (
            # '/static/js/test.js',
            '/static/js/product_stock_limit.js',
        )

    #折扣展示及保存操作
    def catalog_discount(self, obj):
        output = ""
        #输入控制
        onkeyup = str("this.value=this.value.replace(/[^\d{1,}\.\d{1,}|\d{1,}]/g,'')")
        input_contron = str("onkeyup=")+onkeyup
        discount = obj.discount
        output += "<div style='margin-left:10%;padding:3px;><label for='catalog_discount'></label><input type='text' name='catalog_discount' value='"+str(discount)+"' "+str(input_contron)+" onchange='discount_change(this)' id='new_discount'></div>"
        return output
    catalog_discount.allow_tags = True
    catalog_discount.short_description = 'Discount'

    def save_model(self, request, obj, form, change):
        try:
            super(CatalogAdmin, self).save_model(request, obj, form, change)
        except Exception as e:
            print e
        obj.discount_save(request)

    save_as = True
    save_on_top = True
    search_fields = ['name']
    list_display = ('id','name','visibility','parent','discount','description',)
    fields = ('name','parent','catalog_discount','visibility','description')
    readonly_fields = ('catalog_discount',)
admin.site.register(Catalog,CatalogAdmin)
        

class ProductImageInline(admin.TabularInline):
    model = ProductImage

    #产品图片展示
    def product_image(self, obj):
        output = ""
        image = obj.image
        no_picture = "this.src='/static/assets/images/no_picture.png'"
        onerror = "onerror="+str(no_picture)
        if image:
            image_url = "/site_media/"+str(image)
            output += "<a href='"
            output += image_url
            output += "' target='blank'><img src='"
            output += image_url
            output += "' height='160px' width='120px' "+str(onerror)+"></a>"
        return output
    product_image.allow_tags = True
    product_image.short_description = 'Image priview'

    extra = 0
    max_num = 5
    can_delete = True
    fields = ('product_image','image','title')
    readonly_fields = ('product_image',)
        

class ProductAdmin(admin.ModelAdmin):

    #产品列表页产品图片展示
    def show_pro_image(self,obj):
        output = ''
        product_id = obj.id
        no_picture = "this.src='/static/assets/images/no_picture.png'"
        onerror = "onerror="+str(no_picture)

        image = ProductImage.objects.filter(product_id=product_id).order_by('id').first()
        if image:
            image_url = "/site_media/"+str(image.image)
            output += "<img src='" + image_url + "' height='115px' width='85px'"+str(onerror)+">"
        else:
            image_url = "/static/assets/images/no_picture.png"
            output += "<img src='" + image_url + "' height='115px' width='85px' "+str(onerror)+">"
        return output
    show_pro_image.allow_tags = True
    show_pro_image.short_description = 'Pimage'

    inlines = (ProductImageInline,)

    save_as = True
    save_on_top = True
    
    #支持搜索的字段
    search_fields = ['sku', 'name','catalog__name']

    #自定义搜索
    def get_search_results(self, request, queryset, search_term):
        queryset, use_distinct = super(ProductAdmin, self).get_search_results(request, queryset, search_term)
        search_term = search_term.strip()
        if search_term:
            try:
                #搜索关键词中只包含数字且不带空格：1.拆分数字，匹配sku；2.不拆分，搜索产品名称
                is_start_zero = search_term.startswith('0')
                search_term = int(search_term)
                #拆分数字
                if is_start_zero:
                    search_term = str('0') + str(search_term)
                else:
                    search_term = str(search_term)
                    
                search_sku = ''
                i = 0
                while i < len(search_term):
                    search_sku += str(search_term[i:i+2]) + str(' ')
                    i += 2

                #去掉最后一个空格
                search_sku = search_sku.strip()

                queryset =  self.model.objects.filter(Q(sku__istartswith=search_sku)|Q(name__icontains=search_term)|Q(catalog__name__icontains=search_term)).all().order_by('-id')

            except ValueError:
                queryset =  self.model.objects.filter(Q(sku__istartswith=search_term)|Q(name__icontains=search_term)|Q(catalog__name__icontains=search_term)).all().order_by('-id')

        return queryset, use_distinct

    list_filter = ('visibility','is_net_price','mark')

    list_display = ('id','name','sku','catalog','visibility','qty','qty2','price','ssp','rrp','is_net_price','mark','show_pro_image')
    
    fieldsets = (
        ('Base',{
            'fields':('name','catalog','sku','visibility',('qty','qty2','mark'),'expected_time',('price','ssp','rrp'),'is_net_price'),
        }),
        ('Description',{
            'fields':('description','description_fr','description_de','description_nl'),
            'classes':('collapse',),
        }),
    )

    readonly_fields = ('show_pro_image',)
admin.site.register(Product,ProductAdmin)   