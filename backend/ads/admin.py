from django.contrib import admin
from django.urls import reverse
from django.utils.html import format_html
from django.db.models import Sum, Count
from django.utils import timezone
from datetime import timedelta

from .models import (
    AdCategory, AdCampaign, AdGroup, AdCreative, AdPlacement,
    AdAuction, AdImpression, AdClick, AdConversion, AdBudgetSpend,
    AdKeyword, AdAudienceSegment, AdReportingData
)


@admin.register(AdCategory)
class AdCategoryAdmin(admin.ModelAdmin):
    """Admin for ad categories"""
    
    list_display = [
        'name', 'organization', 'parent', 'is_active',
        'sort_order', 'children_count', 'created_at'
    ]
    list_filter = ['organization', 'is_active', 'parent']
    search_fields = ['name', 'description']
    list_editable = ['is_active', 'sort_order']
    raw_id_fields = ['organization', 'parent']
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = [
        ('Category Information', {
            'fields': ('name', 'description', 'parent', 'organization')
        }),
        ('Configuration', {
            'fields': ('is_active', 'sort_order', 'keywords', 'targeting_attributes')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    ]
    
    def children_count(self, obj):
        return obj.children.count()
    children_count.short_description = 'Children'
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('organization', 'parent')


@admin.register(AdPlacement)
class AdPlacementAdmin(admin.ModelAdmin):
    """Admin for ad placements"""
    
    list_display = [
        'name', 'organization', 'placement_type', 'is_active',
        'base_cpm', 'base_cpc', 'monthly_impressions', 'average_ctr'
    ]
    list_filter = ['organization', 'placement_type', 'is_active']
    search_fields = ['name', 'description']
    list_editable = ['is_active']
    raw_id_fields = ['organization']
    filter_horizontal = ['allowed_categories']
    readonly_fields = ['average_ctr', 'average_cpc', 'monthly_impressions', 'created_at', 'updated_at']
    
    fieldsets = [
        ('Placement Information', {
            'fields': ('name', 'description', 'placement_type', 'organization')
        }),
        ('Configuration', {
            'fields': ('dimensions', 'supported_formats', 'max_ads_per_page', 'is_active')
        }),
        ('Pricing', {
            'fields': ('base_cpm', 'base_cpc', 'minimum_bid')
        }),
        ('Targeting', {
            'fields': ('allowed_categories', 'content_restrictions')
        }),
        ('Performance', {
            'fields': ('average_ctr', 'average_cpc', 'monthly_impressions'),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    ]


@admin.register(AdCampaign)
class AdCampaignAdmin(admin.ModelAdmin):
    """Admin for ad campaigns"""
    
    list_display = [
        'name', 'advertiser', 'status', 'campaign_type',
        'daily_budget', 'spend', 'impressions', 'clicks',
        'conversions', 'ctr_display', 'cpc_display', 'is_active_display'
    ]
    list_filter = [
        'status', 'campaign_type', 'bidding_strategy',
        'organization', 'created_at', 'start_date'
    ]
    search_fields = ['name', 'description', 'advertiser__business_name']
    list_editable = ['status']
    raw_id_fields = ['organization', 'advertiser']
    filter_horizontal = ['target_categories']
    readonly_fields = [
        'impressions', 'clicks', 'conversions', 'spend', 'revenue',
        'ctr', 'cpc', 'cpa', 'roas', 'is_active',
        'approved_by', 'approved_at', 'created_at', 'updated_at'
    ]
    
    fieldsets = [
        ('Campaign Information', {
            'fields': ('name', 'description', 'campaign_type', 'status', 'organization', 'advertiser')
        }),
        ('Timing', {
            'fields': ('start_date', 'end_date', 'is_evergreen')
        }),
        ('Bidding & Budget', {
            'fields': (
                'bidding_strategy', 'daily_budget', 'total_budget',
                'default_bid', 'max_bid', 'target_cpa', 'target_roas'
            )
        }),
        ('Targeting', {
            'fields': (
                'target_categories', 'target_keywords', 'target_demographics',
                'target_locations', 'target_devices', 'target_schedule'
            )
        }),
        ('Advanced Options', {
            'fields': (
                'exclude_keywords', 'exclude_placements', 'audience_targeting',
                'auto_pause_low_performance', 'enable_dynamic_ads', 'enable_audience_expansion'
            ),
            'classes': ('collapse',)
        }),
        ('Performance', {
            'fields': ('impressions', 'clicks', 'conversions', 'spend', 'revenue', 'ctr', 'cpc', 'cpa', 'roas'),
            'classes': ('collapse',)
        }),
        ('Approval', {
            'fields': ('approved_by', 'approved_at', 'rejection_reason'),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_by', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    ]
    
    def ctr_display(self, obj):
        return f"{obj.ctr:.2f}%"
    ctr_display.short_description = 'CTR'
    
    def cpc_display(self, obj):
        return f"₹{obj.cpc}"
    cpc_display.short_description = 'CPC'
    
    def is_active_display(self, obj):
        return obj.is_active
    is_active_display.boolean = True
    is_active_display.short_description = 'Active'
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('organization', 'advertiser')


@admin.register(AdGroup)
class AdGroupAdmin(admin.ModelAdmin):
    """Admin for ad groups"""
    
    list_display = [
        'name', 'campaign', 'status', 'default_bid',
        'impressions', 'clicks', 'conversions', 'spend'
    ]
    list_filter = ['status', 'campaign__organization', 'created_at']
    search_fields = ['name', 'campaign__name']
    list_editable = ['status']
    raw_id_fields = ['campaign']
    readonly_fields = ['impressions', 'clicks', 'conversions', 'spend', 'revenue', 'created_at', 'updated_at']
    
    fieldsets = [
        ('Ad Group Information', {
            'fields': ('name', 'campaign', 'status')
        }),
        ('Bidding', {
            'fields': ('default_bid',)
        }),
        ('Keywords', {
            'fields': ('keywords', 'negative_keywords')
        }),
        ('Performance', {
            'fields': ('impressions', 'clicks', 'conversions', 'spend', 'revenue'),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    ]
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('campaign')


@admin.register(AdCreative)
class AdCreativeAdmin(admin.ModelAdmin):
    """Admin for ad creatives"""
    
    list_display = [
        'name', 'ad_group', 'creative_type', 'status',
        'compliance_status', 'impressions', 'clicks', 'quality_score'
    ]
    list_filter = [
        'creative_type', 'status', 'compliance_status',
        'ad_group__campaign__organization', 'created_at'
    ]
    search_fields = ['name', 'headline', 'description', 'ad_group__name']
    list_editable = ['status', 'compliance_status']
    raw_id_fields = ['ad_group']
    readonly_fields = [
        'impressions', 'clicks', 'conversions', 'spend',
        'quality_score', 'created_at', 'updated_at'
    ]
    
    fieldsets = [
        ('Creative Information', {
            'fields': ('name', 'ad_group', 'creative_type', 'status')
        }),
        ('Content', {
            'fields': ('headline', 'description', 'call_to_action')
        }),
        ('Media', {
            'fields': ('image_url', 'video_url', 'thumbnail_url', 'media_assets')
        }),
        ('Landing Page', {
            'fields': ('destination_url', 'display_url')
        }),
        ('Product/Merchant', {
            'fields': ('promoted_products', 'merchant_info'),
            'classes': ('collapse',)
        }),
        ('Performance', {
            'fields': ('impressions', 'clicks', 'conversions', 'spend', 'quality_score'),
            'classes': ('collapse',)
        }),
        ('Compliance', {
            'fields': ('compliance_status', 'review_notes'),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    ]


@admin.register(AdKeyword)
class AdKeywordAdmin(admin.ModelAdmin):
    """Admin for ad keywords"""
    
    list_display = [
        'keyword_text', 'match_type', 'ad_group', 'status',
        'bid_amount', 'quality_score', 'impressions', 'clicks'
    ]
    list_filter = ['match_type', 'status', 'ad_group__campaign__organization']
    search_fields = ['keyword_text', 'ad_group__name']
    list_editable = ['status', 'bid_amount']
    raw_id_fields = ['ad_group']
    readonly_fields = [
        'impressions', 'clicks', 'conversions', 'spend',
        'quality_score', 'monthly_searches', 'competition_level',
        'suggested_bid', 'created_at', 'updated_at'
    ]


@admin.register(AdAudienceSegment)
class AdAudienceSegmentAdmin(admin.ModelAdmin):
    """Admin for audience segments"""
    
    list_display = [
        'name', 'segment_type', 'organization', 'created_by',
        'size_estimate', 'is_active', 'last_refreshed'
    ]
    list_filter = ['segment_type', 'organization', 'is_active']
    search_fields = ['name', 'description']
    raw_id_fields = ['organization', 'created_by']
    readonly_fields = [
        'size_estimate', 'avg_ctr', 'avg_conversion_rate',
        'last_refreshed', 'created_at', 'updated_at'
    ]


@admin.register(AdImpression)
class AdImpressionAdmin(admin.ModelAdmin):
    """Admin for ad impressions"""
    
    list_display = [
        'impression_id', 'creative', 'placement', 'customer',
        'country', 'device_type', 'viewable', 'cost', 'served_at'
    ]
    list_filter = [
        'viewable', 'device_type', 'country',
        'creative__ad_group__campaign__organization', 'served_at'
    ]
    search_fields = ['impression_id', 'page_url']
    raw_id_fields = ['creative', 'placement', 'auction', 'customer']
    readonly_fields = ['impression_id', 'served_at']
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related(
            'creative', 'placement', 'customer'
        )


@admin.register(AdClick)
class AdClickAdmin(admin.ModelAdmin):
    """Admin for ad clicks"""
    
    list_display = [
        'click_id', 'creative', 'is_valid', 'fraud_score',
        'cost', 'time_to_click', 'clicked_at'
    ]
    list_filter = [
        'is_valid', 'creative__ad_group__campaign__organization', 'clicked_at'
    ]
    search_fields = ['click_id', 'destination_url']
    raw_id_fields = ['impression', 'creative']
    readonly_fields = ['click_id', 'clicked_at']
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('impression', 'creative')


@admin.register(AdConversion)
class AdConversionAdmin(admin.ModelAdmin):
    """Admin for ad conversions"""
    
    list_display = [
        'conversion_type', 'conversion_value', 'creative',
        'attribution_model', 'is_verified', 'converted_at'
    ]
    list_filter = [
        'conversion_type', 'attribution_model', 'is_verified',
        'creative__ad_group__campaign__organization', 'converted_at'
    ]
    raw_id_fields = ['click', 'creative', 'order']
    readonly_fields = ['converted_at']


@admin.register(AdBudgetSpend)
class AdBudgetSpendAdmin(admin.ModelAdmin):
    """Admin for budget spend tracking"""
    
    list_display = [
        'campaign', 'spend_date', 'daily_budget', 'total_spend',
        'budget_utilization_display', 'is_budget_exceeded',
        'impressions', 'clicks', 'conversions'
    ]
    list_filter = ['is_budget_exceeded', 'campaign__organization', 'spend_date']
    raw_id_fields = ['campaign']
    readonly_fields = [
        'total_spend', 'impressions', 'clicks', 'conversions',
        'revenue', 'budget_exhausted_at', 'created_at', 'updated_at'
    ]
    
    def budget_utilization_display(self, obj):
        return f"{obj.budget_utilization:.1f}%"
    budget_utilization_display.short_description = 'Budget Used'


@admin.register(AdAuction)
class AdAuctionAdmin(admin.ModelAdmin):
    """Admin for ad auctions"""
    
    list_display = [
        'request_id', 'placement', 'auction_type', 'winner_creative',
        'winning_bid', 'clearing_price', 'total_participating', 'auction_time'
    ]
    list_filter = ['auction_type', 'organization', 'auction_time']
    search_fields = ['request_id']
    raw_id_fields = ['organization', 'placement', 'winner_creative']
    readonly_fields = ['auction_time']
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related(
            'placement', 'winner_creative'
        )


@admin.register(AdReportingData)
class AdReportingDataAdmin(admin.ModelAdmin):
    """Admin for reporting data"""
    
    list_display = [
        'campaign', 'aggregation_level', 'granularity',
        'report_date', 'impressions', 'clicks', 'conversions',
        'spend', 'ctr', 'cpc'
    ]
    list_filter = [
        'aggregation_level', 'granularity', 'organization', 'report_date'
    ]
    raw_id_fields = ['organization', 'campaign']
    readonly_fields = ['created_at']


# Custom admin site configuration
admin.site.site_header = 'SUPER Ads Administration'
admin.site.site_title = 'SUPER Ads Admin'
admin.site.index_title = 'Ads Platform Management'