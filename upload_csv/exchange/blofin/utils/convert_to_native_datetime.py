from rest_framework import serializers
from decimal import Decimal
import requests
from django.conf import settings
import re
import logging
from datetime import datetime


def convert_to_naive_datetime(date_str, date_format='%m/%d/%Y %H:%M:%S'):
    """
    Convert a string to a naive datetime object.

    :param date_str: The string representation of the date.
    :param date_format: The format of the date string (default: '%m/%d/%Y %H:%M:%S').
    :return: A naive datetime object or None if conversion fails.
    """
    try:
        return datetime.strptime(date_str, date_format)
    except ValueError:
        # Log or handle the error if needed
        return None