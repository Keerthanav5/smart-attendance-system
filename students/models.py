from django.db import models
from django.contrib.auth.models import AbstractUser
import datetime

class Student(models.Model):
    objects = models.Manager()
    user = models.OneToOneField('authentication.User', on_delete=models.CASCADE, primary_key=True)
    student_id = models.CharField(max_length=50, unique=True)
    name = models.CharField(max_length=150, blank=True, null=True)
    email = models.EmailField(blank=True, null=True)
    password = models.CharField(max_length=255, blank=True)
    is_registered = models.BooleanField(default=False)
    department = models.ForeignKey('departments.Department', on_delete=models.SET_NULL, null=True, blank=True)
    assigned_class = models.ForeignKey('classes.Class', on_delete=models.SET_NULL, null=True, blank=True)
    parent_name = models.CharField(max_length=150, blank=True, null=True)
    parent_email = models.EmailField(blank=True, null=True)
    parent_phone = models.CharField(max_length=15, blank=True, null=True)
    preferred_language = models.CharField(max_length=10, default='en')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.student_id} - {self.name}"
    class Meta:
        db_table = 'api_student'


