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
def classes(request):
    if request.method == 'GET':
        qs = Class.objects.select_related('department').annotate(
            student_count=Count('student')
        )
        dept_id = request.GET.get('department_id')
        if dept_id:
            qs = qs.filter(department_id=dept_id)
        data = [{'id': c.id, 'name': c.name, 'year': c.year,
                 'department_name': c.department.name, 'department_id': c.department_id,
                 'student_count': c.student_count} for c in qs]
        return Response(data)
    try:
        dept = Department.objects.get(pk=request.data.get('department_id'))
    except Department.DoesNotExist:
        return Response({'error': 'Department not found'}, status=400)
    cls = Class.objects.create(
        name=request.data.get('name', '').strip(),
        department=dept,
        year=request.data.get('year', 1)
    )
    return Response({'id': cls.id, 'name': cls.name}, status=201)

@api_view(['PUT', 'DELETE'])
def class_detail(request, pk):
    try:
        cls = Class.objects.get(pk=pk)
    except Class.DoesNotExist:
        return Response({'error': 'Not found'}, status=404)
    if request.method == 'PUT':
        cls.name = request.data.get('name', cls.name)
        cls.year = request.data.get('year', cls.year)
        cls.save()
        return Response({'id': cls.id, 'name': cls.name})
    cls.delete()
    return Response({'message': 'Deleted'})

@api_view(['GET'])
def classes_by_department(request, dept_id):
    qs = Class.objects.filter(department_id=dept_id).values('id', 'name', 'year')
    return Response(list(qs))

@api_view(['GET'])
def semesters_by_class(request, class_id):
    from classes.models import Semester
    qs = Semester.objects.filter(class_obj_id=class_id).values('id', 'name', 'number')
    return Response(list(qs))
