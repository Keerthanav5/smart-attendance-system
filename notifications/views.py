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

logger = logging.getLogger(__name__)

@api_view(['GET'])
def notification_logs(request):
    """Return recent notification logs, optionally filtered by date."""
    date_str = request.GET.get('date', str(dt.date.today()))
    qs = NotificationLog.objects.select_related('student', 'subject').order_by('-sent_at')[:200]
    if date_str:
        qs = NotificationLog.objects.select_related('student', 'subject').filter(date=date_str).order_by('-sent_at')
    data = [{
        'id': n.id,
        'student_id': n.student.student_id,
        'student_name': n.student.name,
        'parent_email': n.parent_email,
        'subject': n.subject.name if n.subject else '-',
        'date': str(n.date),
        'status': n.status,
        'error': n.error_message,
        'sent_at': n.sent_at.strftime('%d %b %Y %H:%M'),
    } for n in qs]
    return Response(data)

@api_view(['POST'])
def send_absent_alerts(request):
    """
    Send bilingual email notifications to parents of absent students.
    Body: { date: 'YYYY-MM-DD', subject_ids: [1,2,...] }  (subject_ids optional - all if omitted)
    """
    date_str = request.data.get('date', str(dt.date.today()))
    subject_ids = request.data.get('subject_ids', [])

    try:
        date = dt.datetime.strptime(date_str, '%Y-%m-%d').date()
    except ValueError:
        return Response({'error': 'Invalid date format'}, status=400)

    # Get all absent attendance records for that date
    qs = Attendance.objects.select_related('student', 'subject').filter(
        date=date, is_present=False
    )
    if subject_ids:
        qs = qs.filter(subject_id__in=subject_ids)

    if not qs.exists():
        return Response({'message': 'No absent students found for the selected date/subjects.', 'sent': 0})

    if not settings.EMAIL_HOST_USER:
        return Response({'error': 'Email is not configured. Add EMAIL_HOST_USER to your .env file.'}, status=500)

    sent = 0
    failed = 0
    skipped = 0
    details = []

    # Group absent records by student for consolidated email
    student_records = {}
    for record in qs:
        student = record.student
        if student not in student_records:
            student_records[student] = []
        student_records[student].append(record)

    for student, records in student_records.items():
        if not student.parent_email:
            skipped += 1
            details.append({'student': student.student_id, 'status': 'skipped', 'reason': 'No parent email'})
            continue

        try:
            total   = Attendance.objects.filter(student=student).count()
            present = Attendance.objects.filter(student=student, is_present=True).count()
            pct     = round((present / total * 100), 1) if total > 0 else 0
            min_pct = SystemSettings.get().min_attendance_percent

            # Collect unique absent subjects (deduplicate multi-period records)
            seen_subject_ids = set()
            absent_subjects = []
            for r in records:
                if r.subject_id not in seen_subject_ids:
                    seen_subject_ids.add(r.subject_id)
                    absent_subjects.append(r.subject)
            subject_names_str = ", ".join([s.name for s in absent_subjects])

            # Build bilingual HTML email using shared template
            html = build_absence_alert_html(
                student=student,
                absent_subjects=absent_subjects,
                date=date,
                pct=pct,
                min_pct=min_pct,
            )

            # Send ONE consolidated email per student
            if student.parent_email:
                send_mail(
                    subject=f'Attendance Alert – RPA First Grade College – {student.name}',
                    message='',
                    from_email=settings.EMAIL_HOST_USER,
                    recipient_list=[student.parent_email],
                    html_message=html,
                    fail_silently=False,
                )

            # Log one notification per unique absent subject
            for subj in absent_subjects:
                NotificationLog.objects.create(
                    student=student, parent_email=student.parent_email,
                    subject=subj, date=date, status='SENT'
                )

            sent += 1
            details.append({'student': student.student_id, 'name': student.name,
                            'parent_email': student.parent_email, 'subject': subject_names_str, 'status': 'sent'})
        except Exception as e:
            NotificationLog.objects.create(
                student=student, parent_email=student.parent_email or '',
                subject=records[0].subject if records else None, date=date, status='FAILED', error_message=str(e)
            )
            failed += 1
            details.append({'student': student.student_id, 'name': student.name,
                            'subject': 'N/A', 'status': 'failed', 'error': str(e)})

    return Response({
        'message': f'Done - {sent} sent, {failed} failed, {skipped} skipped.',
        'sent': sent, 'failed': failed, 'skipped': skipped,
        'details': details,
    })

@api_view(['POST'])
def send_class_absent_alerts(request):
    """
    Send bilingual email notifications to parents of absent students per class.
    Body: { date: 'YYYY-MM-DD', class_id: int }
    """
    date_str = request.data.get('date', str(dt.date.today()))
    class_id = request.data.get('class_id')

    try:
        date = dt.datetime.strptime(date_str, '%Y-%m-%d').date()
    except ValueError:
        return Response({'error': 'Invalid date format'}, status=400)
        
    day_name = date.strftime('%A')

    if not class_id:
        return Response({'error': 'class_id is required'}, status=400)

    # CHECK: All subjects attendance must be marked
    scheduled_subjects = Timetable.objects.filter(semester__class_obj_id=class_id, day=day_name).values_list('subject_id', flat=True)
    if not scheduled_subjects:
        return Response({'error': 'No subjects scheduled for this class on this date'}, status=400)
        
    for sub_id in scheduled_subjects:
        if not Attendance.objects.filter(subject_id=sub_id, date=date).exists():
            return Response({'error': 'Cannot send notifications. Attendance for all subjects must be marked first.'}, status=400)

    force = request.data.get('force', False)
    
    # PREVENT DUPLICATE SENDING (Unless forced)
    if not force and NotificationLog.objects.filter(class_id=class_id, date=date).exists():
        return Response({
            "error": "Notifications were already sent for this class today.", 
            "needs_force": True
        }, status=400)

    # GET ABSENT STUDENTS ONLY
    qs = Attendance.objects.select_related('student', 'subject').filter(
        date=date, is_present=False, student__assigned_class_id=class_id
    )

    if not qs.exists():
        return Response({'message': 'No absent students found.', 'sent': 0})

    if not settings.EMAIL_HOST_USER:
        return Response({'error': 'Email not configured. Add EMAIL_HOST_USER to .env'}, status=500)

    # Group by student
    student_absences = {}
    for record in qs:
        student = record.student
        subject = record.subject
        if student not in student_absences:
            student_absences[student] = []
        student_absences[student].append(subject)

    sent = 0
    failed = 0
    skipped = 0
    details = []

    for student, subjects in student_absences.items():
        if not student.parent_email:
            skipped += 1
            details.append({'student': student.student_id, 'status': 'skipped', 'reason': 'No parent email'})
            continue

        # Deduplicate subjects (same subject may appear multiple times from multi-period records)
        seen_ids = set()
        unique_subjects = []
        for s in subjects:
            if s.id not in seen_ids:
                seen_ids.add(s.id)
                unique_subjects.append(s)
        subject_names = ", ".join([s.name for s in unique_subjects])
        
        # Calculate attendance percentage
        total   = Attendance.objects.filter(student=student).count()
        present = Attendance.objects.filter(student=student, is_present=True).count()
        pct     = round((present / total * 100), 1) if total > 0 else 0
        min_pct = SystemSettings.get().min_attendance_percent

        # Build bilingual HTML email using shared template
        html = build_absence_alert_html(
            student=student,
            absent_subjects=unique_subjects,
            date=date,
            pct=pct,
            min_pct=min_pct,
        )

        try:
            if student.parent_email:
                send_mail(
                    subject=f'Attendance Alert – RPA First Grade College – {student.name}',
                    message='',
                    from_email=settings.EMAIL_HOST_USER,
                    recipient_list=[student.parent_email],
                    html_message=html,
                    fail_silently=False,
                )
                
            sent += 1
            details.append({'student': student.student_id, 'name': student.name,
                            'parent_email': student.parent_email, 'subjects': subject_names, 'status': 'sent'})
        except Exception as e:
            failed += 1
            details.append({'student': student.student_id, 'status': 'failed', 'error': str(e)})

    # SAVE LOG
    NotificationLog.objects.create(
        class_id=class_id,
        date=date
    )

    return Response({
        'message': f'Done - {sent} sent, {failed} failed, {skipped} skipped.',
        'sent': sent, 'failed': failed, 'skipped': skipped,
        'details': details,
    })
