#-*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models
from django_unixdatetimefield import UnixDateTimeField
from ckeditor.fields import RichTextField
from ckeditor_uploader.fields import RichTextUploadingField


class Promotion(models.Model):
    VISIBILITY = (
            (1,"visible"),
            (0,u"invisible"),
        )

    # content = RichTextField(config_name='awesome_ckeditor')
    visibility = models.IntegerField(choices=VISIBILITY, default=0, verbose_name=u"Visibility")
    content = RichTextUploadingField('contents')
    created = UnixDateTimeField(auto_now_add=True, blank=True, null=True, verbose_name=u"Create")
    updated = UnixDateTimeField(auto_now=True,blank=True,null=True, verbose_name=u"Update")


        