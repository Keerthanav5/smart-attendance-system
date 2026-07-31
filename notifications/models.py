from django.db import models


class NotificationLog(models.Model):
    objects = models.Manager()
    student = models.ForeignKey('students.Student', on_delete=models.CASCADE, null=True, blank=True)
    parent_email = models.EmailField(null=True, blank=True)
    subject = models.ForeignKey('subjects.Subject', on_delete=models.SET_NULL, null=True, blank=True)
    date = models.DateField()
    status = models.CharField(max_length=10, default='SENT')
    error_message = models.TextField(blank=True)
    sent_at = models.DateTimeField(auto_now_add=True)
    class_id = models.IntegerField(null=True, blank=True)

    def __str__(self):
        if self.class_id:
            return f"Class {self.class_id} - {self.date}"
        return f"{self.student.student_id} - {self.status} - {self.sent_at}"

    class Meta:
        db_table = 'api_notificationlog'


class SMSLog(models.Model):
    """SMS log table (deprecated in v2.0 — kept for historical audit records)."""
    objects = models.Manager()
    parent_phone = models.CharField(max_length=20, blank=True, default='')
    student_name = models.CharField(max_length=150, blank=True, default='')
    subject_names = models.CharField(max_length=500, blank=True, default='')
    semester_info = models.CharField(max_length=100, blank=True, default='')
    message = models.TextField(blank=True, default='')
    status = models.CharField(max_length=10, choices=[
        ('SUCCESS', 'Success'),
        ('FAILED', 'Failed'),
    ], default='FAILED')
    error_message = models.TextField(blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.parent_phone} — {self.status} — {self.created_at}"

    class Meta:
        db_table = 'api_smslog'
        ordering = ['-created_at']
