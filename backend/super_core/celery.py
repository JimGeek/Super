"""
Celery configuration for SUPER platform
"""
import os
from celery import Celery
from django.conf import settings

# Set the default Django settings module for the 'celery' program.
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'super_core.settings')

app = Celery('super_core')

# Using a string here means the worker doesn't have to serialize
# the configuration object to child processes.
app.config_from_object('django.conf:settings', namespace='CELERY')

# Load task modules from all registered Django apps.
app.autodiscover_tasks()

# Celery Beat Configuration
app.conf.beat_schedule = {
    # Run settlements every hour
    'process-settlements': {
        'task': 'settlements.tasks.process_pending_settlements',
        'schedule': 60.0 * 60,  # Every hour
    },
    
    # Check payment status every 5 minutes
    'check-payment-status': {
        'task': 'payments_upi.tasks.check_pending_payments',
        'schedule': 60.0 * 5,  # Every 5 minutes
    },
    
    # Process expired rewards daily
    'expire-rewards': {
        'task': 'rewards.tasks.expire_old_rewards',
        'schedule': 60.0 * 60 * 24,  # Daily
    },
    
    # Send reminder notifications
    'send-reminders': {
        'task': 'notifications.tasks.send_scheduled_notifications',
        'schedule': 60.0 * 15,  # Every 15 minutes
    },
    
    # Update analytics daily
    'update-analytics': {
        'task': 'analytics.tasks.update_daily_metrics',
        'schedule': 60.0 * 60 * 24,  # Daily
    },
    
    # Clean up old logs weekly
    'cleanup-logs': {
        'task': 'super_core.tasks.cleanup_old_logs',
        'schedule': 60.0 * 60 * 24 * 7,  # Weekly
    },
}

app.conf.timezone = settings.TIME_ZONE

@app.task(bind=True)
def debug_task(self):
    print(f'Request: {self.request!r}')