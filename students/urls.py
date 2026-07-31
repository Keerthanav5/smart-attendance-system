from django.urls import path
from . import views

urlpatterns = [
    path('', views.students),
    path('bulk-upload/', views.bulk_upload_students),
    path('upload-template/', views.download_upload_template),
    path('<str:student_id>/dashboard/', views.student_detail_dashboard),
    path('send-report/', views.send_report_to_parent),
    path('send-bulk-reports/', views.send_bulk_reports),
    path('<str:student_id>/', views.student_detail),
]
