from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.utils import timezone
from django.db.models import F
from decimal import Decimal

from .models import AdClick, AdConversion, AdImpression, AdBudgetSpend, AdCampaign, AdGroup, AdCreative


@receiver(post_save, sender=AdImpression)
def update_impression_metrics(sender, instance, created, **kwargs):
    """Update campaign, ad group, and creative metrics when impression is created"""
    if created:
        # Update creative metrics
        AdCreative.objects.filter(id=instance.creative.id).update(
            impressions=F('impressions') + 1
        )
        
        # Update ad group metrics
        AdGroup.objects.filter(id=instance.creative.ad_group.id).update(
            impressions=F('impressions') + 1
        )
        
        # Update campaign metrics
        AdCampaign.objects.filter(id=instance.creative.ad_group.campaign.id).update(
            impressions=F('impressions') + 1
        )
        
        # Update daily budget spend
        today = timezone.now().date()
        campaign = instance.creative.ad_group.campaign
        
        budget_spend, created_budget = AdBudgetSpend.objects.get_or_create(
            campaign=campaign,
            spend_date=today,
            defaults={
                'daily_budget': campaign.daily_budget,
                'impressions': 1,
                'total_spend': instance.cost
            }
        )
        
        if not created_budget:
            AdBudgetSpend.objects.filter(
                campaign=campaign,
                spend_date=today
            ).update(
                impressions=F('impressions') + 1,
                total_spend=F('total_spend') + instance.cost
            )


@receiver(post_save, sender=AdClick)
def update_click_metrics(sender, instance, created, **kwargs):
    """Update campaign, ad group, and creative metrics when click is created"""
    if created and instance.is_valid:
        # Update creative metrics
        AdCreative.objects.filter(id=instance.creative.id).update(
            clicks=F('clicks') + 1,
            spend=F('spend') + instance.cost
        )
        
        # Update ad group metrics
        AdGroup.objects.filter(id=instance.creative.ad_group.id).update(
            clicks=F('clicks') + 1,
            spend=F('spend') + instance.cost
        )
        
        # Update campaign metrics
        AdCampaign.objects.filter(id=instance.creative.ad_group.campaign.id).update(
            clicks=F('clicks') + 1,
            spend=F('spend') + instance.cost
        )
        
        # Update daily budget spend
        today = timezone.now().date()
        campaign = instance.creative.ad_group.campaign
        
        AdBudgetSpend.objects.filter(
            campaign=campaign,
            spend_date=today
        ).update(
            clicks=F('clicks') + 1,
            total_spend=F('total_spend') + instance.cost
        )
        
        # Check if daily budget is exceeded
        budget_spend = AdBudgetSpend.objects.get(
            campaign=campaign,
            spend_date=today
        )
        
        if budget_spend.total_spend >= budget_spend.daily_budget and not budget_spend.is_budget_exceeded:
            budget_spend.is_budget_exceeded = True
            budget_spend.budget_exhausted_at = timezone.now()
            budget_spend.save()
            
            # Optionally pause campaign if auto-pause is enabled
            if campaign.auto_pause_low_performance:
                campaign.status = 'paused'
                campaign.save()


@receiver(post_save, sender=AdConversion)
def update_conversion_metrics(sender, instance, created, **kwargs):
    """Update campaign, ad group, and creative metrics when conversion is created"""
    if created and instance.is_verified:
        # Update creative metrics
        AdCreative.objects.filter(id=instance.creative.id).update(
            conversions=F('conversions') + 1
        )
        
        # Update ad group metrics
        AdGroup.objects.filter(id=instance.creative.ad_group.id).update(
            conversions=F('conversions') + 1,
            revenue=F('revenue') + instance.conversion_value
        )
        
        # Update campaign metrics
        AdCampaign.objects.filter(id=instance.creative.ad_group.campaign.id).update(
            conversions=F('conversions') + 1,
            revenue=F('revenue') + instance.conversion_value
        )
        
        # Update daily budget spend
        today = timezone.now().date()
        campaign = instance.creative.ad_group.campaign
        
        AdBudgetSpend.objects.filter(
            campaign=campaign,
            spend_date=today
        ).update(
            conversions=F('conversions') + 1,
            revenue=F('revenue') + instance.conversion_value
        )


@receiver(post_save, sender=AdCampaign)
def handle_campaign_approval(sender, instance, created, **kwargs):
    """Handle campaign approval workflow"""
    if not created and instance.status == 'active':
        # Campaign was approved, activate all associated ad groups and creatives
        instance.ad_groups.filter(status='paused').update(status='active')
        
        for ad_group in instance.ad_groups.all():
            ad_group.creatives.filter(
                status='pending_review',
                compliance_status='approved'
            ).update(status='active')


@receiver(post_save, sender=AdCreative)
def handle_creative_compliance(sender, instance, created, **kwargs):
    """Handle creative compliance review"""
    if not created and instance.compliance_status == 'approved' and instance.status == 'pending_review':
        # Creative was approved, activate it if campaign and ad group are active
        if (instance.ad_group.status == 'active' and 
            instance.ad_group.campaign.status == 'active'):
            instance.status = 'active'
            instance.save()


@receiver(post_delete, sender=AdImpression)
def handle_impression_deletion(sender, instance, **kwargs):
    """Handle impression deletion by updating metrics"""
    # Update creative metrics
    AdCreative.objects.filter(id=instance.creative.id).update(
        impressions=F('impressions') - 1
    )
    
    # Update ad group metrics
    AdGroup.objects.filter(id=instance.creative.ad_group.id).update(
        impressions=F('impressions') - 1
    )
    
    # Update campaign metrics
    AdCampaign.objects.filter(id=instance.creative.ad_group.campaign.id).update(
        impressions=F('impressions') - 1
    )


@receiver(post_delete, sender=AdClick)
def handle_click_deletion(sender, instance, **kwargs):
    """Handle click deletion by updating metrics"""
    if instance.is_valid:
        # Update creative metrics
        AdCreative.objects.filter(id=instance.creative.id).update(
            clicks=F('clicks') - 1,
            spend=F('spend') - instance.cost
        )
        
        # Update ad group metrics
        AdGroup.objects.filter(id=instance.creative.ad_group.id).update(
            clicks=F('clicks') - 1,
            spend=F('spend') - instance.cost
        )
        
        # Update campaign metrics
        AdCampaign.objects.filter(id=instance.creative.ad_group.campaign.id).update(
            clicks=F('clicks') - 1,
            spend=F('spend') - instance.cost
        )


@receiver(post_delete, sender=AdConversion)
def handle_conversion_deletion(sender, instance, **kwargs):
    """Handle conversion deletion by updating metrics"""
    if instance.is_verified:
        # Update creative metrics
        AdCreative.objects.filter(id=instance.creative.id).update(
            conversions=F('conversions') - 1
        )
        
        # Update ad group metrics
        AdGroup.objects.filter(id=instance.creative.ad_group.id).update(
            conversions=F('conversions') - 1,
            revenue=F('revenue') - instance.conversion_value
        )
        
        # Update campaign metrics
        AdCampaign.objects.filter(id=instance.creative.ad_group.campaign.id).update(
            conversions=F('conversions') - 1,
            revenue=F('revenue') - instance.conversion_value
        )