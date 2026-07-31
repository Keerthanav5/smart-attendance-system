import os

APPS = {
    'authentication': ['User', 'PasswordResetToken'],
    'departments': ['Department'],
    'classes': ['Class'],
    'subjects': ['Subject'],
    'students': ['Student'],
    'teachers': ['Teacher'],
    'timetable': ['Timetable'],
    'attendance': ['Attendance', 'Holiday'],
    'notifications': ['NotificationLog'],
    'utils': ['SystemSettings'],
}

for app, models in APPS.items():
    if not os.path.exists(app):
        continue
    with open(f'{app}/admin.py', 'w', encoding='utf-8') as f:
        f.write("from django.contrib import admin\n")
        if models:
            f.write(f"from .models import {', '.join(models)}\n")
            f.write(f"admin.site.register([{', '.join(models)}])\n")

print("admin.py created for all apps")
