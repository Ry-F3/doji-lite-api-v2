# Generated by Django 4.2.11 on 2024-10-07 22:11

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('upload_csv', '0005_livetrades'),
    ]

    operations = [
        migrations.AddField(
            model_name='filename',
            name='cancel_processing',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='filename',
            name='processing',
            field=models.BooleanField(default=False),
        ),
    ]
