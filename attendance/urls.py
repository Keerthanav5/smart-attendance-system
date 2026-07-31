from django.urls import path
from . import views

urlpatterns = [
    path('mark/', views.mark_attendance),
    path('edit/', views.edit_attendance),
    path('status/', views.attendance_status),
    path('list/', views.attendance_list),
    path('summary/', views.attendance_summary),
]
