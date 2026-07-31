from django.urls import path
from . import views

urlpatterns = [
    path('', views.timetable),
    path('today/', views.today_timetable),
    path('semester/<int:semester_id>/', views.timetable_by_semester),
    path('<int:pk>/', views.timetable_detail),
]
