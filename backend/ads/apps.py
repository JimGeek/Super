from django.apps import AppConfig


class AdsConfig(AppConfig):
    """Configuration for the ads app"""
    
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'ads'
    verbose_name = 'Advertisement Platform'
    
    def ready(self):
        """Initialize the app when Django starts"""
        import ads.signals  # Import signals to register them