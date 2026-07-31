from django.db import migrations


def normalize_phones(apps, schema_editor):
    Student = apps.get_model('students', 'Student')
    for student in Student.objects.all():
        phone = student.parent_phone
        if phone:
            phone = phone.strip().replace(" ", "").replace("-", "")
            if phone.startswith('+91'):
                pass  # already correct
            elif phone.startswith('91') and len(phone) == 12:
                student.parent_phone = '+' + phone
                student.save()
            elif len(phone) == 10 and phone.isdigit():
                student.parent_phone = '+91' + phone
                student.save()


class Migration(migrations.Migration):
    dependencies = [
        ('students', '0001_initial'),
    ]
    operations = [
        migrations.RunPython(normalize_phones, migrations.RunPython.noop),
    ]
