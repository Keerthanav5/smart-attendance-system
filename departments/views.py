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
def departments(request):
    if request.method == 'GET':
        data = Department.objects.annotate(
            class_count=Count('classes'),
            student_count=Count('student')
        ).values('id', 'name', 'class_count', 'student_count')
        return Response(list(data))
    name = request.data.get('name', '').strip()
    if not name:
        return Response({'error': 'Name is required'}, status=400)
    if Department.objects.filter(name__iexact=name).exists():
        return Response({'error': 'Department already exists'}, status=400)
    dept = Department.objects.create(name=name)
    return Response({'id': dept.id, 'name': dept.name}, status=201)

@api_view(['PUT', 'DELETE'])
def department_detail(request, pk):
    try:
        dept = Department.objects.get(pk=pk)
    except Department.DoesNotExist:
        return Response({'error': 'Not found'}, status=404)
    if request.method == 'PUT':
        dept.name = request.data.get('name', dept.name)
        dept.save()
        return Response({'id': dept.id, 'name': dept.name})
    dept.delete()
    return Response({'message': 'Deleted'})

