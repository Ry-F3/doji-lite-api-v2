from django.contrib.auth.models import User
from django.db import models
from decimal import Decimal

class TradeUploadBlofin(models.Model):
    EXCHANGE_CHOICES = [
        ('BloFin', 'BloFin'),
        ('OtherExchange', 'Other Exchange'),
        # Add other exchanges as needed
    ]
    owner = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name='blofin_futures_csv')
    file_name = models.CharField(max_length=250)
    underlying_asset = models.CharField(max_length=10)
    margin_mode = models.CharField(max_length=10)
    leverage = models.IntegerField()
    order_time = models.DateTimeField()
    side = models.CharField(max_length=4)
    avg_fill = models.DecimalField(
        max_digits=40, decimal_places=20)
    price = models.DecimalField(
        max_digits=20, decimal_places=10)
    filled_quantity = models.DecimalField(
        max_digits=20, decimal_places=10)
    original_filled_quantity = models.DecimalField(
        max_digits=20, decimal_places=10, null=True, blank=True)
    pnl = models.DecimalField(
        max_digits=20, decimal_places=2, null=True, blank=True)
    pnl_percentage = models.DecimalField(
        max_digits=20, decimal_places=2, null=True, blank=True)
    fee = models.DecimalField(
        max_digits=20, decimal_places=10)
    reduce_only = models.BooleanField()
    trade_status = models.CharField(max_length=10)
    exchange = models.CharField(
        max_length=100, choices=EXCHANGE_CHOICES, default='')
    is_open = models.BooleanField(default=None)
    is_matched = models.BooleanField(default=None)
    is_partially_matched = models.BooleanField(default=False)
    last_updated = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-order_time']
        unique_together = ('underlying_asset',
                           'avg_fill', 'fee')

    def __str__(self):
        return f"{self.underlying_asset} - {self.side}"
