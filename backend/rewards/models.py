from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone
from decimal import Decimal
import uuid
import json

from accounts.models import Organization, Customer, Merchant
from orders.models import Order


class SuperCashWallet(models.Model):
    """Customer's SuperCash wallet"""
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    customer = models.OneToOneField(Customer, on_delete=models.CASCADE, related_name='supercash_wallet')
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name='supercash_wallets')
    
    # Wallet balances
    available_balance = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    pending_balance = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    lifetime_earned = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    lifetime_spent = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    
    # Wallet status
    is_active = models.BooleanField(default=True)
    is_frozen = models.BooleanField(default=False)
    freeze_reason = models.TextField(blank=True)
    
    # Referral tracking
    referral_code = models.CharField(max_length=20, unique=True, blank=True)
    referred_by = models.ForeignKey(Customer, on_delete=models.SET_NULL, null=True, blank=True, related_name='referrals')
    total_referrals = models.IntegerField(default=0)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'rewards_supercash_wallets'
        indexes = [
            models.Index(fields=['organization', 'customer']),
            models.Index(fields=['referral_code']),
        ]
    
    def __str__(self):
        return f"SuperCash Wallet - {self.customer.full_name} (₹{self.available_balance})"
    
    @property
    def total_balance(self):
        return self.available_balance + self.pending_balance
    
    def save(self, *args, **kwargs):
        if not self.referral_code:
            self.referral_code = self._generate_referral_code()
        super().save(*args, **kwargs)
    
    def _generate_referral_code(self):
        """Generate unique referral code"""
        import random
        import string
        
        prefix = self.customer.full_name[:3].upper()
        suffix = ''.join(random.choices(string.digits, k=4))
        return f"{prefix}{suffix}"


class SuperCashTransaction(models.Model):
    """SuperCash transaction records"""
    
    TRANSACTION_TYPES = [
        ('earn_purchase', 'Earned from Purchase'),
        ('earn_referral', 'Earned from Referral'),
        ('earn_bonus', 'Bonus Earned'),
        ('earn_cashback', 'Cashback Earned'),
        ('earn_promo', 'Promotional Credit'),
        ('spend_purchase', 'Spent on Purchase'),
        ('spend_transfer', 'Transfer Out'),
        ('refund', 'Refund'),
        ('penalty', 'Penalty'),
        ('expire', 'Expired'),
        ('admin_adjust', 'Admin Adjustment'),
    ]
    
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
        ('cancelled', 'Cancelled'),
        ('expired', 'Expired'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    wallet = models.ForeignKey(SuperCashWallet, on_delete=models.CASCADE, related_name='transactions')
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE)
    
    # Transaction details
    transaction_type = models.CharField(max_length=20, choices=TRANSACTION_TYPES)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    
    # Reference information
    order = models.ForeignKey(Order, on_delete=models.SET_NULL, null=True, blank=True, related_name='supercash_transactions')
    reference_id = models.CharField(max_length=100, blank=True, help_text="External reference ID")
    description = models.TextField(blank=True)
    
    # Metadata
    metadata = models.JSONField(default=dict, help_text="Additional transaction data")
    
    # Expiry for earned credits
    expires_at = models.DateTimeField(null=True, blank=True)
    
    # Balance tracking
    balance_before = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    balance_after = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    
    # Timestamps
    processed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'rewards_supercash_transactions'
        indexes = [
            models.Index(fields=['wallet', 'status']),
            models.Index(fields=['organization', 'transaction_type']),
            models.Index(fields=['order']),
            models.Index(fields=['expires_at']),
        ]
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.transaction_type} - ₹{self.amount} - {self.wallet.customer.full_name}"


class RewardCampaign(models.Model):
    """Reward campaigns for earning SuperCash"""
    
    CAMPAIGN_TYPES = [
        ('cashback', 'Cashback'),
        ('referral', 'Referral Bonus'),
        ('signup', 'Signup Bonus'),
        ('milestone', 'Milestone Reward'),
        ('seasonal', 'Seasonal Campaign'),
        ('merchant_specific', 'Merchant Specific'),
    ]
    
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('active', 'Active'),
        ('paused', 'Paused'),
        ('expired', 'Expired'),
        ('completed', 'Completed'),
    ]
    
    REWARD_TYPES = [
        ('percentage', 'Percentage of Order'),
        ('flat_amount', 'Flat Amount'),
        ('tiered', 'Tiered Rewards'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name='reward_campaigns')
    
    # Campaign details
    name = models.CharField(max_length=200)
    description = models.TextField()
    campaign_type = models.CharField(max_length=20, choices=CAMPAIGN_TYPES)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    
    # Reward configuration
    reward_type = models.CharField(max_length=20, choices=REWARD_TYPES, default='percentage')
    reward_value = models.DecimalField(max_digits=8, decimal_places=2, help_text="Percentage or flat amount")
    max_reward_amount = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    min_order_amount = models.DecimalField(max_digits=8, decimal_places=2, default=Decimal('0.00'))
    
    # Tiered rewards (JSON structure)
    tier_config = models.JSONField(default=list, help_text="Tiered reward configuration")
    
    # Campaign validity
    start_date = models.DateTimeField()
    end_date = models.DateTimeField()
    
    # Usage limits
    max_uses_per_customer = models.IntegerField(null=True, blank=True)
    max_total_uses = models.IntegerField(null=True, blank=True)
    current_uses = models.IntegerField(default=0)
    
    # Target criteria
    target_customers = models.JSONField(default=dict, help_text="Customer targeting criteria")
    target_merchants = models.ManyToManyField(Merchant, blank=True)
    target_categories = models.JSONField(default=list, help_text="Product category filters")
    
    # Promotion settings
    is_auto_apply = models.BooleanField(default=True)
    requires_code = models.BooleanField(default=False)
    promo_code = models.CharField(max_length=50, blank=True)
    
    # Budget and spending
    total_budget = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    spent_amount = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    
    # Timestamps
    created_by = models.CharField(max_length=100)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'rewards_campaigns'
        indexes = [
            models.Index(fields=['organization', 'status']),
            models.Index(fields=['start_date', 'end_date']),
            models.Index(fields=['campaign_type']),
        ]
    
    def __str__(self):
        return f"{self.name} - {self.organization.name}"
    
    @property
    def is_active(self):
        now = timezone.now()
        return (
            self.status == 'active' and
            self.start_date <= now <= self.end_date and
            (self.max_total_uses is None or self.current_uses < self.max_total_uses) and
            (self.total_budget is None or self.spent_amount < self.total_budget)
        )
    
    def calculate_reward(self, order_amount, customer=None):
        """Calculate reward amount for given order"""
        if not self.is_active or order_amount < self.min_order_amount:
            return Decimal('0.00')
        
        if self.reward_type == 'percentage':
            reward = (order_amount * self.reward_value) / 100
        elif self.reward_type == 'flat_amount':
            reward = self.reward_value
        elif self.reward_type == 'tiered':
            reward = self._calculate_tiered_reward(order_amount)
        else:
            reward = Decimal('0.00')
        
        # Apply maximum reward limit
        if self.max_reward_amount and reward > self.max_reward_amount:
            reward = self.max_reward_amount
        
        return reward
    
    def _calculate_tiered_reward(self, order_amount):
        """Calculate tiered reward based on order amount"""
        if not self.tier_config:
            return Decimal('0.00')
        
        for tier in sorted(self.tier_config, key=lambda x: x.get('min_amount', 0), reverse=True):
            min_amount = Decimal(str(tier.get('min_amount', 0)))
            if order_amount >= min_amount:
                if tier.get('reward_type') == 'percentage':
                    return (order_amount * Decimal(str(tier.get('reward_value', 0)))) / 100
                else:
                    return Decimal(str(tier.get('reward_value', 0)))
        
        return Decimal('0.00')


class CustomerRewardUsage(models.Model):
    """Track customer usage of reward campaigns"""
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE)
    campaign = models.ForeignKey(RewardCampaign, on_delete=models.CASCADE)
    order = models.ForeignKey(Order, on_delete=models.CASCADE)
    
    # Usage details
    reward_amount = models.DecimalField(max_digits=8, decimal_places=2)
    order_amount = models.DecimalField(max_digits=8, decimal_places=2)
    
    # Timestamps
    used_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'rewards_customer_usage'
        indexes = [
            models.Index(fields=['customer', 'campaign']),
            models.Index(fields=['campaign', 'used_at']),
        ]
        unique_together = ['customer', 'campaign', 'order']


class SuperCashRedemption(models.Model):
    """SuperCash redemption records"""
    
    REDEMPTION_TYPES = [
        ('order_payment', 'Order Payment'),
        ('bank_transfer', 'Bank Transfer'),
        ('gift_card', 'Gift Card'),
        ('partner_store', 'Partner Store'),
    ]
    
    STATUS_CHOICES = [
        ('initiated', 'Initiated'),
        ('processing', 'Processing'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
        ('cancelled', 'Cancelled'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    wallet = models.ForeignKey(SuperCashWallet, on_delete=models.CASCADE, related_name='redemptions')
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE)
    
    # Redemption details
    redemption_type = models.CharField(max_length=20, choices=REDEMPTION_TYPES)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='initiated')
    
    # Reference information
    order = models.ForeignKey(Order, on_delete=models.SET_NULL, null=True, blank=True)
    external_reference = models.CharField(max_length=100, blank=True)
    
    # Bank transfer details (if applicable)
    bank_details = models.JSONField(default=dict, help_text="Bank account details for transfer")
    
    # Processing information
    processed_by = models.CharField(max_length=100, blank=True)
    processing_fee = models.DecimalField(max_digits=6, decimal_places=2, default=Decimal('0.00'))
    net_amount = models.DecimalField(max_digits=10, decimal_places=2, help_text="Amount after fees")
    
    # Timestamps
    initiated_at = models.DateTimeField(auto_now_add=True)
    processed_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        db_table = 'rewards_supercash_redemptions'
        indexes = [
            models.Index(fields=['wallet', 'status']),
            models.Index(fields=['redemption_type']),
        ]
        ordering = ['-initiated_at']
    
    def __str__(self):
        return f"Redemption - ₹{self.amount} - {self.wallet.customer.full_name}"


class LoyaltyTier(models.Model):
    """Customer loyalty tiers"""
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name='loyalty_tiers')
    
    # Tier details
    name = models.CharField(max_length=100)
    description = models.TextField()
    tier_level = models.IntegerField(validators=[MinValueValidator(1)])
    
    # Qualification criteria
    min_orders = models.IntegerField(default=0)
    min_spend = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    min_supercash_earned = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    
    # Benefits
    cashback_multiplier = models.DecimalField(max_digits=4, decimal_places=2, default=Decimal('1.00'))
    free_delivery = models.BooleanField(default=False)
    priority_support = models.BooleanField(default=False)
    exclusive_offers = models.BooleanField(default=False)
    
    # Visual elements
    badge_icon = models.URLField(blank=True)
    badge_color = models.CharField(max_length=7, default='#000000')  # Hex color
    
    # Status
    is_active = models.BooleanField(default=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'rewards_loyalty_tiers'
        indexes = [
            models.Index(fields=['organization', 'tier_level']),
        ]
        unique_together = ['organization', 'tier_level']
        ordering = ['tier_level']
    
    def __str__(self):
        return f"{self.name} (Level {self.tier_level}) - {self.organization.name}"


class CustomerLoyalty(models.Model):
    """Customer loyalty status and progression"""
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    customer = models.OneToOneField(Customer, on_delete=models.CASCADE, related_name='loyalty_status')
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE)
    
    # Current tier
    current_tier = models.ForeignKey(LoyaltyTier, on_delete=models.SET_NULL, null=True, related_name='customers')
    
    # Progression metrics
    total_orders = models.IntegerField(default=0)
    total_spend = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    total_supercash_earned = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    
    # Period-based metrics (for tier maintenance)
    ytd_orders = models.IntegerField(default=0)
    ytd_spend = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    ytd_supercash_earned = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    
    # Tier history
    tier_achieved_at = models.DateTimeField(null=True, blank=True)
    tier_expires_at = models.DateTimeField(null=True, blank=True)
    previous_tier = models.ForeignKey(LoyaltyTier, on_delete=models.SET_NULL, null=True, related_name='previous_customers')
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'rewards_customer_loyalty'
        indexes = [
            models.Index(fields=['organization', 'current_tier']),
            models.Index(fields=['customer']),
        ]
    
    def __str__(self):
        tier_name = self.current_tier.name if self.current_tier else 'No Tier'
        return f"{self.customer.full_name} - {tier_name}"
    
    def calculate_next_tier(self):
        """Calculate if customer qualifies for next tier"""
        available_tiers = LoyaltyTier.objects.filter(
            organization=self.organization,
            is_active=True,
            tier_level__gt=self.current_tier.tier_level if self.current_tier else 0
        ).order_by('tier_level')
        
        for tier in available_tiers:
            if (self.ytd_orders >= tier.min_orders and 
                self.ytd_spend >= tier.min_spend and 
                self.ytd_supercash_earned >= tier.min_supercash_earned):
                return tier
        
        return None
    
    def update_metrics(self, order_amount, supercash_earned):
        """Update customer metrics after order completion"""
        self.total_orders += 1
        self.total_spend += order_amount
        self.total_supercash_earned += supercash_earned
        
        self.ytd_orders += 1
        self.ytd_spend += order_amount
        self.ytd_supercash_earned += supercash_earned
        
        # Check for tier upgrade
        next_tier = self.calculate_next_tier()
        if next_tier and next_tier != self.current_tier:
            self.previous_tier = self.current_tier
            self.current_tier = next_tier
            self.tier_achieved_at = timezone.now()
        
        self.save()


class SuperCashExpiry(models.Model):
    """Track SuperCash expiry batches"""
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE)
    
    # Expiry batch details
    expiry_date = models.DateField()
    total_amount = models.DecimalField(max_digits=12, decimal_places=2)
    expired_amount = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    customers_affected = models.IntegerField(default=0)
    
    # Processing status
    is_processed = models.BooleanField(default=False)
    processed_at = models.DateTimeField(null=True, blank=True)
    
    # Notifications
    notification_sent = models.BooleanField(default=False)
    notification_sent_at = models.DateTimeField(null=True, blank=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'rewards_supercash_expiry'
        indexes = [
            models.Index(fields=['organization', 'expiry_date']),
            models.Index(fields=['is_processed']),
        ]
        ordering = ['expiry_date']
    
    def __str__(self):
        return f"SuperCash Expiry - {self.expiry_date} - ₹{self.total_amount}"


class RewardsSettings(models.Model):
    """Organization-specific rewards configuration"""
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.OneToOneField(Organization, on_delete=models.CASCADE, related_name='rewards_settings')
    
    # SuperCash configuration
    is_supercash_enabled = models.BooleanField(default=True)
    default_cashback_percentage = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal('2.00'))
    max_cashback_per_order = models.DecimalField(max_digits=8, decimal_places=2, default=Decimal('500.00'))
    min_order_for_cashback = models.DecimalField(max_digits=8, decimal_places=2, default=Decimal('100.00'))
    
    # SuperCash expiry
    supercash_expiry_days = models.IntegerField(default=365)
    expiry_notification_days = models.IntegerField(default=30)
    
    # Referral program
    is_referral_enabled = models.BooleanField(default=True)
    referrer_reward = models.DecimalField(max_digits=8, decimal_places=2, default=Decimal('100.00'))
    referee_reward = models.DecimalField(max_digits=8, decimal_places=2, default=Decimal('50.00'))
    min_referee_order = models.DecimalField(max_digits=8, decimal_places=2, default=Decimal('200.00'))
    max_referrals_per_customer = models.IntegerField(default=50)
    
    # Loyalty program
    is_loyalty_enabled = models.BooleanField(default=True)
    loyalty_tier_reset_annually = models.BooleanField(default=True)
    
    # Redemption settings
    min_redemption_amount = models.DecimalField(max_digits=8, decimal_places=2, default=Decimal('100.00'))
    max_redemption_per_order = models.DecimalField(max_digits=8, decimal_places=2, default=Decimal('1000.00'))
    redemption_processing_fee_percentage = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal('2.00'))
    
    # Auto-application settings
    auto_apply_best_offer = models.BooleanField(default=True)
    combine_multiple_offers = models.BooleanField(default=False)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'rewards_settings'
    
    def __str__(self):
        return f"Rewards Settings - {self.organization.name}"