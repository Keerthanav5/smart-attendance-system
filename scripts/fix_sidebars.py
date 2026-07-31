import os
import glob

for file in glob.glob('templates/admin/*.html'):
    with open(file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    if '/admin/timetable/' not in content:
        content = content.replace(
            '<a class="nav-link" href="/admin/students/">🎓 Students</a>',
            '<a class="nav-link" href="/admin/students/">🎓 Students</a>\n<a class="nav-link" href="/admin/timetable/">📅 Timetable</a>'
        )
        content = content.replace(
            '<a class="nav-link active" href="/admin/students/">🎓 Students</a>',
            '<a class="nav-link active" href="/admin/students/">🎓 Students</a>\n<a class="nav-link" href="/admin/timetable/">📅 Timetable</a>'
        )
        with open(file, 'w', encoding='utf-8') as f:
            f.write(content)
print("Done patching sidebars!")
