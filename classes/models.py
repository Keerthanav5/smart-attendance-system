from django.db import models
from django.contrib.auth.models import AbstractUser
import datetime

class Class(models.Model):
    objects = models.Manager()
    name = models.CharField(max_length=100)
    department = models.ForeignKey('departments.Department', on_delete=models.CASCADE, related_name='classes')
    year = models.IntegerField(default=1)

    class Meta:
        db_table = 'api_class'
        unique_together = ('name', 'department')

    def __str__(self):
        return f"{self.name} - {self.department.name} Year {self.year}"

class Semester(models.Model):
    name = models.CharField(max_length=10)
    number = models.IntegerField()
    class_obj = models.ForeignKey(Class, on_delete=models.CASCADE, related_name='semesters')

    class Meta:
        db_table = 'api_semester'
        unique_together = ('class_obj', 'number')

    def __str__(self):
        return f"{self.class_obj.name} - {self.name}"

from django.db.models.signals import post_save
from django.dispatch import receiver

SEMESTER_MAP = {
    1: [("Sem 1", 1), ("Sem 2", 2)],
    2: [("Sem 3", 3), ("Sem 4", 4)],
    3: [("Sem 5", 5), ("Sem 6", 6)],
    4: [("Sem 7", 7), ("Sem 8", 8)],
}

@receiver(post_save, sender=Class)
def create_semesters_for_class(sender, instance, created, **kwargs):
    """Ensure the correct semesters exist for this class.
    Uses get_or_create so it is safe to call on both new and existing classes.
    """
    expected = SEMESTER_MAP.get(instance.year, [])
    for name, number in expected:
        Semester.objects.get_or_create(
            class_obj=instance,
            number=number,
            defaults={'name': name},
        )
