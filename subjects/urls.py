from django.urls import path
from . import views

urlpatterns = [
    path('', views.subjects),
    path('by-class/<int:class_id>/', views.subjects_by_class),
    path('by-semester/<int:semester_id>/', views.subjects_by_semester),
    path('<int:pk>/', views.subject_detail),
]
