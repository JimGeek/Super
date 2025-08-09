from django.apps import AppConfig


class RewardsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'rewards'
    verbose_name = 'SuperCash Rewards System'
    
    def ready(self):
        # Import signals
        try:
            import rewards.signals
        except ImportError:
            pass