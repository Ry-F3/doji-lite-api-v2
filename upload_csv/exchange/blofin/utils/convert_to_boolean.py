from rest_framework import serializers
import requests


def convert_to_boolean(value):
    """Convert value to Boolean."""
    bool_map = {"Y": True, "N": False}
    return bool_map.get(value, None)