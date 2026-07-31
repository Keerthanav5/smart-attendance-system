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
def subjects(request):
    if request.method == 'GET':
        qs = Subject.objects.select_related('semester', 'semester__class_obj', 'semester__class_obj__department', 'teacher')
        semester_id = request.GET.get('semester_id')
        if semester_id:
            qs = qs.filter(semester_id=semester_id)
        class_id = request.GET.get('class_id')
        if class_id:
            qs = qs.filter(semester__class_obj_id=class_id)
        data = [{'id': s.id, 'code': s.code, 'name': s.name,
                 'semester_name': s.semester.name,
                 'semester_id': s.semester_id,
                 'class_name': s.semester.class_obj.name,
                 'class_id': s.semester.class_obj_id,
                 'department': s.semester.class_obj.department.name,
                 'teacher_name': s.teacher.name if s.teacher else None, 'teacher_id': s.teacher_id} for s in qs]
        return Response(data)
    
    from classes.models import Semester
    try:
        sem = Semester.objects.get(pk=request.data.get('semester_id'))
    except Semester.DoesNotExist:
        return Response({'error': 'Semester not found'}, status=400)
    teacher = None
    if request.data.get('teacher_id'):
        try:
            teacher = Teacher.objects.get(pk=request.data['teacher_id'])
        except Teacher.DoesNotExist:
            pass
    subj = Subject.objects.create(
        code=request.data.get('code', '').strip(),
        name=request.data.get('name', '').strip(),
        semester=sem,
        teacher=teacher
    )
    return Response({'id': subj.id, 'name': subj.name}, status=201)

@api_view(['PUT', 'DELETE'])
def subject_detail(request, pk):
    try:
        subj = Subject.objects.get(pk=pk)
    except Subject.DoesNotExist:
        return Response({'error': 'Not found'}, status=404)
    if request.method == 'PUT':
        subj.name = request.data.get('name', subj.name)
        subj.code = request.data.get('code', subj.code)
        
        # update teacher if provided
        teacher_id = request.data.get('teacher_id')
        if teacher_id is not None:
            if teacher_id:
                try:
                    subj.teacher = Teacher.objects.get(pk=teacher_id)
                except Teacher.DoesNotExist:
                    pass
            else:
                subj.teacher = None

        # update semester if provided
        semester_id = request.data.get('semester_id')
        if semester_id:
            from classes.models import Semester
            try:
                subj.semester = Semester.objects.get(pk=semester_id)
            except Semester.DoesNotExist:
                pass

        subj.save()
        return Response({'id': subj.id, 'name': subj.name})
    subj.delete()
    return Response({'message': 'Deleted'})

@api_view(['GET'])
def subjects_by_class(request, class_id):
    qs = Subject.objects.filter(semester__class_obj_id=class_id).values('id', 'code', 'name', 'semester_id', 'semester__name')
    return Response(list(qs))

@api_view(['GET'])
def subjects_by_semester(request, semester_id):
    qs = Subject.objects.filter(semester_id=semester_id).values('id', 'code', 'name')
    return Response(list(qs))

