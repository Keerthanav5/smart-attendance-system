from django.db import models
from django.contrib.auth.models import AbstractUser
import datetime

class Subject(models.Model):
    objects = models.Manager()
    code = models.CharField(max_length=20, unique=True)
    name = models.CharField(max_length=100)
    semester = models.ForeignKey('classes.Semester', on_delete=models.CASCADE, related_name='subjects')
    teacher = models.ForeignKey('teachers.Teacher', on_delete=models.SET_NULL, null=True, blank=True, related_name='subjects')

    def __str__(self):
        return f"{self.code} - {self.name}"
    class Meta:
        db_table = 'api_subject'
