# Generated by Django 5.1.5 on 2025-01-25 12:28

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0006_alter_caregiverrelationship_options_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='customuser',
            name='user_type',
            field=models.CharField(choices=[('PATIENT', 'Patient'), ('CAREGIVER', 'Caregiver')], default='PATIENT', max_length=20),
        ),
    ]
