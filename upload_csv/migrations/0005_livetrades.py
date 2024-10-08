# Generated by Django 4.2.11 on 2024-10-04 11:30

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('upload_csv', '0004_filename'),
    ]

    operations = [
        migrations.CreateModel(
            name='LiveTrades',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('asset', models.CharField(max_length=10)),
                ('total_quantity', models.DecimalField(decimal_places=10, max_digits=20)),
                ('long_short', models.CharField(blank=True, max_length=4, null=True)),
                ('live_fill', models.DecimalField(blank=True, decimal_places=10, max_digits=20, null=True)),
                ('live_price', models.DecimalField(blank=True, decimal_places=10, max_digits=20, null=True)),
                ('live_pnl', models.DecimalField(blank=True, decimal_places=2, max_digits=20, null=True)),
                ('live_percentage', models.DecimalField(blank=True, decimal_places=2, max_digits=20, null=True)),
                ('last_updated', models.DateTimeField(auto_now=True)),
                ('trade_ids', models.TextField(default='[]')),
                ('is_live', models.BooleanField(default=False)),
                ('owner', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='live_trades', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'ordering': ['-last_updated'],
                'unique_together': {('owner', 'asset')},
            },
        ),
    ]
