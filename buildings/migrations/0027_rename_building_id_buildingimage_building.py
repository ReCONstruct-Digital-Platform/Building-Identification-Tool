# Generated by Django 4.1.7 on 2023-06-18 19:50

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("buildings", "0026_buildingimage"),
    ]

    operations = [
        migrations.RenameField(
            model_name="buildingimage",
            old_name="building_id",
            new_name="building",
        ),
    ]