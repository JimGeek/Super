from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils import timezone
from decimal import Decimal
from .models import (
    SuperCashWallet, SuperCashTransaction, RewardCampaign,
    CustomerRewardUsage, SuperCashRedemption, LoyaltyTier,
    CustomerLoyalty, SuperCashExpiry, RewardsSettings
)


@admin.register(SuperCashWallet)
class SuperCashWalletAdmin(admin.ModelAdmin):
    list_display = [
        'customer_name', 'organization', 'available_balance', 'pending_balance',
        'lifetime_earned', 'lifetime_spent', 'total_referrals', 'is_active',
        'is_frozen', 'created_at'
    ]
    list_filter = [
        'is_active', 'is_frozen', 'organization', 'created_at'
    ]
    search_fields = [
        'customer__full_name', 'customer__email', 'customer__phone_number',
        'referral_code'
    ]
    readonly_fields = [
        'lifetime_earned', 'lifetime_spent', 'total_referrals',
        'referral_code', 'created_at', 'updated_at'
    ]
    
    fieldsets = [
        ('Customer Information', {
            'fields': ['customer', 'organization']
        }),
        ('Balance Information', {
            'fields': [
                'available_balance', 'pending_balance', 'lifetime_earned',
                'lifetime_spent'
            ]
        }),
        ('Wallet Status', {
            'fields': ['is_active', 'is_frozen', 'freeze_reason']
        }),
        ('Referral Information', {
            'fields': ['referral_code', 'referred_by', 'total_referrals']
        }),
        ('Timestamps', {
            'fields': ['created_at', 'updated_at'],
            'classes': ['collapse']
        })
    ]
    
    def customer_name(self, obj):
        return obj.customer.full_name
    customer_name.short_description = 'Customer'
    customer_name.admin_order_field = 'customer__full_name'
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('customer', 'organization')
    
    actions = ['freeze_wallets', 'unfreeze_wallets']
    
    def freeze_wallets(self, request, queryset):
        updated = queryset.update(is_frozen=True, freeze_reason='Admin action')
        self.message_user(request, f'{updated} wallets frozen.')
    freeze_wallets.short_description = 'Freeze selected wallets'
    
    def unfreeze_wallets(self, request, queryset):
        updated = queryset.update(is_frozen=False, freeze_reason='')
        self.message_user(request, f'{updated} wallets unfrozen.')
    unfreeze_wallets.short_description = 'Unfreeze selected wallets'


@admin.register(SuperCashTransaction)
class SuperCashTransactionAdmin(admin.ModelAdmin):
    list_display = [
        'customer_name', 'transaction_type', 'amount', 'status',
        'order_number', 'expires_at', 'created_at'
    ]
    list_filter = [
        'transaction_type', 'status', 'organization', 'created_at',
        'expires_at', 'processed_at'
    ]
    search_fields = [
        'wallet__customer__full_name', 'order__order_number',
        'reference_id', 'description'
    ]
    readonly_fields = [
        'balance_before', 'balance_after', 'processed_at',
        'created_at', 'updated_at'
    ]
    
    fieldsets = [
        ('Transaction Details', {
            'fields': [
                'wallet', 'organization', 'transaction_type', 'status', 'amount'
            ]
        }),
        ('Reference Information', {
            'fields': ['order', 'reference_id', 'description', 'metadata']
        }),
        ('Balance Tracking', {
            'fields': ['balance_before', 'balance_after']
        }),
        ('Expiry & Processing', {
            'fields': ['expires_at', 'processed_at']
        }),
        ('Timestamps', {
            'fields': ['created_at', 'updated_at'],
            'classes': ['collapse']
        })
    ]
    
    def customer_name(self, obj):
        return obj.wallet.customer.full_name
    customer_name.short_description = 'Customer'
    
    def order_number(self, obj):
        return obj.order.order_number if obj.order else '-'
    order_number.short_description = 'Order'
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related(
            'wallet__customer', 'order', 'organization'
        )


@admin.register(RewardCampaign)
class RewardCampaignAdmin(admin.ModelAdmin):
    list_display = [
        'name', 'campaign_type', 'status', 'reward_value', 'current_uses',
        'max_total_uses', 'spent_amount', 'total_budget', 'is_active_display',
        'start_date', 'end_date'
    ]
    list_filter = [
        'campaign_type', 'status', 'reward_type', 'organization',
        'start_date', 'end_date', 'is_auto_apply', 'requires_code'
    ]
    search_fields = ['name', 'description', 'promo_code']
    readonly_fields = [
        'current_uses', 'spent_amount', 'is_active_display',
        'created_at', 'updated_at'
    ]
    filter_horizontal = ['target_merchants']
    
    fieldsets = [
        ('Campaign Information', {
            'fields': [
                'name', 'description', 'organization', 'campaign_type', 'status'
            ]
        }),
        ('Reward Configuration', {
            'fields': [
                'reward_type', 'reward_value', 'max_reward_amount',
                'min_order_amount', 'tier_config'
            ]
        }),
        ('Campaign Validity', {
            'fields': ['start_date', 'end_date']
        }),
        ('Usage Limits', {
            'fields': [
                'max_uses_per_customer', 'max_total_uses', 'current_uses',
                'total_budget', 'spent_amount'
            ]
        }),
        ('Targeting', {
            'fields': [
                'target_customers', 'target_merchants', 'target_categories'
            ]
        }),
        ('Promotion Settings', {
            'fields': ['is_auto_apply', 'requires_code', 'promo_code']
        }),
        ('Metadata', {
            'fields': ['created_by', 'created_at', 'updated_at'],
            'classes': ['collapse']
        })
    ]
    
    def is_active_display(self, obj):
        if obj.is_active:
            return format_html('<span style="color: green;">✓ Active</span>')
        else:
            return format_html('<span style="color: red;">✗ Inactive</span>')
    is_active_display.short_description = 'Active Status'
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('organization')


@admin.register(CustomerRewardUsage)
class CustomerRewardUsageAdmin(admin.ModelAdmin):
    list_display = [
        'customer_name', 'campaign_name', 'order_number',
        'reward_amount', 'order_amount', 'used_at'
    ]
    list_filter = ['used_at', 'campaign__campaign_type']
    search_fields = [
        'customer__full_name', 'campaign__name', 'order__order_number'
    ]
    readonly_fields = ['used_at']
    
    def customer_name(self, obj):
        return obj.customer.full_name
    customer_name.short_description = 'Customer'
    
    def campaign_name(self, obj):
        return obj.campaign.name
    campaign_name.short_description = 'Campaign'
    
    def order_number(self, obj):
        return obj.order.order_number
    order_number.short_description = 'Order'
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related(
            'customer', 'campaign', 'order'
        )


@admin.register(SuperCashRedemption)
class SuperCashRedemptionAdmin(admin.ModelAdmin):
    list_display = [
        'customer_name', 'redemption_type', 'amount', 'net_amount',
        'status', 'order_number', 'initiated_at', 'completed_at'
    ]
    list_filter = [
        'redemption_type', 'status', 'organization', 'initiated_at'
    ]
    search_fields = [
        'wallet__customer__full_name', 'external_reference',
        'order__order_number'
    ]
    readonly_fields = [
        'processing_fee', 'net_amount', 'initiated_at',
        'processed_at', 'completed_at'
    ]
    
    fieldsets = [
        ('Redemption Details', {
            'fields': [
                'wallet', 'organization', 'redemption_type', 'amount',
                'processing_fee', 'net_amount', 'status'
            ]
        }),
        ('Reference Information', {
            'fields': ['order', 'external_reference', 'bank_details']
        }),
        ('Processing Information', {
            'fields': ['processed_by', 'initiated_at', 'processed_at', 'completed_at']
        })
    ]
    
    def customer_name(self, obj):
        return obj.wallet.customer.full_name
    customer_name.short_description = 'Customer'
    
    def order_number(self, obj):
        return obj.order.order_number if obj.order else '-'
    order_number.short_description = 'Order'
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related(
            'wallet__customer', 'order', 'organization'
        )
    
    actions = ['approve_redemptions', 'complete_redemptions']
    
    def approve_redemptions(self, request, queryset):
        updated = queryset.filter(status='initiated').update(
            status='processing',
            processed_by=str(request.user.id),
            processed_at=timezone.now()
        )
        self.message_user(request, f'{updated} redemptions approved.')
    approve_redemptions.short_description = 'Approve selected redemptions'
    
    def complete_redemptions(self, request, queryset):
        updated = queryset.filter(status='processing').update(
            status='completed',
            completed_at=timezone.now()
        )
        self.message_user(request, f'{updated} redemptions completed.')
    complete_redemptions.short_description = 'Complete selected redemptions'


@admin.register(LoyaltyTier)
class LoyaltyTierAdmin(admin.ModelAdmin):
    list_display = [
        'name', 'tier_level', 'organization', 'min_orders', 'min_spend',
        'cashback_multiplier', 'free_delivery', 'priority_support',
        'exclusive_offers', 'customer_count', 'is_active'
    ]
    list_filter = [
        'is_active', 'organization', 'free_delivery',
        'priority_support', 'exclusive_offers'
    ]
    search_fields = ['name', 'description']
    readonly_fields = ['customer_count', 'created_at', 'updated_at']
    
    fieldsets = [
        ('Tier Information', {
            'fields': ['name', 'description', 'organization', 'tier_level', 'is_active']
        }),
        ('Qualification Criteria', {
            'fields': ['min_orders', 'min_spend', 'min_supercash_earned']
        }),
        ('Benefits', {
            'fields': [
                'cashback_multiplier', 'free_delivery', 'priority_support',
                'exclusive_offers'
            ]
        }),
        ('Visual Elements', {
            'fields': ['badge_icon', 'badge_color']
        }),
        ('Statistics', {
            'fields': ['customer_count'],
            'classes': ['collapse']
        }),
        ('Timestamps', {
            'fields': ['created_at', 'updated_at'],
            'classes': ['collapse']
        })
    ]
    
    def customer_count(self, obj):
        return obj.customers.count()
    customer_count.short_description = 'Customers'
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('organization')


@admin.register(CustomerLoyalty)
class CustomerLoyaltyAdmin(admin.ModelAdmin):
    list_display = [
        'customer_name', 'current_tier_name', 'total_orders', 'total_spend',
        'ytd_orders', 'ytd_spend', 'tier_achieved_at', 'progress_indicator'
    ]
    list_filter = [
        'current_tier', 'organization', 'tier_achieved_at'
    ]
    search_fields = ['customer__full_name', 'customer__email']
    readonly_fields = [
        'total_orders', 'total_spend', 'total_supercash_earned',
        'tier_achieved_at', 'created_at', 'updated_at'
    ]
    
    fieldsets = [
        ('Customer Information', {
            'fields': ['customer', 'organization', 'current_tier', 'previous_tier']
        }),
        ('Lifetime Metrics', {
            'fields': ['total_orders', 'total_spend', 'total_supercash_earned']
        }),
        ('Year-to-Date Metrics', {
            'fields': ['ytd_orders', 'ytd_spend', 'ytd_supercash_earned']
        }),
        ('Tier History', {
            'fields': ['tier_achieved_at', 'tier_expires_at']
        }),
        ('Timestamps', {
            'fields': ['created_at', 'updated_at'],
            'classes': ['collapse']
        })
    ]
    
    def customer_name(self, obj):
        return obj.customer.full_name
    customer_name.short_description = 'Customer'
    
    def current_tier_name(self, obj):
        return obj.current_tier.name if obj.current_tier else 'No Tier'
    current_tier_name.short_description = 'Current Tier'
    
    def progress_indicator(self, obj):
        next_tier = obj.calculate_next_tier()
        if not next_tier:
            return format_html('<span style="color: gold;">★ Highest Tier</span>')
        
        # Calculate progress percentage
        order_progress = (obj.ytd_orders / next_tier.min_orders * 100) if next_tier.min_orders > 0 else 100
        spend_progress = (float(obj.ytd_spend) / float(next_tier.min_spend) * 100) if next_tier.min_spend > 0 else 100
        overall_progress = min(order_progress, spend_progress)
        
        color = 'green' if overall_progress >= 80 else 'orange' if overall_progress >= 50 else 'red'
        return format_html(
            '<div style="width: 100px; background: #f0f0f0; border: 1px solid #ccc;">'
            '<div style="width: {}px; height: 20px; background: {}; text-align: center; color: white; font-size: 10px; line-height: 20px;">'
            '{:.0f}%</div></div>',
            overall_progress, color, overall_progress
        )
    progress_indicator.short_description = 'Next Tier Progress'
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related(
            'customer', 'organization', 'current_tier', 'previous_tier'
        )


@admin.register(SuperCashExpiry)
class SuperCashExpiryAdmin(admin.ModelAdmin):
    list_display = [
        'expiry_date', 'organization', 'total_amount', 'expired_amount',
        'customers_affected', 'is_processed', 'notification_sent', 'created_at'
    ]
    list_filter = [
        'is_processed', 'notification_sent', 'organization', 'expiry_date'
    ]
    readonly_fields = [
        'expired_amount', 'customers_affected', 'processed_at',
        'notification_sent_at', 'created_at'
    ]
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('organization')


@admin.register(RewardsSettings)
class RewardsSettingsAdmin(admin.ModelAdmin):
    list_display = [
        'organization', 'is_supercash_enabled', 'default_cashback_percentage',
        'is_referral_enabled', 'is_loyalty_enabled', 'created_at'
    ]
    list_filter = [
        'is_supercash_enabled', 'is_referral_enabled',
        'is_loyalty_enabled', 'auto_apply_best_offer'
    ]
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = [
        ('Organization', {
            'fields': ['organization']
        }),
        ('SuperCash Configuration', {
            'fields': [
                'is_supercash_enabled', 'default_cashback_percentage',
                'max_cashback_per_order', 'min_order_for_cashback',
                'supercash_expiry_days', 'expiry_notification_days'
            ]
        }),
        ('Referral Program', {
            'fields': [
                'is_referral_enabled', 'referrer_reward', 'referee_reward',
                'min_referee_order', 'max_referrals_per_customer'
            ]
        }),
        ('Loyalty Program', {
            'fields': ['is_loyalty_enabled', 'loyalty_tier_reset_annually']
        }),
        ('Redemption Settings', {
            'fields': [
                'min_redemption_amount', 'max_redemption_per_order',
                'redemption_processing_fee_percentage'
            ]
        }),
        ('Auto-Application Settings', {
            'fields': ['auto_apply_best_offer', 'combine_multiple_offers']
        }),
        ('Timestamps', {
            'fields': ['created_at', 'updated_at'],
            'classes': ['collapse']
        })
    ]
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('organization')


# Custom admin site configurations
admin.site.site_header = "SUPER Rewards Administration"
admin.site.site_title = "SUPER Rewards Admin"
admin.site.index_title = "Welcome to SUPER Rewards Administration"