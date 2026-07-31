from django.db import models
from django.contrib.auth.models import AbstractUser
import datetime

class SystemSettings(models.Model):
    objects = models.Manager()
    college_name = models.CharField(max_length=200, default='My College')
    college_logo = models.ImageField(upload_to='college/', null=True, blank=True)
    principal_name = models.CharField(max_length=150, blank=True)
    college_address = models.TextField(blank=True)
    academic_year = models.CharField(max_length=20, default='2025-2026')
    semester = models.CharField(max_length=50, default='Even Semester')
    min_attendance_percent = models.IntegerField(default=75)
    auto_send_alerts = models.BooleanField(default=True)

    class Meta:
        db_table = 'api_systemsettings'
        verbose_name = 'System Settings'

    @classmethod
    def get(cls):
        obj, _ = cls.objects.get_or_create(id=1)
        return obj

    def __str__(self):
        return self.college_name

