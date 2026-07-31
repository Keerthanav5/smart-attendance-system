from django.db import models
from django.contrib.auth.models import AbstractUser
import datetime

class Timetable(models.Model):
    objects = models.Manager()
    DAY_CHOICES = [
        ('Monday', 'Monday'), ('Tuesday', 'Tuesday'),
        ('Wednesday', 'Wednesday'), ('Thursday', 'Thursday'),
        ('Friday', 'Friday'), ('Saturday', 'Saturday'),
    ]
    semester = models.ForeignKey('classes.Semester', on_delete=models.CASCADE, related_name='timetable_entries', null=True)
    subject = models.ForeignKey('subjects.Subject', on_delete=models.CASCADE)
    teacher = models.ForeignKey('teachers.Teacher', on_delete=models.SET_NULL, null=True, blank=True)
    day = models.CharField(max_length=20, choices=DAY_CHOICES)
    period_number = models.IntegerField(default=1)
    start_time = models.TimeField()
    end_time = models.TimeField()

    def __str__(self):
        return f"{self.day} P{self.period_number} - {self.subject.name}"
    class Meta:
        db_table = 'api_timetable'


