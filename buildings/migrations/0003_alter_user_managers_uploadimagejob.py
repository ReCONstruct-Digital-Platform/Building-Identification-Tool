# Generated by Django 4.1.7 on 2023-08-24 17:10

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
        (
            "buildings",
            "0002_remove_evalunit_cardinal_pt_remove_evalunit_way_link_and_more",
        ),
    ]

    operations = [
        migrations.AlterModelManagers(
            name="user",
            managers=[],
        ),
        migrations.CreateModel(
            name="UploadImageJob",
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
                    "date_added",
                    models.DateTimeField(
                        default=django.utils.timezone.now, verbose_name="date added"
                    ),
                ),
                (
                    "status",
                    models.TextField(
                        choices=[
                            ("pending", "Pending"),
                            ("in_progress", "In Progress"),
                            ("done", "Done"),
                            ("error", "Error"),
                        ],
                        default="pending",
                    ),
                ),
                ("job_data", models.JSONField()),
                (
                    "eval_unit",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        to="buildings.evalunit",
                    ),
                ),
                (
                    "user",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
        ),
    ]