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
from utils.email_helpers import build_absence_alert_html
try:
    from utils.views import get_student_from_token, get_teacher_from_token, mask_email, calculate_student_percent
except ImportError:
    pass
from utils.notifications import send_sms

logger = logging.getLogger(__name__)

@api_view(['POST'])
def mark_attendance(request):
    teacher = get_teacher_from_token(request)
    subject_id = request.data.get('subject_id')
    date_str = request.data.get('date', str(dt.date.today()))
    period_number = int(request.data.get('period_number', 1))
    records = request.data.get('records', [])

    try:
        subject = Subject.objects.get(pk=subject_id)
    except Subject.DoesNotExist:
        return Response({'error': 'Subject not found'}, status=404)

    try:
        date = dt.datetime.strptime(date_str, '%Y-%m-%d').date()
    except ValueError:
        return Response({'error': 'Invalid date format'}, status=400)

    if Holiday.objects.filter(date=date).exists():
        return Response({'error': 'This is a holiday. Cannot mark attendance.'}, status=400)

    # BLOCK DUPLICATES — per subject + date + period_number
    if Attendance.objects.filter(subject=subject, date=date, period_number=period_number).exists():
        return Response({'error': f'Attendance already marked for Period {period_number}'}, status=400)

    absent_students = []
    saved = 0
    for rec in records:
        try:
            student = Student.objects.get(student_id=rec['student_id'])
            is_present = rec.get('is_present', False)
            Attendance.objects.create(
                student=student, subject=subject, date=date,
                period_number=period_number,
                is_present=is_present, marked_by=teacher,
                time=dt.datetime.now().time()
            )
            saved += 1
            if not is_present:
                absent_students.append(student)
        except Student.DoesNotExist:
            pass

    # Attendance saved — emails sent separately via /api/notifications/send-alerts/
    absent_count = sum(1 for r in records if not r.get('is_present', False))
    return Response({
        'message': f'Attendance saved for {saved} students (Period {period_number}).',
        'absent_count': absent_count,
    })

@api_view(['GET'])
def attendance_status(request):
    """
    GET /api/attendance/status/?semester_id=&date=
    Returns per-subject marked status for the given semester and date,
    including which period_numbers have already been marked.
    """
    semester_id = request.GET.get('semester_id')
    date_str = request.GET.get('date', str(dt.date.today()))
    if not semester_id:
        return Response({'error': 'semester_id is required'}, status=400)
    # Find all subjects for this semester
    subjects = Subject.objects.filter(semester_id=semester_id)
    result = []
    for subj in subjects:
        # Find which period_numbers are already marked for this subject on this date
        marked_periods = list(Attendance.objects.filter(
            subject=subj, date=date_str,
            student__assigned_class__semesters__id=semester_id
        ).values_list('period_number', flat=True).distinct())
        result.append({
            'subject_id': subj.id,
            'subject_name': subj.name,
            'subject_code': subj.code,
            'marked': len(marked_periods) > 0,
            'marked_periods': marked_periods,
        })
    return Response(result)

@api_view(['GET'])
def attendance_list(request):
    subject_id = request.GET.get('subject_id')
    date_str = request.GET.get('date', str(dt.date.today()))
    class_id = request.GET.get('class_id')
    period_number = request.GET.get('period_number')

    qs = Attendance.objects.select_related('student', 'subject')
    if subject_id:
        qs = qs.filter(subject_id=subject_id)
    if date_str:
        qs = qs.filter(date=date_str)
    if class_id:
        qs = qs.filter(student__assigned_class_id=class_id)
    if period_number:
        qs = qs.filter(period_number=int(period_number))

    data = [{'student_id': a.student.student_id, 'name': a.student.name,
              'subject': a.subject.name, 'date': str(a.date),
              'period_number': a.period_number,
              'is_present': a.is_present} for a in qs]
    return Response(data)

@api_view(['GET'])
def attendance_summary(request):
    return Response(_get_attendance_summary_data(
        class_id=request.GET.get('class_id'),
        semester_id=request.GET.get('semester_id'),
        subject_id=request.GET.get('subject_id'),
        date_from=request.GET.get('from'),
        date_to=request.GET.get('to')
    ))

def _get_attendance_summary_data(class_id=None, semester_id=None, subject_id=None, date_from=None, date_to=None):
    students_qs = Student.objects.select_related('assigned_class', 'department')
    if class_id:
        students_qs = students_qs.filter(assigned_class_id=class_id)

    # 1. PRE-CALCULATE SESSIONS HELD (The "True Total")
    # This ensures new students show 0/X instead of 0/0
    session_totals = {}
    sessions_qs = Attendance.objects.filter(student__in=students_qs)
    if subject_id: sessions_qs = sessions_qs.filter(subject_id=subject_id)
    elif semester_id: sessions_qs = sessions_qs.filter(subject__semester_id=semester_id)
    if date_from: sessions_qs = sessions_qs.filter(date__gte=date_from)
    if date_to: sessions_qs = sessions_qs.filter(date__lte=date_to)
    
    # Count distinct sessions per subject (subject + date + period_number)
    # This correctly counts multiple periods of same subject on same day as separate sessions
    held_sessions = sessions_qs.values('subject_id', 'date', 'period_number').distinct()
    for hs in held_sessions:
        subid = hs['subject_id']
        session_totals[subid] = session_totals.get(subid, 0) + 1

    # 2. GET STUDENT PRESENTS
    all_attendance_qs = Attendance.objects.filter(student__in=students_qs)
    if subject_id: all_attendance_qs = all_attendance_qs.filter(subject_id=subject_id)
    elif semester_id: all_attendance_qs = all_attendance_qs.filter(subject__semester_id=semester_id)
    if date_from: all_attendance_qs = all_attendance_qs.filter(date__gte=date_from)
    if date_to: all_attendance_qs = all_attendance_qs.filter(date__lte=date_to)
    
    # Map: student_pk -> subject_id -> present_count
    present_map = {} 
    for att in all_attendance_qs:
        if not att.is_present: continue
        sid, subid = att.student_id, att.subject_id
        if sid not in present_map: present_map[sid] = {}
        present_map[sid][subid] = present_map[sid].get(subid, 0) + 1

    subjects_to_show = []
    if semester_id:
        subjects_to_show = list(Subject.objects.filter(semester_id=semester_id).order_by('code'))
    elif not subject_id and class_id:
        subjects_to_show = list(Subject.objects.filter(semester__class_obj_id=class_id).order_by('code'))

    # 3. BUILD RESULT
    students_result = []
    for student in students_qs:
        s_presents = present_map.get(student.pk, {})
        
        overall_total = 0
        overall_present = 0
        
        if subject_id:
            try:
                sid_int = int(subject_id)
                overall_total = session_totals.get(sid_int, 0)
                overall_present = s_presents.get(sid_int, 0)
            except (ValueError, TypeError):
                pass
        else:
            # Sum of all sessions held for all subjects
            overall_total = sum(session_totals.values())
            overall_present = sum(s_presents.values())
        
        absent = overall_total - overall_present
        pct = round((overall_present / overall_total * 100), 1) if overall_total > 0 else 0
        
        student_data = {
            'student_id': student.student_id, 'name': student.name,
            'department': student.department.name if student.department else '',
            'class_name': student.assigned_class.name if student.assigned_class else '',
            'total': overall_total, 'present': overall_present, 'absent': absent, 'percent': pct,
            'status': 'Safe' if pct >= 75 else ('At Risk' if pct >= 60 else 'Danger')
        }
        
        if subjects_to_show:
            subject_percents = {}
            for sub in subjects_to_show:
                s_total = session_totals.get(sub.id, 0)
                s_present = s_presents.get(sub.id, 0)
                if s_total > 0:
                    subject_percents[str(sub.id)] = round((s_present / s_total * 100), 1)
                else:
                    subject_percents[str(sub.id)] = None
            student_data['subject_percents'] = subject_percents
            
        students_result.append(student_data)
        
    return {
        'students': students_result,
        'subjects': [{'id': s.id, 'name': s.name, 'code': s.code} for s in subjects_to_show] if subjects_to_show else []
    }

@api_view(['PUT'])
def edit_attendance(request):
    """
    PUT /api/attendance/edit/
    Body: { subject_id, date, period_number, records: [{student_id, is_present}, ...] }
    """
    teacher = get_teacher_from_token(request)
    if not teacher:
        return Response({'error': 'Unauthorized'}, status=401)

    subject_id = request.data.get('subject_id')
    date_str = request.data.get('date', str(dt.date.today()))
    period_number = int(request.data.get('period_number', 1))
    records = request.data.get('records', [])

    try:
        subject = Subject.objects.get(pk=subject_id)
    except Subject.DoesNotExist:
        return Response({'error': 'Subject not found'}, status=404)

    updated = 0
    for rec in records:
        student_id = rec.get('student_id')
        is_present = rec.get('is_present', False)
        try:
            student = Student.objects.get(student_id=student_id)
            att, created = Attendance.objects.update_or_create(
                student=student, subject=subject, date=date_str, period_number=period_number,
                defaults={'is_present': is_present, 'marked_by': teacher, 'time': dt.datetime.now().time()}
            )
            updated += 1
        except Student.DoesNotExist:
            pass

    return Response({'message': f'Attendance updated for {updated} students (Period {period_number}).'})

@api_view(['GET'])
def student_attendance_log(request):
    student = get_student_from_token(request)
    if not student:
        return Response({'error': 'Unauthorized'}, status=401)
    
    from_date = request.GET.get('from')
    to_date = request.GET.get('to')
    subject_id = request.GET.get('subject_id')

    qs = Attendance.objects.filter(student=student).select_related('subject').order_by('-date')
    if from_date:
        qs = qs.filter(date__gte=from_date)
    if to_date:
        qs = qs.filter(date__lte=to_date)
    if subject_id:
        qs = qs.filter(subject_id=subject_id)

    data = []
    for a in qs:
        data.append({
            'date': str(a.date),
            'day': a.date.strftime('%A'),
            'subject': a.subject.name,
            'period_number': a.period_number,
            'status': 'Present' if a.is_present else 'Absent'
        })
    return Response(data)

def _send_absent_emails(absent_students, subject, date):
    for student in absent_students:
        if not student.parent_email:
            continue
        try:
            # Build bilingual HTML email using shared template
            html = build_absence_alert_html(
                student=student,
                absent_subjects=[subject],
                date=date,
            )
            send_mail(
                subject=f'Attendance Alert – RPA First Grade College – {student.name}',
                message='', from_email=settings.EMAIL_HOST_USER,
                recipient_list=[student.parent_email],
                html_message=html, fail_silently=True
            )
            
            NotificationLog.objects.create(
                student=student, parent_email=student.parent_email,
                subject=subject, date=date, status='SENT'
            )
        except Exception as e:
            NotificationLog.objects.create(
                student=student, parent_email=student.parent_email or '',
                subject=subject, date=date, status='FAILED', error_message=str(e)
            )


