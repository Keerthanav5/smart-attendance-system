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

logger = logging.getLogger(__name__)

@api_view(['GET'])
def admin_stats(request):
    today = dt.date.today()
    total_students = Student.objects.count()
    total_teachers = Teacher.objects.count()
    total_depts = Department.objects.count()
    total_classes = Class.objects.count()

    today_att = Attendance.objects.filter(date=today)
    today_total = today_att.count()
    today_present = today_att.filter(is_present=True).count()
    today_pct = round((today_present / today_total * 100), 1) if today_total > 0 else 0

    # Low attendance students
    low_att = []
    min_pct = SystemSettings.get().min_attendance_percent
    for student in Student.objects.select_related('assigned_class', 'department'):
        total = Attendance.objects.filter(student=student).count()
        present = Attendance.objects.filter(student=student, is_present=True).count()
        pct = round((present / total * 100), 1) if total > 0 else 0
        if pct < min_pct and total > 0:
            low_att.append({'student_id': student.student_id, 'name': student.name,
                            'class_name': student.assigned_class.name if student.assigned_class else '',
                            'percent': pct})

    return Response({
        'total_students': total_students,
        'total_teachers': total_teachers,
        'total_departments': total_depts,
        'total_classes': total_classes,
        'today_attendance_percent': today_pct,
        'low_attendance_students': low_att[:10],
    })

@api_view(['GET'])
def teacher_stats(request):
    teacher = get_teacher_from_token(request)
    if not teacher:
        return Response({'error': 'Unauthorized'}, status=401)
    subjects = Subject.objects.filter(teacher=teacher)
    today = dt.date.today()
    today_name = today.strftime('%A')
    today_periods = Timetable.objects.filter(teacher=teacher, day=today_name).count()
    submitted_today = Attendance.objects.filter(subject__in=subjects, date=today, marked_by=teacher).values('subject', 'period_number').distinct().count()
    return Response({
        'teacher_name': teacher.name,
        'subject_count': subjects.count(),
        'today_periods': today_periods,
        'submitted_today': submitted_today,
    })

@api_view(['GET'])
def student_dashboard(request):
    student = get_student_from_token(request)
    if not student:
        return Response({'error': 'Unauthorized'}, status=401)

    all_att = Attendance.objects.filter(student=student)
    total = all_att.count()
    present = all_att.filter(is_present=True).count()
    absent = total - present
    overall_pct = round((present / total * 100), 1) if total > 0 else 0
    min_pct = SystemSettings.get().min_attendance_percent
    needed = 0
    if overall_pct < min_pct and total > 0:
        needed = max(0, int((min_pct * total - present * 100) / (100 - min_pct)) + 1)

    subjects_data = []
    for subj in Subject.objects.filter(semester__class_obj=student.assigned_class).select_related('semester'):
        s_att = Attendance.objects.filter(student=student, subject=subj)
        s_total = s_att.count()
        s_present = s_att.filter(is_present=True).count()
        s_pct = round((s_present / s_total * 100), 1) if s_total > 0 else 0
        subjects_data.append({
            'subject': subj.name, 'code': subj.code,
            'semester': subj.semester.name if subj.semester else '',
            'total': s_total, 'present': s_present,
            'absent': s_total - s_present, 'percent': s_pct,
            'status': 'Safe' if s_pct >= 75 else ('At Risk' if s_pct >= 60 else 'Danger')
        })
    subjects_data.sort(key=lambda x: x['percent'])

    # Recent 7 days
    recent = []
    for i in range(7):
        day = dt.date.today() - dt.timedelta(days=i)
        day_att = Attendance.objects.filter(student=student, date=day).select_related('subject')
        if day_att.exists():
            recent.append({
                'date': str(day),
                'date_label': day.strftime('%d %b'),
                'subjects': [{'name': a.subject.name, 'present': a.is_present} for a in day_att]
            })

    return Response({
        'name': student.name, 'student_id': student.student_id,
        'class_name': student.assigned_class.name if student.assigned_class else '',
        'department': student.department.name if student.department else '',
        'overall_percent': overall_pct, 'total_classes': total,
        'present_count': present, 'absent_count': absent,
        'classes_needed_for_75': needed,
        'subject_breakdown': subjects_data,
        'recent_7_days': recent,
    })

@api_view(['GET'])
def student_calendar(request):
    student = get_student_from_token(request)
    if not student:
        return Response({'error': 'Unauthorized'}, status=401)
    month = int(request.GET.get('month', dt.date.today().month))
    year = int(request.GET.get('year', dt.date.today().year))
    import calendar
    _, days_in_month = calendar.monthrange(year, month)
    result = []
    holidays_set = set(Holiday.objects.filter(date__month=month, date__year=year).values_list('date', flat=True))
    for day in range(1, days_in_month + 1):
        d = dt.date(year, month, day)
        if d in holidays_set:
            status = 'holiday'
        else:
            att = Attendance.objects.filter(student=student, date=d)
            if not att.exists():
                status = 'no_class'
            elif att.filter(is_present=True).exists():
                status = 'present'
            else:
                status = 'absent'
        result.append({'date': str(d), 'day': day, 'status': status})
    return Response(result)


# ═══════════════════════════════════════════════════════════════════════
# Chart Data APIs — added for dashboard visualizations
# ═══════════════════════════════════════════════════════════════════════

@api_view(['GET'])
def admin_chart_data(request):
    """Returns class-wise attendance bar data + 7-day trend line data."""
    today = dt.date.today()

    # ── Class-wise attendance (bar chart) ────────────────────────────────
    class_data = []
    for cls in Class.objects.select_related('department').all():
        att = Attendance.objects.filter(student__assigned_class=cls)
        total = att.count()
        present = att.filter(is_present=True).count()
        pct = round((present / total * 100), 1) if total > 0 else 0
        class_data.append({
            'label': cls.name,
            'department': cls.department.name if cls.department else '',
            'percent': pct,
            'total': total,
            'present': present,
        })

    # ── 7-day attendance trend (line chart) ──────────────────────────────
    trend_data = []
    for i in range(6, -1, -1):
        day = today - dt.timedelta(days=i)
        day_att = Attendance.objects.filter(date=day)
        total = day_att.count()
        present = day_att.filter(is_present=True).count()
        absent = total - present
        pct = round((present / total * 100), 1) if total > 0 else 0
        trend_data.append({
            'date': str(day),
            'label': day.strftime('%d %b'),
            'day_name': day.strftime('%a'),
            'present': present,
            'absent': absent,
            'total': total,
            'percent': pct,
        })

    # ── Department-wise attendance (doughnut) ────────────────────────────
    dept_data = []
    for dept in Department.objects.all():
        att = Attendance.objects.filter(student__department=dept)
        total = att.count()
        present = att.filter(is_present=True).count()
        pct = round((present / total * 100), 1) if total > 0 else 0
        dept_data.append({
            'label': dept.name,
            'percent': pct,
            'total': total,
            'present': present,
        })

    return Response({
        'class_wise': class_data,
        'trend_7day': trend_data,
        'dept_wise': dept_data,
    })


@api_view(['GET'])
def teacher_chart_data(request):
    """Returns class-wise bar + weekly trend for the teacher's own subjects."""
    teacher = get_teacher_from_token(request)
    if not teacher:
        return Response({'error': 'Unauthorized'}, status=401)

    today = dt.date.today()
    subjects = Subject.objects.filter(teacher=teacher)

    # ── Class-wise attendance for teacher's subjects ─────────────────────
    class_data = []
    class_ids = set()
    for subj in subjects.select_related('semester__class_obj'):
        if subj.semester and subj.semester.class_obj:
            cls = subj.semester.class_obj
            if cls.id in class_ids:
                continue
            class_ids.add(cls.id)
            att = Attendance.objects.filter(student__assigned_class=cls, subject__in=subjects)
            total = att.count()
            present = att.filter(is_present=True).count()
            pct = round((present / total * 100), 1) if total > 0 else 0
            class_data.append({
                'label': cls.name,
                'percent': pct,
                'total': total,
                'present': present,
            })

    # ── 7-day trend for teacher's subjects ───────────────────────────────
    trend_data = []
    for i in range(6, -1, -1):
        day = today - dt.timedelta(days=i)
        day_att = Attendance.objects.filter(date=day, subject__in=subjects)
        total = day_att.count()
        present = day_att.filter(is_present=True).count()
        absent = total - present
        pct = round((present / total * 100), 1) if total > 0 else 0
        trend_data.append({
            'date': str(day),
            'label': day.strftime('%d %b'),
            'day_name': day.strftime('%a'),
            'present': present,
            'absent': absent,
            'total': total,
            'percent': pct,
        })

    # ── Subject-wise attendance ──────────────────────────────────────────
    subject_data = []
    for subj in subjects:
        att = Attendance.objects.filter(subject=subj)
        total = att.count()
        present = att.filter(is_present=True).count()
        pct = round((present / total * 100), 1) if total > 0 else 0
        subject_data.append({
            'label': subj.name,
            'code': subj.code,
            'percent': pct,
            'total': total,
            'present': present,
        })

    # ── Low attendance students (below min %) for teacher's subjects ─────
    min_pct = SystemSettings.get().min_attendance_percent
    low_attendance = []
    # Get all students in classes the teacher teaches
    student_ids_seen = set()
    for subj in subjects.select_related('semester__class_obj'):
        if not subj.semester or not subj.semester.class_obj:
            continue
        cls = subj.semester.class_obj
        for student in Student.objects.filter(assigned_class=cls).select_related('assigned_class', 'department'):
            if student.pk in student_ids_seen:
                continue
            student_ids_seen.add(student.pk)
            s_att = Attendance.objects.filter(student=student, subject__in=subjects)
            s_total = s_att.count()
            s_present = s_att.filter(is_present=True).count()
            s_pct = round((s_present / s_total * 100), 1) if s_total > 0 else 0
            if s_total > 0 and s_pct < min_pct:
                low_attendance.append({
                    'student_id': student.student_id,
                    'name': student.name or student.student_id,
                    'class_name': student.assigned_class.name if student.assigned_class else '',
                    'department': student.department.name if student.department else '',
                    'percent': s_pct,
                    'total': s_total,
                    'present': s_present,
                })
    low_attendance.sort(key=lambda x: x['percent'])

    return Response({
        'class_wise': class_data,
        'trend_7day': trend_data,
        'subject_wise': subject_data,
        'low_attendance': low_attendance[:15],
        'min_attendance_percent': min_pct,
    })

