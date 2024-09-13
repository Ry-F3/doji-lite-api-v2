from upload_csv.exchange.blofin.utils.convert_to_decimal import convert_to_decimal
from upload_csv.exchange.blofin.utils.convert_to_native_datetime import convert_to_naive_datetime
from upload_csv.exchange.blofin.utils.convert_to_boolean import convert_to_boolean
# Modal imports
from upload_csv.models import TradeUploadBlofin
# Pachage and library imports
from decimal import Decimal, InvalidOperation
from datetime import datetime
from django.utils import timezone
from django.db.models import Sum, Q
import requests
import pytz


class CsvCopyProcessor:
    def __init__(self, handler: 'BloFinHandler'):
        self.handler = handler

    def process_csv_data(self, csv_data, user, exchange, file_name):
        """Process CSV data, only adding new trades."""
        new_trades = []
        duplicates = []
        duplicates_count = 0
        canceled_count = 0

        for row in csv_data:
            trade_status = row.get('Status', None)
            if trade_status == 'Canceled':
                canceled_count += 1
                continue

            trade = self.handler.process_row(row, user, exchange, file_name)
            if trade:
                if self.is_duplicate(trade):
                    duplicates_count += 1

                else:
                    new_trades.append(trade)

            else:

                duplicates.append(trade)

        # Bulk create new trades in the database
        TradeUploadBlofin.objects.bulk_create(new_trades)

        return len(new_trades), len(duplicates), canceled_count

    def is_duplicate(self, trade):
        """Check if a trade is a duplicate within tolerance."""
        TOLERANCE = Decimal('0.0001')

        duplicate_queryset = TradeUploadBlofin.objects.filter(
            order_time=trade.order_time,
            underlying_asset=trade.underlying_asset,
            fee=trade.fee
        ).filter(
            Q(avg_fill__lte=trade.avg_fill + TOLERANCE) &
            Q(avg_fill__gte=trade.avg_fill - TOLERANCE)
        )

        is_duplicate = duplicate_queryset.exists()

        if is_duplicate:
            print(f"Duplicate check: Trade on {trade.order_time} with asset {
                  trade.underlying_asset} is a duplicate.")
            # Log the duplicate trades for debugging

        else:
            print(f"Duplicate check: Trade on {trade.order_time} with asset {
                  trade.underlying_asset} is not a duplicate.")

        return is_duplicate


class BloFinHandler:
    def process_row(self, row, owner, exchange, file_name):
        duplicates = []
        try:
            # Extract fields from the row
            trade_status = row.get('Status', None)
            if trade_status == 'Canceled':
                return None

            order_time_str = row['Order Time']
            # Use the utility function to convert the order time string
            order_time_naive = convert_to_naive_datetime(order_time_str)
            if order_time_naive:
                order_time = timezone.make_aware(
                    order_time_naive, timezone.get_current_timezone())
            else:
                order_time = None

            underlying_asset = row['Underlying Asset']

            # # Define a set of assets to exclude
            # excluded_assets = {'BOMEUSDT',
            #                    'POPCATUSDT', 'GMEUSDT', 'BRETTUSDT'}

            # # Check if the underlying asset is in the excluded list
            # if underlying_asset in excluded_assets:
            #     return None

            # if underlying_asset not in ['ARBUSDT', 'BTCUSDT', 'ETHUSDT',
            #                             'RUNEUSDT', 'INJUSDT', 'VRAUSDT', 'LDOUSDT', 'WIFUSDT', 'SOLUSDT',
            #                             'BLURUSDT', 'MATICUSDT', 'SEIUSDT', 'NEARUSDT']:
            #     return None

            if underlying_asset not in ['ARBUSDT', 'BTCUSDT', 'ETHUSDT',
                                        'RUNEUSDT']:
                 return None

            avg_fill = convert_to_decimal(row['Avg Fill'])
            pnl = convert_to_decimal(row['PNL'])
            pnl_percentage = convert_to_decimal(row['PNL%'])
            fee = convert_to_decimal(row['Fee'])
            price = convert_to_decimal(row['Price'])
            filled_quantity = convert_to_decimal(row['Filled'])
            reduce_only = convert_to_boolean(row['Reduce-only'])

            is_matched = False
            is_open = False

            # Define the tolerance level
            TOLERANCE = Decimal('0.0001')

            # Create a query to find duplicates within the tolerance range
            duplicate_queryset = TradeUploadBlofin.objects.filter(
                order_time=order_time,
                underlying_asset=underlying_asset,
                fee=fee
            ).filter(
                Q(avg_fill__lte=avg_fill +
                  TOLERANCE) & Q(avg_fill__gte=avg_fill - TOLERANCE)
            )

            if duplicate_queryset.exists():
                duplicate_count = 0

                # Iterate over the duplicate queryset
                for idx, duplicate in enumerate(duplicate_queryset):
                    duplicate_count += 1

                    # Print the count of duplicates
                    print("Count of duplicates:", duplicate_count)

                    # If there are more than one duplicate
                    if duplicate_count > 1:
                        # Get all but the first duplicate
                        excess_duplicates = duplicate_queryset[1:]

                        #

                        # Delete the excess duplicates
                        excess_duplicates.delete()

                        # Since we only need to handle the first duplicate case,
                        # we can break the loop after processing excess duplicates
                        break

                return None

            trade_upload_csv = TradeUploadBlofin(
                owner=owner,
                file_name=file_name,
                underlying_asset=underlying_asset,
                margin_mode=row['Margin Mode'],
                leverage=row['Leverage'],
                order_time=order_time,
                side=row['Side'],
                avg_fill=avg_fill,
                price=price,
                filled_quantity=filled_quantity,
                original_filled_quantity=filled_quantity,
                pnl=pnl,
                pnl_percentage=pnl_percentage,
                fee=fee,
                reduce_only=reduce_only,
                trade_status=row.get('Status', None),
                exchange=exchange,
                is_open=is_open,
                is_matched=is_matched,
            )
            return trade_upload_csv

        except (InvalidOperation, ValueError) as e:

            return None
