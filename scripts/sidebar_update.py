import os
import glob
import re

admin_sidebar = """{% block sidebar_links %}
<div class="nav-section">Main</div>
<a class="nav-link" href="/admin-dashboard/">🏠 Dashboard</a>
<div class="nav-section">Management</div>
<a class="nav-link" href="/admin/departments/">🏢 Departments</a>
<a class="nav-link" href="/admin/classes/">📁 Classes</a>
<a class="nav-link" href="/admin/subjects/">📚 Subjects</a>
<a class="nav-link" href="/admin/students/">🎓 Students</a>
<div class="nav-section">Academic</div>
<a class="nav-link" href="/admin/holidays/">⭐ Holidays</a>
<a class="nav-link" href="/admin/reports/">📊 Reports</a>
<a class="nav-link" href="/admin/notifications/">🔔 Notifications</a>
{% endblock %}"""

teacher_sidebar = """{% block sidebar_links %}
<div class="nav-section">Teacher Portal</div>
<a class="nav-link" href="/teacher/dashboard/">🏠 Dashboard</a>
<a class="nav-link" href="/teacher/mark-attendance/">✏️ Mark Attendance</a>
<a class="nav-link" href="/teacher/edit-attendance/">📝 Edit Attendance</a>
<a class="nav-link" href="/teacher/attendance-percentage/">📊 Attendance Percentage</a>
<a class="nav-link" href="/teacher/timetable/">📅 Timetable</a>
<a class="nav-link" href="/teacher/notifications/">🔔 Notifications</a>
<a class="nav-link" href="/teacher/students/">🎓 Students View</a>
{% endblock %}"""

student_sidebar = """{% block sidebar_links %}
<div class="nav-section">Student Portal</div>
<a class="nav-link" href="/student/dashboard/">🏠 Dashboard</a>
<a class="nav-link" href="/student/attendance/">📝 Attendance</a>
<a class="nav-link" href="/student/attendance-percentage/">📊 Attendance Percentage</a>
{% endblock %}"""

def replace_sidebar(folder, new_sidebar):
    for f in glob.glob(os.path.join(folder, '*.html')):
        with open(f, 'r', encoding='utf-8') as file:
            content = file.read()
        
        # Regex to find block sidebar_links ... endblock
        pattern = re.compile(r'{%\s*block sidebar_links\s*%}.*?{%\s*endblock\s*%}', re.DOTALL)
        
        if pattern.search(content):
            content = pattern.sub(new_sidebar, content)
            
            # Re-add 'active' class based on filename if needed, or we can just let JS handle it, 
            # but usually it's server rendered. We'll leave it without active and use JS in base.html if needed,
            # or just rely on the current state.
            
            with open(f, 'w', encoding='utf-8') as file:
                file.write(content)
            print('Updated', f)

base_path = r'c:\Users\Admin\OneDrive\Desktop\smart_attendance_v2\templates'
replace_sidebar(os.path.join(base_path, 'admin'), admin_sidebar)
replace_sidebar(os.path.join(base_path, 'teacher'), teacher_sidebar)
replace_sidebar(os.path.join(base_path, 'student'), student_sidebar)
