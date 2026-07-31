from django.contrib import admin
from .models import Attendance, Holiday
admin.site.register([Attendance, Holiday])
