# Generated by Django 4.1.7 on 2024-07-28 19:29

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('buildings', '0003_alter_evalunit_lot_id'),
    ]

    operations = [
        migrations.RenameField(
            model_name='evalunit',
            old_name='lot_id',
            new_name='lot',
        ),
    ]
