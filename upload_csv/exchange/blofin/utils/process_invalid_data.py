from rest_framework import serializers
import requests
from django.conf import settings
import re
import logging


def process_invalid_data(reader, handler, user, exchange):
    new_trades_count = 0
    duplicates_count = 0
    canceled_count = 0

    for _, row in reader.iterrows():
        trade_status = row.get('Status', None)

        # Handle canceled trades
        if trade_status == 'Canceled':
            canceled_count += 1
            continue  # Skip the rest of the loop for canceled trades

        # Process the row for non-canceled trades
        trade_upload_csv = handler.process_row(row, user, exchange)

        # Debugging: Log the type and value of trade_upload_csv
        logger.debug(f"Type of trade_upload_csv: {type(trade_upload_csv)}")
        logger.debug(f"Value of trade_upload_csv: {trade_upload_csv}")

        # Check if the trade is not None (i.e., not a duplicate)
        if trade_upload_csv:
            if isinstance(trade_upload_csv, str):
                logger.error("Expected a model instance but got a string.")
            else:
                trade_upload_csv.save()
                new_trades_count += 1  # Increment the new trades count
        else:
            duplicates_count += 1  # Increment the duplicates count

    return new_trades_count, duplicates_count, canceled_count