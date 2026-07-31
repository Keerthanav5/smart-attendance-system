import os
import glob
d = r'c:\Users\Admin\OneDrive\Desktop\smart_attendance_v2\templates\admin'
for f in glob.glob(os.path.join(d, '*.html')):
    with open(f, 'r', encoding='utf-8') as file:
        content = file.read()
    
    # Check for active and inactive links
    changed = False
    if '<a class="nav-link active" href="/admin/timetable/">📅 Timetable</a>\n' in content:
        content = content.replace('<a class="nav-link active" href="/admin/timetable/">📅 Timetable</a>\n', '')
        changed = True
    if '<a class="nav-link" href="/admin/timetable/">📅 Timetable</a>\n' in content:
        content = content.replace('<a class="nav-link" href="/admin/timetable/">📅 Timetable</a>\n', '')
        changed = True

    if changed:
        with open(f, 'w', encoding='utf-8') as file:
            file.write(content)
        print('Updated', f)
