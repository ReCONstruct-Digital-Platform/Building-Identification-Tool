# Generated by Django 4.1.7 on 2023-08-07 17:24

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="EvalUnit",
            fields=[
                ("id", models.TextField(primary_key=True, serialize=False)),
                ("lat", models.FloatField()),
                ("lng", models.FloatField()),
                ("muni", models.TextField()),
                ("muni_code", models.TextField(blank=True, null=True)),
                ("arrond", models.TextField(blank=True, null=True)),
                ("address", models.TextField()),
                ("num_adr_inf", models.TextField(blank=True, null=True)),
                ("num_adr_inf_2", models.TextField(blank=True, null=True)),
                ("num_adr_sup", models.TextField(blank=True, null=True)),
                ("num_adr_sup_2", models.TextField(blank=True, null=True)),
                ("way_type", models.TextField(blank=True, null=True)),
                ("way_link", models.TextField(blank=True, null=True)),
                ("street_name", models.TextField(blank=True, null=True)),
                ("cardinal_pt", models.TextField(blank=True, null=True)),
                ("apt_num", models.TextField(blank=True, null=True)),
                ("apt_num_1", models.TextField(blank=True, null=True)),
                ("apt_num_2", models.TextField(blank=True, null=True)),
                ("mat18", models.TextField()),
                ("cubf", models.IntegerField()),
                ("file_num", models.TextField(blank=True, null=True)),
                ("nghbr_unit", models.TextField(blank=True, null=True)),
                ("owner_date", models.DateTimeField(blank=True, null=True)),
                ("owner_type", models.TextField(blank=True, null=True)),
                ("owner_status", models.TextField(blank=True, null=True)),
                ("lot_lin_dim", models.FloatField(blank=True, null=True)),
                ("lot_area", models.FloatField(blank=True, null=True)),
                ("max_floors", models.IntegerField(blank=True, null=True)),
                ("const_yr", models.IntegerField(blank=True, null=True)),
                ("const_yr_real", models.TextField(blank=True, null=True)),
                ("floor_area", models.FloatField(blank=True, null=True)),
                ("phys_link", models.TextField(blank=True, null=True)),
                ("const_type", models.TextField(blank=True, null=True)),
                ("num_dwelling", models.IntegerField(blank=True, null=True)),
                ("num_rental", models.IntegerField(blank=True, null=True)),
                ("num_non_res", models.IntegerField(blank=True, null=True)),
                ("apprais_date", models.DateTimeField(blank=True, null=True)),
                ("lot_value", models.IntegerField(blank=True, null=True)),
                ("building_value", models.IntegerField(blank=True, null=True)),
                ("value", models.IntegerField(blank=True, null=True)),
                ("prev_value", models.IntegerField(blank=True, null=True)),
                ("associated", models.JSONField(blank=True, null=True)),
                (
                    "date_added",
                    models.DateTimeField(
                        default=django.utils.timezone.now, verbose_name="date added"
                    ),
                ),
            ],
        ),
        migrations.CreateModel(
            name="Vote",
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
                    models.DateTimeField(auto_now_add=True, verbose_name="date added"),
                ),
                (
                    "data_modified",
                    models.DateTimeField(auto_now=True, verbose_name="date modified"),
                ),
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
        migrations.CreateModel(
            name="SurveyV1",
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
                ("has_simple_footprint", models.BooleanField()),
                ("has_simple_volume", models.BooleanField()),
                ("num_storeys", models.IntegerField(blank=True, null=True)),
                ("has_basement", models.BooleanField(blank=True, null=True)),
                ("site_obstructions", models.JSONField()),
                ("appendages", models.JSONField()),
                ("exterior_cladding", models.JSONField()),
                ("facade_condition", models.TextField(blank=True, null=True)),
                ("window_wall_ratio", models.TextField(blank=True, null=True)),
                ("large_irregular_windows", models.BooleanField(blank=True, null=True)),
                ("roof_geometry", models.TextField()),
                ("structure_type", models.TextField()),
                ("new_or_renovated", models.BooleanField(blank=True, null=True)),
                (
                    "vote",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE, to="buildings.vote"
                    ),
                ),
            ],
            options={
                "abstract": False,
            },
        ),
        migrations.CreateModel(
            name="Profile",
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
                    "user",
                    models.OneToOneField(
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
        ),
        migrations.CreateModel(
            name="NoBuildingFlag",
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
                    "vote",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE, to="buildings.vote"
                    ),
                ),
            ],
        ),
        migrations.CreateModel(
            name="HLMBuilding",
            fields=[
                ("id", models.IntegerField(primary_key=True, serialize=False)),
                ("project_id", models.IntegerField()),
                ("organism", models.TextField()),
                ("service_center", models.TextField()),
                ("street_num", models.TextField()),
                ("street_name", models.TextField()),
                ("muni", models.TextField()),
                ("postal_code", models.TextField()),
                ("num_dwellings", models.IntegerField()),
                ("num_floors", models.IntegerField()),
                ("area_footprint", models.FloatField()),
                ("area_total", models.FloatField()),
                ("ivp", models.FloatField()),
                ("disrepair_state", models.TextField()),
                ("interest_adjust_date", models.DateTimeField(blank=True, null=True)),
                ("contract_end_date", models.DateTimeField(blank=True, null=True)),
                ("category", models.TextField()),
                ("building_id", models.IntegerField()),
                (
                    "eval_unit",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        to="buildings.evalunit",
                    ),
                ),
            ],
        ),
        migrations.CreateModel(
            name="EvalUnitStreetViewImage",
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
                ("uuid", models.TextField()),
                (
                    "date_added",
                    models.DateTimeField(
                        default=django.utils.timezone.now, verbose_name="date added"
                    ),
                ),
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
        migrations.CreateModel(
            name="EvalUnitSatelliteImage",
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
                ("uuid", models.TextField()),
                (
                    "date_added",
                    models.DateTimeField(
                        default=django.utils.timezone.now, verbose_name="date added"
                    ),
                ),
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
        migrations.CreateModel(
            name="EvalUnitLatestViewData",
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
                ("sv_pano", models.TextField(blank=True, null=True)),
                ("sv_heading", models.FloatField(blank=True, null=True)),
                ("sv_pitch", models.FloatField(blank=True, null=True)),
                ("sv_zoom", models.FloatField(blank=True, null=True)),
                ("marker_lat", models.FloatField(blank=True, null=True)),
                ("marker_lng", models.FloatField(blank=True, null=True)),
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
