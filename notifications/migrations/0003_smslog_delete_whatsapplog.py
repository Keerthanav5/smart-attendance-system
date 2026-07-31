from django.db import migrations, models


class Migration(migrations.Migration):
    """
    Drops the WhatsAppLog table and creates the SMSLog table.
    NotificationLog is untouched.
    """

    dependencies = [
        ("notifications", "0002_whatsapplog_delete_voicecalllog"),
    ]

    operations = [
        # Remove old WhatsApp log table
        migrations.DeleteModel(
            name="WhatsAppLog",
        ),

        # Create new SMS log table
        migrations.CreateModel(
            name="SMSLog",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "parent_phone",
                    models.CharField(blank=True, default="", max_length=20),
                ),
                (
                    "student_name",
                    models.CharField(blank=True, default="", max_length=150),
                ),
                (
                    "subject_names",
                    models.CharField(blank=True, default="", max_length=500),
                ),
                (
                    "semester_info",
                    models.CharField(blank=True, default="", max_length=100),
                ),
                ("message", models.TextField(blank=True, default="")),
                (
                    "status",
                    models.CharField(
                        choices=[("SUCCESS", "Success"), ("FAILED", "Failed")],
                        default="FAILED",
                        max_length=10,
                    ),
                ),
                ("error_message", models.TextField(blank=True, default="")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
            ],
            options={
                "db_table": "api_smslog",
                "ordering": ["-created_at"],
            },
        ),
    ]
