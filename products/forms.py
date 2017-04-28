# -*- coding: utf-8 -*-
from __future__ import unicode_literals
from django.conf import settings
from django import forms
from django.forms import ModelForm

from products.models import Product
from dal import autocomplete


class OrderItemAdminForm(forms.ModelForm):

    class Meta:
        model = Product
        fields = '__all__'
        # exclude = ['options','sku']
        widgets = {
                # 'options':forms.CheckboxSelectMultiple,
                'product': autocomplete.ModelSelect2(url='product-autocomplete'),
                }

