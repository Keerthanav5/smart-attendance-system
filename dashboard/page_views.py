from django.shortcuts import render, redirect
from django.contrib.auth import logout
from functools import wraps


# ── Auth protection decorator ────────────────────────────────────────────────

def admin_required(view_func):
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('/login/?next=' + request.path)
        if request.user.role != 'ADMIN':
            return redirect('/login/')
        return view_func(request, *args, **kwargs)
    return wrapper


# ── Helpers ──────────────────────────────────────────────────────────────────

def redirect_root(request):
    logout(request)
    return redirect('/login/')


def logout_page(request):
    logout(request)
    return redirect('/login/')


# ── Admin auth ───────────────────────────────────────────────────────────────

def admin_login_page(request):
    if request.user.is_authenticated and request.user.role == 'ADMIN':
        return redirect('/admin-dashboard/')
    return render(request, 'auth/login.html')


def admin_register_page(request):
    if request.user.is_authenticated and request.user.role == 'ADMIN':
        return redirect('/admin-dashboard/')
    return render(request, 'auth/admin_register.html')


def admin_forgot_page(request):
    return render(request, 'auth/admin_forgot.html')


# ── Teacher auth ─────────────────────────────────────────────────────────────

def teacher_login_page(request):
    if request.user.is_authenticated and request.user.role == 'TEACHER':
        return redirect('/teacher/dashboard/')
    return render(request, 'auth/teacher_login.html')


def teacher_register_page(request):
    return render(request, 'auth/teacher_register.html')


def teacher_forgot_page(request):
    return render(request, 'auth/teacher_forgot.html')


# ── Student auth ─────────────────────────────────────────────────────────────

def student_login_page(request):
    if request.user.is_authenticated and request.user.role == 'STUDENT':
        return redirect('/student/dashboard/')
    return render(request, 'auth/student_login.html')


def student_register_page(request):
    return render(request, 'auth/student_register.html')


def student_forgot_page(request):
    return render(request, 'auth/student_forgot.html')


def reset_password_page(request):
    return render(request, 'auth/reset_password.html')


# ── Admin pages (all protected) ───────────────────────────────────────────────

@admin_required
def admin_dashboard_page(request):
    return render(request, 'admin/dashboard.html')


@admin_required
def departments_page(request):
    return render(request, 'admin/departments.html')


@admin_required
def classes_page(request):
    return render(request, 'admin/classes.html')


@admin_required
def subjects_page(request):
    return render(request, 'admin/subjects.html')


@admin_required
def teachers_page(request):
    return render(request, 'admin/teachers.html')


@admin_required
def students_page(request):
    return render(request, 'admin/students.html')


@admin_required
def upload_students_page(request):
    return render(request, 'admin/upload_students.html')

@admin_required
def admin_timetable_page(request):
    return render(request, 'admin/timetable.html')



@admin_required
def admin_student_detail_page(request, student_id):
    return render(request, 'admin/student_detail.html', {'student_id': student_id})
@admin_required
def holidays_page(request):
    return render(request, 'admin/holidays.html')


@admin_required
def reports_page(request):
    return render(request, 'admin/reports.html')


@admin_required
def notifications_page(request):
    return render(request, 'admin/notifications.html')


# ── Teacher pages ─────────────────────────────────────────────────────────────

def teacher_dashboard_page(request):
    return render(request, 'teacher/dashboard.html')


def mark_attendance_page(request):
    return render(request, 'teacher/mark_attendance.html')


def edit_attendance_page(request):
    return render(request, 'teacher/edit_attendance.html')


def teacher_percentage_page(request):
    return render(request, 'teacher/attendance_percentage.html')

def teacher_notifications_page(request):
    return render(request, 'teacher/notifications.html')

def teacher_students_page(request):
    return render(request, 'teacher/students.html')


def teacher_timetable_page(request):
    """Teacher-only timetable view (Dept → Class → Subject flow)."""
    return render(request, 'teacher/timetable.html')


def student_detail_page(request, student_id):
    """Student detail dashboard for teacher view."""
    return render(request, 'teacher/student_detail.html', {'student_id': student_id})


# ── Student pages ─────────────────────────────────────────────────────────────

def student_dashboard_page(request):
    return render(request, 'student/dashboard.html')

def student_attendance_page(request):
    return render(request, 'student/attendance.html')

def student_percentage_page(request):
    return render(request, 'student/attendance_percentage.html')
