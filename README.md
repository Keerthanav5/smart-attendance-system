# Smart Attendance System

A web-based attendance management system for colleges, built with Django and MySQL. The system provides separate portals for Admin, Teacher, and Student users to manage attendance, academic data, reports, and notifications.
---

## ✨ Features

- 👤 Separate Admin, Teacher, and Student portals
- 🏫 Department, class, subject, teacher, and student management
- 📊 Attendance marking and subject-wise attendance tracking
- 📈 Attendance analytics and reports
- 📄 Attendance report generation
- 📥 Bulk student upload using Excel/CSV
- 📧 Email notifications for absent students
- 🗓️ Timetable and holiday management
- 🔐 Role-based authentication and password security
- 🔑 JWT-based authentication for Teacher and Student portals

## 🚀 Quick Setup

### 1. Clone / extract the project

```
smart_attendance/
  backend/         ← Django project (manage.py is here)
  templates/       ← All HTML templates
  static/          ← CSS / JS
  media/           ← Uploads (auto-created)
  .env.example     ← Copy to .env and fill in
```

### 2. Create virtual environment & install dependencies

```bash
cd smart_attendance
python -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 3. Configure environment

```bash
cp .env.example .env
# Edit .env with your DB credentials and Gmail app password
```

### 4. Create MySQL database

```sql
CREATE DATABASE smart_attendance_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
```

### 5. Run migrations

```bash
cd backend
python manage.py migrate
```

### 6. Create admin superuser

```bash
python manage.py createsuperuser
# Then set the role to ADMIN:
python manage.py shell
>>> from api.models import User
>>> u = User.objects.get(username='your_username')
>>> u.role = 'ADMIN'
>>> u.save()
>>> exit()
```

### 7. Run the server

```bash
python manage.py runserver
```

Visit: http://127.0.0.1:8000/

---

## 🧭 URL Map

| URL | Purpose |
|-----|---------|
| `/login/` | Admin login |
| `/teacher/login/` | Teacher login |
| `/teacher/register/` | Teacher first-time registration |
| `/student/login/` | Student login |
| `/student/register/` | Student first-time registration |
| `/admin-dashboard/` | Admin dashboard |
| `/admin/departments/` | Manage departments |
| `/admin/classes/` | Manage classes |
| `/admin/subjects/` | Manage subjects |
| `/admin/teachers/` | Manage teachers |
| `/admin/students/` | Manage students |
| `/admin/students/upload/` | Bulk upload students via Excel/CSV |
| `/teacher/timetable/` | Manage timetable |
| `/admin/holidays/` | Manage holidays |
| `/admin/reports/` | Attendance reports |
| `/admin/notifications/` | Notification logs |
| `/teacher/dashboard/` | Teacher dashboard |
| `/teacher/mark-attendance/` | Mark attendance |
| `/teacher/reports/` | Teacher reports |
| `/student/dashboard/` | Student attendance dashboard |

---

## 🔄 Complete Flow

### Adding a Teacher and letting them register:
1. Admin → `/admin/teachers/` → Add teacher (name + email, leave password blank)
2. Teacher → `/teacher/register/` → Enter email → Set password → Login

### Adding a Student and letting them register:
1. Admin → `/admin/students/` or `/admin/students/upload/` → Add student
2. Student → `/student/register/` → Enter register number → Set password → Login

### Marking Attendance:
1. Teacher logs in → `/teacher/mark-attendance/`
2. Select subject + date → Students load
3. Toggle Present/Absent for each → Submit
4. Parents of absent students receive email alerts automatically

---

## 📧 Email Setup (Gmail)

1. Enable 2-Step Verification on your Google account
2. Go to: https://myaccount.google.com/apppasswords
3. Create an App Password for "Mail"
4. Add to `.env`:
   ```
   EMAIL_HOST_USER=your.email@gmail.com
   EMAIL_HOST_PASSWORD=xxxx xxxx xxxx xxxx
   ```

---

## 🔐 Security Notes

- Passwords are always stored **hashed** using Django's `make_password()`
- Verification uses `check_password()` — never plain `==` comparison
- JWT tokens expire after 24 hours
- Admin pages require Django session auth (`@admin_required`)
- Teacher/student pages use localStorage JWT guard
- Password reset tokens are single-use and expire in 1 hour

---

## 🛠️ Tech Stack

| Category | Technologies |
|---|---|
| Backend | Python, Django 4.2, Django REST Framework |
| Database | MySQL, mysqlclient |
| Authentication | Django Sessions, JWT |
| Frontend | HTML, CSS, JavaScript, Chart.js |
| Email | Gmail SMTP |
| Excel / Reports | openpyxl, xlsxwriter |
