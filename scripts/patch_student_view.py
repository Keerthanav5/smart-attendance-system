import os

# 1. Create admin/student_detail.html
teacher_detail_path = 'templates/teacher/student_detail.html'
admin_detail_path = 'templates/admin/student_detail.html'

with open(teacher_detail_path, 'r', encoding='utf-8') as f:
    content = f.read()

# Replace sidebar
old_sidebar = """<div class="nav-section">Teacher Portal</div>
<a class="nav-link" href="/teacher/dashboard/">🏠 Dashboard</a>
<a class="nav-link" href="/teacher/mark-attendance/">✏️ Mark Attendance</a>
<a class="nav-link" href="/teacher/edit-attendance/">📝 Edit Attendance</a>
<a class="nav-link" href="/teacher/attendance-percentage/">📊 Attendance Percentage</a>
<a class="nav-link" href="/teacher/timetable/">📅 Timetable</a>
<a class="nav-link" href="/teacher/notifications/">🔔 Notifications</a>
<a class="nav-link" href="/teacher/students/">🎓 Students View</a>"""

new_sidebar = """<div class="nav-section">Main</div>
<a class="nav-link" href="/admin-dashboard/">🏠 Dashboard</a>
<div class="nav-section">Management</div>
<a class="nav-link" href="/admin/departments/">🏢 Departments</a>
<a class="nav-link" href="/admin/classes/">📁 Classes</a>
<a class="nav-link" href="/admin/subjects/">📚 Subjects</a>
<a class="nav-link" href="/admin/teachers/">👨‍🏫 Teachers</a>
<a class="nav-link" href="/admin/students/">🎓 Students</a>
<div class="nav-section">Academic</div>
<a class="nav-link" href="/admin/holidays/">⭐ Holidays</a>
<a class="nav-link" href="/admin/reports/">📊 Reports</a>"""

content = content.replace(old_sidebar, new_sidebar)

# Replace JS token check
js_old = """const token = localStorage.getItem('teacher_token')||'';
if(!token) window.location.href='/teacher/login/';

document.getElementById('userAvatar').textContent=(localStorage.getItem('teacher_name')||'T').charAt(0).toUpperCase();
document.getElementById('userName').textContent=localStorage.getItem('teacher_name')||'Teacher';
document.getElementById('userRole').textContent='Teacher';"""

js_new = """// Admin is authenticated via session
document.getElementById('userAvatar').textContent='A';
document.getElementById('userName').textContent='Admin';
document.getElementById('userRole').textContent='Administrator';"""

content = content.replace(js_old, js_new)

# Remove Authorization header from fetch
content = content.replace(", {\n      headers: { 'Authorization': 'Bearer ' + token }\n    }", "")

with open(admin_detail_path, 'w', encoding='utf-8') as f:
    f.write(content)


# 2. Update templates/admin/students.html
admin_students_path = 'templates/admin/students.html'
with open(admin_students_path, 'r', encoding='utf-8') as f:
    content = f.read()

target = "<button class=\"btn btn-secondary btn-sm\" onclick='editStudent(${JSON.stringify(s)})'>Edit</button>"
replacement = "<a href=\"/admin/students/${s.student_id}/\" class=\"btn btn-primary btn-sm\">View</a>\n        " + target

content = content.replace(target, replacement)

with open(admin_students_path, 'w', encoding='utf-8') as f:
    f.write(content)


# 3. Update templates/teacher/students.html
teacher_students_path = 'templates/teacher/students.html'
with open(teacher_students_path, 'r', encoding='utf-8') as f:
    content = f.read()

target = "<button class=\"btn btn-secondary btn-sm\" onclick='editStudent(${JSON.stringify(s)})'>Edit</button>"
replacement = "<a href=\"/teacher/students/${s.student_id}/\" class=\"btn btn-primary btn-sm\">View</a>\n        " + target

content = content.replace(target, replacement)

with open(teacher_students_path, 'w', encoding='utf-8') as f:
    f.write(content)

print("Done patching student detail views.")
