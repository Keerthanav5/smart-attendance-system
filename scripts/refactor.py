import os
import re

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

VIEWS = {
    'authentication': [
        'admin_login', 'admin_register', 'teacher_login', 'student_login', 
        'logout_view', 'forgot_password', 'validate_reset_token', 'reset_password',
        'student_check_register', 'student_set_password', 'teacher_check_email', 'teacher_set_password'
    ],
    'departments': ['departments', 'department_detail'],
    'classes': ['classes', 'class_detail', 'classes_by_department'],
    'subjects': ['subjects', 'subject_detail', 'subjects_by_class'],
    'teachers': ['teachers', 'teacher_detail'],
    'students': ['students', 'student_detail', 'bulk_upload_students', 'download_upload_template', 'student_detail_dashboard'],
    'timetable': ['timetable', 'timetable_detail', 'today_timetable', 'timetable_by_class'],
    'attendance': ['mark_attendance', 'attendance_status', 'attendance_list', 'attendance_summary', '_get_attendance_summary_data', 'edit_attendance', 'student_attendance_log', '_send_absent_emails'],
    'reports': ['reports_data', 'export_excel', 'export_csv', 'export_pdf'],
    'notifications': ['notification_logs', 'send_absent_alerts', 'send_class_absent_alerts', 'mock_send_sms'],
    'dashboard': ['admin_stats', 'teacher_stats', 'student_dashboard', 'student_calendar'],
    'utils': ['get_student_from_token', 'get_teacher_from_token', 'mask_email', 'calculate_student_percent', 'global_search', 'system_settings', 'test_email']
}

URLS = {
    'authentication': [
        'auth/admin-login/', 'auth/admin-register/', 'auth/teacher-login/', 'auth/student-login/',
        'auth/logout/', 'auth/forgot-password/', 'auth/validate-reset-token/', 'auth/reset-password/',
        'auth/student/check-register/', 'auth/student/set-password/', 'auth/teacher/check-email/', 'auth/teacher/set-password/'
    ],
    'departments': ['departments/'],
    'classes': ['classes/'],
    'subjects': ['subjects/'],
    'teachers': ['teachers/'],
    'students': ['students/'],
    'timetable': ['timetable/'],
    'attendance': ['attendance/'],
    'reports': ['reports/'],
    'notifications': ['notifications/'],
    'dashboard': ['stats/', 'student/'],
    'utils': ['search/', 'settings/']
}

def parse_blocks(file_path, block_start_pattern):
    with open(file_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()
        
    blocks = {}
    current_block = None
    current_lines = []
    
    for i, line in enumerate(lines):
        match = re.match(block_start_pattern, line)
        if match:
            if current_block:
                blocks[current_block] = ''.join(current_lines)
            current_block = match.group(1)
            current_lines = []
            
            # If the previous line was a decorator, it belongs to this block
            j = i - 1
            decorator_lines = []
            while j >= 0 and (lines[j].startswith('@') or lines[j].startswith(' ')):
                if lines[j].startswith('@'):
                    decorator_lines.insert(0, lines[j])
                j -= 1
            
            # Some decorators were already added to the previous block by mistake, let's fix
            # Actually, simpler: we just extract blocks by name. We will use AST to get exact line numbers.
            pass
            
    return blocks

# Let's use ast to get start and end lines
import ast

def extract_nodes(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        source = f.read()
        
    tree = ast.parse(source)
    nodes = {}
    
    lines = source.split('\n')
    
    for i, node in enumerate(tree.body):
        if isinstance(node, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
            start_line = node.lineno - 1
            # Check for decorators
            if node.decorator_list:
                start_line = node.decorator_list[0].lineno - 1
            
            end_line = node.end_lineno
            # Get the exact source for this node
            node_source = '\n'.join(lines[start_line:end_line])
            nodes[node.name] = node_source
            
    return nodes

def setup_apps():
    # 1. Create folders
    for app in APPS.keys():
        os.makedirs(app, exist_ok=True)
        with open(f'{app}/__init__.py', 'w') as f:
            pass
            
    # 2. Extract models and views
    models_source = extract_nodes('backend/api/models.py')
    views_source = extract_nodes('backend/api/views.py')
    page_views_source = extract_nodes('backend/api/page_views.py')
    
    # 3. Create models.py for each app
    for app, models in APPS.items():
        if app in ['config', 'static_templates']: continue
        
        with open(f'{app}/models.py', 'w', encoding='utf-8') as f:
            f.write("from django.db import models\n")
            f.write("from django.contrib.auth.models import AbstractUser\n")
            f.write("import datetime\n\n")
            
            # Import models from other apps using strings or direct imports
            # We will just write the models and inject db_table to prevent migration issues
            for model in models:
                if model in models_source:
                    source = models_source[model]
                    # inject db_table if not exists
                    if "class Meta:" not in source:
                        source += f"\n    class Meta:\n        db_table = 'api_{model.lower()}'\n"
                    else:
                        # Ensure we don't break existing Meta
                        if "db_table" not in source:
                            source = source.replace("class Meta:", f"class Meta:\n        db_table = 'api_{model.lower()}'")
                    f.write(source + "\n\n")
                    
    # 4. Create views.py for each app
    for app, views in VIEWS.items():
        if app in ['config', 'static_templates']: continue
        
        with open(f'{app}/views.py', 'w', encoding='utf-8') as f:
            f.write("import os, io, csv, uuid, jwt, secrets, logging, datetime as dt\n")
            f.write("from django.shortcuts import render, redirect\n")
            f.write("from django.http import HttpResponse\n")
            f.write("from django.contrib.auth import authenticate, login, logout\n")
            f.write("from django.contrib.auth.hashers import make_password, check_password\n")
            f.write("from django.core.mail import send_mail\n")
            f.write("from django.template.loader import render_to_string\n")
            f.write("from django.conf import settings\n")
            f.write("from django.db import transaction\n")
            f.write("from django.db.models import Q, Count, Avg\n")
            f.write("from django.utils import timezone\n")
            f.write("from rest_framework.decorators import api_view, parser_classes\n")
            f.write("from rest_framework.parsers import MultiPartParser, FormParser\n")
            f.write("from rest_framework.response import Response\n")
            
            # Import ALL models from all apps (dirty but guarantees no MissingImport)
            for m_app, m_models in APPS.items():
                if m_models:
                    f.write(f"from {m_app}.models import {', '.join(m_models)}\n")
                    
            f.write("try:\n    from utils.views import get_student_from_token, get_teacher_from_token, mask_email, calculate_student_percent\nexcept ImportError:\n    pass\n")
            f.write("from utils.notifications import send_sms\n\n")
            
            f.write("logger = logging.getLogger(__name__)\n\n")
            
            for view in views:
                if view in views_source:
                    f.write(views_source[view] + "\n\n")
                    
    # Move page_views to dashboard/page_views.py
    with open('dashboard/page_views.py', 'w', encoding='utf-8') as f:
        with open('backend/api/page_views.py', 'r', encoding='utf-8') as pv:
            f.write(pv.read())
            
    print("Nodes extracted and files generated!")

if __name__ == "__main__":
    setup_apps()
