# Generated by Django 4.1.7 on 2024-07-28 19:21

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('buildings', '0002_evalunitlot_remove_evalunit_lot_geom_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='evalunit',
            name='lot_id',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='buildings.evalunitlot'),
        ),
    ]
