# Generated by Django 4.1.7 on 2023-08-29 18:42

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("buildings", "0004_rename_data_modified_vote_date_modified"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="surveyv1",
            name="structure_type",
        ),
        migrations.AddField(
            model_name="surveyv1",
            name="self_similar_cluster",
            field=models.BooleanField(null=True),
        ),
        migrations.AlterField(
            model_name="surveyv1",
            name="facade_condition",
            field=models.BooleanField(blank=True, null=True),
        ),
        migrations.AlterField(
            model_name="surveyv1",
            name="window_wall_ratio",
            field=models.BooleanField(blank=True, null=True),
        ),
    ]
