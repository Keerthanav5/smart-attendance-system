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
def teachers(request):
    if request.method == 'GET':
        qs = Teacher.objects.all()
        data = [{'id': t.id, 'name': t.name, 'email': t.email,
                 'is_active': t.is_active,
                 'subject_count': t.subjects.count(), 'created_at': t.created_at.isoformat() if t.created_at else None} for t in qs]
        return Response(data)
    name = request.data.get('name', '').strip()
    email = request.data.get('email', '').strip()
    password = request.data.get('password', '').strip()
    if not email:
        return Response({'error': 'Email is required'}, status=400)
    if Teacher.objects.filter(email=email).exists():
        return Response({'error': 'Teacher with this email already exists'}, status=400)
    teacher = Teacher.objects.create(
        name=name, email=email,
        password=make_password(password) if password else '',
        is_active=True
    )
    return Response({'id': teacher.id, 'name': teacher.name, 'email': teacher.email}, status=201)

@api_view(['GET', 'PUT', 'DELETE'])
def teacher_detail(request, pk):
    try:
        teacher = Teacher.objects.get(pk=pk)
    except Teacher.DoesNotExist:
        return Response({'error': 'Not found'}, status=404)
    if request.method == 'GET':
        return Response({'id': teacher.id, 'name': teacher.name,
                         'email': teacher.email, 'is_active': teacher.is_active})
    if request.method == 'PUT':
        teacher.name = request.data.get('name', teacher.name)
        teacher.is_active = request.data.get('is_active', teacher.is_active)
        if request.data.get('password'):
            teacher.password = make_password(request.data['password'])
        teacher.save()
        return Response({'id': teacher.id, 'name': teacher.name})
    teacher.delete()
    return Response({'message': 'Deleted'})

