from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from django.utils import timezone
from decimal import Decimal
import logging

from .models import SuperCashWallet, SuperCashTransaction, RewardCampaign, CustomerLoyalty
from .services import SuperCashService, LoyaltyService
from orders.models import Order
from accounts.models import Customer

logger = logging.getLogger(__name__)


@receiver(post_save, sender=Customer)
def create_supercash_wallet_on_customer_creation(sender, instance, created, **kwargs):
    """Create SuperCash wallet when customer is created"""
    
    if created:
        try:
            supercash_service = SuperCashService(instance.organization)
            wallet = supercash_service.get_or_create_wallet(instance)
            
            # Check for signup bonus campaign
            signup_campaigns = RewardCampaign.objects.filter(
                organization=instance.organization,
                campaign_type='signup',
                status='active',
                start_date__lte=timezone.now(),
                end_date__gte=timezone.now()
            )
            
            for campaign in signup_campaigns:
                if campaign.reward_type == 'flat_amount':
                    # Award signup bonus
                    SuperCashTransaction.objects.create(
                        wallet=wallet,
                        organization=instance.organization,
                        transaction_type='earn_bonus',
                        amount=campaign.reward_value,
                        description=f"Signup bonus: {campaign.name}",
                        expires_at=timezone.now() + timezone.timedelta(
                            days=supercash_service.settings.supercash_expiry_days
                        ),
                        balance_before=wallet.available_balance,
                        balance_after=wallet.available_balance + campaign.reward_value,
                        status='completed'
                    )
                    
                    # Update wallet balance
                    wallet.available_balance += campaign.reward_value
                    wallet.lifetime_earned += campaign.reward_value
                    wallet.save()
                    
                    # Update campaign usage
                    campaign.current_uses += 1
                    campaign.spent_amount += campaign.reward_value
                    campaign.save()
                    
                    logger.info(f"Awarded signup bonus of ₹{campaign.reward_value} to new customer {instance.full_name}")
                    break  # Only apply one signup campaign
            
        except Exception as e:
            logger.error(f"Error creating SuperCash wallet for customer {instance.id}: {str(e)}")


@receiver(post_save, sender=Order)
def process_order_rewards(sender, instance, created, **kwargs):
    """Process rewards when order status changes"""
    
    # Only process rewards for delivered orders
    if instance.status == 'delivered':
        try:
            supercash_service = SuperCashService(instance.organization)
            
            # Check if cashback already awarded
            existing_cashback = SuperCashTransaction.objects.filter(
                wallet__customer=instance.customer,
                order=instance,
                transaction_type='earn_purchase',
                status='completed'
            ).exists()
            
            if not existing_cashback:
                # Calculate and award cashback
                cashback_amount, campaign = supercash_service.calculate_order_cashback(instance)
                
                if cashback_amount > 0:
                    # Apply loyalty multiplier
                    multiplier = Decimal('1.00')
                    try:
                        loyalty = instance.customer.loyalty_status
                        if loyalty.current_tier:
                            multiplier = loyalty.current_tier.cashback_multiplier
                            cashback_amount *= multiplier
                    except CustomerLoyalty.DoesNotExist:
                        pass
                    
                    # Award the cashback
                    transaction = supercash_service.award_cashback(
                        order=instance,
                        amount=cashback_amount,
                        campaign=campaign
                    )
                    
                    logger.info(f"Awarded ₹{cashback_amount} cashback for order {instance.order_number}")
            
            # Process referral rewards for first order
            if instance.customer.orders.filter(
                organization=instance.organization,
                status='delivered'
            ).count() == 1:  # This is the first delivered order
                
                wallet = supercash_service.get_or_create_wallet(instance.customer)
                
                if wallet.referred_by:
                    try:
                        supercash_service.process_referral_reward(
                            referrer=wallet.referred_by,
                            referee=instance.customer,
                            referee_order=instance
                        )
                        logger.info(f"Processed referral rewards for customer {instance.customer.full_name}")
                    except Exception as e:
                        logger.error(f"Error processing referral reward: {str(e)}")
        
        except Exception as e:
            logger.error(f"Error processing order rewards for order {instance.id}: {str(e)}")


@receiver(post_save, sender=SuperCashTransaction)
def update_wallet_on_transaction(sender, instance, created, **kwargs):
    """Update wallet balances when transaction is created/updated"""
    
    if created and instance.status == 'completed':
        wallet = instance.wallet
        
        # Update balance tracking if not already set
        if instance.balance_before == Decimal('0.00') and instance.balance_after == Decimal('0.00'):
            instance.balance_before = wallet.available_balance
            
            if instance.transaction_type.startswith('earn_'):
                # Earning transaction
                wallet.available_balance += instance.amount
                wallet.lifetime_earned += instance.amount
            else:
                # Spending transaction
                wallet.available_balance -= abs(instance.amount)
                wallet.lifetime_spent += abs(instance.amount)
            
            instance.balance_after = wallet.available_balance
            wallet.save()
            instance.save(update_fields=['balance_before', 'balance_after'])


@receiver(post_save, sender=SuperCashTransaction)
def update_loyalty_metrics_on_transaction(sender, instance, created, **kwargs):
    """Update loyalty metrics when SuperCash is earned"""
    
    if (created and 
        instance.status == 'completed' and 
        instance.transaction_type.startswith('earn_') and 
        instance.order):
        
        try:
            loyalty_service = LoyaltyService(instance.organization)
            
            # Get or create loyalty record
            loyalty, loyalty_created = CustomerLoyalty.objects.get_or_create(
                customer=instance.wallet.customer,
                organization=instance.organization
            )
            
            # Update metrics based on the order
            order = instance.order
            loyalty.update_metrics(order.total_amount, instance.amount)
            
        except Exception as e:
            logger.error(f"Error updating loyalty metrics for transaction {instance.id}: {str(e)}")


@receiver(pre_save, sender=RewardCampaign)
def validate_campaign_before_save(sender, instance, **kwargs):
    """Validate campaign configuration before saving"""
    
    # Validate promo code uniqueness if required
    if instance.requires_code and instance.promo_code:
        existing_campaign = RewardCampaign.objects.filter(
            organization=instance.organization,
            promo_code=instance.promo_code,
            status__in=['active', 'draft']
        ).exclude(pk=instance.pk)
        
        if existing_campaign.exists():
            raise ValueError(f"Promo code '{instance.promo_code}' already exists for another campaign")
    
    # Validate tier configuration
    if instance.reward_type == 'tiered' and instance.tier_config:
        try:
            # Validate tier structure
            for tier in instance.tier_config:
                required_fields = ['min_amount', 'reward_value']
                if not all(field in tier for field in required_fields):
                    raise ValueError("Each tier must have min_amount and reward_value")
                
                if tier['min_amount'] < 0 or tier['reward_value'] < 0:
                    raise ValueError("Tier amounts must be positive")
        except (TypeError, KeyError) as e:
            raise ValueError(f"Invalid tier configuration: {str(e)}")


@receiver(post_save, sender=RewardCampaign)
def log_campaign_status_changes(sender, instance, created, **kwargs):
    """Log campaign status changes for audit"""
    
    if created:
        logger.info(f"New reward campaign created: {instance.name} ({instance.campaign_type})")
    else:
        # Check if status changed
        if hasattr(instance, '_original_status') and instance._original_status != instance.status:
            logger.info(f"Campaign {instance.name} status changed from {instance._original_status} to {instance.status}")


@receiver(pre_save, sender=RewardCampaign)
def track_campaign_status_changes(sender, instance, **kwargs):
    """Track original status for change detection"""
    
    if instance.pk:
        try:
            original = RewardCampaign.objects.get(pk=instance.pk)
            instance._original_status = original.status
        except RewardCampaign.DoesNotExist:
            pass


# Scheduled signal handlers (would be triggered by celery tasks)
@receiver(post_save, sender=SuperCashTransaction)
def schedule_expiry_notifications(sender, instance, created, **kwargs):
    """Schedule expiry notifications for new earn transactions"""
    
    if (created and 
        instance.transaction_type.startswith('earn_') and 
        instance.expires_at and
        instance.status == 'completed'):
        
        # Calculate notification date (30 days before expiry)
        notification_date = instance.expires_at - timezone.timedelta(days=30)
        
        if notification_date > timezone.now():
            # Here you would schedule a celery task for the notification
            # For now, just log it
            logger.info(f"Should schedule expiry notification for transaction {instance.id} on {notification_date}")


@receiver(post_save, sender=CustomerLoyalty)
def notify_tier_upgrade(sender, instance, created, **kwargs):
    """Send notification when customer's tier is upgraded"""
    
    if not created and hasattr(instance, '_previous_tier_level'):
        current_level = instance.current_tier.tier_level if instance.current_tier else 0
        
        if current_level > instance._previous_tier_level:
            # Tier upgraded
            logger.info(f"Customer {instance.customer.full_name} upgraded to {instance.current_tier.name}")
            
            # Here you would send push notification/email/SMS
            # For now, just log the upgrade
            
            # Award tier upgrade bonus if configured
            if instance.current_tier and hasattr(instance.current_tier, 'upgrade_bonus'):
                try:
                    supercash_service = SuperCashService(instance.organization)
                    wallet = supercash_service.get_or_create_wallet(instance.customer)
                    
                    # Award tier upgrade bonus (this would be configurable)
                    bonus_amount = Decimal('100.00')  # Example bonus
                    
                    SuperCashTransaction.objects.create(
                        wallet=wallet,
                        organization=instance.organization,
                        transaction_type='earn_bonus',
                        amount=bonus_amount,
                        description=f"Tier upgrade bonus: {instance.current_tier.name}",
                        expires_at=timezone.now() + timezone.timedelta(days=365),
                        balance_before=wallet.available_balance,
                        balance_after=wallet.available_balance + bonus_amount,
                        status='completed'
                    )
                    
                    wallet.available_balance += bonus_amount
                    wallet.lifetime_earned += bonus_amount
                    wallet.save()
                    
                except Exception as e:
                    logger.error(f"Error awarding tier upgrade bonus: {str(e)}")


@receiver(pre_save, sender=CustomerLoyalty)
def track_tier_changes(sender, instance, **kwargs):
    """Track tier changes for upgrade detection"""
    
    if instance.pk:
        try:
            original = CustomerLoyalty.objects.get(pk=instance.pk)
            instance._previous_tier_level = original.current_tier.tier_level if original.current_tier else 0
        except CustomerLoyalty.DoesNotExist:
            instance._previous_tier_level = 0


# Cleanup signals
@receiver(post_save, sender=SuperCashTransaction)
def cleanup_expired_transactions(sender, instance, created, **kwargs):
    """Mark expired transactions as expired status"""
    
    if (instance.expires_at and 
        instance.expires_at < timezone.now() and 
        instance.status == 'completed' and
        instance.transaction_type.startswith('earn_')):
        
        # This transaction has expired
        instance.status = 'expired'
        instance.save(update_fields=['status'])
        
        # Create expiry transaction to deduct from wallet
        SuperCashTransaction.objects.create(
            wallet=instance.wallet,
            organization=instance.organization,
            transaction_type='expire',
            amount=-instance.amount,
            description=f"Expired SuperCash from {instance.created_at.date()}",
            reference_id=str(instance.id),
            status='completed'
        )
        
        logger.info(f"Marked transaction {instance.id} as expired and created expiry transaction")