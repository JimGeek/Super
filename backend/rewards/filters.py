import django_filters
from django.db import models
from django.utils import timezone
from datetime import timedelta
from .models import (
    SuperCashTransaction, RewardCampaign, SuperCashRedemption,
    CustomerLoyalty, SuperCashWallet
)


class SuperCashTransactionFilter(django_filters.FilterSet):
    """Filter for SuperCash transactions"""
    
    transaction_type = django_filters.MultipleChoiceFilter(
        choices=SuperCashTransaction.TRANSACTION_TYPES,
        help_text="Filter by transaction type"
    )
    
    status = django_filters.MultipleChoiceFilter(
        choices=SuperCashTransaction.STATUS_CHOICES,
        help_text="Filter by transaction status"
    )
    
    customer = django_filters.UUIDFilter(
        field_name='wallet__customer__id',
        help_text="Filter by customer ID"
    )
    
    customer_name = django_filters.CharFilter(
        field_name='wallet__customer__full_name',
        lookup_expr='icontains',
        help_text="Filter by customer name"
    )
    
    order = django_filters.UUIDFilter(
        field_name='order__id',
        help_text="Filter by order ID"
    )
    
    order_number = django_filters.CharFilter(
        field_name='order__order_number',
        lookup_expr='icontains',
        help_text="Filter by order number"
    )
    
    amount_min = django_filters.NumberFilter(
        field_name='amount',
        lookup_expr='gte',
        help_text="Minimum transaction amount"
    )
    
    amount_max = django_filters.NumberFilter(
        field_name='amount',
        lookup_expr='lte',
        help_text="Maximum transaction amount"
    )
    
    created_after = django_filters.DateTimeFilter(
        field_name='created_at',
        lookup_expr='gte',
        help_text="Filter transactions created after this datetime"
    )
    
    created_before = django_filters.DateTimeFilter(
        field_name='created_at',
        lookup_expr='lte',
        help_text="Filter transactions created before this datetime"
    )
    
    expires_after = django_filters.DateTimeFilter(
        field_name='expires_at',
        lookup_expr='gte',
        help_text="Filter by expiry date after"
    )
    
    expires_before = django_filters.DateTimeFilter(
        field_name='expires_at',
        lookup_expr='lte',
        help_text="Filter by expiry date before"
    )
    
    expiring_soon = django_filters.BooleanFilter(
        method='filter_expiring_soon',
        help_text="Filter transactions expiring in next 30 days"
    )
    
    is_expired = django_filters.BooleanFilter(
        method='filter_is_expired',
        help_text="Filter expired transactions"
    )
    
    reference_id = django_filters.CharFilter(
        field_name='reference_id',
        lookup_expr='icontains',
        help_text="Filter by reference ID"
    )
    
    class Meta:
        model = SuperCashTransaction
        fields = []
    
    def filter_expiring_soon(self, queryset, name, value):
        if value is True:
            cutoff_date = timezone.now() + timedelta(days=30)
            return queryset.filter(
                expires_at__isnull=False,
                expires_at__lte=cutoff_date,
                expires_at__gt=timezone.now(),
                status='completed',
                transaction_type__startswith='earn_'
            )
        elif value is False:
            return queryset.exclude(
                expires_at__isnull=False,
                expires_at__lte=timezone.now() + timedelta(days=30),
                expires_at__gt=timezone.now()
            )
        return queryset
    
    def filter_is_expired(self, queryset, name, value):
        if value is True:
            return queryset.filter(
                models.Q(status='expired') |
                models.Q(expires_at__lt=timezone.now(), expires_at__isnull=False)
            )
        elif value is False:
            return queryset.exclude(
                models.Q(status='expired') |
                models.Q(expires_at__lt=timezone.now(), expires_at__isnull=False)
            )
        return queryset


class RewardCampaignFilter(django_filters.FilterSet):
    """Filter for reward campaigns"""
    
    campaign_type = django_filters.MultipleChoiceFilter(
        choices=RewardCampaign.CAMPAIGN_TYPES,
        help_text="Filter by campaign type"
    )
    
    status = django_filters.MultipleChoiceFilter(
        choices=RewardCampaign.STATUS_CHOICES,
        help_text="Filter by campaign status"
    )
    
    reward_type = django_filters.MultipleChoiceFilter(
        choices=RewardCampaign.REWARD_TYPES,
        help_text="Filter by reward type"
    )
    
    name = django_filters.CharFilter(
        field_name='name',
        lookup_expr='icontains',
        help_text="Filter by campaign name"
    )
    
    is_active = django_filters.BooleanFilter(
        method='filter_is_active',
        help_text="Filter active campaigns"
    )
    
    start_date_after = django_filters.DateTimeFilter(
        field_name='start_date',
        lookup_expr='gte',
        help_text="Filter campaigns starting after this date"
    )
    
    start_date_before = django_filters.DateTimeFilter(
        field_name='start_date',
        lookup_expr='lte',
        help_text="Filter campaigns starting before this date"
    )
    
    end_date_after = django_filters.DateTimeFilter(
        field_name='end_date',
        lookup_expr='gte',
        help_text="Filter campaigns ending after this date"
    )
    
    end_date_before = django_filters.DateTimeFilter(
        field_name='end_date',
        lookup_expr='lte',
        help_text="Filter campaigns ending before this date"
    )
    
    min_reward_value = django_filters.NumberFilter(
        field_name='reward_value',
        lookup_expr='gte',
        help_text="Minimum reward value"
    )
    
    max_reward_value = django_filters.NumberFilter(
        field_name='reward_value',
        lookup_expr='lte',
        help_text="Maximum reward value"
    )
    
    min_order_amount = django_filters.NumberFilter(
        field_name='min_order_amount',
        lookup_expr='gte',
        help_text="Minimum order amount requirement"
    )
    
    requires_code = django_filters.BooleanFilter(
        field_name='requires_code',
        help_text="Filter campaigns that require promo code"
    )
    
    is_auto_apply = django_filters.BooleanFilter(
        field_name='is_auto_apply',
        help_text="Filter auto-apply campaigns"
    )
    
    target_merchant = django_filters.UUIDFilter(
        field_name='target_merchants__id',
        help_text="Filter campaigns targeting specific merchant"
    )
    
    budget_available = django_filters.BooleanFilter(
        method='filter_budget_available',
        help_text="Filter campaigns with available budget"
    )
    
    usage_below_limit = django_filters.BooleanFilter(
        method='filter_usage_below_limit',
        help_text="Filter campaigns below usage limit"
    )
    
    created_by = django_filters.CharFilter(
        field_name='created_by',
        lookup_expr='icontains',
        help_text="Filter by creator"
    )
    
    class Meta:
        model = RewardCampaign
        fields = []
    
    def filter_is_active(self, queryset, name, value):
        now = timezone.now()
        if value is True:
            return queryset.filter(
                status='active',
                start_date__lte=now,
                end_date__gte=now
            )
        elif value is False:
            return queryset.exclude(
                status='active',
                start_date__lte=now,
                end_date__gte=now
            )
        return queryset
    
    def filter_budget_available(self, queryset, name, value):
        if value is True:
            return queryset.filter(
                models.Q(total_budget__isnull=True) |
                models.Q(spent_amount__lt=models.F('total_budget'))
            )
        elif value is False:
            return queryset.filter(
                total_budget__isnull=False,
                spent_amount__gte=models.F('total_budget')
            )
        return queryset
    
    def filter_usage_below_limit(self, queryset, name, value):
        if value is True:
            return queryset.filter(
                models.Q(max_total_uses__isnull=True) |
                models.Q(current_uses__lt=models.F('max_total_uses'))
            )
        elif value is False:
            return queryset.filter(
                max_total_uses__isnull=False,
                current_uses__gte=models.F('max_total_uses')
            )
        return queryset


class SuperCashRedemptionFilter(django_filters.FilterSet):
    """Filter for SuperCash redemptions"""
    
    redemption_type = django_filters.MultipleChoiceFilter(
        choices=SuperCashRedemption.REDEMPTION_TYPES,
        help_text="Filter by redemption type"
    )
    
    status = django_filters.MultipleChoiceFilter(
        choices=SuperCashRedemption.STATUS_CHOICES,
        help_text="Filter by redemption status"
    )
    
    customer = django_filters.UUIDFilter(
        field_name='wallet__customer__id',
        help_text="Filter by customer ID"
    )
    
    customer_name = django_filters.CharFilter(
        field_name='wallet__customer__full_name',
        lookup_expr='icontains',
        help_text="Filter by customer name"
    )
    
    amount_min = django_filters.NumberFilter(
        field_name='amount',
        lookup_expr='gte',
        help_text="Minimum redemption amount"
    )
    
    amount_max = django_filters.NumberFilter(
        field_name='amount',
        lookup_expr='lte',
        help_text="Maximum redemption amount"
    )
    
    initiated_after = django_filters.DateTimeFilter(
        field_name='initiated_at',
        lookup_expr='gte',
        help_text="Filter redemptions initiated after this datetime"
    )
    
    initiated_before = django_filters.DateTimeFilter(
        field_name='initiated_at',
        lookup_expr='lte',
        help_text="Filter redemptions initiated before this datetime"
    )
    
    processed_after = django_filters.DateTimeFilter(
        field_name='processed_at',
        lookup_expr='gte',
        help_text="Filter redemptions processed after this datetime"
    )
    
    processed_before = django_filters.DateTimeFilter(
        field_name='processed_at',
        lookup_expr='lte',
        help_text="Filter redemptions processed before this datetime"
    )
    
    order = django_filters.UUIDFilter(
        field_name='order__id',
        help_text="Filter by associated order ID"
    )
    
    processed_by = django_filters.CharFilter(
        field_name='processed_by',
        lookup_expr='icontains',
        help_text="Filter by processor"
    )
    
    external_reference = django_filters.CharFilter(
        field_name='external_reference',
        lookup_expr='icontains',
        help_text="Filter by external reference"
    )
    
    pending_approval = django_filters.BooleanFilter(
        method='filter_pending_approval',
        help_text="Filter redemptions pending approval"
    )
    
    class Meta:
        model = SuperCashRedemption
        fields = []
    
    def filter_pending_approval(self, queryset, name, value):
        if value is True:
            return queryset.filter(status='initiated')
        elif value is False:
            return queryset.exclude(status='initiated')
        return queryset


class CustomerLoyaltyFilter(django_filters.FilterSet):
    """Filter for customer loyalty status"""
    
    current_tier = django_filters.UUIDFilter(
        field_name='current_tier__id',
        help_text="Filter by current tier ID"
    )
    
    tier_level = django_filters.NumberFilter(
        field_name='current_tier__tier_level',
        help_text="Filter by tier level"
    )
    
    customer_name = django_filters.CharFilter(
        field_name='customer__full_name',
        lookup_expr='icontains',
        help_text="Filter by customer name"
    )
    
    min_total_orders = django_filters.NumberFilter(
        field_name='total_orders',
        lookup_expr='gte',
        help_text="Minimum total orders"
    )
    
    max_total_orders = django_filters.NumberFilter(
        field_name='total_orders',
        lookup_expr='lte',
        help_text="Maximum total orders"
    )
    
    min_total_spend = django_filters.NumberFilter(
        field_name='total_spend',
        lookup_expr='gte',
        help_text="Minimum total spend"
    )
    
    max_total_spend = django_filters.NumberFilter(
        field_name='total_spend',
        lookup_expr='lte',
        help_text="Maximum total spend"
    )
    
    min_ytd_orders = django_filters.NumberFilter(
        field_name='ytd_orders',
        lookup_expr='gte',
        help_text="Minimum YTD orders"
    )
    
    max_ytd_orders = django_filters.NumberFilter(
        field_name='ytd_orders',
        lookup_expr='lte',
        help_text="Maximum YTD orders"
    )
    
    min_ytd_spend = django_filters.NumberFilter(
        field_name='ytd_spend',
        lookup_expr='gte',
        help_text="Minimum YTD spend"
    )
    
    max_ytd_spend = django_filters.NumberFilter(
        field_name='ytd_spend',
        lookup_expr='lte',
        help_text="Maximum YTD spend"
    )
    
    tier_achieved_after = django_filters.DateTimeFilter(
        field_name='tier_achieved_at',
        lookup_expr='gte',
        help_text="Filter customers who achieved tier after this date"
    )
    
    tier_achieved_before = django_filters.DateTimeFilter(
        field_name='tier_achieved_at',
        lookup_expr='lte',
        help_text="Filter customers who achieved tier before this date"
    )
    
    eligible_for_upgrade = django_filters.BooleanFilter(
        method='filter_eligible_for_upgrade',
        help_text="Filter customers eligible for tier upgrade"
    )
    
    class Meta:
        model = CustomerLoyalty
        fields = []
    
    def filter_eligible_for_upgrade(self, queryset, name, value):
        if value is True:
            # This would require complex logic to determine upgrade eligibility
            # For now, return customers who might be close to next tier
            return queryset.filter(
                ytd_orders__gte=models.F('current_tier__min_orders') * 0.8
            )
        return queryset


class SuperCashWalletFilter(django_filters.FilterSet):
    """Filter for SuperCash wallets"""
    
    is_active = django_filters.BooleanFilter(
        field_name='is_active',
        help_text="Filter by active status"
    )
    
    is_frozen = django_filters.BooleanFilter(
        field_name='is_frozen',
        help_text="Filter by frozen status"
    )
    
    customer_name = django_filters.CharFilter(
        field_name='customer__full_name',
        lookup_expr='icontains',
        help_text="Filter by customer name"
    )
    
    customer_phone = django_filters.CharFilter(
        field_name='customer__phone_number',
        lookup_expr='icontains',
        help_text="Filter by customer phone"
    )
    
    min_balance = django_filters.NumberFilter(
        field_name='available_balance',
        lookup_expr='gte',
        help_text="Minimum available balance"
    )
    
    max_balance = django_filters.NumberFilter(
        field_name='available_balance',
        lookup_expr='lte',
        help_text="Maximum available balance"
    )
    
    has_balance = django_filters.BooleanFilter(
        method='filter_has_balance',
        help_text="Filter wallets with non-zero balance"
    )
    
    min_lifetime_earned = django_filters.NumberFilter(
        field_name='lifetime_earned',
        lookup_expr='gte',
        help_text="Minimum lifetime earned"
    )
    
    min_lifetime_spent = django_filters.NumberFilter(
        field_name='lifetime_spent',
        lookup_expr='gte',
        help_text="Minimum lifetime spent"
    )
    
    has_referrals = django_filters.BooleanFilter(
        method='filter_has_referrals',
        help_text="Filter wallets with referrals"
    )
    
    min_referrals = django_filters.NumberFilter(
        field_name='total_referrals',
        lookup_expr='gte',
        help_text="Minimum number of referrals"
    )
    
    referral_code = django_filters.CharFilter(
        field_name='referral_code',
        lookup_expr='iexact',
        help_text="Filter by referral code"
    )
    
    created_after = django_filters.DateTimeFilter(
        field_name='created_at',
        lookup_expr='gte',
        help_text="Filter wallets created after this date"
    )
    
    created_before = django_filters.DateTimeFilter(
        field_name='created_at',
        lookup_expr='lte',
        help_text="Filter wallets created before this date"
    )
    
    class Meta:
        model = SuperCashWallet
        fields = []
    
    def filter_has_balance(self, queryset, name, value):
        if value is True:
            return queryset.filter(available_balance__gt=0)
        elif value is False:
            return queryset.filter(available_balance=0)
        return queryset
    
    def filter_has_referrals(self, queryset, name, value):
        if value is True:
            return queryset.filter(total_referrals__gt=0)
        elif value is False:
            return queryset.filter(total_referrals=0)
        return queryset