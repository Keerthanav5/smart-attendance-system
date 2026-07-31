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

@api_view(['POST'])
def admin_login(request):
    username = request.data.get('username', '').strip()
    password = request.data.get('password', '').strip()
    if not username or not password:
        return Response({'error': 'Username and password are required'}, status=400)
    user = authenticate(username=username, password=password)
    if user is None:
        return Response({'error': 'Invalid username or password'}, status=401)
    if user.role != 'ADMIN':
        return Response({'error': 'Access denied. Admin accounts only.'}, status=403)
    login(request, user)
    return Response({'message': 'Login successful', 'redirect': '/admin-dashboard/'})

@api_view(['POST'])
def admin_register(request):
    name             = request.data.get('name', '').strip()
    username         = request.data.get('username', '').strip()
    email            = request.data.get('email', '').strip().lower()
    phone            = request.data.get('phone', '').strip()
    password         = request.data.get('password', '').strip()
    confirm_password = request.data.get('confirm_password', '').strip()
    registration_key = request.data.get('registration_key', '').strip()

    # ── Validation ──────────────────────────────────────────
    if not username or not password:
        return Response({'error': 'Username and password are required'}, status=400)
    if not email:
        return Response({'error': 'Email address is required'}, status=400)
    if password != confirm_password:
        return Response({'error': 'Passwords do not match'}, status=400)
    if len(password) < 8:
        return Response({'error': 'Password must be at least 8 characters'}, status=400)
    if registration_key != settings.ADMIN_REGISTRATION_KEY:
        return Response({'error': 'Invalid registration key. Contact your system administrator.'}, status=403)
    if User.objects.filter(username=username).exists():
        return Response({'error': 'Username already taken. Please choose another.'}, status=400)
    if User.objects.filter(email=email).exists():
        return Response({'error': 'An account with this email already exists.'}, status=400)

    # ── Create admin user ────────────────────────────────────
    parts = name.split(' ', 1) if name else ['', '']
    user = User.objects.create_superuser(
        username=username,
        email=email,
        password=password,
        role='ADMIN',
        first_name=parts[0],
        last_name=parts[1] if len(parts) > 1 else '',
        phone=phone if phone else None,
    )
    logger.info(f"New admin registered: {username} ({email})")
    return Response({'message': f'Admin account for {username} created successfully.'}, status=201)

@api_view(['POST'])
def teacher_login(request):
    email = request.data.get('email', '').strip()
    password = request.data.get('password', '').strip()
    if not email or not password:
        return Response({'error': 'Email and password are required'}, status=400)
    try:
        teacher = Teacher.objects.get(email=email)
    except Teacher.DoesNotExist:
        return Response({'error': 'Invalid email or password'}, status=401)
    if not teacher.is_active:
        return Response({'error': 'Account not activated. Contact administrator.'}, status=403)
    if not teacher.password:
        return Response({
            'error': 'Password not set. Please register first.',
            'redirect': '/teacher/register/'
        }, status=401)
    if not check_password(password, teacher.password):
        return Response({'error': 'Invalid email or password'}, status=401)
    token = jwt.encode({
        'teacher_id': teacher.id,
        'email': teacher.email,
        'role': 'TEACHER',
        'exp': dt.datetime.utcnow() + dt.timedelta(hours=24)
    }, settings.SECRET_KEY, algorithm='HS256')
    return Response({'token': token, 'name': teacher.name, 'email': teacher.email})

@api_view(['POST'])
def student_login(request):
    register_number = request.data.get('register_number', '').strip().upper()
    password = request.data.get('password', '').strip()
    if not register_number or not password:
        return Response({'error': 'Register number and password are required'}, status=400)
    try:
        student = Student.objects.get(student_id=register_number)
    except Student.DoesNotExist:
        return Response({'error': 'Invalid register number or password'}, status=401)
    if not student.password:
        return Response({
            'error': 'Password not set. Please register first.',
            'redirect': '/student/register/'
        }, status=401)
    if not student.is_registered:
        return Response({
            'error': 'Account not activated. Please complete registration first.',
            'redirect': '/student/register/'
        }, status=401)
    if not check_password(password, student.password):
        return Response({'error': 'Invalid register number or password'}, status=401)
    token = jwt.encode({
        'student_id': student.student_id,
        'role': 'STUDENT',
        'exp': dt.datetime.utcnow() + dt.timedelta(hours=24)
    }, settings.SECRET_KEY, algorithm='HS256')
    return Response({
        'token': token,
        'name': student.name,
        'student_id': student.student_id,
        'class_name': student.assigned_class.name if student.assigned_class else '',
        'department': student.department.name if student.department else '',
    })

@api_view(['POST'])
def logout_view(request):
    logout(request)
    return Response({'message': 'Logged out'})

@api_view(['POST'])
def forgot_password(request):
    role = request.data.get('role', '').strip()
    if role == 'student':
        register_number = request.data.get('register_number', '').strip()
        try:
            student = Student.objects.get(student_id=register_number)
        except Student.DoesNotExist:
            return Response({'message': 'If this register number exists, a reset link has been sent to the registered email.'})
        email_to = student.parent_email
        name = student.name or register_number
        identifier = student.student_id
    elif role == 'teacher':
        email = request.data.get('email', '').strip()
        try:
            teacher = Teacher.objects.get(email=email)
        except Teacher.DoesNotExist:
            return Response({'message': 'If this email exists, a reset link has been sent.'})
        email_to = teacher.email
        name = teacher.name or email
        identifier = teacher.email
    elif role == 'admin':
        email = request.data.get('email', '').strip()
        try:
            user = User.objects.get(email=email, role='ADMIN')
        except User.DoesNotExist:
            return Response({'message': 'If this email exists, a reset link has been sent.'})
        email_to = user.email
        name = user.get_full_name() or user.username
        identifier = user.email
    else:
        return Response({'error': 'Invalid role'}, status=400)

    if not email_to:
        return Response({'message': 'If this account exists, a reset link has been sent.'})

    token = secrets.token_urlsafe(32)
    PasswordResetToken.objects.filter(identifier=identifier, role=role).delete()
    PasswordResetToken.objects.create(
        identifier=identifier,
        role=role,
        token=token,
        expires_at=dt.datetime.now() + dt.timedelta(hours=1)
    )

    reset_url = f"{request.scheme}://{request.get_host()}/{role}/reset-password/?token={token}"

    html_message = f"""
    <div style="font-family:Arial,sans-serif;max-width:520px;margin:0 auto;">
      <div style="background:#2563EB;padding:28px 32px;border-radius:12px 12px 0 0;text-align:center;">
        <h2 style="color:white;margin:0;font-size:1.4rem;">Password Reset</h2>
        <p style="color:#BFDBFE;margin:6px 0 0;font-size:0.9rem;">Smart Attendance System</p>
      </div>
      <div style="background:white;border:1px solid #E2E8F0;padding:32px;border-radius:0 0 12px 12px;">
        <p style="color:#1E293B;font-size:1rem;">Hello <strong>{name}</strong>,</p>
        <p style="color:#64748B;line-height:1.6;">
          We received a request to reset your password.
          Click the button below to set a new password.
        </p>
        <div style="text-align:center;margin:32px 0;">
          <a href="{reset_url}"
             style="background:#2563EB;color:white;padding:14px 36px;
                    border-radius:8px;text-decoration:none;font-weight:700;
                    font-size:1rem;display:inline-block;">
            Reset My Password
          </a>
        </div>
        <p style="color:#94A3B8;font-size:0.82rem;text-align:center;">
          This link expires in <strong>1 hour</strong>.<br>
          If you did not request this, you can safely ignore this email.
        </p>
        <hr style="border:none;border-top:1px solid #F1F5F9;margin:24px 0;">
        <p style="color:#CBD5E1;font-size:0.75rem;text-align:center;">
          Smart Attendance System — Automated Email
        </p>
      </div>
    </div>
    """

    try:
        send_mail(
            subject='Password Reset — Smart Attendance System',
            message=f'Reset your password: {reset_url}\nExpires in 1 hour.',
            from_email=settings.EMAIL_HOST_USER,
            recipient_list=[email_to],
            html_message=html_message,
            fail_silently=False,
        )
    except Exception as e:
        logger.error(f"Password reset email failed: {e}")
        return Response({'error': 'Failed to send email. Check email settings.'}, status=500)

    return Response({'message': 'If this account exists, a reset link has been sent.'})

@api_view(['GET'])
def validate_reset_token(request):
    token = request.GET.get('token', '')
    try:
        reset = PasswordResetToken.objects.get(token=token)
        if reset.expires_at < dt.datetime.now():
            reset.delete()
            return Response({'valid': False, 'error': 'This link has expired. Please request a new one.'})
        return Response({'valid': True, 'role': reset.role})
    except PasswordResetToken.DoesNotExist:
        return Response({'valid': False, 'error': 'Invalid or already used link.'})

@api_view(['POST'])
def reset_password(request):
    token = request.data.get('token', '').strip()
    new_password = request.data.get('new_password', '').strip()
    confirm_password = request.data.get('confirm_password', '').strip()

    if new_password != confirm_password:
        return Response({'error': 'Passwords do not match'}, status=400)
    if len(new_password) < 8:
        return Response({'error': 'Password must be at least 8 characters'}, status=400)

    try:
        reset = PasswordResetToken.objects.get(token=token)
    except PasswordResetToken.DoesNotExist:
        return Response({'error': 'Invalid or already used link'}, status=400)

    if reset.expires_at < dt.datetime.now():
        reset.delete()
        return Response({'error': 'Link has expired. Please request a new one.'}, status=400)

    hashed = make_password(new_password)

    if reset.role == 'student':
        try:
            student = Student.objects.get(student_id=reset.identifier)
            student.password = hashed
            student.is_registered = True
            student.save()
        except Student.DoesNotExist:
            return Response({'error': 'Student not found'}, status=404)
    elif reset.role == 'teacher':
        try:
            teacher = Teacher.objects.get(email=reset.identifier)
            teacher.password = hashed
            teacher.save()
        except Teacher.DoesNotExist:
            return Response({'error': 'Teacher not found'}, status=404)
    elif reset.role == 'admin':
        try:
            user = User.objects.get(email=reset.identifier, role='ADMIN')
            user.set_password(new_password)
            user.save()
        except User.DoesNotExist:
            return Response({'error': 'Admin account not found'}, status=404)

    reset.delete()
    return Response({'message': 'Password reset successful. You can now log in.'})

@api_view(['POST'])
def student_check_register(request):
    """Check if register number exists and if student can register."""
    register_number = request.data.get('register_number', '').strip().upper()
    email = request.data.get('email', '').strip().lower()
    
    if not register_number or not email:
        return Response({'error': 'Register number and email are required'}, status=400)
    
    if len(register_number) != 12:
        return Response({'error': 'Register number must be exactly 12 characters'}, status=400)
        
    try:
        student = Student.objects.get(student_id=register_number)
    except Student.DoesNotExist:
        return Response({'error': 'Register number not found. Contact your administrator.'}, status=404)
        
    if student.email.lower() != email and student.parent_email.lower() != email:
        return Response({'error': 'Email does not match our records.'}, status=400)
        
    if student.is_registered:
        return Response({'error': 'already_registered', 'message': 'Account already exists. Please login.'}, status=409)
    return Response({
        'success': True,
        'name': student.name or register_number,
        'register_number': student.student_id,
        'masked_email': mask_email(student.parent_email) if student.parent_email else None,
    })

@api_view(['POST'])
def student_set_password(request):
    """Set password for first-time student registration."""
    register_number = request.data.get('register_number', '').strip().upper()
    email = request.data.get('email', '').strip().lower()
    new_password = request.data.get('new_password', '').strip()
    confirm_password = request.data.get('confirm_password', '').strip()

    if not register_number or not email:
        return Response({'error': 'Register number and email are required'}, status=400)
    if len(register_number) != 12:
        return Response({'error': 'Register number must be exactly 12 characters'}, status=400)
    if new_password != confirm_password:
        return Response({'error': 'Passwords do not match'}, status=400)
    if len(new_password) < 8:
        return Response({'error': 'Password must be at least 8 characters'}, status=400)

    try:
        student = Student.objects.get(student_id=register_number)
    except Student.DoesNotExist:
        return Response({'error': 'Register number not found'}, status=404)

    if student.email.lower() != email and student.parent_email.lower() != email:
        return Response({'error': 'Email does not match our records.'}, status=400)

    if student.is_registered:
        return Response({'error': 'Account is already activated. Please login.'}, status=409)

    student.password = make_password(new_password)
    student.is_registered = True
    student.save()
    return Response({'message': 'Account activated successfully. You can now login.'})

@api_view(['POST'])
def teacher_check_email(request):
    """Check if teacher email exists and if they can register."""
    email = request.data.get('email', '').strip().lower()
    if not email:
        return Response({'error': 'Email is required'}, status=400)
    try:
        teacher = Teacher.objects.get(email=email)
    except Teacher.DoesNotExist:
        return Response({'error': 'Email not found. Contact your administrator.'}, status=404)
    if teacher.password:
        return Response({'error': 'already_registered', 'message': 'Account already active. Please login.'}, status=409)
    return Response({
        'success': True,
        'name': teacher.name or email,
        'email': teacher.email,
    })

@api_view(['POST'])
def teacher_set_password(request):
    """Set password for first-time teacher registration."""
    email = request.data.get('email', '').strip().lower()
    new_password = request.data.get('new_password', '').strip()
    confirm_password = request.data.get('confirm_password', '').strip()

    if not email:
        return Response({'error': 'Email is required'}, status=400)
    if new_password != confirm_password:
        return Response({'error': 'Passwords do not match'}, status=400)
    if len(new_password) < 8:
        return Response({'error': 'Password must be at least 8 characters'}, status=400)

    try:
        teacher = Teacher.objects.get(email=email)
    except Teacher.DoesNotExist:
        return Response({'error': 'Email not found'}, status=404)

    if teacher.password:
        return Response({'error': 'Account is already activated. Please login.'}, status=409)

    teacher.password = make_password(new_password)
    teacher.is_active = True
    teacher.save()
    return Response({'message': 'Account activated successfully. You can now login.'})

