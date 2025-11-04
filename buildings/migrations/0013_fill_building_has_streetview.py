# Generated manually

from django.db import migrations


def fill_has_streetview(apps, schema_editor):
    """
    Fill in the has_streetview field for all existing buildings.
    Set it to True for all buildings that have been successfully geocoded.
    """
    Building = apps.get_model('buildings', 'Building')
    
    # Update all buildings with successful geocoding to have streetview
    Building.objects.filter(geocoding_error__isnull=True).update(has_streetview=True)


def reverse_fill_has_streetview(apps, schema_editor):
    """
    Reverse the migration by setting has_streetview back to null
    """
    Building = apps.get_model('buildings', 'Building')
    Building.objects.all().update(has_streetview=None)


class Migration(migrations.Migration):

    dependencies = [
        ('buildings', '0012_alter_building_unique_together'),
    ]

    operations = [
        migrations.RunPython(
            fill_has_streetview,
            reverse_fill_has_streetview
        ),
    ]