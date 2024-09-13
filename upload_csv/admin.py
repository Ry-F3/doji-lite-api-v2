from django.contrib import admin
from .models import TradeUploadBlofin
from upload_csv.utils.convert_fields_to_readable import FormattingUtils


@admin.register(TradeUploadBlofin)
class TradeUploadBlofinAdmin(admin.ModelAdmin):
    list_display = ('id', 'owner', 'underlying_asset_formatted', 'margin_mode', 'leverage',
                    'order_time', 'side', 'avg_fill_formatted', 'price_formatted', 'filled_quantity_formatted',
                    'pnl_formatted', 'pnl_percentage_formatted', 'fee', 'trade_status',
                    'exchange', 'is_open', 'is_matched', 'is_partially_matched', 'last_updated')
    list_filter = ('owner', 'underlying_asset', 'side', 'exchange',
                   'is_open', 'is_matched', 'is_partially_matched')
    search_fields = ('owner__username', 'underlying_asset', 'side')
    date_hierarchy = 'order_time'
    ordering = ('-order_time',)

    def underlying_asset_formatted(self, obj):
        return FormattingUtils.format_asset_name(obj.underlying_asset)
    underlying_asset_formatted.short_description = 'Asset'

    def avg_fill_formatted(self, obj):
        return FormattingUtils.formatted_value(obj.avg_fill)
    avg_fill_formatted.short_description = 'Avg Fill'

    def filled_quantity_formatted(self, obj):
        return FormattingUtils.formatted_value(obj.filled_quantity)
    filled_quantity_formatted.short_description = 'Quantity'

    def pnl_formatted(self, obj):
        return FormattingUtils.formatted_pnl(obj.pnl, obj.avg_fill, obj.price, obj.is_open)
    pnl_formatted.short_description = 'PnL'

    def pnl_percentage_formatted(self, obj):
        return FormattingUtils.formatted_percentage(obj.pnl_percentage, obj.avg_fill, obj.price, obj.is_open)
    pnl_percentage_formatted.short_description = 'PnL Percentage'

    def price_formatted(self, obj):
        return FormattingUtils.formatted_price(obj.price, obj.avg_fill, obj.is_open)
    price_formatted.short_description = 'Price'


