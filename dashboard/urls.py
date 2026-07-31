from django.urls import path
from . import views
from attendance.views import student_attendance_log

urlpatterns = [
    path('admin/', views.admin_stats),
    path('admin/charts/', views.admin_chart_data),
    path('teacher/', views.teacher_stats),
    path('teacher/charts/', views.teacher_chart_data),
    path('dashboard/', views.student_dashboard),
    path('calendar/', views.student_calendar),
    path('attendance-log/', student_attendance_log),
]
