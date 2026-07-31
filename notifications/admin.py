from django.contrib import admin
from .models import NotificationLog, SMSLog

admin.site.register([NotificationLog, SMSLog])
