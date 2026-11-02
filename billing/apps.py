from django.apps import AppConfig

class BillingConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'billing'

    def ready(self):
        from django.db.models.signals import post_save
        from users.models import Branch
        from .models import Subscription
        from django.utils import timezone
        from datetime import timedelta

        def create_trial(sender, instance, created, **kwargs):
            if created:
                Subscription.objects.get_or_create(
                    branch=instance,
                    defaults={
                        'is_trial': True,
                        'status': 'trial',
                        'trial_started_at': timezone.now(),
                        'trial_ends_at': timezone.now() + timedelta(days=30),
                        'expires_at': timezone.now() + timedelta(days=30),
                    }
                )

        post_save.connect(create_trial, sender=Branch)
        
        