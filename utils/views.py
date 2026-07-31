import os, io, csv, uuid, jwt, secrets, logging, datetime as dt
from django.shortcuts import render, redirect
from django.http import HttpResponse
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.hashers import make_password, check_password
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.conf import settings
from django.db import transaction
from django.db.models import Q, Count, Avg
from django.utils import timezone
from rest_framework.decorators import api_view, parser_classes
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.response import Response
from authentication.models import User, PasswordResetToken
from departments.models import Department
from classes.models import Class
from subjects.models import Subject
from students.models import Student
from teachers.models import Teacher
from timetable.models import Timetable
from attendance.models import Attendance, Holiday
from notifications.models import NotificationLog
from utils.models import SystemSettings
try:
    from utils.views import get_student_from_token, get_teacher_from_token, mask_email, calculate_student_percent
except ImportError:
    pass
from utils.notifications import send_sms

logger = logging.getLogger(__name__)

def get_student_from_token(request):
    auth = request.headers.get('Authorization', '')
    token = auth.replace('Bearer ', '').strip()
    if not token:
        return None
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=['HS256'])
        if payload.get('role') != 'STUDENT':
            return None
        return Student.objects.select_related('assigned_class', 'department').get(
            student_id=payload['student_id']
        )
    except Exception:
        return None

def get_teacher_from_token(request):
    auth = request.headers.get('Authorization', '')
    token = auth.replace('Bearer ', '').strip()
    if not token:
        return None
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=['HS256'])
        if payload.get('role') != 'TEACHER':
            return None
        return Teacher.objects.get(id=payload['teacher_id'])
    except Exception:
        return None

def mask_email(email):
    if not email or '@' not in email:
        return email
    local, domain = email.split('@', 1)
    return local[0] + '***@' + domain

def get_total_sessions_count(class_obj, subject=None, from_date=None, to_date=None):
    """
    Returns the number of unique attendance sessions (subject + date) held for a class.
    """
    from attendance.models import Attendance
    qs = Attendance.objects.filter(student__assigned_class=class_obj)
    if subject:
        qs = qs.filter(subject=subject)
    if from_date:
        qs = qs.filter(date__gte=from_date)
    if to_date:
        qs = qs.filter(date__lte=to_date)
    
    return qs.values('subject_id', 'date', 'period_number').distinct().count()

def calculate_student_percent(student, subject=None):
    if not student.assigned_class:
        from attendance.models import Attendance
        qs = Attendance.objects.filter(student=student)
        if subject: qs = qs.filter(subject=subject)
        total = qs.count()
        if total == 0: return 0
        present = qs.filter(is_present=True).count()
        return round((present / total) * 100, 1)
    
    total = get_total_sessions_count(student.assigned_class, subject=subject)
    if total == 0:
        return 0
    
    from attendance.models import Attendance
    present_qs = Attendance.objects.filter(student=student, is_present=True)
    if subject:
        present_qs = present_qs.filter(subject=subject)
    
    present = present_qs.count()
    return round((present / total) * 100, 1)

@api_view(['GET'])
def global_search(request):
    q = request.GET.get('q', '').strip()
    if len(q) < 2:
        return Response({'students': [], 'teachers': [], 'subjects': [], 'classes': []})
    students = list(Student.objects.filter(
        Q(name__icontains=q) | Q(student_id__icontains=q)
    ).select_related('assigned_class')[:6].values('student_id', 'name', 'assigned_class__name'))
    teachers = list(Teacher.objects.filter(
        Q(name__icontains=q) | Q(email__icontains=q)
    )[:5].values('id', 'name', 'email'))
    subjects = list(Subject.objects.filter(
        Q(name__icontains=q) | Q(code__icontains=q)
    ).select_related('assigned_class')[:5].values('id', 'name', 'code', 'assigned_class__name'))
    classes = list(Class.objects.filter(name__icontains=q).select_related('department')[:5].values('id', 'name', 'department__name'))
    return Response({'students': students, 'teachers': teachers, 'subjects': subjects, 'classes': classes})

@api_view(['GET', 'POST'])
def system_settings(request):
    s = SystemSettings.get()
    if request.method == 'GET':
        return Response({
            'college_name': s.college_name, 'principal_name': s.principal_name,
            'college_address': s.college_address, 'academic_year': s.academic_year,
            'semester': s.semester, 'min_attendance_percent': s.min_attendance_percent,
            'auto_send_alerts': s.auto_send_alerts,
        })
    s.college_name = request.data.get('college_name', s.college_name)
    s.principal_name = request.data.get('principal_name', s.principal_name)
    s.college_address = request.data.get('college_address', s.college_address)
    s.academic_year = request.data.get('academic_year', s.academic_year)
    s.min_attendance_percent = request.data.get('min_attendance_percent', s.min_attendance_percent)
    s.auto_send_alerts = request.data.get('auto_send_alerts', s.auto_send_alerts)
    s.save()
    return Response({'message': 'Settings saved.'})

@api_view(['POST'])
def test_email(request):
    try:
        send_mail(
            subject='Test Email — Smart Attendance System',
            message='This is a test email. Your email settings are working correctly.',
            from_email=settings.EMAIL_HOST_USER,
            recipient_list=[settings.EMAIL_HOST_USER],
            fail_silently=False,
        )
        return Response({'message': 'Test email sent successfully!'})
    except Exception as e:
        return Response({'error': str(e)}, status=500)


# ═══════════════════════════════════════════════════════════════════════
# Bulk Delete APIs — Admin only
# ═══════════════════════════════════════════════════════════════════════

@api_view(['DELETE'])
def delete_all_departments(request):
    count = Department.objects.count()
    Department.objects.all().delete()
    return Response({'message': f'Deleted {count} departments'})

@api_view(['DELETE'])
def delete_all_classes(request):
    count = Class.objects.count()
    Class.objects.all().delete()
    return Response({'message': f'Deleted {count} classes'})

@api_view(['DELETE'])
def delete_all_subjects(request):
    count = Subject.objects.count()
    Subject.objects.all().delete()
    return Response({'message': f'Deleted {count} subjects'})

@api_view(['DELETE'])
def delete_all_teachers(request):
    teachers = Teacher.objects.all()
    count = teachers.count()
    # Delete linked User accounts too
    user_ids = list(teachers.values_list('user_id', flat=True))
    teachers.delete()
    User.objects.filter(id__in=user_ids, role='TEACHER').delete()
    return Response({'message': f'Deleted {count} teachers'})

@api_view(['DELETE'])
def delete_all_students(request):
    students = Student.objects.all()
    count = students.count()
    # Delete linked User accounts too
    user_ids = list(students.values_list('user_id', flat=True))
    students.delete()
    User.objects.filter(id__in=user_ids, role='STUDENT').delete()
    return Response({'message': f'Deleted {count} students'})

