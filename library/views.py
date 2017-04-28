#-*- coding:utf-8 -*-
import sys
from django.conf import settings
from django.template import loader
from django.core.mail import EmailMultiAlternatives
import demjson
reload(sys)
sys.setdefaultencoding('utf8')
from django.shortcuts import render
from django.http import HttpResponse, HttpResponseRedirect
from promotions.models import Promotion

def sendEmail(email,template,data):
    if not email.has_key('sender'):
        email['sender'] = settings.DEFAULT_FROM_EMAIL
    if not email.has_key('receiver'):
        return False
    if not email.has_key('copy'):
        email['copy'] = []
    if not template:
        return False
    if not data:
        return False
    subject = 'RIVE – B2B UPDATE'

    html_content = loader.render_to_string(
        template,  # 需要渲染的html模板
        data
    )

    try:
        msg = EmailMultiAlternatives(subject, html_content, email['sender'], email['receiver'],email['copy'])
        msg.content_subtype = "html"
        msg.send()
    except Exception as e:
        # print e.message
        return False
    else:
        return True


def getCookie(request):
    lang = ''
    
    try:
        lang = request.COOKIES['lang']
    except Exception as e:
        lang = ''

    return lang


def get_promotion(request):
    promotion = Promotion.objects.filter(visibility=1).first()
    if promotion:
        return 1
    else:
        return 0

