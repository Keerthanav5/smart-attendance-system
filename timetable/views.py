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

@api_view(['GET', 'POST'])
def timetable(request):
    if request.method == 'GET':
        semester_id = request.GET.get('semester_id')
        date_str = request.GET.get('date')
        
        qs = Timetable.objects.select_related('subject', 'semester', 'teacher')
        if semester_id:
            qs = qs.filter(semester_id=semester_id)
            
        if date_str:
            try:
                date_obj = dt.datetime.strptime(date_str, '%Y-%m-%d').date()
                day_name = date_obj.strftime('%A')
                qs = qs.filter(day=day_name)
            except ValueError:
                pass
                
        if not qs.exists():
            return Response({"message": "No subjects scheduled"}, status=200)
            
        data = [{'id': t.id, 'day': t.day, 'period_number': t.period_number,
                 'subject': t.subject.name, 'subject_name': t.subject.name, 'subject_id': t.subject_id,
                 'semester_name': t.semester.name if t.semester else '',
                 'teacher': t.teacher.name if t.teacher else '',
                 'start_time': str(t.start_time), 'end_time': str(t.end_time)} for t in qs]
        return Response(data)
    try:
        subj = Subject.objects.get(pk=request.data.get('subject_id'))
        from classes.models import Semester
        sem = Semester.objects.get(pk=request.data.get('semester_id'))
    except (Subject.DoesNotExist, Exception):
        return Response({'error': 'Subject or Semester not found'}, status=400)
    tt = Timetable.objects.create(
        semester=sem, subject=subj,
        day=request.data.get('day'),
        period_number=request.data.get('period_number', 1),
        start_time=request.data.get('start_time'),
        end_time=request.data.get('end_time'),
    )
    return Response({'id': tt.id, 'day': tt.day}, status=201)

@api_view(['PUT', 'DELETE'])
def timetable_detail(request, pk):
    try:
        tt = Timetable.objects.get(pk=pk)
    except Timetable.DoesNotExist:
        return Response({'error': 'Not found'}, status=404)
    if request.method == 'DELETE':
        tt.delete()
        return Response({'message': 'Deleted'})
    tt.day = request.data.get('day', tt.day)
    tt.period_number = request.data.get('period_number', tt.period_number)
    tt.start_time = request.data.get('start_time', tt.start_time)
    tt.end_time = request.data.get('end_time', tt.end_time)
    tt.save()
    return Response({'id': tt.id})

@api_view(['GET'])
def today_timetable(request):
    teacher = get_teacher_from_token(request)
    today = dt.datetime.now().strftime('%A')
    qs = Timetable.objects.filter(day=today).select_related('subject', 'semester')
    if teacher:
        qs = qs.filter(teacher=teacher)
    data = [{'id': t.id, 'subject': t.subject.name, 'subject_id': t.subject_id,
             'semester_name': t.semester.name if t.semester else '',
             'semester_id': t.semester_id,
             'period_number': t.period_number,
             'start_time': str(t.start_time), 'end_time': str(t.end_time)} for t in qs]
    return Response(data)

@api_view(['GET'])
def timetable_by_semester(request, semester_id):
    """Return timetable entries for a specific semester. Used by teacher timetable and attendance."""
    qs = Timetable.objects.filter(semester_id=semester_id).select_related('subject', 'teacher').order_by('period_number')
    day = request.GET.get('day')
    if day:
        qs = qs.filter(day=day)
    data = [{
        'id': t.id,
        'day': t.day,
        'period_number': t.period_number,
        'subject_id': t.subject_id,
        'subject_name': t.subject.name if t.subject else None,
        'subject_code': t.subject.code if t.subject else None,
        'teacher_name': t.teacher.name if t.teacher else None,
        'start_time': str(t.start_time),
        'end_time': str(t.end_time),
    } for t in qs]
    return Response(data)

