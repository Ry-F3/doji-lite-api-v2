from decimal import Decimal


class FormattingUtils:
    @staticmethod
    def get_decimal_places(price):
        """Determine the number of decimal places needed for the given price."""
        if price is None:
            return 2  # Default decimal places if price is None

        abs_price = abs(price)
        if abs_price < 0.01:
            return 4
        elif abs_price < 1:
            return 3
        elif abs_price < 10:
            return 2
        else:
            return 2

    @staticmethod
    def formatted_value(value, decimal_places=None, default='N/A'):
        """Format a value with conditional decimal places."""
        if value is not None:
            decimal_places = decimal_places or FormattingUtils.get_decimal_places(
                Decimal(value))
            return f"{Decimal(value):.{decimal_places}f}"
        return default

    @staticmethod
    def formatted_filled_quantity(filled_quantity, default='N/A'):
        """Format filled with conditional decimal places."""
        return FormattingUtils.formatted_value(filled_quantity, default=default)

    @staticmethod
    def formatted_original_filled_quantity(original_filled_quantity, default='N/A'):
        """Format filled with conditional decimal places."""
        return FormattingUtils.formatted_value(original_filled_quantity, default=default)

    @staticmethod
    def formatted_pnl(pnl, avg_fill, price, default='N/A'):
        """Format pnl based on conditions."""
        if avg_fill == price:
            return '--'

        if price == Decimal('0.0') and pnl == Decimal('0.0'):
            return '--'

        return FormattingUtils.formatted_value(pnl) if pnl is not None else default

    @staticmethod
    def formatted_percentage(percentage, avg_fill, price, default='N/A'):
        """Format percentage based on conditions."""
        if avg_fill == price:
            return '--'

        if  price == Decimal('0.0') and percentage == Decimal('0.0'):
            return '--'

        return f"{Decimal(percentage):.2f}%" if percentage is not None else default

    @staticmethod
    def formatted_price(price, avg_fill, is_open, default='N/A'):
        """Show price based on is_open status and automatic decimal places."""
        if avg_fill == price:
            return '--'

        if not is_open and price == Decimal('0.0'):
            return '--'

        return FormattingUtils.formatted_value(price) if price is not None else default

    @staticmethod
    def format_asset_name(asset_name):
        if asset_name:
            return asset_name.replace('_', ' ').upper()
        return 'N/A'