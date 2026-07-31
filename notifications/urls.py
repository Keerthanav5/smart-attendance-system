from django.urls import path
from . import views

urlpatterns = [
    path('', views.notification_logs),
    path('send-alerts/', views.send_absent_alerts),
    path('send-class-alerts/', views.send_class_absent_alerts),
]
