# Generated by Django 4.1.7 on 2023-03-28 15:10

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("buildings", "0018_alter_buildingtypology_vote"),
    ]

    operations = [
        migrations.AddField(
            model_name="building",
            name="place_id",
            field=models.TextField(blank=True, null=True),
        ),
    ]
