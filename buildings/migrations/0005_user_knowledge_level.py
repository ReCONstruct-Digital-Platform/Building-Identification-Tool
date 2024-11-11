# Generated by Django 4.1.7 on 2024-10-26 18:51

from django.db import migrations, models

from buildings.models.models import User
from allauth.account.admin import EmailAddress


def forward_verify_emails_of_all_existing_users(apps, schema_editor):
    users = User.objects.all()
    for u in users:
        print(u.id, u.username, u.email)
        if u.email is not None and u.email != "":
            e = EmailAddress.objects.get_or_create(user=u, email=u.email)[0]
            e.verified = True
            try:
                e.save()
            except Exception as e:
                print(e)


def backward_verify_emails_of_all_existing_users(apps, schema_editor):
    users = User.objects.all()
    for u in users:
        if u.email is not None and u.email != "":
            e = EmailAddress.objects.get(user=u, email=u.email)
            if e:
                e.delete()


class Migration(migrations.Migration):

    dependencies = [
        ("buildings", "0004_rename_lot_id_evalunit_lot"),
        ("mailer", "0006_message_retry_count"),
    ]

    operations = [
        migrations.AddField(
            model_name="user",
            name="knowledge_level",
            field=models.TextField(blank=True, null=True),
        ),
        migrations.RunPython(
            forward_verify_emails_of_all_existing_users,
            backward_verify_emails_of_all_existing_users,
        ),
    ]