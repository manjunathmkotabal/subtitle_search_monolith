from __future__ import absolute_import,unicode_literals
import os
from celery import Celery
from django.conf import settings
import redis
# Set the default Django settings module for the 'celery' program.
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'videouploader.settings')

app = Celery('videouploader')
# app.conf.enable_utc = False
# # Load task modules from all registered Django app configs.

# app.conf.update(timezone = 'Asia/Kotkata')

app.config_from_object(settings, namespace = 'CELERY')

app.autodiscover_tasks()

@app.task(bind=True)
def debug_task(self): 
    print(f'Request: {self.request!r}')