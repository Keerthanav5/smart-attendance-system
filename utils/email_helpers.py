# ═══════════════════════════════════════════════════════════════════════
# RPA Smart Attendance System — Email Helper Utilities
# Centralises bilingual email rendering for absence notifications.
# Used by notifications/views.py and attendance/views.py.
# ═══════════════════════════════════════════════════════════════════════

import logging
from django.template.loader import render_to_string
from utils.models import SystemSettings

logger = logging.getLogger(__name__)


def build_absence_alert_html(student, absent_subjects, date, pct=None, min_pct=None):
    """
    Render the bilingual (English + Kannada) absence alert email.

    Parameters
    ----------
    student       : students.models.Student instance
    absent_subjects : list of subjects.models.Subject instances (deduplicated)
    date          : datetime.date — the attendance date
    pct           : float | None — overall attendance percentage (auto-calculated if None)
    min_pct       : int | None — minimum required percentage (fetched from settings if None)

    Returns
    -------
    str — rendered HTML email body
    """
    from attendance.models import Attendance  # local import to avoid circular

    # Auto-calculate percentage if not provided
    if pct is None:
        total = Attendance.objects.filter(student=student).count()
        present = Attendance.objects.filter(student=student, is_present=True).count()
        pct = round((present / total * 100), 1) if total > 0 else 0

    if min_pct is None:
        min_pct = SystemSettings.get().min_attendance_percent

    # Build subject name list
    subject_names = [s.name for s in absent_subjects]

    # Extract student metadata with safe fallbacks
    dept_name = 'N/A'
    class_name = 'N/A'
    if student.assigned_class:
        class_name = student.assigned_class.name
        if student.assigned_class.department:
            dept_name = student.assigned_class.department.name

    # Build semester info from subjects
    semester_set = set()
    for s in absent_subjects:
        if hasattr(s, 'semester') and s.semester:
            semester_set.add(s.semester.name)
    semester_info = ', '.join(semester_set) if semester_set else 'N/A'

    # Attendance percentage color
    pct_color = '#DC2626' if pct < min_pct else '#16A34A'

    context = {
        'student_name': student.name or student.student_id,
        'parent_name': student.parent_name or 'Parent/Guardian',
        'student_id': student.student_id,
        'date_formatted': date.strftime('%d %B %Y'),
        'date_kannada': date.strftime('%d-%m-%Y'),
        'absent_subjects': subject_names,
        'dept_name': dept_name,
        'class_name': class_name,
        'semester_info': semester_info,
        'pct': pct,
        'pct_color': pct_color,
        'min_pct': min_pct,
        'college_name': SystemSettings.get().college_name,
    }

    try:
        html = render_to_string('emails/absence_alert.html', context)
    except Exception as e:
        logger.error(f"Failed to render absence_alert template: {e}")
        # Fallback: return a minimal plain-text-style HTML
        html = _fallback_html(context)

    return html


def _fallback_html(ctx):
    """Minimal fallback HTML if the template fails to render."""
    subjects_str = ', '.join(ctx['absent_subjects'])
    return f"""
    <div style="font-family:Arial,sans-serif;max-width:560px;margin:0 auto;padding:20px;">
      <h2 style="color:#6D5DF6;">Attendance Alert – RPA First Grade College</h2>
      <p>Dear <strong>{ctx['parent_name']}</strong>,</p>
      <p>Your child <strong>{ctx['student_name']}</strong> ({ctx['student_id']})
      was marked ABSENT on <strong>{ctx['date_formatted']}</strong>
      for: <strong>{subjects_str}</strong>.</p>
      <p>Department: {ctx['dept_name']} | Semester: {ctx['semester_info']}</p>
      <p>Overall Attendance: {ctx['pct']}% (Minimum: {ctx['min_pct']}%)</p>
      <hr>
      <p>ನಿಮ್ಮ ಮಗ/ಮಗಳು <strong>{ctx['student_name']}</strong> ಅವರು
      ದಿನಾಂಕ {ctx['date_kannada']} ರಂದು ಗೈರುಹಾಜರಾಗಿದ್ದಾರೆ.</p>
      <p style="color:#94A3B8;font-size:12px;">RPA First Grade College · RPA Smart Attendance System</p>
    </div>"""
