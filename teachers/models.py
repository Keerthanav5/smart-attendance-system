from django.db import models
from django.contrib.auth.models import AbstractUser
import datetime

class Teacher(models.Model):
    objects = models.Manager()
    name = models.CharField(max_length=150, blank=True)
    email = models.EmailField(unique=True)
    password = models.CharField(max_length=255, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.name} ({self.email})"
    class Meta:
        db_table = 'api_teacher'


