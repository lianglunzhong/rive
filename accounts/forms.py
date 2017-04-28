# -*- coding: utf-8 -*-
from django.core.exceptions import ValidationError
from django.conf import settings
from django import forms

#用户登录
class LoginForm(forms.Form):
	email = forms.EmailField(error_messages={'required':u'邮箱不能为空','invalid':u'请输入正确的邮箱'})
	password = forms.CharField(widget=forms.PasswordInput(),error_messages={'required':u'密码不能为空'})


	def clean_eamil(self):
		from accounts.models import Customer
		data = self.cleaned_data('email')
		is_exist = Customer.objects.filter(email=data).exists()

		if not is_exist:
			raise forms.ValidationError('NOT EXIST')
		return data