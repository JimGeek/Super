from django.apps import AppConfig


class PaymentsUpiConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'payments_upi'
    verbose_name = 'UPI Payments'