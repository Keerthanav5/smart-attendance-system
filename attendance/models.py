from django.db import models
from django.contrib.auth.models import AbstractUser
import datetime

class Attendance(models.Model):
    objects = models.Manager()
    student = models.ForeignKey('students.Student', on_delete=models.CASCADE)
    subject = models.ForeignKey('subjects.Subject', on_delete=models.CASCADE)
    date = models.DateField(default=datetime.date.today)
    period_number = models.IntegerField(default=1)
    time = models.TimeField(null=True, blank=True)
    is_present = models.BooleanField(default=False)
    marked_by = models.ForeignKey('teachers.Teacher', on_delete=models.SET_NULL, null=True)

    class Meta:
        db_table = 'api_attendance'
        unique_together = ('student', 'subject', 'date', 'period_number')
        indexes = [
            models.Index(fields=['student', 'date']),
            models.Index(fields=['subject', 'date']),
        ]

    def __str__(self):
        status = 'Present' if self.is_present else 'Absent'
        return f"{self.student.student_id} - {self.subject.name} - {self.date} - {status}"

class Holiday(models.Model):
    objects = models.Manager()
    date = models.DateField(unique=True)
    name = models.CharField(max_length=100)

    def __str__(self):
        return f"{self.date} - {self.name}"
    class Meta:
        db_table = 'api_holiday'


