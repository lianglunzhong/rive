#-*- coding:utf-8 -*-
from django.shortcuts import render
from django.http import HttpResponse, HttpResponseRedirect
from django.conf.urls import url
from django.shortcuts import get_object_or_404, redirect
from accounts.models import Customer, Currency
from products.models import Product, ProductImage,Catalog
from django.db.models import Q
from accounts.views import is_login, order_list_count,get_stock_group,get_est_date
from orders.models import CartItem
import time
import StringIO
import csv
from django.contrib import messages

from django.contrib.auth.decorators import login_required
from translates.models import ProductFr
import os
from django.db import connection, transaction

from dal import autocomplete

import chardet
import sys
reload(sys)
sys.setdefaultencoding('utf8')

import base64
import urllib
from library.views import getCookie, get_promotion

# print dir(autocomplete)

#后台带产品外键的地方产品先部分加载（搜索功能）
class ProductAutocomplete(autocomplete.Select2QuerySetView):
    def get_queryset(self):
        if not self.request.user.is_authenticated():
            return Product.objects.none()

        qs = Product.objects.all()

        if self.q:
            qs = qs.filter(sku__istartswith=self.q)

        return qs


#前台切换货币设置（cookie）
def currency_set(request):
    #获取上一个页面url，数据处理之后跳转回该页面
    referer_url = request.META['HTTP_REFERER']

    if request.method == 'POST':
        if request.POST['type'] == 'select_currency':
            #获取当前选择的货币
            currency = request.POST['currency']
            #货币存在，设置cookie
            if currency:
                request.session['currency'] = currency
                # response = HttpResponse('test')
                # print response.set_cookie('currency',currency)
                # print request.COOKIES.get('currency')
                
    return redirect(referer_url)

#前台获取币种公用方法
def currency_get(request):
    #默认币种
    default_currency = 'EUR'
    #检查币种cookie是否存在
    currency = request.session.get('currency', False)
    if currency:
        default_currency = currency
    return default_currency

#前台获取币种符号公用方法
def get_currency_code(request):
    code = '€'
    #前台价格不同货币对应的符号展示
    currency = currency_get(request)
    currency_code = Currency.objects.filter(name=currency).first()
    if currency_code:
        code = currency_code.code

    return code

#前台产品列表页
def products(request, page_id='1'):

    data = {}
    lang = getCookie(request)
    data['lang'] = lang
    if lang == 'fr':
        in_stock_title = 'En stock'
    elif lang == 'de':
        in_stock_title = 'Im Lager'
    elif lang == 'nl':
        in_stock_title = 'in stock'
    else:
        in_stock_title = 'in stock'
    data['in_stock_title'] = in_stock_title
    

    has_promotion = get_promotion(request)
    data['has_promotion'] = has_promotion

    page_id = ''
    category_id=''
    search_total = ''

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

    #通过url获取page_id,分类查询的分类名称
    current_url = request.get_full_path()
    current_url = urllib.unquote(current_url)
    current_url = current_url.strip().split('/')
    #分页id
    page = current_url[2]
    if page and page.startswith('page_'):
        page_id = int(page.strip('page_'))

    
    #用户所属库存组判断
    stock_group = get_stock_group(customer.id)
    #前台显示时间：当前时间+14天
    est_date = get_est_date()

    data['est_date'] = est_date
    data['stock_group'] = stock_group
    data['customer'] = customer

    #order list数量显示
    data['number'] = order_list_count(request,customer.id)

    #产品页表单提交：搜索/分类筛选/分页
    if request.method == 'POST':
        #通过输入框输入搜索：产品名称/sku
        if request.POST['type'] == 'product_search':
            search_word = request.POST['search_word'].strip()
            if search_word:
                try:
                    #搜索关键词中只包含数字且不带空格：1.拆分数字，匹配sku；2.不拆分，搜索产品名称
                    is_start_zero = search_word.startswith('0')
                    search_word = int(search_word)
                    #拆分数字
                    if is_start_zero:
                        search_word = str('0') + str(search_word)
                    else:
                        search_word = str(search_word)

                    search_sku = ''
                    i = 0
                    while i < len(search_word):
                        search_sku += str(search_word[i:i+2]) + str(' ')
                        i += 2
                    
                    #去掉最后一个空格
                    search_sku = search_sku.strip()
                    #匹配搜索关键字的产品 sku或产品名称
                    total_product = Product.objects.filter(Q(sku__istartswith=search_sku)|Q(name__icontains=search_word),visibility=1,catalog__visibility=1).all().order_by('-id')
                    products = total_product[0:10]
                    search_total = total_product.count()
                except Exception as e:
                    total_product = Product.objects.filter(Q(sku__istartswith=search_word)|Q(name__icontains=search_word),visibility=1,catalog__visibility=1).all().order_by('-id')
                    products = total_product[0:10]
                    search_total = total_product.count()

                data['search_word'] = search_word

            else:
                products = Product.objects.filter(~Q(sku=''),visibility=1,catalog__visibility=1).order_by('-id')[0:10]
        #分页，点击分页触发表单提交
        elif request.POST['type'] == 'product_page':
            # page_id = int(request.POST['page_id'])
            category_id = request.POST['category_id']
            search_word = request.POST['search_word_for_page']
            #产品分页数据
            if page_id and page_id >= 1:
                product_start = (page_id - 1) * 10
                product_end = product_start + 10
                #搜索分页
                if search_word:
                    try:
                        #搜索关键词中只包含数字且不带空格：1.拆分数字，匹配sku；2.不拆分，搜索产品名称
                        is_start_zero = search_word.startswith('0')
                        search_word = int(search_word)
                        #拆分数字
                        if is_start_zero:
                            search_word = str('0') + str(search_word)
                        else:
                            search_word = str(search_word)

                        search_sku = ''
                        i = 0
                        while i < len(search_word):
                            search_sku += str(search_word[i:i+2]) + str(' ')
                            i += 2
                        
                        #去掉最后一个空格
                        search_sku = search_sku.strip()
                        #匹配搜索关键字的产品 sku或产品名称
                        total_product = Product.objects.filter(Q(sku__istartswith=search_sku)|Q(name__icontains=search_word),visibility=1,catalog__visibility=1).all().order_by('-id')
                        products = total_product[product_start:product_end]
                        search_total = total_product.count()
                    except Exception as e:
                        total_product = Product.objects.filter(Q(sku__istartswith=search_word)|Q(name__icontains=search_word),visibility=1,catalog__visibility=1).all().order_by('-id')
                        products = total_product[product_start:product_end]
                        search_total = total_product.count()

                    data['search_word'] = search_word
                #分类筛选分页
                elif category_id:
                    category_id = int(category_id)
                    data['category_id'] = category_id
                    #获取分类及其子分类
                    catalogs = Catalog.objects.filter(Q(id=category_id)|Q(parent_id=category_id),visibility=1).all()
                    #获取子分类的分类id
                    if catalogs:
                        catalog_ids = []
                        for catalog in catalogs:
                            catalog_ids.append(catalog.id)
                        catalog_ids = tuple(catalog_ids)
                        total_product = Product.objects.filter(~Q(sku=''),visibility=1,catalog_id__in=catalog_ids).order_by('-id').all()
                        products = total_product[product_start:product_end]
                        search_total = total_product.count()
                    else:
                        products = Product.objects.filter(~Q(sku=''),visibility=1,catalog__visibility=1).order_by('-id')[0:10]
                else:
                    #正常浏览时的分页
                    products = Product.objects.filter(~Q(sku=''),visibility=1,catalog__visibility=1).order_by('-id')[product_start:product_end]
            else:
            #获取首页产品列表
                products = Product.objects.filter(~Q(sku=''),visibility=1,catalog__visibility=1).order_by('-id')[0:10]
        #分类筛选
        elif request.POST['type'] == 'catelog_search':
            category_id = request.POST['catelog_id']
            if category_id:
                category_id = int(category_id)
                data['category_id'] = category_id
                #获取分类及其子分类
                catalogs = Catalog.objects.filter(Q(id=category_id)|Q(parent_id=category_id),visibility=1).all()
                #获取子分类的分类id
                if catalogs:
                    catalog_ids = []
                    for catalog in catalogs:
                        catalog_ids.append(catalog.id)
                    catalog_ids = tuple(catalog_ids)
                    total_product = Product.objects.filter(~Q(sku=''),visibility=1,catalog_id__in=catalog_ids).order_by('-id').all()
                    products = total_product[0:10]
                    search_total = total_product.count()
                else:
                    products = Product.objects.filter(~Q(sku=''),visibility=1,catalog__visibility=1).order_by('-id')[0:10]
            else:
            #获取首页产品列表
                products = Product.objects.filter(~Q(sku=''),visibility=1,catalog__visibility=1).order_by('-id')[0:10]
        else:
        #获取首页产品列表
            products = Product.objects.filter(~Q(sku=''),visibility=1,catalog__visibility=1).order_by('-id')[0:10]
    #正常打开时的页面
    else:
        if page_id and page_id > 1:
            product_start = (page_id - 1) * 10
            product_end = product_start + 10
            products = Product.objects.filter(~Q(sku=''),visibility=1,catalog__visibility=1).order_by('-id')[product_start:product_end]
        else:
            #获取首页产品列表
            products = Product.objects.filter(~Q(sku=''),visibility=1,catalog__visibility=1).order_by('-id')[0:10]

    if products:
        #产品总数
        #搜索时统计该分类下的产品总数
        if search_total:
            total_page = search_total
        else:
            total_page = Product.objects.filter(~Q(sku=''),visibility=1,catalog__visibility=1).all().count()
        data['total_page'] = total_page

        #产品图片图片，默认展示第一张
        images = {}
        #获取每个用户对应的每个产品价格
        final_price = {}
        #所有产品id，用户描述字符长度判断
        product_ids = []
        #获取当前选择的货币，用于计算产品最终价格
        currency = currency_get(request)
        #获取产品描述的翻译
        product_descriptions = {}
        #产品库存状态
        stocks = {}

        #产品到货时间格式转化
        expected_times = {}

        for product in products:
            #产品库存状态
            stock_type = product.get_stock_type(stock_group)
            stocks[int(product.id)] = stock_type

            #产品图片
            product_ids.append(str(product.id))

            #产品到货时间格式转化
            expected_time = product.expected_time
            if expected_time:
                expected_time = time_stamp2(expected_time)
                expected_time = time_str2(expected_time)
                expected_times[int(product.id)] = expected_time

            #更新产品到货时间（不能为0
            is_zero = time_stamp2(product.expected_time)
            if is_zero == 0:
                sql = "UPDATE `products_product` SET expected_time = NULL WHERE id="+str(product.id)
                cursor = connection.cursor()
                cursor.execute(sql)

            # 产品价格
            show_price = {}
            show_price['price'] = product.final_price(customer.id, currency)
            if product.ssp:
                try:
                    show_price['ssp'] = product.final_ssp_rrp(product.ssp, currency)
                except Exception as e:
                    show_price['ssp'] = product.final_ssp_rrp(0, currency)
            else:
                show_price['ssp'] = product.final_ssp_rrp(0, currency)

            if product.rrp:
                try:
                    show_price['rrp'] = product.final_ssp_rrp(product.rrp, currency)
                except Exception as e:
                    show_price['rrp'] = product.final_ssp_rrp(0, currency)
            else:
                show_price['rrp'] = product.final_ssp_rrp(0, currency)

            final_price[int(product.id)] = show_price

            image = ProductImage.objects.filter(product_id=product.id).order_by('id').first()
            if image:
                images[int(product.id)] = image.image
            else:
                images[int(product.id)] = ''
            
            #产品描述翻译
            if lang == 'fr':
                product_descriptions[int(product.id)] = product.description_fr
            elif lang == 'de':
                product_descriptions[int(product.id)] = product.description_de
            elif lang == 'nl':
                product_descriptions[int(product.id)] = product.description_nl
            else:
                product_descriptions[int(product.id)] = product.description

            if product_descriptions[int(product.id)] == '':
                product_descriptions[int(product.id)] = product.description

        data['expected_times'] = expected_times
        data['product_descriptions'] = product_descriptions

        #前台价格不同货币对应的符号展示
        data['code'] = get_currency_code(request)
        #前台展示时判断当前选择的货币
        data['current_currency'] = currency
        #产品库存状态前台展示
        data['stocks'] = stocks

        product_ids = ','.join(product_ids)
        data['product_ids'] = product_ids

        data['products'] = products
        data['final_price'] = final_price
        data['images'] = images

        if page_id and page_id >= 1:
            data['page_id'] = page_id
        else:
            data['page_id'] = 1

    #获取所有的分类，用于分类筛选
    catalogs = Catalog.objects.filter(visibility=1).all()
    data['catalogs'] = catalogs
    
    #导航栏激活样式
    data['nav_products'] = 'active'
    data['nav_order_list'] = ''
    data['nav_order_history'] = ''
    data['nav_promotion'] = ''

    #前台币种选择
    currencies = Currency.objects.all()
    data['currencies'] = currencies


    return render(request, 'products-list.html', data)


#后台csv批量上传产品信息
@login_required
def upload_products(request):
    data = {}
    #获取上一个页面url，数据处理之后跳转回该页面
    referer_url = request.META['HTTP_REFERER']

    if request.method == 'POST':
        #上传csv批量更新订单的erpnum
        if request.POST['type'] == 'upload_products':

            #获取文件对象
            file_obj = request.FILES.get('upload_products_file', None)

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
                "Name","Ref.","Price","SSP","RRP","Is_net_price","Catalog_name/id","Visibility","Public-qty","CNL-qty","Special-Mark","Expected-time","Description","Description-fr","Description-de","Description-nl","Images"
            ]
            field_header = [
                "name","sku","price","ssp","rrp","is_net_price","catalog_id","visibility","qty","qty2","mark","expected_time","description","description_fr","description_de","description_nl","images"
            ]

            # 由于bom头的问题, 就不比较第一列的header了
            if header[1:] != std_header[1:]:
                print header[1:]
                print std_header[1:]
                messages.error(request,'Please use the correct template and save as UTF-8 format.')
                return redirect(referer_url)

            # 用于保存sku已经存在的错误产品数据返回提示
            sku_error = []

            #获取csv表格每一行的值，i为行数，row该行对应的列的值
            for i, row in enumerate(reader,2):
                #将上传的每一行的值与改行的标题一一对应
                res = zip(field_header,row)

                #转为为字典，方便后面取值
                res = dict(res)
                
                #产品sku和产品name为必须存在的字段
                if res['sku'] and res['name']:
                    #产品价格去掉货币符号
                    res['name'] = res['name'].strip().decode('gbk').encode('utf-8')
                    res['description'] = res['description'].strip().decode('gbk').encode('utf-8')
                    res['description_fr'] = res['description_fr'].strip().decode('gbk').encode('utf-8')
                    res['description_de'] = res['description_de'].strip().decode('gbk').encode('utf-8')
                    res['description_nl'] = res['description_nl'].strip().decode('gbk').encode('utf-8')
                    res['sku'] = res['sku'].strip().decode('gbk').encode('utf-8')
                    res['catalog_id'] = res['catalog_id'].strip().decode('gbk').encode('utf-8')
                    res['price'] = res['price'].strip().decode('gbk').encode('utf-8')
                    res['images'] = res['images'].strip().decode('gbk').encode('utf-8')


                    #判断sku是否已存在，存在则跳过
                    product = Product.objects.filter(sku=res['sku'])
                    if product:
                        sku_error.append(res['sku'])
                    else:
                        #价格判断及格式转换
                        price = res['price']
                        if price:
                            try:
                                price = round(float(price),2)
                            except Exception as e:
                                price = 0.0
                        else:
                            price = 0.0

                        ssp = res['ssp']
                        if ssp:
                            try:
                                ssp = round(float(ssp),2)
                            except Exception as e:
                                ssp = 0.0
                        else:
                            ssp = 0.0

                        rrp = res['rrp']
                        if rrp:
                            try:
                                rrp = round(float(rrp),2)
                            except Exception as e:
                                rrp = 0.0
                        else:
                            rrp = 0.0

                        #是否净价
                        try:
                            is_net_price = int(res['is_net_price'])
                        except Exception as e:
                            is_net_price = 0
                        #是否净价的值只能为0和1
                        if is_net_price != 0 and is_net_price != 1:
                            is_net_price = 0

                        #产品分类
                        catalog_id = res['catalog_id']
                        if catalog_id:
                            try:
                                catalog_id = int(res['catalog_id'])
                                catalog = Catalog.objects.filter(id=catalog_id).first()
                            except Exception as e:
                                catalog = Catalog.objects.filter(name=catalog_id).first()
                            if catalog:
                                catalog_id = catalog.id
                            else:
                                catalog_id = ''

                        #可见性
                        try:
                            visibility = int(res['visibility'])
                        except Exception as e:
                            visibility = 1
                        #可见性的值只能为0和1
                        if visibility != 0 and visibility != 1:
                            visibility = 1

                        #库存：
                        try:
                            qty = int(res['qty'])
                        except Exception as e:
                            qty = 0
                        #库存2：
                        try:
                            qty2 = int(res['qty2'])
                        except Exception as e:
                            qty2 = 0

                        #库存限制标记：
                        try:
                            mark = int(res['mark'])
                        except Exception as e:
                            mark = 1
                        #库存限制标记至只能为0和1
                        if mark != 0 and mark != 1:
                            mark = 1

                        #新增产品   
                        product_create = Product.objects.create(
                                name=res['name'],
                                sku=res['sku'],
                                price=price,
                                ssp=ssp,
                                rrp=rrp,
                                is_net_price=is_net_price,
                                catalog_id=catalog_id,
                                visibility=visibility,
                                qty=qty,
                                qty2=qty2,
                                mark=mark,
                                description = res['description'],
                                description_fr = res['description_fr'],
                                description_de = res['description_de'],
                                description_nl = res['description_nl']
                            )
                        #产品新增成功，更新到货时间和产品图片（如果存在）
                        if product_create:
                            #到货时间
                            if res['expected_time']:
                                try:
                                    timearray = time.strptime(str(res['expected_time']), "%Y/%m/%d")
                                    timestamp = int(time.mktime(timearray))
                                    expected_time = timestamp
                                except Exception as e:
                                    expected_time = ''
                                if expected_time:
                                    sql = "UPDATE products_product SET expected_time='"+str(expected_time)+"' WHERE id='"+str(product_create.id)+"'"
                                    print sql
                                    cursor = connection.cursor()
                                    cursor.execute(sql)
                                    # product_updated1 = Product.objects.filter(id=product_create.id).update(expected_time=expected_time)
                            #产品图片
                            if res['images']:
                                images = str(res['images']).strip('\r\n').split(',')
                                for image in images:
                                    #判断图片名称是否带后缀
                                    fn,ext = os.path.splitext(image)
                                    if ext:
                                        # if lower(ext) in ('jpg','png','bmp','jpeg','bmp')
                                        image_name = str('pimg/') + str(image)
                                    else:
                                        image_name = str('pimg/') + str(image) + str('.jpg')
                                    image_create = ProductImage.objects.create(image=image_name,product_id=product_create.id)

            if sku_error:
                sku_error = tuple(sku_error)
                messages.error(request,"Product(s) "+str(sku_error)+" has existed.")
                return redirect(referer_url)
            else:
                messages.success(request,"Product(s) add success.")
                return redirect(referer_url)

    return HttpResponse('1111111')

#后台csv批量上传分类信息
@login_required
def upload_catalogs(request):
    data = {}
    #获取上一个页面url，数据处理之后跳转回该页面
    referer_url = request.META['HTTP_REFERER']

    if request.method == 'POST':
        if request.POST['type'] == 'upload_catalogs':

            #获取文件对象
            file_obj = request.FILES.get('upload_catalogs_file',None)

            if file_obj == None:
                return redirect(referer_url)

            #获取文件内容
            file_content = file_obj.read()

            #格式转化
            try:
                reader = csv.reader(StringIO.StringIO(file_content),delimiter=';')
                header = next(reader)
            except Exception as e:
                return redirect(referer_url)

            std_header = [
                "Name","Parent_name/id","Discount","Visibility","Description"
            ]
            field_header = [
                "name","parent","discount","visibility","description"
            ]

            #由于bom头的问题, 就不比较第一列的header了
            if header[1:] != std_header[1:]:
                messages.error(request,"Please use the correct template and save as UTF-8 format.")
                return redirect(referer_url)

            #保存已经存在的分类，用于返回时错误数据提示
            catalog_error = []
            #保存父级分类
            parent_data = {}
            #获取csv表格每一行的值，i为行数，row该行对应的列的值

            for i, row in enumerate(reader,2):
                #将上传的每一行的值与该行的标题一一对应
                res = zip(field_header,row)
                #转为为字典，方便后面取值
                res = dict(res)

                if res['name']:
                    res['name'] = res['name'].strip().decode('gbk').encode('utf-8')
                    res['description'] = res['description'].strip().decode('gbk').encode('utf-8')
                    #判断分类是否存在
                    catalog = Catalog.objects.filter(name=res['name'])
                    if catalog:
                        catalog_error.append(res['name'])
                    #添加新的分类
                    else:
                        #父级分类获取及判断  
                        # parent = Catalog.objects.filter(Q(name=res['parent'])|Q(id=res['parent']))

                        #可见性
                        try:
                            visibility = int(res['visibility'])
                        except Exception as e:
                            visibility = 1
                        #折扣
                        discount = 1.0
                        if res['discount']:
                            try:
                                discount = round(float(res['discount']),2)
                            except Exception as e:
                                discount = 1.0
                        if discount<=0 or discount>1.0:
                            discount = 1.0

                        #新增分类
                        # res['name'] = 'Sièges Feeder'
                        name = '%s' %str(res['name'])
                        catalog_create = Catalog.objects.create(
                                name=name,
                                visibility = visibility,
                                discount = discount,
                                description = res['description']
                            )
                        if catalog_create:
                            if res['parent']:
                                res['parent'] = res['parent'].strip().decode('gbk').encode('utf-8')
                                parent_data[catalog_create.id] = res['parent']
                        # sql = "INSERT INTO products_catalog (name,visibility,discount) values('%s',%s,%s)" %(name,visibility,discount)
                        # cursor = connection.cursor()
                        # cursor.execute(sql)

            #所有的分类都添加完成之后，再更新父级分类
            for key,value in parent_data.items():
                catalog = Catalog.objects.filter(id=key)
                if catalog:
                    #父级分类获取及判断
                    try:
                        parent_catalog = int(value)
                        parent = Catalog.objects.filter(id=parent_catalog).first()
                    except Exception as e:
                        parent = Catalog.objects.filter(name=value).first()
                    if parent:
                        catalog.update(parent_id=parent.id)

            if catalog_error:
                catalog_error = tuple(catalog_error)
                messages.error(request,"Category(s):"+str(catalog_error)+" has existed.")
                return redirect(referer_url)
            else:
                messages.success(request,"Category(s) add success.")
                return redirect(referer_url)
                        
    return HttpResponse('111111')

#后台scv批量更新产品库存
@login_required
def update_stock(request):
    data = {}
    #获取上一个页面url，数据处理之后跳转回该页面
    referer_url = request.META['HTTP_REFERER']

    if request.method == 'POST':
        if request.POST['type'] == 'update_stock':
            #获取文件对象
            file_obj = request.FILES.get('update_stock_file', None)

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
                "Ref.","Public-qty","CNL-qty","Special-Mark","Expected-time"
            ]
            field_header = [
                "sku","qty","qty2","mark","expected_time"
            ]

            #由于bom头的问题, 就不比较第一列的header了
            if header[1:] != std_header[1:]:
                messages.error(request,"Please use the correct template and save as UTF-8 format.")
                return redirect(referer_url)

            #用户保存错误的sku
            sku_error = []

            #获取csv表格每一行的值，i为行数，row该行对应的列的值
            for i, row in enumerate(reader,2):
                #将上传的每一行的值与改行的标题一一对应
                res = zip(field_header,row)
                #转为为字典，方便后面取值
                res = dict(res)

                if res['sku']:
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

                    #判断sku对应的产品是否存在
                    product = Product.objects.filter(sku=res['sku']).first()
                    if product:
                        #库存
                        try:
                            qty = int(res['qty'])
                        except Exception as e:
                            qty = 0
                        #库存2
                        try:
                            qty2 = int(res['qty2'])
                        except Exception as e:
                            qty2 = 1

                        #库存状态限制
                        try:
                            mark = int(res['mark'])
                        except Exception as e:
                            mark = 1
                        #mark标记只能为0和1
                        if mark != 0 and mark != 1:
                            mark = 1
                        
                        #到货时间
                        expected_time = ''
                        if res['expected_time']:
                            try:
                                timearray = time.strptime(str(res['expected_time']), "%Y/%m/%d")
                                timestamp = int(time.mktime(timearray))
                                expected_time = timestamp
                            except Exception as e:
                                expected_time = ''

                        if expected_time:
                            sql = "UPDATE products_product SET expected_time='"+str(expected_time)+"', qty='"+str(qty)+"', qty2='"+str(qty2)+"', mark='"+str(mark)+"'  WHERE id='"+str(product.id)+"'"
                        else:
                            sql = "UPDATE products_product SET qty='"+str(qty)+"', qty2='"+str(qty2)+"', mark='"+str(mark)+"' WHERE id='"+str(product.id)+"'"

                        cursor =  connection.cursor()
                        cursor.execute(sql)
                    else:
                        sku_error.append(res['sku'])

            if sku_error:
                sku_error = tuple(sku_error)
                messages.error(request,"Product(s):"+str(sku_error)+" has not existed.")
                return redirect(referer_url)
            else:
                messages.success(request,"Product(s) update success.")
                return redirect(referer_url)

    return HttpResponse('111111')


#测试
def pagination(request):
    data = {}

    return render(request, 'pagination_test.html', data)

#把时间戳转为为日期字符，用于订单号拼接
def time_str(timestamp):
    try:
        t = int(timestamp)
        t = time.localtime(t)
        t = time.strftime("%m%d",t)
    except Exception,e:
        print e
    return t

#将从数据库读取的时间戳转换成可读的字符串形式
def time_str2(timestamp):
    try:
        t = int(timestamp)
        t = time.localtime(t)
        t = time.strftime("%Y-%m-%d",t)
    except Exception,e:
        print e
    return t

 # 将从页面上获取的时间字符串转换为时间戳
def time_stamp(stime):
    try:
        timearray = time.strptime(str(stime), "%Y-%m-%d")
        timestamp = int(time.mktime(timearray))
        return timestamp
    except Exception,e:
        print e
    
def time_stamp2(stime):
    try:
        timearray = time.strptime(str(stime), "%Y-%m-%d %H:%M:%S")
        timestamp = int(time.mktime(timearray))
        return timestamp
    except Exception,e:
        print e

#导出公用方法
def write_csv(filename):
    response = HttpResponse(content_type='text/csv')
    response.write('\xEF\xBB\xBF')
    response['Content-Disposition'] = 'attachment; filename="%s.csv"' % filename
    writer = csv.writer(response, delimiter=';')
    return response, writer

def eparse(value, offset=None):
    try:
        if offset:
            value += offset
        t = parse(value)
    except Exception, e:
        t = None
    return t


#update_basic_products
@login_required
def update_basic_products(request):
    data = {}
    #获取上一个页面url，数据处理之后跳转回该页面
    referer_url = request.META['HTTP_REFERER']

    if request.method == 'POST':
        if request.POST['type'] == 'update_basic_products':

            file_obj = request.FILES.get('update_basic_products_file', None)

            if file_obj == None:
                messages.error(request, u'Please upload a valid CSV file.')
                return redirect(referer_url)

            file_content = file_obj.read()

            #格式转化
            try:
                reader = csv.reader(StringIO.StringIO(file_content),delimiter=str(';'))
                header = next(reader)
            except Exception as e:
                messages.error(request, u'Please upload a valid CSV file.')
                return redirect(referer_url)

            std_header = [
                "Ref.","Name","Price","SSP","RRP","Is_net_price","Catalog_name","Visibility","Public-qty","CNL-qty","Special-Mark","Expected-time","Description","Description-fr","Description-de","Description-nl"
            ]
            field_header = [
                "sku","name","price","ssp","rrp","is_net_price","catalog_id","visibility","qty","qty2","mark","expected_time","description","description_fr","description_de","description_nl"
            ]

            #由于bom头的问题, 就不比较第一列的header了
            if header[1:] != std_header[1:]:
                print header[1:]
                print std_header[1:]
                messages.error(request,"Please use the correct template and save as UTF-8 format.")
                return redirect(referer_url)

            #用于保存不存在的用户email
            sku_error = []

            #获取csv表格每一行的值，i为行数，row该行对应的列的值
            for i, row in enumerate(reader,2):
                #将上传的每一行的值与该行的标题一一对应
                res = zip(field_header,row)
                #转为为字典，方便后面取值
                res = dict(res)

                if res['sku']:
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
                        
                    res['name'] = res['name'].strip().decode('gbk').encode('utf-8')
                    res['catalog_id'] = res['catalog_id'].strip().decode('gbk').encode('utf-8')
                    res['description'] = res['description'].strip().decode('gbk').encode('utf-8')
                    res['description_fr'] = res['description_fr'].strip().decode('gbk').encode('utf-8')
                    res['description_de'] = res['description_de'].strip().decode('gbk').encode('utf-8')
                    res['description_nl'] = res['description_nl'].strip().decode('gbk').encode('utf-8')

                    #去除字典里面的空值
                    res2 = {}
                    for key, value in res.items():
                        if value:
                            res2[key] = value
                    if res2['sku']:
                        product = Product.objects.filter(sku=res2['sku']).first()
                        if product:
                            sql = ""
                            for key, value in res2.items():
                                #价格判断及格式转换
                                if key == 'price':
                                    try:
                                        value = round(float(value),2)
                                    except Exception as e:
                                        value = 0.0

                                if key == 'ssp':
                                    try:
                                        value = round(float(value),2)
                                    except Exception as e:
                                        value = 0.0

                                if key == 'rrp':
                                    try:
                                        value = round(float(value),2)
                                    except Exception as e:
                                        value = 0.0

                                #是否净价
                                if key == 'is_net_price':
                                    try:
                                        value = int(value)
                                    except Exception as e:
                                        value = 0
                                    #是否净价的值只能为0和1
                                    if value != 0 and value != 1:
                                        value = 0

                                #产品分类
                                if key == 'catalog_id':
                                    catalog = Catalog.objects.filter(name=value).first()
                                    if catalog:
                                        value = catalog.id
                                    else:
                                        value = ''

                                #可见性
                                if key == 'visibility':
                                    try:
                                        value = int(value)
                                    except Exception as e:
                                        value = 1
                                    #可见性的值只能为0和1
                                    if value != 0 and value != 1:
                                        value = 1

                                #库存：
                                if key == 'qty':
                                    try:
                                        value = int(value)
                                    except Exception as e:
                                        value = 0

                                #库存2：
                                if key == 'qty2':
                                    try:
                                        value = int(value)
                                    except Exception as e:
                                        value = 0

                                #库存限制标记：
                                if key == 'mark':
                                    try:
                                        value = int(value)
                                    except Exception as e:
                                        value = 1
                                    #库存限制标记至只能为0和1
                                    if value != 0 and value != 1:
                                        value = 1

                                #到货时间
                                if key == 'expected_time':
                                    try:
                                        timearray = time.strptime(str(value), "%Y/%m/%d")
                                        timestamp = int(time.mktime(timearray))
                                        value = timestamp
                                    except Exception as e:
                                        value = ''
                                    #如果格式转化出错，时间为空，则不更新expected_time
                                    if value == '':
                                        continue

                                #更新字段拼接
                                sql += key + " = '" + str(value) + "',"

                            #去掉最后一个','
                            sql = sql.strip(',')

                            sql_update = "UPDATE products_product SET " + sql + "  WHERE id=" + str(product.id)

                            try:
                                cursor = connection.cursor()
                                cursor.execute(sql_update)
                            except Exception as e:
                                print e

                        else:
                            sku_error.append(res2['sku'])

            if sku_error:
                sku_error = tuple(sku_error)
                messages.error(request,"sku(s):"+str(sku_error)+" has not existed.")
                return redirect(referer_url)
            else:
                messages.success(request,"Product(s) update success.")
                return redirect(referer_url)

    return redirect(referer_url)



