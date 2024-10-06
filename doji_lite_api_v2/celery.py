from __future__ import absolute_import, unicode_literals
import os
from celery import Celery

# set the default Django settings module for the 'celery' program.
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'doji_lite_api_v2.settings')

app = Celery('doji_lite_api_v2')

# Using a string here means the worker will not have to serialize
# the configuration object to child processes.
# - namespace='CELERY' means all celery-related config keys
#   should have a `CELERY_` prefix.
app.config_from_object('django.conf:settings', namespace='CELERY')
broker_connection_retry_on_startup = True 

# Load task modules from all registered Django app configs.
app.autodiscover_tasks()
