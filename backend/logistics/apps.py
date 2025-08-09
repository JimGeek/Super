from django.apps import AppConfig


class LogisticsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'logistics'
    verbose_name = 'Logistics & Dispatch'
    
    def ready(self):
        # Import signals
        try:
            import logistics.signals
        except ImportError:
            pass