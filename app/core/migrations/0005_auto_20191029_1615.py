# Generated by Django 2.1.13 on 2019-10-29 16:15

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0004_recipe'),
    ]

    operations = [
        migrations.RenameField(
            model_name='recipe',
            old_name='time_miniutes',
            new_name='time_minutes',
        ),
    ]
