from rest_framework import serializers
from .models import TradeUploadBlofin
from collections import defaultdict
from decimal import Decimal
from django.contrib.auth.models import User
from upload_csv.utils.convert_fields_to_readable import FormattingUtils


class FileUploadSerializer(serializers.Serializer):
    file = serializers.FileField()
    exchange = serializers.ChoiceField(
        choices=[('BloFin', 'BloFin'), ('OtherExchange', 'Other Exchange')])


class SaveTradeSerializer(serializers.ModelSerializer):
    avg_fill_formatted = serializers.SerializerMethodField()
    filled_quantity_formatted = serializers.SerializerMethodField()
    original_filled_quantity_formatted = serializers.SerializerMethodField()
    pnl_formatted = serializers.SerializerMethodField()
    pnl_percentage_formatted = serializers.SerializerMethodField()
    price_formatted = serializers.SerializerMethodField()

    class Meta:
        model = TradeUploadBlofin
        fields = ['id', 'owner', 'underlying_asset', 'margin_mode',
                  'leverage', 'order_time', 'side', 'avg_fill_formatted', 'price_formatted',
                  'filled_quantity_formatted', 'original_filled_quantity_formatted', 'pnl_formatted',
                  'pnl_percentage_formatted', 'fee', 'exchange',
                  'trade_status', 'is_open', 'is_matched', 'last_updated']

    def get_avg_fill_formatted(self, obj):
        return FormattingUtils.formatted_value(obj.avg_fill)

    def get_original_filled_quantity_formatted(self, obj):
        return FormattingUtils.formatted_original_filled_quantity(obj.original_filled_quantity)

    def get_filled_quantity_formatted(self, obj):
        return FormattingUtils.formatted_filled_quantity(obj.filled_quantity)

    def get_pnl_formatted(self, obj):
        return FormattingUtils.formatted_pnl(obj.pnl, obj.avg_fill, obj.price, obj.is_open)

    def get_pnl_percentage_formatted(self, obj):
        return FormattingUtils.formatted_percentage(obj.pnl_percentage, obj.avg_fill, obj.price, obj.is_open)

    def get_price_formatted(self, obj):
        return FormattingUtils.formatted_price(obj.price, obj.avg_fill, obj.is_open)
