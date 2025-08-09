from decimal import Decimal
from django.db import transaction, models
from django.utils import timezone
from django.core.exceptions import ValidationError
from datetime import timedelta
from typing import Dict, List, Optional, Tuple
import logging

from .models import (
    SuperCashWallet, SuperCashTransaction, RewardCampaign, 
    CustomerRewardUsage, SuperCashRedemption, LoyaltyTier,
    CustomerLoyalty, SuperCashExpiry, RewardsSettings
)
from accounts.models import Customer, Organization
from orders.models import Order

logger = logging.getLogger(__name__)


class SuperCashService:
    """Service for managing SuperCash operations"""
    
    def __init__(self, organization: Organization):
        self.organization = organization
        self.settings = self._get_or_create_settings()
    
    def _get_or_create_settings(self) -> RewardsSettings:
        """Get or create rewards settings for organization"""
        settings, created = RewardsSettings.objects.get_or_create(
            organization=self.organization
        )
        return settings
    
    def get_or_create_wallet(self, customer: Customer) -> SuperCashWallet:
        """Get or create SuperCash wallet for customer"""
        wallet, created = SuperCashWallet.objects.get_or_create(
            customer=customer,
            organization=self.organization
        )
        return wallet
    
    def calculate_order_cashback(self, order: Order) -> Decimal:
        """Calculate cashback amount for an order"""
        if not self.settings.is_supercash_enabled:
            return Decimal('0.00')
        
        if order.total_amount < self.settings.min_order_for_cashback:
            return Decimal('0.00')
        
        # Get active campaigns that apply to this order
        applicable_campaigns = self._get_applicable_campaigns(order)
        
        best_reward = Decimal('0.00')
        best_campaign = None
        
        # Check campaign rewards
        for campaign in applicable_campaigns:
            if self._can_use_campaign(order.customer, campaign):
                reward = campaign.calculate_reward(order.total_amount, order.customer)
                if reward > best_reward:
                    best_reward = reward
                    best_campaign = campaign
        
        # Check default cashback
        default_cashback = (order.total_amount * self.settings.default_cashback_percentage) / 100
        if self.settings.max_cashback_per_order:
            default_cashback = min(default_cashback, self.settings.max_cashback_per_order)
        
        if default_cashback > best_reward:
            best_reward = default_cashback
            best_campaign = None
        
        return best_reward, best_campaign
    
    def _get_applicable_campaigns(self, order: Order) -> List[RewardCampaign]:
        """Get campaigns applicable to the order"""
        now = timezone.now()
        
        campaigns = RewardCampaign.objects.filter(
            organization=self.organization,
            status='active',
            start_date__lte=now,
            end_date__gte=now,
            campaign_type__in=['cashback', 'merchant_specific', 'seasonal']
        )
        
        # Filter by merchant if specified
        campaigns = campaigns.filter(
            models.Q(target_merchants__isnull=True) |
            models.Q(target_merchants=order.merchant)
        ).distinct()
        
        # Additional filtering can be added here (categories, customer segments, etc.)
        return list(campaigns)
    
    def _can_use_campaign(self, customer: Customer, campaign: RewardCampaign) -> bool:
        """Check if customer can use the campaign"""
        if not campaign.is_active:
            return False
        
        # Check usage limits
        if campaign.max_uses_per_customer:
            usage_count = CustomerRewardUsage.objects.filter(
                customer=customer,
                campaign=campaign
            ).count()
            
            if usage_count >= campaign.max_uses_per_customer:
                return False
        
        # Check target customer criteria
        if campaign.target_customers:
            # Implement customer targeting logic based on criteria
            pass
        
        return True
    
    @transaction.atomic
    def award_cashback(self, order: Order, amount: Decimal, 
                      campaign: RewardCampaign = None) -> SuperCashTransaction:
        """Award cashback for an order"""
        if amount <= 0:
            raise ValidationError("Cashback amount must be positive")
        
        wallet = self.get_or_create_wallet(order.customer)
        
        if wallet.is_frozen:
            raise ValidationError("Customer wallet is frozen")
        
        # Calculate expiry date
        expires_at = timezone.now() + timedelta(days=self.settings.supercash_expiry_days)
        
        # Create transaction
        transaction = SuperCashTransaction.objects.create(
            wallet=wallet,
            organization=self.organization,
            transaction_type='earn_purchase',
            amount=amount,
            order=order,
            description=f"Cashback for order {order.order_number}",
            expires_at=expires_at,
            balance_before=wallet.available_balance,
            status='completed'
        )
        
        # Update wallet balance
        wallet.available_balance += amount
        wallet.lifetime_earned += amount
        transaction.balance_after = wallet.available_balance
        
        wallet.save()
        transaction.save()
        
        # Record campaign usage if applicable
        if campaign:
            CustomerRewardUsage.objects.create(
                customer=order.customer,
                campaign=campaign,
                order=order,
                reward_amount=amount,
                order_amount=order.total_amount
            )
            
            # Update campaign statistics
            campaign.current_uses += 1
            campaign.spent_amount += amount
            campaign.save()
        
        # Update loyalty metrics
        self._update_loyalty_metrics(order.customer, order.total_amount, amount)
        
        logger.info(f"Awarded ₹{amount} cashback to {order.customer.full_name} for order {order.order_number}")
        return transaction
    
    @transaction.atomic
    def process_referral_reward(self, referrer: Customer, referee: Customer, 
                               referee_order: Order) -> Tuple[SuperCashTransaction, SuperCashTransaction]:
        """Process referral rewards for both referrer and referee"""
        if not self.settings.is_referral_enabled:
            raise ValidationError("Referral program is disabled")
        
        if referee_order.total_amount < self.settings.min_referee_order:
            raise ValidationError(f"Referee order amount must be at least ₹{self.settings.min_referee_order}")
        
        referrer_wallet = self.get_or_create_wallet(referrer)
        referee_wallet = self.get_or_create_wallet(referee)
        
        # Check referral limits
        if referrer_wallet.total_referrals >= self.settings.max_referrals_per_customer:
            raise ValidationError("Maximum referral limit reached")
        
        expires_at = timezone.now() + timedelta(days=self.settings.supercash_expiry_days)
        
        # Award referrer
        referrer_transaction = SuperCashTransaction.objects.create(
            wallet=referrer_wallet,
            organization=self.organization,
            transaction_type='earn_referral',
            amount=self.settings.referrer_reward,
            order=referee_order,
            description=f"Referral bonus for {referee.full_name}",
            expires_at=expires_at,
            balance_before=referrer_wallet.available_balance,
            status='completed'
        )
        
        referrer_wallet.available_balance += self.settings.referrer_reward
        referrer_wallet.lifetime_earned += self.settings.referrer_reward
        referrer_wallet.total_referrals += 1
        referrer_transaction.balance_after = referrer_wallet.available_balance
        referrer_wallet.save()
        referrer_transaction.save()
        
        # Award referee
        referee_transaction = SuperCashTransaction.objects.create(
            wallet=referee_wallet,
            organization=self.organization,
            transaction_type='earn_referral',
            amount=self.settings.referee_reward,
            order=referee_order,
            description=f"Welcome bonus for using referral code",
            expires_at=expires_at,
            balance_before=referee_wallet.available_balance,
            status='completed'
        )
        
        referee_wallet.available_balance += self.settings.referee_reward
        referee_wallet.lifetime_earned += self.settings.referee_reward
        referee_transaction.balance_after = referee_wallet.available_balance
        referee_wallet.save()
        referee_transaction.save()
        
        logger.info(f"Processed referral rewards: ₹{self.settings.referrer_reward} to {referrer.full_name}, ₹{self.settings.referee_reward} to {referee.full_name}")
        return referrer_transaction, referee_transaction
    
    @transaction.atomic
    def redeem_supercash(self, customer: Customer, amount: Decimal, 
                        order: Order = None, redemption_type: str = 'order_payment') -> SuperCashRedemption:
        """Redeem SuperCash for payment or transfer"""
        if amount <= 0:
            raise ValidationError("Redemption amount must be positive")
        
        if amount < self.settings.min_redemption_amount:
            raise ValidationError(f"Minimum redemption amount is ₹{self.settings.min_redemption_amount}")
        
        wallet = self.get_or_create_wallet(customer)
        
        if wallet.available_balance < amount:
            raise ValidationError("Insufficient SuperCash balance")
        
        if wallet.is_frozen:
            raise ValidationError("Wallet is frozen")
        
        # Check order-specific limits
        if order and amount > self.settings.max_redemption_per_order:
            raise ValidationError(f"Maximum redemption per order is ₹{self.settings.max_redemption_per_order}")
        
        # Calculate processing fee
        processing_fee = Decimal('0.00')
        if redemption_type == 'bank_transfer':
            processing_fee = (amount * self.settings.redemption_processing_fee_percentage) / 100
        
        net_amount = amount - processing_fee
        
        # Create redemption record
        redemption = SuperCashRedemption.objects.create(
            wallet=wallet,
            organization=self.organization,
            redemption_type=redemption_type,
            amount=amount,
            order=order,
            processing_fee=processing_fee,
            net_amount=net_amount,
            status='initiated'
        )
        
        # Create transaction record
        transaction = SuperCashTransaction.objects.create(
            wallet=wallet,
            organization=self.organization,
            transaction_type='spend_purchase' if redemption_type == 'order_payment' else 'spend_transfer',
            amount=-amount,  # Negative for spending
            order=order,
            description=f"SuperCash redeemed - {redemption_type}",
            balance_before=wallet.available_balance,
            status='completed'
        )
        
        # Update wallet balance
        wallet.available_balance -= amount
        wallet.lifetime_spent += amount
        transaction.balance_after = wallet.available_balance
        
        wallet.save()
        transaction.save()
        
        # Update redemption status
        redemption.status = 'completed'
        redemption.processed_at = timezone.now()
        redemption.save()
        
        logger.info(f"Redeemed ₹{amount} SuperCash from {customer.full_name}")
        return redemption
    
    def _update_loyalty_metrics(self, customer: Customer, order_amount: Decimal, supercash_earned: Decimal):
        """Update customer loyalty metrics"""
        if not self.settings.is_loyalty_enabled:
            return
        
        loyalty, created = CustomerLoyalty.objects.get_or_create(
            customer=customer,
            organization=self.organization
        )
        
        loyalty.update_metrics(order_amount, supercash_earned)
    
    def get_wallet_summary(self, customer: Customer) -> Dict:
        """Get comprehensive wallet summary for customer"""
        wallet = self.get_or_create_wallet(customer)
        
        # Get recent transactions
        recent_transactions = wallet.transactions.filter(
            status='completed'
        ).order_by('-created_at')[:10]
        
        # Get expiring balance
        expiring_soon = wallet.transactions.filter(
            transaction_type__startswith='earn_',
            status='completed',
            expires_at__isnull=False,
            expires_at__lte=timezone.now() + timedelta(days=30)
        ).aggregate(
            expiring_amount=models.Sum('amount')
        )['expiring_amount'] or Decimal('0.00')
        
        # Get loyalty status
        loyalty_status = None
        try:
            loyalty = customer.loyalty_status
            loyalty_status = {
                'current_tier': loyalty.current_tier.name if loyalty.current_tier else None,
                'tier_level': loyalty.current_tier.tier_level if loyalty.current_tier else 0,
                'next_tier': loyalty.calculate_next_tier(),
                'ytd_orders': loyalty.ytd_orders,
                'ytd_spend': loyalty.ytd_spend
            }
        except CustomerLoyalty.DoesNotExist:
            pass
        
        return {
            'wallet_id': wallet.id,
            'available_balance': wallet.available_balance,
            'pending_balance': wallet.pending_balance,
            'total_balance': wallet.total_balance,
            'lifetime_earned': wallet.lifetime_earned,
            'lifetime_spent': wallet.lifetime_spent,
            'expiring_soon': expiring_soon,
            'referral_code': wallet.referral_code,
            'total_referrals': wallet.total_referrals,
            'loyalty_status': loyalty_status,
            'recent_transactions': [
                {
                    'id': txn.id,
                    'type': txn.transaction_type,
                    'amount': txn.amount,
                    'description': txn.description,
                    'created_at': txn.created_at,
                    'expires_at': txn.expires_at
                }
                for txn in recent_transactions
            ]
        }


class RewardCampaignService:
    """Service for managing reward campaigns"""
    
    def __init__(self, organization: Organization):
        self.organization = organization
    
    @transaction.atomic
    def create_campaign(self, campaign_data: Dict) -> RewardCampaign:
        """Create a new reward campaign"""
        campaign = RewardCampaign.objects.create(
            organization=self.organization,
            **campaign_data
        )
        
        logger.info(f"Created reward campaign: {campaign.name}")
        return campaign
    
    def get_active_campaigns(self, campaign_type: str = None) -> List[RewardCampaign]:
        """Get active campaigns"""
        queryset = RewardCampaign.objects.filter(
            organization=self.organization,
            status='active'
        )
        
        if campaign_type:
            queryset = queryset.filter(campaign_type=campaign_type)
        
        return list(queryset.order_by('-created_at'))
    
    def simulate_campaign_impact(self, campaign: RewardCampaign, 
                                days_to_simulate: int = 30) -> Dict:
        """Simulate the potential impact of a campaign"""
        # This would use historical data to estimate campaign performance
        # For now, returning a basic simulation structure
        
        estimated_participants = 100  # Based on target criteria
        avg_order_value = Decimal('500.00')  # Historical average
        estimated_orders = estimated_participants * 2  # Assumption
        
        total_reward_cost = Decimal('0.00')
        for _ in range(estimated_orders):
            reward = campaign.calculate_reward(avg_order_value)
            total_reward_cost += reward
        
        return {
            'estimated_participants': estimated_participants,
            'estimated_orders': estimated_orders,
            'estimated_revenue': estimated_orders * avg_order_value,
            'estimated_reward_cost': total_reward_cost,
            'estimated_roi': ((estimated_orders * avg_order_value) / total_reward_cost) * 100 if total_reward_cost > 0 else 0,
            'budget_utilization': (total_reward_cost / campaign.total_budget * 100) if campaign.total_budget else 0
        }


class LoyaltyService:
    """Service for managing loyalty program"""
    
    def __init__(self, organization: Organization):
        self.organization = organization
    
    def setup_default_tiers(self) -> List[LoyaltyTier]:
        """Set up default loyalty tiers for organization"""
        default_tiers = [
            {
                'name': 'Bronze',
                'tier_level': 1,
                'min_orders': 0,
                'min_spend': Decimal('0.00'),
                'cashback_multiplier': Decimal('1.00'),
                'badge_color': '#CD7F32'
            },
            {
                'name': 'Silver',
                'tier_level': 2,
                'min_orders': 10,
                'min_spend': Decimal('5000.00'),
                'cashback_multiplier': Decimal('1.25'),
                'free_delivery': True,
                'badge_color': '#C0C0C0'
            },
            {
                'name': 'Gold',
                'tier_level': 3,
                'min_orders': 25,
                'min_spend': Decimal('15000.00'),
                'cashback_multiplier': Decimal('1.50'),
                'free_delivery': True,
                'priority_support': True,
                'badge_color': '#FFD700'
            },
            {
                'name': 'Platinum',
                'tier_level': 4,
                'min_orders': 50,
                'min_spend': Decimal('50000.00'),
                'cashback_multiplier': Decimal('2.00'),
                'free_delivery': True,
                'priority_support': True,
                'exclusive_offers': True,
                'badge_color': '#E5E4E2'
            }
        ]
        
        created_tiers = []
        for tier_data in default_tiers:
            tier, created = LoyaltyTier.objects.get_or_create(
                organization=self.organization,
                tier_level=tier_data['tier_level'],
                defaults=tier_data
            )
            created_tiers.append(tier)
        
        return created_tiers
    
    def evaluate_all_customers(self):
        """Evaluate all customers for tier upgrades/downgrades"""
        from accounts.models import Customer
        
        customers = Customer.objects.filter(
            organization=self.organization
        )
        
        updated_count = 0
        
        for customer in customers:
            loyalty, created = CustomerLoyalty.objects.get_or_create(
                customer=customer,
                organization=self.organization
            )
            
            # Calculate metrics from orders
            orders = customer.orders.filter(
                organization=self.organization,
                status='delivered'
            )
            
            # Update YTD metrics (this year)
            current_year = timezone.now().year
            ytd_orders = orders.filter(created_at__year=current_year)
            
            ytd_metrics = ytd_orders.aggregate(
                count=models.Count('id'),
                total=models.Sum('total_amount')
            )
            
            loyalty.ytd_orders = ytd_metrics['count'] or 0
            loyalty.ytd_spend = ytd_metrics['total'] or Decimal('0.00')
            
            # Calculate YTD SuperCash earned
            ytd_supercash = SuperCashTransaction.objects.filter(
                wallet__customer=customer,
                organization=self.organization,
                transaction_type__startswith='earn_',
                created_at__year=current_year
            ).aggregate(
                total=models.Sum('amount')
            )['total'] or Decimal('0.00')
            
            loyalty.ytd_supercash_earned = ytd_supercash
            
            # Check for tier upgrade
            current_tier_level = loyalty.current_tier.tier_level if loyalty.current_tier else 0
            
            best_tier = LoyaltyTier.objects.filter(
                organization=self.organization,
                is_active=True,
                min_orders__lte=loyalty.ytd_orders,
                min_spend__lte=loyalty.ytd_spend,
                min_supercash_earned__lte=loyalty.ytd_supercash_earned
            ).order_by('-tier_level').first()
            
            if best_tier and (not loyalty.current_tier or best_tier.tier_level > current_tier_level):
                loyalty.previous_tier = loyalty.current_tier
                loyalty.current_tier = best_tier
                loyalty.tier_achieved_at = timezone.now()
                updated_count += 1
            
            loyalty.save()
        
        logger.info(f"Updated loyalty tiers for {updated_count} customers")
        return updated_count


class SuperCashExpiryService:
    """Service for handling SuperCash expiry"""
    
    def __init__(self, organization: Organization):
        self.organization = organization
    
    def process_expiring_supercash(self, expiry_date=None):
        """Process SuperCash expiring on a specific date"""
        if not expiry_date:
            expiry_date = timezone.now().date()
        
        # Find expiring transactions
        expiring_transactions = SuperCashTransaction.objects.filter(
            organization=self.organization,
            expires_at__date=expiry_date,
            status='completed',
            transaction_type__startswith='earn_'
        ).select_related('wallet')
        
        total_expired = Decimal('0.00')
        customers_affected = 0
        processed_wallets = set()
        
        with transaction.atomic():
            for txn in expiring_transactions:
                if txn.wallet.id not in processed_wallets:
                    processed_wallets.add(txn.wallet.id)
                    customers_affected += 1
                
                # Create expiry transaction
                SuperCashTransaction.objects.create(
                    wallet=txn.wallet,
                    organization=self.organization,
                    transaction_type='expire',
                    amount=-txn.amount,
                    description=f"Expired SuperCash from {txn.created_at.date()}",
                    balance_before=txn.wallet.available_balance,
                    balance_after=txn.wallet.available_balance - txn.amount,
                    status='completed'
                )
                
                # Update wallet balance
                txn.wallet.available_balance -= txn.amount
                txn.wallet.save()
                
                # Mark original transaction as expired
                txn.status = 'expired'
                txn.save()
                
                total_expired += txn.amount
        
        # Create expiry record
        expiry_record = SuperCashExpiry.objects.create(
            organization=self.organization,
            expiry_date=expiry_date,
            total_amount=total_expired,
            expired_amount=total_expired,
            customers_affected=customers_affected,
            is_processed=True,
            processed_at=timezone.now()
        )
        
        logger.info(f"Processed SuperCash expiry for {expiry_date}: ₹{total_expired} from {customers_affected} customers")
        return expiry_record
    
    def send_expiry_notifications(self, days_before_expiry: int = 7):
        """Send notifications for SuperCash expiring soon"""
        expiry_date = timezone.now().date() + timedelta(days=days_before_expiry)
        
        # Find customers with expiring SuperCash
        expiring_transactions = SuperCashTransaction.objects.filter(
            organization=self.organization,
            expires_at__date=expiry_date,
            status='completed',
            transaction_type__startswith='earn_'
        ).values('wallet__customer').annotate(
            expiring_amount=models.Sum('amount')
        )
        
        notifications_sent = 0
        
        for item in expiring_transactions:
            customer_id = item['wallet__customer']
            expiring_amount = item['expiring_amount']
            
            # Here you would integrate with notification service
            # For now, just log the notification
            logger.info(f"Should notify customer {customer_id} about ₹{expiring_amount} expiring on {expiry_date}")
            notifications_sent += 1
        
        return notifications_sent