import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from classes.models import Class, Semester, create_semesters_for_class

for c in Class.objects.all():
    create_semesters_for_class(Class, c, True)
    print(f"Created semesters for {c}")
