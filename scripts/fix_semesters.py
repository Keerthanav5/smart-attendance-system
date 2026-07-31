"""
Run with: python fix_semesters.py
Fixes missing semesters for classes that already exist in the DB.
"""
import os, django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from classes.models import Class, Semester

SEMESTER_MAP = {
    1: [("Sem 1", 1), ("Sem 2", 2)],
    2: [("Sem 3", 3), ("Sem 4", 4)],
    3: [("Sem 5", 5), ("Sem 6", 6)],
    4: [("Sem 7", 7), ("Sem 8", 8)],
}

for cls in Class.objects.all():
    existing_numbers = set(Semester.objects.filter(class_obj=cls).values_list('number', flat=True))
    expected = SEMESTER_MAP.get(cls.year, [])
    print(f"\nClass: {cls.name} | Year: {cls.year} | Existing sems: {sorted(existing_numbers)}")
    for name, num in expected:
        if num not in existing_numbers:
            Semester.objects.create(name=name, number=num, class_obj=cls)
            print(f"  [CREATED] {name} (Sem {num})")
        else:
            print(f"  [OK]      {name} already exists")

print("\nDone.")
