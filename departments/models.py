from django.db import models
from django.contrib.auth.models import AbstractUser
import datetime

class Department(models.Model):
    objects = models.Manager()
    name = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return self.name
    class Meta:
        db_table = 'api_department'


