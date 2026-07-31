from django.urls import path
from . import views

urlpatterns = [
    path('search/', views.global_search),
    path('settings/', views.system_settings),
    path('test-email/', views.test_email),
    path('delete-all/departments/', views.delete_all_departments),
    path('delete-all/classes/', views.delete_all_classes),
    path('delete-all/subjects/', views.delete_all_subjects),
    path('delete-all/teachers/', views.delete_all_teachers),
    path('delete-all/students/', views.delete_all_students),
]
