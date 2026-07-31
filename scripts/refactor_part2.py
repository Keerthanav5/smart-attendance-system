import os
import re
import shutil

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
    'reports': [],
    'dashboard': [],
    'utils': ['SystemSettings'],
    'static_templates': [],
    'config': []
}

URLS = {
    'authentication': [
        'auth/admin-login/', 'auth/admin-register/', 'auth/teacher-login/', 'auth/student-login/',
        'auth/logout/', 'auth/forgot-password/', 'auth/validate-reset-token/', 'auth/reset-password/',
        'auth/student/check-register/', 'auth/student/set-password/', 'auth/teacher/check-email/', 'auth/teacher/set-password/'
    ],
    'departments': ['departments/', 'departments/<int:pk>/'],
    'classes': ['classes/', 'classes/by-department/<int:dept_id>/', 'classes/<int:pk>/'],
    'subjects': ['subjects/', 'subjects/by-class/<int:class_id>/', 'subjects/<int:pk>/'],
    'teachers': ['teachers/', 'teachers/<int:pk>/'],
    'students': ['students/', 'students/bulk-upload/', 'students/upload-template/', 'students/<str:student_id>/dashboard/', 'students/<str:student_id>/'],
    'timetable': ['timetable/', 'timetable/today/', 'timetable/class/<int:class_id>/', 'timetable/<int:pk>/'],
    'attendance': ['attendance/mark/', 'attendance/edit/', 'attendance/status/', 'attendance/list/', 'attendance/summary/'],
    'reports': ['reports/data/', 'reports/export/excel/', 'reports/export/csv/', 'reports/export/pdf/'],
    'notifications': ['notifications/', 'notifications/send-alerts/', 'notifications/send-class-alerts/'],
    'dashboard': ['stats/admin/', 'stats/teacher/', 'student/dashboard/', 'student/calendar/', 'student/attendance-log/'],
    'utils': ['search/', 'settings/', 'settings/test-email/']
}

# Mapping model name -> 'app.Model'
MODEL_MAP = {}
for app, models in APPS.items():
    for model in models:
        MODEL_MAP[model] = f"'{app}.{model}'"

def fix_models():
    for app in APPS.keys():
        if app in ['config', 'static_templates']: continue
        model_file = f'{app}/models.py'
        if not os.path.exists(model_file): continue
        with open(model_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Replace ForeignKey(Model, ...) with ForeignKey('app.Model', ...)
        def replacer(match):
            field_type = match.group(1)
            model_name = match.group(2)
            if model_name in MODEL_MAP:
                return f"models.{field_type}({MODEL_MAP[model_name]},"
            return match.group(0)
            
        content = re.sub(r'models\.(ForeignKey|OneToOneField|ManyToManyField)\(\s*([A-Za-z]+)\s*,', replacer, content)
        
        # Fix indexes (e.g. models.Index)
        # There's no cross-app index issue directly if we use strings, but indexes don't use model classes.
        
        with open(model_file, 'w', encoding='utf-8') as f:
            f.write(content)

def generate_urls():
    for app, urls in URLS.items():
        if app in ['config', 'static_templates']: continue
        with open(f'{app}/urls.py', 'w', encoding='utf-8') as f:
            f.write("from django.urls import path\n")
            f.write("from . import views\n\n")
            f.write("urlpatterns = [\n")
            for url in urls:
                # Need to map the url string to the corresponding view function
                # This requires parsing backend/api/urls.py
                pass
            f.write("]\n")

def parse_original_urls():
    # Read backend/api/urls.py
    with open('backend/api/urls.py', 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Extract path('...', views.func_name)
    pattern = r"path\(['\"]([^'\"]+)['\"]\s*,\s*views\.([a-zA-Z0-9_]+)[^\)]*\)"
    matches = re.findall(pattern, content)
    url_to_view = {m[0]: m[1] for m in matches}
    return url_to_view

def generate_app_urls(url_to_view):
    for app, urls in URLS.items():
        if app in ['config', 'static_templates']: continue
        with open(f'{app}/urls.py', 'w', encoding='utf-8') as f:
            f.write("from django.urls import path\n")
            f.write("from . import views\n\n")
            f.write("urlpatterns = [\n")
            for url in urls:
                # The original URLs don't have '/api/', they are exactly like the URLS list
                view_func = url_to_view.get(url)
                if view_func:
                    # Strip the prefix defined in config/urls.py (e.g. 'auth/') because include('auth.urls') will handle it
                    # But the user asked for: include: /api/auth/, /api/departments/...
                    # Let's just output the exact string minus the app prefix.
                    # Wait, the user said: include: /api/auth/
                    # So in auth/urls.py, the path should be 'admin-login/' instead of 'auth/admin-login/'.
                    prefix = app + '/' if app != 'authentication' else 'auth/'
                    if app == 'dashboard' and url.startswith('stats/'): prefix = 'stats/'
                    elif app == 'dashboard' and url.startswith('student/'): prefix = 'student/'
                    elif app == 'utils' and url.startswith('search/'): prefix = 'search/'
                    elif app == 'utils' and url.startswith('settings/'): prefix = 'settings/'
                    
                    sub_url = url
                    if sub_url.startswith(prefix):
                        sub_url = sub_url[len(prefix):]
                        
                    f.write(f"    path('{sub_url}', views.{view_func}),\n")
            f.write("]\n")

def move_config():
    if os.path.exists('backend/smart_attendance'):
        shutil.copytree('backend/smart_attendance', 'config', dirs_exist_ok=True)
    
    # Update settings.py
    with open('config/settings.py', 'r', encoding='utf-8') as f:
        settings = f.read()
    
    # Change ROOT_URLCONF = 'smart_attendance.urls' to 'config.urls'
    settings = settings.replace("'smart_attendance.urls'", "'config.urls'")
    settings = settings.replace("WSGI_APPLICATION = 'smart_attendance.wsgi.application'", "WSGI_APPLICATION = 'config.wsgi.application'")
    
    # Replace 'api' in INSTALLED_APPS
    apps_list = ["'" + a + "'" for a in APPS.keys() if a != 'config']
    apps_str = ",\n    ".join(apps_list)
    settings = re.sub(r"'api'\s*,", apps_str + ",", settings)
    
    # Auth user model
    settings = settings.replace("AUTH_USER_MODEL = 'api.User'", "AUTH_USER_MODEL = 'authentication.User'")
    
    with open('config/settings.py', 'w', encoding='utf-8') as f:
        f.write(settings)
        
    # Update wsgi.py and asgi.py
    for file in ['wsgi.py', 'asgi.py']:
        path = f'config/{file}'
        if os.path.exists(path):
            with open(path, 'r', encoding='utf-8') as f:
                content = f.read()
            content = content.replace("smart_attendance.settings", "config.settings")
            with open(path, 'w', encoding='utf-8') as f:
                f.write(content)

def create_config_urls():
    with open('config/urls.py', 'w', encoding='utf-8') as f:
        f.write("from django.contrib import admin\n")
        f.write("from django.urls import path, include\n")
        f.write("from django.conf import settings\n")
        f.write("from django.conf.urls.static import static\n")
        f.write("from dashboard import page_views\n\n")
        f.write("urlpatterns = [\n")
        f.write("    path('django-admin/', admin.site.urls),\n")
        f.write("    path('api/auth/', include('authentication.urls')),\n")
        f.write("    path('api/departments/', include('departments.urls')),\n")
        f.write("    path('api/classes/', include('classes.urls')),\n")
        f.write("    path('api/subjects/', include('subjects.urls')),\n")
        f.write("    path('api/students/', include('students.urls')),\n")
        f.write("    path('api/teachers/', include('teachers.urls')),\n")
        f.write("    path('api/attendance/', include('attendance.urls')),\n")
        f.write("    path('api/timetable/', include('timetable.urls')),\n")
        f.write("    path('api/notifications/', include('notifications.urls')),\n")
        f.write("    path('api/reports/', include('reports.urls')),\n")
        f.write("    path('api/stats/', include('dashboard.urls')),\n") # Dashboard stats logic
        f.write("    path('api/student/', include('dashboard.urls')),\n") # Dashboard student logic
        f.write("    path('api/search/', include('utils.urls')),\n")
        f.write("    path('api/settings/', include('utils.urls')),\n\n")
        f.write("    # Frontend UI routes\n")
        f.write("    path('', page_views.redirect_root),\n")
        f.write("    path('login/', page_views.admin_login_page),\n")
        f.write("    path('admin/register/', page_views.admin_register_page),\n")
        f.write("    path('logout/', page_views.logout_page),\n")
        f.write("    path('teacher/login/', page_views.teacher_login_page),\n")
        f.write("    path('teacher/register/', page_views.teacher_register_page),\n")
        f.write("    path('teacher/forgot-password/', page_views.teacher_forgot_page),\n")
        f.write("    path('teacher/reset-password/', page_views.reset_password_page),\n")
        f.write("    path('student/login/', page_views.student_login_page),\n")
        f.write("    path('student/register/', page_views.student_register_page),\n")
        f.write("    path('student/forgot-password/', page_views.student_forgot_page),\n")
        f.write("    path('student/reset-password/', page_views.reset_password_page),\n")
        f.write("    path('admin-dashboard/', page_views.admin_dashboard_page),\n")
        f.write("    path('admin/departments/', page_views.departments_page),\n")
        f.write("    path('admin/classes/', page_views.classes_page),\n")
        f.write("    path('admin/subjects/', page_views.subjects_page),\n")
        f.write("    path('admin/teachers/', page_views.teachers_page),\n")
        f.write("    path('admin/students/', page_views.students_page),\n")
        f.write("    path('admin/students/upload/', page_views.upload_students_page),\n")
        f.write("    path('admin/students/<str:student_id>/', page_views.admin_student_detail_page),\n")
        f.write("    path('admin/holidays/', page_views.holidays_page),\n")
        f.write("    path('admin/reports/', page_views.reports_page),\n")
        f.write("    path('admin/notifications/', page_views.notifications_page),\n")
        f.write("    path('teacher/dashboard/', page_views.teacher_dashboard_page),\n")
        f.write("    path('teacher/mark-attendance/', page_views.mark_attendance_page),\n")
        f.write("    path('teacher/edit-attendance/', page_views.edit_attendance_page),\n")
        f.write("    path('teacher/attendance-percentage/', page_views.teacher_percentage_page),\n")
        f.write("    path('teacher/timetable/', page_views.teacher_timetable_page),\n")
        f.write("    path('teacher/notifications/', page_views.teacher_notifications_page),\n")
        f.write("    path('teacher/students/', page_views.teacher_students_page),\n")
        f.write("    path('teacher/students/<str:student_id>/', page_views.student_detail_page),\n")
        f.write("    path('student/dashboard/', page_views.student_dashboard_page),\n")
        f.write("    path('student/attendance/', page_views.student_attendance_page),\n")
        f.write("    path('student/attendance-percentage/', page_views.student_percentage_page),\n")
        f.write("] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)\n")

def fix_manage_py():
    with open('manage.py', 'r', encoding='utf-8') as f:
        content = f.read()
    content = content.replace("'smart_attendance.settings'", "'config.settings'")
    with open('manage.py', 'w', encoding='utf-8') as f:
        f.write(content)

if __name__ == "__main__":
    fix_models()
    url_map = parse_original_urls()
    generate_app_urls(url_map)
    move_config()
    create_config_urls()
    fix_manage_py()
    print("Part 2 complete!")
