#!/bin/bash
# ============================================================
#  Smart Attendance System — Restructure Script
#  Run this from INSIDE the Smart_Attendance_System/ folder
#  Usage:  cd Smart_Attendance_System && bash restructure.sh
# ============================================================

set -e
echo "🚀 Starting restructure..."

# ── 1. Move manage.py to root (outside backend/) ────────────
cp backend/manage.py ./manage.py
echo "✅ manage.py copied to root"

# ── 2. Create modules/ folder with 14 subfolders ────────────
mkdir -p modules/01_authentication
mkdir -p modules/02_user_management
mkdir -p modules/03_department
mkdir -p modules/04_class_management
mkdir -p modules/05_subject
mkdir -p modules/06_timetable
mkdir -p modules/07_attendance
mkdir -p modules/08_reports
mkdir -p modules/09_notifications
mkdir -p modules/10_holidays
mkdir -p modules/11_student_upload
mkdir -p modules/12_dashboard
mkdir -p modules/13_utils
mkdir -p modules/14_api
echo "✅ 14 module folders created"

# ── 3. Copy relevant files into each module ─────────────────

# Module 01 — Authentication
cp -r templates/auth/            modules/01_authentication/templates
cp backend/api/views.py          modules/01_authentication/views_reference.py

# Module 02 — User Management
cp backend/api/models.py         modules/02_user_management/models_reference.py
cp backend/api/admin.py          modules/02_user_management/admin_reference.py

# Module 03 — Department
cp backend/api/models.py         modules/03_department/models_reference.py

# Module 04 — Class Management
cp backend/api/models.py         modules/04_class_management/models_reference.py

# Module 05 — Subject
cp backend/api/models.py         modules/05_subject/models_reference.py

# Module 06 — Timetable
cp -r templates/teacher/timetable.html  modules/06_timetable/

# Module 07 — Attendance
cp templates/teacher/mark_attendance.html   modules/07_attendance/
cp templates/teacher/edit_attendance.html   modules/07_attendance/
cp templates/student/attendance.html        modules/07_attendance/
cp templates/student/attendance_percentage.html  modules/07_attendance/
cp templates/teacher/attendance_percentage.html  modules/07_attendance/

# Module 08 — Reports
cp templates/teacher/reports.html   modules/08_reports/
cp templates/admin/reports.html     modules/08_reports/admin_reports.html

# Module 09 — Notifications
cp templates/teacher/notifications.html   modules/09_notifications/
cp templates/admin/notifications.html     modules/09_notifications/admin_notifications.html
cp -r backend/utils/                      modules/09_notifications/utils

# Module 10 — Holidays
cp templates/admin/holidays.html    modules/10_holidays/

# Module 11 — Student Upload
cp templates/admin/upload_students.html   modules/11_student_upload/

# Module 12 — Dashboard
cp templates/admin/dashboard.html     modules/12_dashboard/admin_dashboard.html
cp templates/teacher/dashboard.html   modules/12_dashboard/teacher_dashboard.html
cp templates/student/dashboard.html   modules/12_dashboard/student_dashboard.html
cp templates/base.html                modules/12_dashboard/base.html

# Module 13 — Utils
cp -r backend/utils/   modules/13_utils/

# Module 14 — Core API (main Django app)
cp -r backend/api/     modules/14_api/

echo "✅ Files copied into modules"

# ── 4. Add README.md inside each module ─────────────────────

cat > modules/01_authentication/README.md << 'EOF'
# Module 01 — Authentication
Handles login, logout, and password reset for Admin, Teacher, and Student roles.
Includes forgot-password flow with email token validation.
Key endpoints: /auth/admin-login/, /auth/teacher-login/, /auth/student-login/
EOF

cat > modules/02_user_management/README.md << 'EOF'
# Module 02 — User Management
Manages Admin, Teacher, and Student user accounts.
Supports create, update, delete operations with role-based access control.
Key endpoints: /teachers/, /students/, /students/<id>/
EOF

cat > modules/03_department/README.md << 'EOF'
# Module 03 — Department
Manages college departments (e.g., CSE, ECE, MECH).
Departments are linked to classes and subjects.
Key endpoints: /departments/, /departments/<id>/
EOF

cat > modules/04_class_management/README.md << 'EOF'
# Module 04 — Class Management
Manages classes/sections within departments.
Each class contains students and is assigned subjects and a timetable.
Key endpoints: /classes/, /classes/by-department/<dept_id>/
EOF

cat > modules/05_subject/README.md << 'EOF'
# Module 05 — Subject
Manages subjects assigned to each class.
Subjects are linked to teachers via the timetable.
Key endpoints: /subjects/, /subjects/by-class/<class_id>/
EOF

cat > modules/06_timetable/README.md << 'EOF'
# Module 06 — Timetable
Manages the weekly class schedule for teachers and students.
Timetable entries link a class, subject, teacher, day, and period.
Key endpoints: /timetable/, /timetable/today/, /timetable/class/<class_id>/
EOF

cat > modules/07_attendance/README.md << 'EOF'
# Module 07 — Attendance
Core module for marking, editing, and viewing attendance.
Supports period-wise attendance with present/absent/late status.
Key endpoints: /attendance/mark/, /attendance/edit/, /attendance/summary/
EOF

cat > modules/08_reports/README.md << 'EOF'
# Module 08 — Reports
Generates attendance reports with filters by class, subject, date range.
Supports export in Excel, CSV, and PDF formats.
Key endpoints: /reports/data/, /reports/export/excel/, /reports/export/pdf/
EOF

cat > modules/09_notifications/README.md << 'EOF'
# Module 09 — Notifications
Sends automated absence alerts to students via Email, SMS, and WhatsApp (Twilio).
Logs all sent notifications with timestamps.
Key endpoints: /notifications/send-alerts/, /notifications/send-class-alerts/
EOF

cat > modules/10_holidays/README.md << 'EOF'
# Module 10 — Holidays
Manages the academic holiday calendar.
Attendance cannot be marked on holidays; system checks this automatically.
Key endpoints: /holidays/, /holidays/<id>/
EOF

cat > modules/11_student_upload/README.md << 'EOF'
# Module 11 — Student Bulk Upload
Allows admin to upload students in bulk via Excel file.
Validates data, reports errors in a downloadable error report file.
Key endpoints: /students/bulk-upload/, /students/upload-template/
EOF

cat > modules/12_dashboard/README.md << 'EOF'
# Module 12 — Dashboard
Role-specific dashboards for Admin, Teacher, and Student.
Shows stats, recent activity, attendance summary, and quick actions.
Key endpoints: /stats/admin/, /stats/teacher/, /student/dashboard/
EOF

cat > modules/13_utils/README.md << 'EOF'
# Module 13 — Utils
Shared utility functions used across the project.
Includes notification helpers (email, SMS, WhatsApp via Twilio).
File: utils/notifications.py
EOF

cat > modules/14_api/README.md << 'EOF'
# Module 14 — Core API
The main Django app containing all models, views, URLs, and migrations.
This is the heart of the backend — all other modules reference files from here.
Key files: models.py, views.py, urls.py, migrations/
EOF

echo "✅ README.md created in all 14 modules"

# ── 5. Add a top-level project README ───────────────────────
cat > modules/README.md << 'EOF'
# Smart Attendance System — Module Overview

| # | Module               | Description                              |
|---|----------------------|------------------------------------------|
| 01 | Authentication      | Login, logout, password reset            |
| 02 | User Management     | Admin, Teacher, Student accounts         |
| 03 | Department          | College department management            |
| 04 | Class Management    | Classes and sections per department      |
| 05 | Subject             | Subjects assigned to classes             |
| 06 | Timetable           | Weekly schedule for classes              |
| 07 | Attendance          | Mark, edit, view attendance              |
| 08 | Reports             | Generate & export attendance reports     |
| 09 | Notifications       | Email/SMS/WhatsApp absence alerts        |
| 10 | Holidays            | Academic holiday calendar                |
| 11 | Student Upload      | Bulk student upload via Excel            |
| 12 | Dashboard           | Role-based dashboards & stats            |
| 13 | Utils               | Shared utility functions                 |
| 14 | Core API            | Main Django app (models, views, urls)    |
EOF

echo "✅ Module overview README created"
echo ""
echo "============================================"
echo "  ✅ Restructure complete!"
echo "============================================"
echo ""
echo "📁 New structure:"
echo "  Smart_Attendance_System/"
echo "  ├── manage.py          ← root level ✅"
echo "  ├── modules/           ← 14 modules ✅"
echo "  │   ├── 01_authentication/"
echo "  │   ├── 02_user_management/"
echo "  │   ├── 03_department/"
echo "  │   ├── 04_class_management/"
echo "  │   ├── 05_subject/"
echo "  │   ├── 06_timetable/"
echo "  │   ├── 07_attendance/"
echo "  │   ├── 08_reports/"
echo "  │   ├── 09_notifications/"
echo "  │   ├── 10_holidays/"
echo "  │   ├── 11_student_upload/"
echo "  │   ├── 12_dashboard/"
echo "  │   ├── 13_utils/"
echo "  │   └── 14_api/"
echo "  ├── backend/           ← original code untouched ✅"
echo "  ├── templates/"
echo "  ├── static/"
echo "  └── media/"
echo ""
echo "▶  To run the project (same as before):"
echo "   cd backend && python manage.py runserver"
echo "   OR from root: python manage.py runserver (update DJANGO_SETTINGS_MODULE first)"
