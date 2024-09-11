from rest_framework import serializers
from decimal import Decimal
import requests
from django.conf import settings
import re
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


def convert_to_decimal(value):
    """Convert value to Decimal, handle special cases."""
    # Handle specific cases first

    if value is None:
        return Decimal('0.0')  # Handle NoneType by returning a default value

    if value == "Market":
        return Decimal('0.0')  # Use a dummy value or handle as needed

    if value == '--':
        return Decimal('0.0')  # Set dummy value for '--'

    if isinstance(value, str):
        # Handle potential negative sign and numeric characters
        value = value.strip()
        if value.startswith('-'):
            sign = -1
            value = value[1:]  # Remove the negative sign for processing
        else:
            sign = 1

        # Remove any non-numeric characters (except decimal point)
        numeric_value = re.sub(r'[^\d\.\-]', '', value)

        try:
            decimal_value = Decimal(numeric_value)
            return decimal_value * sign
        except (ValueError, InvalidOperation):
            # Handle conversion errors by returning a default value
            return Decimal('0.0')

    # Convert directly if already numeric (make sure it is a valid Decimal format)
    try:
        return Decimal(value)
    except (ValueError, InvalidOperation):
        return Decimal('0.0')