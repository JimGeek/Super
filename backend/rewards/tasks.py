from celery import shared_task
from django.utils import timezone
from django.db.models import Q, Sum, Count
from django.db import transaction
from datetime import timedelta, date
from decimal import Decimal
import logging

from .models import (
    SuperCashWallet, SuperCashTransaction, RewardCampaign,
    SuperCashRedemption, SuperCashExpiry, CustomerLoyalty
)
from .services import SuperCashService, SuperCashExpiryService, LoyaltyService
from accounts.models import Organization, Customer
from orders.models import Order

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3)
def process_order_cashback(self, order_id):
    """Process cashback for a delivered order"""
    
    try:
        order = Order.objects.get(id=order_id)
        
        if order.status != 'delivered':
            logger.info(f"Order {order_id} is not delivered, skipping cashback processing")
            return f"Order {order_id} not eligible for cashback"
        
        # Check if cashback already processed
        existing_cashback = SuperCashTransaction.objects.filter(
            wallet__customer=order.customer,
            order=order,
            transaction_type='earn_purchase',
            status='completed'
        ).exists()
        
        if existing_cashback:
            logger.info(f"Cashback already processed for order {order_id}")
            return f"Cashback already processed for order {order_id}"
        
        supercash_service = SuperCashService(order.organization)
        cashback_amount, campaign = supercash_service.calculate_order_cashback(order)
        
        if cashback_amount > 0:
            # Apply loyalty multiplier
            multiplier = Decimal('1.00')
            try:
                loyalty = order.customer.loyalty_status
                if loyalty.current_tier:
                    multiplier = loyalty.current_tier.cashback_multiplier
                    cashback_amount *= multiplier
            except CustomerLoyalty.DoesNotExist:
                pass
            
            # Award cashback
            transaction_obj = supercash_service.award_cashback(
                order=order,
                amount=cashback_amount,
                campaign=campaign
            )
            
            logger.info(f"Processed cashback of ₹{cashback_amount} for order {order_id}")
            return f"Awarded ₹{cashback_amount} cashback for order {order_id}"
        else:
            logger.info(f"No cashback applicable for order {order_id}")
            return f"No cashback for order {order_id}"
            
    except Order.DoesNotExist:
        logger.error(f"Order {order_id} not found")
        raise self.retry(countdown=300)
    
    except Exception as exc:
        logger.error(f"Error processing cashback for order {order_id}: {str(exc)}")
        raise self.retry(exc=exc, countdown=300)


@shared_task(bind=True, max_retries=3)
def process_referral_rewards(self, referrer_id, referee_id, referee_order_id):
    """Process referral rewards for referrer and referee"""
    
    try:
        referrer = Customer.objects.get(id=referrer_id)
        referee = Customer.objects.get(id=referee_id)
        referee_order = Order.objects.get(id=referee_order_id)
        
        supercash_service = SuperCashService(referrer.organization)
        
        # Check if this is referee's first delivered order
        is_first_order = referee.orders.filter(
            organization=referrer.organization,
            status='delivered'
        ).count() == 1
        
        if not is_first_order:
            logger.info(f"Referral rewards already processed for referee {referee_id}")
            return "Referral rewards already processed"
        
        # Process referral rewards
        referrer_txn, referee_txn = supercash_service.process_referral_reward(
            referrer=referrer,
            referee=referee,
            referee_order=referee_order
        )
        
        logger.info(f"Processed referral rewards: ₹{referrer_txn.amount} to referrer, ₹{referee_txn.amount} to referee")
        return f"Referral rewards processed successfully"
        
    except (Customer.DoesNotExist, Order.DoesNotExist) as e:
        logger.error(f"Entity not found in referral processing: {str(e)}")
        raise self.retry(countdown=300)
    
    except Exception as exc:
        logger.error(f"Error processing referral rewards: {str(exc)}")
        raise self.retry(exc=exc, countdown=300)


@shared_task
def expire_supercash_batch():
    """Process SuperCash expiry for current date"""
    
    today = timezone.now().date()
    organizations = Organization.objects.all()
    
    total_expired = Decimal('0.00')
    total_customers_affected = 0
    
    for organization in organizations:
        try:
            expiry_service = SuperCashExpiryService(organization)
            expiry_record = expiry_service.process_expiring_supercash(today)
            
            if expiry_record:
                total_expired += expiry_record.expired_amount
                total_customers_affected += expiry_record.customers_affected
                
                logger.info(f"Processed SuperCash expiry for {organization.name}: ₹{expiry_record.expired_amount} from {expiry_record.customers_affected} customers")
        
        except Exception as e:
            logger.error(f"Error processing SuperCash expiry for organization {organization.id}: {str(e)}")
            continue
    
    logger.info(f"Total SuperCash expired today: ₹{total_expired} affecting {total_customers_affected} customers")
    return f"Expired ₹{total_expired} from {total_customers_affected} customers"


@shared_task
def send_expiry_notifications():
    """Send SuperCash expiry notifications"""
    
    organizations = Organization.objects.all()
    total_notifications = 0
    
    for organization in organizations:
        try:
            expiry_service = SuperCashExpiryService(organization)
            
            # Send notifications for SuperCash expiring in 7 days
            notifications_sent = expiry_service.send_expiry_notifications(days_before_expiry=7)
            total_notifications += notifications_sent
            
            # Also send notifications for SuperCash expiring in 1 day
            urgent_notifications = expiry_service.send_expiry_notifications(days_before_expiry=1)
            total_notifications += urgent_notifications
            
            if notifications_sent > 0 or urgent_notifications > 0:
                logger.info(f"Sent {notifications_sent + urgent_notifications} expiry notifications for {organization.name}")
        
        except Exception as e:
            logger.error(f"Error sending expiry notifications for organization {organization.id}: {str(e)}")
            continue
    
    logger.info(f"Sent {total_notifications} total expiry notifications")
    return f"Sent {total_notifications} expiry notifications"


@shared_task
def evaluate_loyalty_tiers():
    """Evaluate all customers for loyalty tier updates"""
    
    organizations = Organization.objects.all()
    total_updated = 0
    
    for organization in organizations:
        try:
            loyalty_service = LoyaltyService(organization)
            updated_count = loyalty_service.evaluate_all_customers()
            total_updated += updated_count
            
            if updated_count > 0:
                logger.info(f"Updated loyalty tiers for {updated_count} customers in {organization.name}")
        
        except Exception as e:
            logger.error(f"Error evaluating loyalty tiers for organization {organization.id}: {str(e)}")
            continue
    
    logger.info(f"Total loyalty tier updates: {total_updated}")
    return f"Updated {total_updated} customer loyalty tiers"


@shared_task
def cleanup_pending_redemptions():
    """Clean up old pending redemptions"""
    
    # Cancel redemptions that have been pending for more than 24 hours
    cutoff_time = timezone.now() - timedelta(hours=24)
    
    pending_redemptions = SuperCashRedemption.objects.filter(
        status='initiated',
        initiated_at__lt=cutoff_time
    )
    
    cancelled_count = 0
    
    with transaction.atomic():
        for redemption in pending_redemptions:
            # Refund the amount back to wallet
            wallet = redemption.wallet
            wallet.available_balance += redemption.amount
            wallet.save()
            
            # Create refund transaction
            SuperCashTransaction.objects.create(
                wallet=wallet,
                organization=redemption.organization,
                transaction_type='refund',
                amount=redemption.amount,
                description=f"Refund for cancelled redemption {redemption.id}",
                reference_id=str(redemption.id),
                balance_before=wallet.available_balance - redemption.amount,
                balance_after=wallet.available_balance,
                status='completed'
            )
            
            # Cancel redemption
            redemption.status = 'cancelled'
            redemption.save()
            
            cancelled_count += 1
    
    logger.info(f"Cancelled {cancelled_count} pending redemptions")
    return f"Cancelled {cancelled_count} pending redemptions"


@shared_task
def generate_rewards_analytics():
    """Generate and cache rewards analytics"""
    
    organizations = Organization.objects.all()
    
    for organization in organizations:
        try:
            # Generate analytics for the past 30 days
            end_date = timezone.now().date()
            start_date = end_date - timedelta(days=30)
            
            # SuperCash metrics
            supercash_metrics = SuperCashTransaction.objects.filter(
                organization=organization,
                created_at__date__range=[start_date, end_date],
                status='completed'
            ).aggregate(
                total_earned=Sum('amount', filter=Q(transaction_type__startswith='earn_')),
                total_spent=Sum('amount', filter=Q(transaction_type__startswith='spend_')),
                total_expired=Sum('amount', filter=Q(transaction_type='expire')),
                transaction_count=Count('id')
            )
            
            # Active wallets
            active_wallets = SuperCashWallet.objects.filter(
                organization=organization,
                is_active=True,
                available_balance__gt=0
            ).count()
            
            # Campaign performance
            campaign_performance = RewardCampaign.objects.filter(
                organization=organization,
                status='active'
            ).aggregate(
                active_campaigns=Count('id'),
                total_budget=Sum('total_budget'),
                total_spent=Sum('spent_amount')
            )
            
            # Store analytics in cache or database
            # For now, just log the metrics
            logger.info(f"Analytics for {organization.name}: "
                       f"Earned: ₹{supercash_metrics['total_earned'] or 0}, "
                       f"Spent: ₹{abs(supercash_metrics['total_spent']) if supercash_metrics['total_spent'] else 0}, "
                       f"Active Wallets: {active_wallets}, "
                       f"Transactions: {supercash_metrics['transaction_count']}")
        
        except Exception as e:
            logger.error(f"Error generating analytics for organization {organization.id}: {str(e)}")
            continue
    
    return "Analytics generation completed"


@shared_task
def process_campaign_auto_deactivation():
    """Auto-deactivate expired campaigns"""
    
    now = timezone.now()
    
    # Find campaigns that should be deactivated
    expired_campaigns = RewardCampaign.objects.filter(
        status='active',
        end_date__lt=now
    )
    
    updated_count = 0
    
    for campaign in expired_campaigns:
        campaign.status = 'expired'
        campaign.save()
        updated_count += 1
        logger.info(f"Auto-deactivated expired campaign: {campaign.name}")
    
    # Also deactivate campaigns that have reached their usage limits
    limit_reached_campaigns = RewardCampaign.objects.filter(
        status='active',
        max_total_uses__isnull=False
    ).filter(
        current_uses__gte=models.F('max_total_uses')
    )
    
    for campaign in limit_reached_campaigns:
        campaign.status = 'completed'
        campaign.save()
        updated_count += 1
        logger.info(f"Auto-completed campaign that reached usage limit: {campaign.name}")
    
    # Deactivate campaigns that have exhausted their budget
    budget_exhausted_campaigns = RewardCampaign.objects.filter(
        status='active',
        total_budget__isnull=False
    ).filter(
        spent_amount__gte=models.F('total_budget')
    )
    
    for campaign in budget_exhausted_campaigns:
        campaign.status = 'completed'
        campaign.save()
        updated_count += 1
        logger.info(f"Auto-completed campaign that exhausted budget: {campaign.name}")
    
    return f"Auto-deactivated {updated_count} campaigns"


@shared_task
def send_loyalty_tier_notifications():
    """Send notifications for loyalty tier achievements and benefits"""
    
    # Find customers who achieved new tiers in the last 24 hours
    yesterday = timezone.now() - timedelta(days=1)
    
    recent_tier_upgrades = CustomerLoyalty.objects.filter(
        tier_achieved_at__gte=yesterday,
        current_tier__isnull=False
    ).select_related('customer', 'current_tier')
    
    notifications_sent = 0
    
    for loyalty in recent_tier_upgrades:
        # Here you would send push notification/email/SMS about tier upgrade
        logger.info(f"Should notify customer {loyalty.customer.full_name} about tier upgrade to {loyalty.current_tier.name}")
        notifications_sent += 1
        
        # Send information about tier benefits
        tier = loyalty.current_tier
        benefits = []
        
        if tier.free_delivery:
            benefits.append("Free delivery on all orders")
        if tier.priority_support:
            benefits.append("Priority customer support")
        if tier.exclusive_offers:
            benefits.append("Exclusive offers and deals")
        if tier.cashback_multiplier > 1:
            benefits.append(f"{tier.cashback_multiplier}x SuperCash on purchases")
        
        logger.info(f"Tier benefits for {loyalty.customer.full_name}: {', '.join(benefits)}")
    
    return f"Sent {notifications_sent} tier achievement notifications"


@shared_task
def reconcile_wallet_balances():
    """Reconcile wallet balances with transaction history"""
    
    wallets_checked = 0
    discrepancies_found = 0
    
    # Check all active wallets
    for wallet in SuperCashWallet.objects.filter(is_active=True):
        try:
            # Calculate balance from transactions
            transactions_balance = SuperCashTransaction.objects.filter(
                wallet=wallet,
                status='completed'
            ).aggregate(
                total_earned=Sum('amount', filter=Q(transaction_type__startswith='earn_')),
                total_spent=Sum('amount', filter=Q(transaction_type__startswith='spend_')),
                total_expired=Sum('amount', filter=Q(transaction_type='expire'))
            )
            
            calculated_balance = Decimal('0.00')
            if transactions_balance['total_earned']:
                calculated_balance += transactions_balance['total_earned']
            if transactions_balance['total_spent']:
                calculated_balance -= abs(transactions_balance['total_spent'])
            if transactions_balance['total_expired']:
                calculated_balance -= abs(transactions_balance['total_expired'])
            
            wallets_checked += 1
            
            # Check for discrepancy
            if abs(calculated_balance - wallet.available_balance) > Decimal('0.01'):
                discrepancies_found += 1
                
                logger.warning(f"Balance discrepancy for wallet {wallet.id}: "
                             f"Recorded: ₹{wallet.available_balance}, "
                             f"Calculated: ₹{calculated_balance}")
                
                # Create adjustment transaction
                adjustment_amount = calculated_balance - wallet.available_balance
                
                SuperCashTransaction.objects.create(
                    wallet=wallet,
                    organization=wallet.organization,
                    transaction_type='admin_adjust',
                    amount=adjustment_amount,
                    description=f"Balance reconciliation adjustment",
                    balance_before=wallet.available_balance,
                    balance_after=calculated_balance,
                    status='completed'
                )
                
                # Update wallet balance
                wallet.available_balance = calculated_balance
                wallet.save()
                
                logger.info(f"Adjusted wallet {wallet.id} balance by ₹{adjustment_amount}")
        
        except Exception as e:
            logger.error(f"Error reconciling wallet {wallet.id}: {str(e)}")
            continue
    
    logger.info(f"Reconciliation completed: {wallets_checked} wallets checked, {discrepancies_found} discrepancies found")
    return f"Checked {wallets_checked} wallets, found {discrepancies_found} discrepancies"


@shared_task
def generate_monthly_rewards_report():
    """Generate monthly rewards report"""
    
    # Generate report for previous month
    today = timezone.now().date()
    first_day_current_month = today.replace(day=1)
    last_day_previous_month = first_day_current_month - timedelta(days=1)
    first_day_previous_month = last_day_previous_month.replace(day=1)
    
    organizations = Organization.objects.all()
    
    for organization in organizations:
        try:
            # SuperCash metrics for the month
            monthly_transactions = SuperCashTransaction.objects.filter(
                organization=organization,
                created_at__date__range=[first_day_previous_month, last_day_previous_month],
                status='completed'
            )
            
            metrics = monthly_transactions.aggregate(
                total_earned=Sum('amount', filter=Q(transaction_type__startswith='earn_')),
                total_spent=Sum('amount', filter=Q(transaction_type__startswith='spend_')),
                total_expired=Sum('amount', filter=Q(transaction_type='expire')),
                unique_customers=Count('wallet__customer', distinct=True),
                transaction_count=Count('id')
            )
            
            # Campaign performance
            campaigns_active = RewardCampaign.objects.filter(
                organization=organization,
                start_date__lte=last_day_previous_month,
                end_date__gte=first_day_previous_month
            ).count()
            
            # Loyalty tier distribution
            tier_distribution = CustomerLoyalty.objects.filter(
                organization=organization
            ).values('current_tier__name').annotate(
                count=Count('id')
            )
            
            # Generate report (would normally be saved to file or sent via email)
            report_data = {
                'organization': organization.name,
                'period': f"{first_day_previous_month} to {last_day_previous_month}",
                'supercash_earned': metrics['total_earned'] or Decimal('0.00'),
                'supercash_spent': abs(metrics['total_spent']) if metrics['total_spent'] else Decimal('0.00'),
                'supercash_expired': abs(metrics['total_expired']) if metrics['total_expired'] else Decimal('0.00'),
                'unique_customers': metrics['unique_customers'] or 0,
                'total_transactions': metrics['transaction_count'] or 0,
                'active_campaigns': campaigns_active,
                'tier_distribution': list(tier_distribution)
            }
            
            logger.info(f"Monthly report generated for {organization.name}: {report_data}")
            
        except Exception as e:
            logger.error(f"Error generating monthly report for organization {organization.id}: {str(e)}")
            continue
    
    return f"Generated monthly reports for {organizations.count()} organizations"


# Periodic task scheduling function
@shared_task
def schedule_rewards_tasks():
    """Schedule all periodic rewards tasks"""
    
    current_time = timezone.now()
    current_hour = current_time.hour
    current_minute = current_time.minute
    
    # Daily tasks at 2 AM
    if current_hour == 2 and current_minute == 0:
        expire_supercash_batch.delay()
        cleanup_pending_redemptions.delay()
        process_campaign_auto_deactivation.delay()
        reconcile_wallet_balances.delay()
    
    # Notification tasks every 6 hours
    if current_minute == 0 and current_hour % 6 == 0:
        send_expiry_notifications.delay()
        send_loyalty_tier_notifications.delay()
    
    # Weekly loyalty evaluation (Sundays at 3 AM)
    if current_time.weekday() == 6 and current_hour == 3 and current_minute == 0:
        evaluate_loyalty_tiers.delay()
    
    # Monthly reports (1st day of month at 4 AM)
    if current_time.day == 1 and current_hour == 4 and current_minute == 0:
        generate_monthly_rewards_report.delay()
    
    # Analytics generation every 4 hours
    if current_minute == 0 and current_hour % 4 == 0:
        generate_rewards_analytics.delay()
    
    return "Scheduled periodic rewards tasks"