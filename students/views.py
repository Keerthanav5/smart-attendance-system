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
from rest_framework.authentication import SessionAuthentication, BasicAuthentication
from rest_framework.decorators import api_view, parser_classes, authentication_classes
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
# SMS removed in v2.0 — email-only notifications

logger = logging.getLogger(__name__)

@api_view(['GET', 'POST'])
def students(request):
    if request.method == 'GET':
        qs = Student.objects.select_related('assigned_class', 'department', 'user')
        q = request.GET.get('q', '')
        if q:
            qs = qs.filter(Q(name__icontains=q) | Q(student_id__icontains=q))
        class_id = request.GET.get('class_id')
        if class_id:
            qs = qs.filter(assigned_class_id=class_id)
        dept_id = request.GET.get('dept_id')
        if dept_id:
            qs = qs.filter(department_id=dept_id)
        # Pre-calculate totals per class to avoid N+1 queries
        class_ids = qs.values_list('assigned_class_id', flat=True).distinct()
        class_totals = {cid: Attendance.objects.filter(student__assigned_class_id=cid).values('subject_id', 'date', 'period_number').distinct().count() for cid in class_ids if cid}

        data = []
        for s in qs:
            total = class_totals.get(s.assigned_class_id, 0) if s.assigned_class_id else Attendance.objects.filter(student=s).count()
            present = Attendance.objects.filter(student=s, is_present=True).count()
            pct = round((present / total * 100), 1) if total > 0 else 0
            data.append({
                'student_id': s.student_id, 'name': s.name,
                'email': s.email, 'parent_name': s.parent_name,
                'parent_email': s.parent_email, 'parent_phone': s.parent_phone,
                'department': s.department.name if s.department else '',
                'class_name': s.assigned_class.name if s.assigned_class else '', 'assigned_class_id': s.assigned_class_id, 'department_id': s.department_id,
                'is_registered': s.is_registered,
                'attendance_percent': pct
            })
        return Response(data)

    # POST - add single student
    sid = request.data.get('student_id', '').strip()
    name = request.data.get('name', '').strip()
    if not sid or not name:
        return Response({'error': 'student_id and name are required'}, status=400)
    if Student.objects.filter(student_id=sid).exists():
        return Response({'error': 'Register number already exists'}, status=400)
    if User.objects.filter(username=sid).exists():
        return Response({'error': 'Username already exists for this register number'}, status=400)

    dept = None
    if request.data.get('department_id'):
        try:
            dept = Department.objects.get(pk=request.data['department_id'])
        except Department.DoesNotExist:
            pass

    cls = None
    if request.data.get('class_id'):
        try:
            cls = Class.objects.get(pk=request.data['class_id'])
        except Class.DoesNotExist:
            pass

    with transaction.atomic():
        user = User.objects.create(username=sid, role='STUDENT',
                                   first_name=name.split()[0] if name else '')
        user.set_unusable_password()
        user.save()
        student = Student.objects.create(
            user=user, student_id=sid, name=name,
            email=request.data.get('email', ''),
            parent_name=request.data.get('parent_name', ''),
            parent_email=request.data.get('parent_email', ''),
            parent_phone=request.data.get('parent_phone', ''),
            department=dept, assigned_class=cls
        )
        # Normalize parent_phone to 91XXXXXXXXXX format
        if student.parent_phone:
            raw = ''.join(filter(str.isdigit, student.parent_phone.strip()))
            if raw.startswith('0') and len(raw) == 11:
                raw = raw[1:]
            if raw.startswith('91') and len(raw) == 12:
                pass  # already correct
            elif len(raw) == 10:
                raw = '91' + raw
            student.parent_phone = raw
            student.save()
    return Response({'student_id': student.student_id, 'name': student.name}, status=201)

@api_view(['GET', 'PUT', 'DELETE'])
def student_detail(request, student_id):
    try:
        student = Student.objects.select_related('assigned_class', 'department').get(student_id=student_id)
    except Student.DoesNotExist:
        return Response({'error': 'Not found'}, status=404)
    if request.method == 'GET':
        att_qs = Attendance.objects.filter(student=student).order_by('-date', '-time')
        
        # Calculate real total from class sessions
        if student.assigned_class:
            total = Attendance.objects.filter(student__assigned_class=student.assigned_class).values('subject_id', 'date', 'period_number').distinct().count()
        else:
            total = att_qs.count()
            
        present = att_qs.filter(is_present=True).count()
        attendance_percent = round((present / total * 100), 1) if total > 0 else 0

        # Subject-wise
        subject_wise = []
        if student.assigned_class:
            for subj in Subject.objects.filter(semester__class_obj=student.assigned_class).select_related('semester'):
                s_total = Attendance.objects.filter(student__assigned_class=student.assigned_class, subject=subj).values('date', 'period_number').distinct().count()
                s_present = Attendance.objects.filter(student=student, subject=subj, is_present=True).count()
                pct = round((s_present / s_total * 100), 1) if s_total > 0 else 0
                subject_wise.append({
                    'subject': subj.name,
                    'semester': subj.semester.name if subj.semester else '',
                    'total': s_total,
                    'present': s_present,
                    'percent': pct
                })

        history = [{
            'date': str(a.date),
            'subject': a.subject.name,
            'is_present': a.is_present,
            'marked_by': a.marked_by.name if getattr(a, 'marked_by', None) else 'System'
        } for a in att_qs]

        return Response({
            'student_id': student.student_id, 'name': student.name,
            'email': student.email, 'parent_name': student.parent_name,
            'parent_email': student.parent_email, 'parent_phone': student.parent_phone,
            'department': student.department.name if student.department else '',
            'class_name': student.assigned_class.name if student.assigned_class else '',
            'is_registered': student.is_registered,
            'attendance_percent': attendance_percent,
            'subject_wise': subject_wise,
            'history': history
        })
    if request.method == 'PUT':
        student.name = request.data.get('name', student.name)
        student.email = request.data.get('email', student.email)
        student.parent_name = request.data.get('parent_name', student.parent_name)
        student.parent_email = request.data.get('parent_email', student.parent_email)
        student.parent_phone = request.data.get('parent_phone', student.parent_phone)
        
        dept_id = request.data.get('department_id')
        if dept_id:
            try:
                student.department = Department.objects.get(pk=dept_id)
            except Department.DoesNotExist:
                pass

        cls_id = request.data.get('class_id')
        if cls_id:
            try:
                student.assigned_class = Class.objects.get(pk=cls_id)
            except Class.DoesNotExist:
                pass

        # Normalize parent_phone to 91XXXXXXXXXX format
        if student.parent_phone:
            raw = ''.join(filter(str.isdigit, student.parent_phone.strip()))
            if raw.startswith('0') and len(raw) == 11:
                raw = raw[1:]
            if raw.startswith('91') and len(raw) == 12:
                pass  # already correct
            elif len(raw) == 10:
                raw = '91' + raw
            student.parent_phone = raw
        student.save()
        return Response({'student_id': student.student_id, 'name': student.name})
    with transaction.atomic():
        student.user.delete()
    return Response({'message': 'Deleted'})

@api_view(['POST'])
@parser_classes([MultiPartParser, FormParser])
def bulk_upload_students(request):
    file = request.FILES.get('file')
    if not file:
        return Response({'error': 'No file uploaded'}, status=400)

    filename = file.name.lower()
    rows = []

    if filename.endswith('.csv'):
        decoded = file.read().decode('utf-8-sig')
        reader = csv.DictReader(io.StringIO(decoded))
        rows = list(reader)
    elif filename.endswith('.xlsx'):
        import openpyxl
        wb = openpyxl.load_workbook(file)
        ws = wb.active
        headers = [str(cell.value).strip() if cell.value else '' for cell in ws[1]]
        for row in ws.iter_rows(min_row=2, values_only=True):
            if any(v for v in row if v is not None):
                rows.append({headers[i]: (str(row[i]).strip() if row[i] is not None else '') for i in range(len(headers))})
    else:
        return Response({'error': 'Only .csv or .xlsx files allowed'}, status=400)

    # Minimum required columns in the file (dept/class/year optional when selected from UI)
    REQUIRED = ['student_id', 'name', 'parent_email', 'parent_phone']
    success_count = 0
    error_rows = []

    # ── Resolve dept/class from Step-1 form dropdowns ────────────────────
    override_dept  = None
    override_class = None

    dept_id_form  = request.data.get('department_id', '').strip()
    class_id_form = request.data.get('class_id', '').strip()

    if dept_id_form:
        try:
            override_dept = Department.objects.get(pk=dept_id_form)
        except Department.DoesNotExist:
            return Response({'error': 'Selected department not found'}, status=400)

    if class_id_form:
        try:
            override_class = Class.objects.get(pk=class_id_form)
        except Class.DoesNotExist:
            return Response({'error': 'Selected class not found'}, status=400)

    for i, row in enumerate(rows, start=2):
        if not any(str(v).strip() for v in row.values()):
            continue
        missing = [c for c in REQUIRED if not str(row.get(c, '') or '').strip()]
        if missing:
            error_rows.append({'row': i, 'student_id': row.get('student_id', ''), 'reason': f"Missing: {', '.join(missing)}"})
            continue

        sid          = str(row['student_id']).strip()
        name         = str(row.get('name', '') or sid).strip()
        email        = str(row.get('email', '') or '').strip()
        parent_name  = str(row.get('parent_name', '') or '').strip()
        parent_email = str(row['parent_email']).strip()
        parent_phone = str(row['parent_phone']).strip()

        if Student.objects.filter(student_id=sid).exists():
            error_rows.append({'row': i, 'student_id': sid, 'reason': 'Register number already exists'})
            continue
        if User.objects.filter(username=sid).exists():
            error_rows.append({'row': i, 'student_id': sid, 'reason': 'Username conflict'})
            continue


        # Priority: form dropdown > CSV column
        dept      = override_dept
        class_obj = override_class

        if not dept:
            dept_name = str(row.get('department', '') or '').strip()
            if dept_name:
                try:
                    dept = Department.objects.get(name__iexact=dept_name)
                except Department.DoesNotExist:
                    error_rows.append({'row': i, 'student_id': sid,
                        'reason': f"Department '{dept_name}' not found. Add it first or select from the dropdown."})
                    continue

        if not class_obj:
            class_name = str(row.get('class', '') or '').strip()
            if class_name and dept:
                try:
                    class_obj = Class.objects.get(name__iexact=class_name, department=dept)
                except Class.DoesNotExist:
                    error_rows.append({'row': i, 'student_id': sid,
                        'reason': f"Class '{class_name}' not found in '{dept.name}'. Add it first."})
                    continue

        try:
            with transaction.atomic():
                user = User.objects.create(username=sid, role='STUDENT',
                                           first_name=name.split()[0] if name else '')
                user.set_unusable_password()
                user.save()
                Student.objects.create(
                    user=user, student_id=sid, name=name, email=email,
                    parent_name=parent_name, parent_email=parent_email,
                    parent_phone=parent_phone, department=dept,
                    assigned_class=class_obj, is_registered=False
                )
                success_count += 1
        except Exception as e:
            error_rows.append({'row': i, 'student_id': sid, 'reason': str(e)})


    error_file_url = None
    if error_rows:
        import openpyxl
        from openpyxl.styles import PatternFill, Font
        wb2 = openpyxl.Workbook()
        ws2 = wb2.active
        ws2.title = "Errors"
        ws2.append(['Row', 'Register Number', 'Reason'])
        for cell in ws2[1]:
            cell.font = Font(bold=True, color='FFFFFF')
            cell.fill = PatternFill('solid', fgColor='DC2626')
        for r in error_rows:
            ws2.append([r['row'], r['student_id'], r['reason']])
        fname = f"upload_errors_{uuid.uuid4().hex[:8]}.xlsx"
        err_dir = os.path.join(settings.MEDIA_ROOT, 'error_reports')
        os.makedirs(err_dir, exist_ok=True)
        wb2.save(os.path.join(err_dir, fname))
        error_file_url = f"/media/error_reports/{fname}"

    return Response({
        'total': len(rows), 'success': success_count,
        'error_count': len(error_rows), 'errors': error_rows,
        'error_file_url': error_file_url
    })

@api_view(['GET'])
def download_upload_template(request):
    import openpyxl
    from openpyxl.styles import PatternFill, Font, Alignment
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Students"
    headers = ['student_id', 'name', 'email', 'parent_name', 'parent_email', 'parent_phone', 'department', 'class', 'year']
    sample = ['22UUCMS001', 'Rahul Kumar', 'rahul@email.com', 'Suresh Kumar', 'suresh@email.com', '9876543210', 'Computer Science', 'CS-A', '3']
    ws.append(headers)
    ws.append(sample)
    for cell in ws[1]:
        cell.font = Font(bold=True, color='FFFFFF')
        cell.fill = PatternFill('solid', fgColor='2563EB')
        cell.alignment = Alignment(horizontal='center')
    for cell in ws[2]:
        cell.fill = PatternFill('solid', fgColor='DBEAFE')
    widths = [20, 25, 30, 25, 30, 18, 25, 15, 8]
    for col, w in zip(ws.columns, widths):
        ws.column_dimensions[col[0].column_letter].width = w
    response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    response['Content-Disposition'] = 'attachment; filename="student_upload_template.xlsx"'
    wb.save(response)
    return response

@api_view(['POST'])
@authentication_classes([SessionAuthentication, BasicAuthentication])
def send_report_to_parent(request):
    """
    POST /api/students/send-report/
    Sends a full attendance report to the student's parent.
    Only Admin and Teacher roles are allowed.
    """
    # 1. Get student id from payload
    student_pk = request.data.get('student_id')
    if not student_pk:
        return Response({'error': 'student_id is required'}, status=400)

    # 2. Get student (Validate existence)
    try:
        # Check if it's a primary key (integer-like) or register number
        if str(student_pk).isdigit():
            student = Student.objects.select_related('assigned_class', 'department').get(pk=student_pk)
        else:
            student = Student.objects.select_related('assigned_class', 'department').get(student_id=student_pk)
    except Student.DoesNotExist:
        return Response({'error': 'Student not found'}, status=404)

    # 3. Security: Allow Admins (Session) OR Teachers (Token)
    is_admin = request.user.is_authenticated and request.user.role == 'ADMIN'
    is_teacher = get_teacher_from_token(request) is not None
    
    if not (is_admin or is_teacher):
        return Response({'error': 'Unauthorized. Only admins and teachers can send reports.'}, status=403)

    # 4. Get attendance & Calculate statistics
    all_att = Attendance.objects.filter(student=student)
    total_classes = all_att.count()
    present_count = all_att.filter(is_present=True).count()
    overall_pct = round((present_count / total_classes * 100), 1) if total_classes > 0 else 0

    # 5. Calculate subject-wise %
    subject_lines = []
    semester_set = set()
    if student.assigned_class:
        subjects = Subject.objects.filter(semester__class_obj=student.assigned_class).select_related('semester')
        for subj in subjects:
            s_att = all_att.filter(subject=subj)
            s_total = s_att.count()
            s_present = s_att.filter(is_present=True).count()
            s_pct = round((s_present / s_total * 100), 1) if s_total > 0 else 0
            subject_lines.append(f"- {subj.name}: {s_pct}%")
            if subj.semester:
                semester_set.add(subj.semester.name)
    
    subject_summary = "\n".join(subject_lines) if subject_lines else "No subject data available."
    semester_info = ", ".join(semester_set) if semester_set else 'N/A'
    min_pct = SystemSettings.get().min_attendance_percent

    # 6. BUILD MESSAGE
    dept_name = student.department.name if student.department else "Institution"
    class_name = student.assigned_class.name if student.assigned_class else "N/A"
    
    email_subject = f"Attendance Report - {student.name}"
    email_body = f"""Dear Parent,

We would like to inform you about your child's attendance performance.

Student Name: {student.name}
Register Number: {student.student_id}
Class: {class_name}
Semester: {semester_info}

---

Subject-wise Attendance:

{subject_summary}

---

Overall Attendance: {overall_pct}%
Minimum Required Attendance: {min_pct}%

---

We request you to ensure regular attendance for better academic performance.

Regards,
Department of {dept_name}
"""

    # 7. SEND EMAIL
    if student.parent_email:
        try:
            send_mail(
                subject=email_subject,
                message=email_body,
                from_email=settings.EMAIL_HOST_USER,
                recipient_list=[student.parent_email],
                fail_silently=False,
            )
        except Exception as e:
            logger.error(f"Failed to send attendance report email to {student.parent_email}: {str(e)}")

    return Response({"message": "Report sent successfully"})

@api_view(['GET'])
def student_detail_dashboard(request, student_id):
    """
    GET /api/students/<student_id>/dashboard/
    Returns full attendance detail for a student — used by teacher's student detail page.
    """
    try:
        student = Student.objects.select_related('assigned_class', 'department').get(student_id=student_id)
    except Student.DoesNotExist:
        return Response({'error': 'Student not found'}, status=404)

    all_att = Attendance.objects.filter(student=student)
    
    # Calculate real total from class sessions (unique subject+date pairs held for this class)
    if student.assigned_class:
        total = Attendance.objects.filter(student__assigned_class=student.assigned_class).values('subject_id', 'date', 'period_number').distinct().count()
    else:
        total = all_att.count()
        
    present = all_att.filter(is_present=True).count()
    absent = total - present
    overall_pct = round((present / total * 100), 1) if total > 0 else 0

    # Subject-wise breakdown
    subjects_data = []
    if student.assigned_class:
        for subj in Subject.objects.filter(semester__class_obj=student.assigned_class).select_related('semester'):
            s_att = Attendance.objects.filter(student=student, subject=subj)
            
            # Real sessions held for this specific subject
            s_total = Attendance.objects.filter(student__assigned_class=student.assigned_class, subject=subj).values('date', 'period_number').distinct().count()
            
            s_present = s_att.filter(is_present=True).count()
            s_pct = round((s_present / s_total * 100), 1) if s_total > 0 else 0
            subjects_data.append({
                'subject_id': subj.id,
                'subject': subj.name,
                'semester': subj.semester.name if subj.semester else '',
                'code': subj.code,
                'total': s_total,
                'present': s_present,
                'absent': s_total - s_present,
                'percent': s_pct,
                'status': 'Safe' if s_pct >= 75 else ('At Risk' if s_pct >= 60 else 'Danger')
            })
    subjects_data.sort(key=lambda x: x['percent'])

    # Recent 30-day history
    history = []
    for i in range(30):
        day = dt.date.today() - dt.timedelta(days=i)
        day_att = Attendance.objects.filter(student=student, date=day).select_related('subject')
        if day_att.exists():
            history.append({
                'date': str(day),
                'date_label': day.strftime('%d %b'),
                'subjects': [{'name': a.subject.name, 'present': a.is_present} for a in day_att]
            })

    return Response({
        'student_id': student.student_id,
        'name': student.name,
        'email': student.email,
        'class_name': student.assigned_class.name if student.assigned_class else '',
        'class_id': student.assigned_class_id,
        'department': student.department.name if student.department else '',
        'parent_name': student.parent_name,
        'parent_email': student.parent_email,
        'parent_phone': student.parent_phone,
        'overall_percent': overall_pct,
        'total_classes': total,
        'present_count': present,
        'absent_count': absent,
        'subject_breakdown': subjects_data,
        'recent_history': history,
    })

@api_view(['POST'])
@authentication_classes([SessionAuthentication, BasicAuthentication])
def send_bulk_reports(request):
    """
    POST /api/students/send-bulk-reports/
    Sends a full attendance report to all students or specific class.
    Only Admin and Teacher roles are allowed.
    Payload: {"class_id": "all" or specific_class_id}
    """
    class_id = request.data.get('class_id')
    
    is_admin = request.user.is_authenticated and request.user.role == 'ADMIN'
    is_teacher = get_teacher_from_token(request) is not None
    
    if not (is_admin or is_teacher):
        return Response({'error': 'Unauthorized. Only admins and teachers can send reports.'}, status=403)

    if class_id == 'all':
        students = Student.objects.select_related('assigned_class', 'department').all()
    elif class_id:
        students = Student.objects.select_related('assigned_class', 'department').filter(assigned_class_id=class_id)
    else:
        return Response({'error': 'class_id is required'}, status=400)

    sent_count = 0
    college = SystemSettings.get().college_name

    # Optimization: Calculate class totals beforehand
    class_ids = students.values_list('assigned_class_id', flat=True).distinct()
    class_totals = {cid: Attendance.objects.filter(student__assigned_class_id=cid).values('subject_id', 'date', 'period_number').distinct().count() for cid in class_ids if cid}

    for student in students:
        if not student.parent_email:
            continue

        all_att = Attendance.objects.filter(student=student)
        total_classes = class_totals.get(student.assigned_class_id, 0) if student.assigned_class_id else all_att.count()
        present_count = all_att.filter(is_present=True).count()
        overall_pct = round((present_count / total_classes * 100), 1) if total_classes > 0 else 0

        subject_lines = []
        semester_set = set()
        if student.assigned_class:
            subjects = Subject.objects.filter(semester__class_obj=student.assigned_class).select_related('semester')
            for subj in subjects:
                s_att = all_att.filter(subject=subj)
                s_total = Attendance.objects.filter(student__assigned_class=student.assigned_class, subject=subj).values('date', 'period_number').distinct().count()
                s_present = s_att.filter(is_present=True).count()
                s_pct = round((s_present / s_total * 100), 1) if s_total > 0 else 0
                subject_lines.append(f"- {subj.name}: {s_pct}%")
                if subj.semester:
                    semester_set.add(subj.semester.name)
        
        subject_summary = "\n".join(subject_lines) if subject_lines else "No subject data available."
        semester_info = ", ".join(semester_set) if semester_set else 'N/A'
        min_pct = SystemSettings.get().min_attendance_percent

        dept_name = student.department.name if student.department else "Institution"
        class_name = student.assigned_class.name if student.assigned_class else "N/A"
        
        email_subject = f"Attendance Report - {student.name}"
        email_body = f"""Dear Parent,

We would like to inform you about your child's attendance performance.

Student Name: {student.name}
Register Number: {student.student_id}
Class: {class_name}
Semester: {semester_info}

---

Subject-wise Attendance:

{subject_summary}

---

Overall Attendance: {overall_pct}%
Minimum Required Attendance: {min_pct}%

---

We request you to ensure regular attendance for better academic performance.

Regards,
Department of {dept_name}
"""

        email_sent = False
        if student.parent_email:
            try:
                send_mail(
                    subject=email_subject,
                    message=email_body,
                    from_email=settings.EMAIL_HOST_USER,
                    recipient_list=[student.parent_email],
                    fail_silently=False,
                )
                email_sent = True
            except Exception as e:
                logger.error(f"Failed to send attendance report email to {student.parent_email}: {str(e)}")

        if email_sent:
            sent_count += 1

    return Response({"message": f"Reports sent successfully to {sent_count} parents."})
