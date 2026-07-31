from django.db import models
from django.contrib.auth.models import AbstractUser
import datetime

class User(AbstractUser):
    ROLE_CHOICES = (
        ('ADMIN', 'Admin'),
        ('TEACHER', 'Teacher'),
        ('STUDENT', 'Student'),
    )
    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default='ADMIN')
    phone = models.CharField(max_length=15, blank=True, null=True)
    class Meta:
        db_table = 'api_user'


class PasswordResetToken(models.Model):
    objects = models.Manager()
    identifier = models.CharField(max_length=100)
    role = models.CharField(max_length=20)
    token = models.CharField(max_length=200, unique=True)
    expires_at = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'api_passwordresettoken'
        indexes = [models.Index(fields=['token'])]

    def __str__(self):
        return f"{self.role} - {self.identifier}"

