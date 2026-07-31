from django.urls import path
from . import views

urlpatterns = [
    path('', views.classes),
    path('by-department/<int:dept_id>/', views.classes_by_department),
    path('<int:class_id>/semesters/', views.semesters_by_class),
    path('<int:pk>/', views.class_detail),
]
