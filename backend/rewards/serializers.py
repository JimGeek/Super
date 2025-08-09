from rest_framework import serializers
from decimal import Decimal
from django.utils import timezone
from .models import (
    SuperCashWallet, SuperCashTransaction, RewardCampaign,
    CustomerRewardUsage, SuperCashRedemption, LoyaltyTier,
    CustomerLoyalty, SuperCashExpiry, RewardsSettings
)


class SuperCashWalletSerializer(serializers.ModelSerializer):
    """Serializer for SuperCash wallet"""
    
    total_balance = serializers.ReadOnlyField()
    success_rate = serializers.SerializerMethodField()
    
    class Meta:
        model = SuperCashWallet
        fields = [
            'id', 'available_balance', 'pending_balance', 'total_balance',
            'lifetime_earned', 'lifetime_spent', 'is_active', 'is_frozen',
            'freeze_reason', 'referral_code', 'total_referrals',
            'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'available_balance', 'pending_balance', 'lifetime_earned',
            'lifetime_spent', 'referral_code', 'total_referrals',
            'created_at', 'updated_at'
        ]
    
    def get_success_rate(self, obj):
        if obj.total_referrals == 0:
            return 100.0
        # Calculate success rate based on referrals who made orders
        successful_referrals = obj.customer.referrals.filter(
            orders__isnull=False
        ).distinct().count()
        return (successful_referrals / obj.total_referrals) * 100


class SuperCashTransactionSerializer(serializers.ModelSerializer):
    """Serializer for SuperCash transactions"""
    
    customer_name = serializers.CharField(source='wallet.customer.full_name', read_only=True)
    order_number = serializers.CharField(source='order.order_number', read_only=True)
    
    class Meta:
        model = SuperCashTransaction
        fields = [
            'id', 'transaction_type', 'status', 'amount', 'customer_name',
            'order_number', 'reference_id', 'description', 'metadata',
            'expires_at', 'balance_before', 'balance_after',
            'processed_at', 'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'balance_before', 'balance_after', 'processed_at',
            'created_at', 'updated_at'
        ]


class RewardCampaignSerializer(serializers.ModelSerializer):
    """Serializer for reward campaigns"""
    
    is_active = serializers.ReadOnlyField()
    usage_percentage = serializers.SerializerMethodField()
    budget_utilization = serializers.SerializerMethodField()
    
    class Meta:
        model = RewardCampaign
        fields = [
            'id', 'name', 'description', 'campaign_type', 'status',
            'reward_type', 'reward_value', 'max_reward_amount', 'min_order_amount',
            'tier_config', 'start_date', 'end_date', 'max_uses_per_customer',
            'max_total_uses', 'current_uses', 'usage_percentage',
            'target_customers', 'target_categories', 'is_auto_apply',
            'requires_code', 'promo_code', 'total_budget', 'spent_amount',
            'budget_utilization', 'is_active', 'created_by', 'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'current_uses', 'spent_amount', 'is_active',
            'created_at', 'updated_at'
        ]
    
    def get_usage_percentage(self, obj):
        if obj.max_total_uses and obj.max_total_uses > 0:
            return (obj.current_uses / obj.max_total_uses) * 100
        return 0
    
    def get_budget_utilization(self, obj):
        if obj.total_budget and obj.total_budget > 0:
            return (obj.spent_amount / obj.total_budget) * 100
        return 0
    
    def validate(self, attrs):
        # Validate date range
        if attrs.get('start_date') and attrs.get('end_date'):
            if attrs['start_date'] >= attrs['end_date']:
                raise serializers.ValidationError("End date must be after start date")
        
        # Validate reward configuration
        if attrs.get('reward_type') == 'tiered' and not attrs.get('tier_config'):
            raise serializers.ValidationError("Tier configuration is required for tiered rewards")
        
        # Validate promo code requirement
        if attrs.get('requires_code') and not attrs.get('promo_code'):
            raise serializers.ValidationError("Promo code is required when requires_code is True")
        
        return attrs


class CustomerRewardUsageSerializer(serializers.ModelSerializer):
    """Serializer for customer reward usage tracking"""
    
    customer_name = serializers.CharField(source='customer.full_name', read_only=True)
    campaign_name = serializers.CharField(source='campaign.name', read_only=True)
    order_number = serializers.CharField(source='order.order_number', read_only=True)
    
    class Meta:
        model = CustomerRewardUsage
        fields = [
            'id', 'customer_name', 'campaign_name', 'order_number',
            'reward_amount', 'order_amount', 'used_at'
        ]
        read_only_fields = ['id', 'used_at']


class SuperCashRedemptionSerializer(serializers.ModelSerializer):
    """Serializer for SuperCash redemptions"""
    
    customer_name = serializers.CharField(source='wallet.customer.full_name', read_only=True)
    order_number = serializers.CharField(source='order.order_number', read_only=True)
    
    class Meta:
        model = SuperCashRedemption
        fields = [
            'id', 'customer_name', 'redemption_type', 'amount', 'status',
            'order_number', 'external_reference', 'bank_details',
            'processed_by', 'processing_fee', 'net_amount',
            'initiated_at', 'processed_at', 'completed_at'
        ]
        read_only_fields = [
            'id', 'processed_by', 'processing_fee', 'net_amount',
            'initiated_at', 'processed_at', 'completed_at'
        ]


class LoyaltyTierSerializer(serializers.ModelSerializer):
    """Serializer for loyalty tiers"""
    
    customer_count = serializers.SerializerMethodField()
    
    class Meta:
        model = LoyaltyTier
        fields = [
            'id', 'name', 'description', 'tier_level', 'min_orders',
            'min_spend', 'min_supercash_earned', 'cashback_multiplier',
            'free_delivery', 'priority_support', 'exclusive_offers',
            'badge_icon', 'badge_color', 'is_active', 'customer_count',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'customer_count', 'created_at', 'updated_at']
    
    def get_customer_count(self, obj):
        return obj.customers.count()


class CustomerLoyaltySerializer(serializers.ModelSerializer):
    """Serializer for customer loyalty status"""
    
    customer_name = serializers.CharField(source='customer.full_name', read_only=True)
    current_tier_name = serializers.CharField(source='current_tier.name', read_only=True)
    next_tier_info = serializers.SerializerMethodField()
    progress_percentage = serializers.SerializerMethodField()
    
    class Meta:
        model = CustomerLoyalty
        fields = [
            'id', 'customer_name', 'current_tier_name', 'total_orders',
            'total_spend', 'total_supercash_earned', 'ytd_orders',
            'ytd_spend', 'ytd_supercash_earned', 'tier_achieved_at',
            'tier_expires_at', 'next_tier_info', 'progress_percentage',
            'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'total_orders', 'total_spend', 'total_supercash_earned',
            'tier_achieved_at', 'created_at', 'updated_at'
        ]
    
    def get_next_tier_info(self, obj):
        next_tier = obj.calculate_next_tier()
        if next_tier:
            return {
                'name': next_tier.name,
                'tier_level': next_tier.tier_level,
                'required_orders': next_tier.min_orders,
                'required_spend': next_tier.min_spend,
                'required_supercash': next_tier.min_supercash_earned
            }
        return None
    
    def get_progress_percentage(self, obj):
        next_tier = obj.calculate_next_tier()
        if not next_tier:
            return 100  # Already at highest tier
        
        # Calculate progress based on most limiting factor
        order_progress = (obj.ytd_orders / next_tier.min_orders * 100) if next_tier.min_orders > 0 else 100
        spend_progress = (float(obj.ytd_spend) / float(next_tier.min_spend) * 100) if next_tier.min_spend > 0 else 100
        supercash_progress = (float(obj.ytd_supercash_earned) / float(next_tier.min_supercash_earned) * 100) if next_tier.min_supercash_earned > 0 else 100
        
        return min(order_progress, spend_progress, supercash_progress)


class SuperCashExpirySerializer(serializers.ModelSerializer):
    """Serializer for SuperCash expiry records"""
    
    class Meta:
        model = SuperCashExpiry
        fields = [
            'id', 'expiry_date', 'total_amount', 'expired_amount',
            'customers_affected', 'is_processed', 'processed_at',
            'notification_sent', 'notification_sent_at', 'created_at'
        ]
        read_only_fields = [
            'id', 'expired_amount', 'customers_affected', 'is_processed',
            'processed_at', 'notification_sent', 'notification_sent_at', 'created_at'
        ]


class RewardsSettingsSerializer(serializers.ModelSerializer):
    """Serializer for rewards settings"""
    
    class Meta:
        model = RewardsSettings
        fields = [
            'id', 'is_supercash_enabled', 'default_cashback_percentage',
            'max_cashback_per_order', 'min_order_for_cashback',
            'supercash_expiry_days', 'expiry_notification_days',
            'is_referral_enabled', 'referrer_reward', 'referee_reward',
            'min_referee_order', 'max_referrals_per_customer',
            'is_loyalty_enabled', 'loyalty_tier_reset_annually',
            'min_redemption_amount', 'max_redemption_per_order',
            'redemption_processing_fee_percentage', 'auto_apply_best_offer',
            'combine_multiple_offers', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


# Request/Response serializers
class CashbackCalculationRequestSerializer(serializers.Serializer):
    """Serializer for cashback calculation requests"""
    
    order_id = serializers.UUIDField()
    customer_id = serializers.UUIDField(required=False)
    order_amount = serializers.DecimalField(max_digits=10, decimal_places=2)
    merchant_id = serializers.UUIDField(required=False)
    apply_campaigns = serializers.BooleanField(default=True)


class CashbackCalculationResponseSerializer(serializers.Serializer):
    """Serializer for cashback calculation responses"""
    
    cashback_amount = serializers.DecimalField(max_digits=10, decimal_places=2)
    campaign_applied = serializers.CharField(allow_null=True)
    campaign_id = serializers.UUIDField(allow_null=True)
    base_cashback = serializers.DecimalField(max_digits=10, decimal_places=2)
    multiplier_applied = serializers.DecimalField(max_digits=4, decimal_places=2)
    expires_at = serializers.DateTimeField(allow_null=True)


class RedemptionRequestSerializer(serializers.Serializer):
    """Serializer for SuperCash redemption requests"""
    
    amount = serializers.DecimalField(max_digits=10, decimal_places=2, min_value=Decimal('1.00'))
    redemption_type = serializers.ChoiceField(choices=SuperCashRedemption.REDEMPTION_TYPES)
    order_id = serializers.UUIDField(required=False)
    bank_details = serializers.JSONField(required=False)
    
    def validate(self, attrs):
        if attrs.get('redemption_type') == 'bank_transfer' and not attrs.get('bank_details'):
            raise serializers.ValidationError("Bank details are required for bank transfer redemption")
        
        if attrs.get('redemption_type') == 'order_payment' and not attrs.get('order_id'):
            raise serializers.ValidationError("Order ID is required for order payment redemption")
        
        return attrs


class ReferralRewardRequestSerializer(serializers.Serializer):
    """Serializer for referral reward processing requests"""
    
    referrer_id = serializers.UUIDField()
    referee_id = serializers.UUIDField()
    referee_order_id = serializers.UUIDField()
    
    def validate(self, attrs):
        # Additional validation can be added here
        # e.g., check if referrer and referee are different customers
        if attrs['referrer_id'] == attrs['referee_id']:
            raise serializers.ValidationError("Referrer and referee must be different customers")
        
        return attrs


class WalletSummarySerializer(serializers.Serializer):
    """Serializer for wallet summary response"""
    
    wallet_id = serializers.UUIDField()
    available_balance = serializers.DecimalField(max_digits=10, decimal_places=2)
    pending_balance = serializers.DecimalField(max_digits=10, decimal_places=2)
    total_balance = serializers.DecimalField(max_digits=10, decimal_places=2)
    lifetime_earned = serializers.DecimalField(max_digits=12, decimal_places=2)
    lifetime_spent = serializers.DecimalField(max_digits=12, decimal_places=2)
    expiring_soon = serializers.DecimalField(max_digits=10, decimal_places=2)
    referral_code = serializers.CharField()
    total_referrals = serializers.IntegerField()
    loyalty_status = serializers.DictField(allow_null=True)
    recent_transactions = serializers.ListField(child=serializers.DictField())


class CampaignSimulationRequestSerializer(serializers.Serializer):
    """Serializer for campaign simulation requests"""
    
    campaign_id = serializers.UUIDField()
    days_to_simulate = serializers.IntegerField(min_value=1, max_value=365, default=30)
    target_participants = serializers.IntegerField(min_value=1, required=False)
    avg_order_value = serializers.DecimalField(max_digits=10, decimal_places=2, required=False)


class CampaignSimulationResponseSerializer(serializers.Serializer):
    """Serializer for campaign simulation responses"""
    
    estimated_participants = serializers.IntegerField()
    estimated_orders = serializers.IntegerField()
    estimated_revenue = serializers.DecimalField(max_digits=12, decimal_places=2)
    estimated_reward_cost = serializers.DecimalField(max_digits=12, decimal_places=2)
    estimated_roi = serializers.DecimalField(max_digits=8, decimal_places=2)
    budget_utilization = serializers.DecimalField(max_digits=5, decimal_places=2)


class RewardsAnalyticsSerializer(serializers.Serializer):
    """Serializer for rewards analytics data"""
    
    total_supercash_issued = serializers.DecimalField(max_digits=12, decimal_places=2)
    total_supercash_redeemed = serializers.DecimalField(max_digits=12, decimal_places=2)
    total_supercash_outstanding = serializers.DecimalField(max_digits=12, decimal_places=2)
    total_supercash_expired = serializers.DecimalField(max_digits=12, decimal_places=2)
    
    active_wallets = serializers.IntegerField()
    total_transactions = serializers.IntegerField()
    avg_wallet_balance = serializers.DecimalField(max_digits=10, decimal_places=2)
    
    referral_signups = serializers.IntegerField()
    referral_conversion_rate = serializers.DecimalField(max_digits=5, decimal_places=2)
    
    tier_distribution = serializers.DictField()
    campaign_performance = serializers.ListField(child=serializers.DictField())
    
    redemption_methods = serializers.DictField()
    monthly_trends = serializers.ListField(child=serializers.DictField())


class LoyaltyTierCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating loyalty tiers"""
    
    class Meta:
        model = LoyaltyTier
        fields = [
            'name', 'description', 'tier_level', 'min_orders',
            'min_spend', 'min_supercash_earned', 'cashback_multiplier',
            'free_delivery', 'priority_support', 'exclusive_offers',
            'badge_icon', 'badge_color'
        ]
    
    def validate_tier_level(self, value):
        organization = self.context['request'].user.organization
        
        # Check if tier level already exists
        if LoyaltyTier.objects.filter(
            organization=organization,
            tier_level=value
        ).exclude(pk=self.instance.pk if self.instance else None).exists():
            raise serializers.ValidationError("Tier level already exists")
        
        return value


class BulkTransactionSerializer(serializers.Serializer):
    """Serializer for bulk transaction operations"""
    
    customer_ids = serializers.ListField(
        child=serializers.UUIDField(),
        max_length=1000,
        help_text="List of customer IDs"
    )
    transaction_type = serializers.ChoiceField(choices=SuperCashTransaction.TRANSACTION_TYPES)
    amount = serializers.DecimalField(max_digits=10, decimal_places=2)
    description = serializers.CharField(max_length=500)
    expires_in_days = serializers.IntegerField(min_value=1, max_value=365, required=False)
    
    def validate_customer_ids(self, value):
        if len(value) != len(set(value)):
            raise serializers.ValidationError("Duplicate customer IDs found")
        return value