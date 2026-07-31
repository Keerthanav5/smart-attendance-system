import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from subjects.models import Subject

for subject in Subject.objects.all():
    # Get the first semester of the assigned class
    first_sem = subject.assigned_class.semesters.first()
    if first_sem:
        subject.semester = first_sem
        subject.save()
        print(f"Assigned {subject} to {first_sem}")
    else:
        print(f"No semester found for class {subject.assigned_class}")
