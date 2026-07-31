from django.urls import path
from . import views

urlpatterns = [
    path('admin-login/', views.admin_login),
    path('admin-register/', views.admin_register),
    path('teacher-login/', views.teacher_login),
    path('student-login/', views.student_login),
    path('logout/', views.logout_view),
    path('forgot-password/', views.forgot_password),
    path('validate-reset-token/', views.validate_reset_token),
    path('reset-password/', views.reset_password),
    path('student/check-register/', views.student_check_register),
    path('student/set-password/', views.student_set_password),
    path('teacher/check-email/', views.teacher_check_email),
    path('teacher/set-password/', views.teacher_set_password),
]
