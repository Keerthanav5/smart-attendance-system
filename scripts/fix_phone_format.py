"""
fix_phone_format.py
───────────────────
One-time script: normalise ALL existing parent_phone values in the DB
from +91XXXXXXXXXX / 0XXXXXXXXXX / XXXXXXXXXX → 91XXXXXXXXXX (Fast2SMS format).

Run once:
    python manage.py shell < fix_phone_format.py
"""
import django, os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from students.models import Student

def normalize(phone):
    if not phone:
        return phone
    raw = ''.join(filter(str.isdigit, phone.strip()))
    if raw.startswith('0') and len(raw) == 11:
        raw = raw[1:]
    if raw.startswith('91') and len(raw) == 12:
        return raw          # already correct
    if len(raw) == 10:
        return '91' + raw   # prepend country code
    return phone            # unrecognised — leave unchanged

updated = 0
skipped = 0
unchanged = 0

for student in Student.objects.exclude(parent_phone__isnull=True).exclude(parent_phone=''):
    original = student.parent_phone
    fixed    = normalize(original)
    if fixed == original:
        unchanged += 1
    else:
        student.parent_phone = fixed
        student.save(update_fields=['parent_phone'])
        print(f"  [{student.student_id}] {original!r} → {fixed!r}")
        updated += 1

print(f"\n✅ Done — {updated} updated, {unchanged} already correct, {skipped} skipped.")
