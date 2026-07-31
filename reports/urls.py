from django.urls import path
from . import views

urlpatterns = [
    path('data/', views.reports_data),
    path('export/excel/', views.export_excel),
    path('export/csv/', views.export_csv),
    path('export/pdf/', views.export_pdf),
]
