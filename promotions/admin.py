#-*- coding: utf-8 -*-
from django.contrib import admin
from .models import Promotion



class PromotionAdmin(admin.ModelAdmin):
    model = Promotion

    save_as = True
    save_on_top = True
    list_display = ('id','content','visibility','created','updated')
    fields = ('visibility','content',)
admin.site.register(Promotion,PromotionAdmin)