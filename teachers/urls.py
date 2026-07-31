from django.urls import path
from . import views

urlpatterns = [
    path('', views.teachers),
    path('<int:pk>/', views.teacher_detail),
]
