import os, io, csv, uuid, jwt, secrets, logging, datetime as dt
from django.shortcuts import render, redirect
from django.http import HttpResponse
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.hashers import make_password, check_password
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.conf import settings
from django.db import transaction
from django.db.models import Q, Count, Avg
from django.utils import timezone
from rest_framework.decorators import api_view, parser_classes
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.response import Response
from authentication.models import User, PasswordResetToken
from departments.models import Department
from classes.models import Class
from subjects.models import Subject
from students.models import Student
from teachers.models import Teacher
from timetable.models import Timetable
from attendance.models import Attendance, Holiday
from notifications.models import NotificationLog
from utils.models import SystemSettings
try:
    from utils.views import get_student_from_token, get_teacher_from_token, mask_email, calculate_student_percent
except ImportError:
    pass

logger = logging.getLogger(__name__)

from attendance.views import _get_attendance_summary_data

@api_view(['POST'])
def reports_data(request):
    return Response(_get_attendance_summary_data(
        class_id=request.data.get('class_id'),
        subject_id=request.data.get('subject_id'),
        date_from=request.data.get('from'),
        date_to=request.data.get('to')
    ))

@api_view(['POST'])
def export_excel(request):
    import xlsxwriter
    try:
        output = io.BytesIO()
        wb = xlsxwriter.Workbook(output, {'in_memory': True})
        ws = wb.add_worksheet('Attendance Report')
        col_settings = SystemSettings.get()

        title_fmt = wb.add_format({'bold': True, 'font_size': 14, 'align': 'center', 'valign': 'vcenter', 'font_name': 'Arial'})
        subtitle_fmt = wb.add_format({'bold': True, 'font_size': 11, 'align': 'center', 'valign': 'vcenter', 'font_color': '#555555', 'font_name': 'Arial'})
        header_fmt = wb.add_format({'bold': True, 'bg_color': '#6D5DF6', 'font_color': 'white', 'align': 'center', 'border': 1, 'font_name': 'Arial', 'text_wrap': True})
        green_fmt = wb.add_format({'bg_color': '#DCFCE7', 'border': 1, 'font_name': 'Arial'})
        yellow_fmt = wb.add_format({'bg_color': '#FEF9C3', 'border': 1, 'font_name': 'Arial'})
        red_fmt = wb.add_format({'bg_color': '#FEE2E2', 'border': 1, 'font_name': 'Arial'})
        normal_fmt = wb.add_format({'border': 1, 'font_name': 'Arial'})
        footer_fmt = wb.add_format({'italic': True, 'font_size': 9, 'font_color': '#888888', 'font_name': 'Arial'})

        class_id = request.data.get('class_id')
        subject_id = request.data.get('subject_id')
        date_from = request.data.get('from')
        date_to = request.data.get('to')

        # Bilingual title rows
        ws.merge_range('A1:H1', col_settings.college_name, title_fmt)
        ws.merge_range('A2:H2', f"Attendance Report / \u0cb9\u0cbe\u0c9c\u0cb0\u0cbe\u0ca4\u0cbf \u0cb5\u0cb0\u0ca6\u0cbf \u2014 {date_from or ''} to {date_to or dt.date.today()}", subtitle_fmt)
        ws.set_row(0, 28)
        ws.set_row(1, 22)

        subjects_to_show = []
        if not subject_id and class_id:
            subjects_qs = Subject.objects.filter(semester__class_obj_id=class_id)
            subjects_to_show = list(subjects_qs.order_by('code'))

        # Bilingual headers
        headers = [
            'Reg No\n(\u0ca8\u0ccb\u0c82\u0ca6\u0ca3\u0cbf \u0cb8\u0c82\u0c96\u0ccd\u0caf\u0cc6)',
            'Name\n(\u0cb9\u0cc6\u0cb8\u0cb0\u0cc1)',
            'Department\n(\u0cb5\u0cbf\u0cad\u0cbe\u0c97)',
            'Class\n(\u0ca4\u0cb0\u0c97\u0ca4\u0cbf)',
            'Total\n(\u0c92\u0c9f\u0ccd\u0c9f\u0cc1)',
            'Present\n(\u0cb9\u0cbe\u0c9c\u0cb0\u0cbf)',
            'Absent\n(\u0c97\u0cc8\u0cb0\u0cc1\u0cb9\u0cbe\u0c9c\u0cb0\u0cbf)',
            'Percentage\n(\u0cb6\u0cc7\u0c95\u0ca1\u0cbe)'
        ]
        for sub in subjects_to_show:
            headers.append(f"{sub.name} %")

        start_row = 3
        for col, h in enumerate(headers):
            ws.write(start_row, col, h, header_fmt)
        ws.set_row(start_row, 32)

        widths = [18, 25, 22, 15, 10, 10, 10, 14] + [14] * len(subjects_to_show)
        for i, w in enumerate(widths):
            ws.set_column(i, i, w)

        students_qs = Student.objects.select_related('assigned_class', 'department')
        if class_id:
            students_qs = students_qs.filter(assigned_class_id=class_id)

        row_count = 0
        for row_idx, student in enumerate(students_qs):
            att_qs = Attendance.objects.filter(student=student)
            if subject_id:
                att_qs = att_qs.filter(subject_id=subject_id)
            if date_from:
                att_qs = att_qs.filter(date__gte=date_from)
            if date_to:
                att_qs = att_qs.filter(date__lte=date_to)
            total = att_qs.count()
            present = att_qs.filter(is_present=True).count()
            absent = total - present
            pct = round((present / total * 100), 1) if total > 0 else 0
            fmt = green_fmt if pct >= 75 else (yellow_fmt if pct >= 60 else red_fmt)
            row = row_idx + start_row + 1
            ws.write(row, 0, student.student_id, normal_fmt)
            ws.write(row, 1, student.name or '', normal_fmt)
            ws.write(row, 2, student.department.name if student.department else '', normal_fmt)
            ws.write(row, 3, student.assigned_class.name if student.assigned_class else '', normal_fmt)
            ws.write(row, 4, total, normal_fmt)
            ws.write(row, 5, present, normal_fmt)
            ws.write(row, 6, absent, normal_fmt)
            ws.write(row, 7, f"{pct}%", fmt)

            col_idx = 8
            for sub in subjects_to_show:
                sub_att_qs = att_qs.filter(subject=sub)
                sub_total = sub_att_qs.count()
                if sub_total > 0:
                    sub_present = sub_att_qs.filter(is_present=True).count()
                    sub_pct = round((sub_present / sub_total * 100), 1)
                    sub_fmt = green_fmt if sub_pct >= 75 else (yellow_fmt if sub_pct >= 60 else red_fmt)
                    ws.write(row, col_idx, f"{sub_pct}%", sub_fmt)
                else:
                    ws.write(row, col_idx, "N/A", normal_fmt)
                col_idx += 1
            row_count = row_idx

        # Bilingual footer
        footer_row = row_count + start_row + 3
        min_pct = col_settings.min_attendance_percent
        ws.merge_range(footer_row, 0, footer_row, 7,
            f"Note: Minimum required attendance is {min_pct}%. / \u0c97\u0cae\u0ca8\u0cbf\u0cb8\u0cbf: \u0c95\u0ca8\u0cbf\u0cb7\u0ccd\u0c9f \u0cb9\u0cbe\u0c9c\u0cb0\u0cbe\u0ca4\u0cbf {min_pct}% \u0c86\u0c97\u0cbf\u0ca6\u0cc6.", footer_fmt)

        wb.close()
        output.seek(0)
        resp = HttpResponse(output.getvalue(),
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
        resp['Content-Disposition'] = 'attachment; filename="attendance_report.xlsx"'
        return resp
    except Exception as e:
        logger.exception("Excel export failed")
        return HttpResponse(f"Export failed: {e}", status=500, content_type='text/plain')

@api_view(['POST'])
def export_csv(request):
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="attendance_report.csv"'
    writer = csv.writer(response)
    class_id = request.data.get('class_id')
    subject_id = request.data.get('subject_id')
    
    subjects_to_show = []
    if not subject_id and class_id:
        subjects_qs = Subject.objects.filter(semester__class_obj_id=class_id)
        subjects_to_show = list(subjects_qs.order_by('code'))

    headers = ['Reg No', 'Name', 'Department', 'Class', 'Total', 'Present', 'Absent', 'Percentage']
    for sub in subjects_to_show:
        headers.append(f"{sub.name} %")
    writer.writerow(headers)

    students_qs = Student.objects.select_related('assigned_class', 'department')
    if class_id:
        students_qs = students_qs.filter(assigned_class_id=class_id)

    date_from = request.data.get('from')
    date_to = request.data.get('to')

    for student in students_qs:
        att_qs = Attendance.objects.filter(student=student)
        if subject_id:
            att_qs = att_qs.filter(subject_id=subject_id)
        if date_from:
            att_qs = att_qs.filter(date__gte=date_from)
        if date_to:
            att_qs = att_qs.filter(date__lte=date_to)

        total = att_qs.count()
        present = att_qs.filter(is_present=True).count()
        pct = round((present / total * 100), 1) if total > 0 else 0
        
        row_data = [
            student.student_id, student.name, 
            student.department.name if student.department else '',
            student.assigned_class.name if student.assigned_class else '',
            total, present, total - present, f"{pct}%"
        ]

        for sub in subjects_to_show:
            sub_att_qs = att_qs.filter(subject=sub)
            sub_total = sub_att_qs.count()
            if sub_total > 0:
                sub_present = sub_att_qs.filter(is_present=True).count()
                sub_pct = round((sub_present / sub_total * 100), 1)
                row_data.append(f"{sub_pct}%")
            else:
                row_data.append("N/A")

        writer.writerow(row_data)
    return response

@api_view(['POST'])
def export_pdf(request):
    import io
    from reportlab.lib.pagesizes import letter
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.lib import colors

    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = 'attachment; filename="attendance_report.pdf"'

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter)
    elements = []
    
    styles = getSampleStyleSheet()
    col_settings = SystemSettings.get()
    
    elements.append(Paragraph(col_settings.college_name, styles['Title']))
    date_from = request.data.get('from', '')
    date_to = request.data.get('to', str(dt.date.today()))
    elements.append(Paragraph(f"Attendance Report — {date_from} to {date_to}", styles['Heading2']))
    elements.append(Spacer(1, 12))

    class_id = request.data.get('class_id')
    subject_id = request.data.get('subject_id')

    subjects_to_show = []
    if not subject_id and class_id:
        subjects_qs = Subject.objects.filter(semester__class_obj_id=class_id)
        subjects_to_show = list(subjects_qs.order_by('code'))

    headers = ['Reg No', 'Name', 'Class', 'Total', 'Present', 'Absent', '%']
    for sub in subjects_to_show:
        headers.append(f"{sub.code} %")
    data = [headers]

    students_qs = Student.objects.select_related('assigned_class')
    if class_id:
        students_qs = students_qs.filter(assigned_class_id=class_id)

    for student in students_qs:
        att_qs = Attendance.objects.filter(student=student)
        if subject_id:
            att_qs = att_qs.filter(subject_id=subject_id)
        if date_from:
            att_qs = att_qs.filter(date__gte=date_from)
        if date_to:
            att_qs = att_qs.filter(date__lte=date_to)
            
        total = att_qs.count()
        present = att_qs.filter(is_present=True).count()
        absent = total - present
        pct = round((present / total * 100), 1) if total > 0 else 0
        
        row_data = [
            student.student_id,
            student.name or '',
            student.assigned_class.name if student.assigned_class else '',
            str(total), str(present), str(absent), f"{pct}%"
        ]

        for sub in subjects_to_show:
            sub_att_qs = att_qs.filter(subject=sub)
            sub_total = sub_att_qs.count()
            if sub_total > 0:
                sub_present = sub_att_qs.filter(is_present=True).count()
                sub_pct = round((sub_present / sub_total * 100), 1)
                row_data.append(f"{sub_pct}%")
            else:
                row_data.append("N/A")

        data.append(row_data)

    t = Table(data)
    t.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#2563EB')),
        ('TEXTCOLOR', (0,0), (-1,0), colors.whitesmoke),
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('BOTTOMPADDING', (0,0), (-1,0), 12),
        ('BACKGROUND', (0,1), (-1,-1), colors.beige),
        ('GRID', (0,0), (-1,-1), 1, colors.black)
    ]))
    
    elements.append(t)
    doc.build(elements)
    
    pdf = buffer.getvalue()
    buffer.close()
    response.write(pdf)
    return response

