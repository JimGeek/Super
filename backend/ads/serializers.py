from rest_framework import serializers
from decimal import Decimal
from django.utils import timezone
from .models import (
    AdCategory, AdCampaign, AdGroup, AdCreative, AdPlacement,
    AdAuction, AdImpression, AdClick, AdConversion, AdBudgetSpend,
    AdKeyword, AdAudienceSegment, AdReportingData
)


class AdCategorySerializer(serializers.ModelSerializer):
    """Serializer for ad categories"""
    
    full_path = serializers.ReadOnlyField()
    children_count = serializers.SerializerMethodField()
    parent_name = serializers.CharField(source='parent.name', read_only=True)
    
    class Meta:
        model = AdCategory
        fields = [
            'id', 'name', 'description', 'parent', 'parent_name',
            'full_path', 'is_active', 'sort_order', 'keywords',
            'targeting_attributes', 'children_count', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def get_children_count(self, obj):
        return obj.children.count()


class AdPlacementSerializer(serializers.ModelSerializer):
    """Serializer for ad placements"""
    
    class Meta:
        model = AdPlacement
        fields = [
            'id', 'name', 'description', 'placement_type', 'dimensions',
            'supported_formats', 'max_ads_per_page', 'base_cpm', 'base_cpc',
            'minimum_bid', 'content_restrictions', 'average_ctr', 'average_cpc',
            'monthly_impressions', 'is_active', 'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'average_ctr', 'average_cpc', 'monthly_impressions',
            'created_at', 'updated_at'
        ]


class AdCampaignSerializer(serializers.ModelSerializer):
    """Serializer for ad campaigns"""
    
    advertiser_name = serializers.CharField(source='advertiser.business_name', read_only=True)
    is_active = serializers.ReadOnlyField()
    ctr = serializers.ReadOnlyField()
    cpc = serializers.ReadOnlyField()
    cpa = serializers.ReadOnlyField()
    roas = serializers.ReadOnlyField()
    target_categories_data = AdCategorySerializer(source='target_categories', many=True, read_only=True)
    
    class Meta:
        model = AdCampaign
        fields = [
            'id', 'advertiser', 'advertiser_name', 'name', 'description',
            'campaign_type', 'status', 'start_date', 'end_date',
            'bidding_strategy', 'daily_budget', 'total_budget',
            'default_bid', 'max_bid', 'target_cpa', 'target_roas',
            'target_categories_data', 'target_keywords', 'target_demographics',
            'target_locations', 'target_devices', 'target_schedule',
            'exclude_keywords', 'exclude_placements', 'audience_targeting',
            'impressions', 'clicks', 'conversions', 'spend', 'revenue',
            'is_active', 'ctr', 'cpc', 'cpa', 'roas',
            'is_evergreen', 'auto_pause_low_performance', 'enable_dynamic_ads',
            'enable_audience_expansion', 'approved_by', 'approved_at',
            'rejection_reason', 'created_by', 'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'impressions', 'clicks', 'conversions', 'spend', 'revenue',
            'is_active', 'ctr', 'cpc', 'cpa', 'roas', 'approved_by',
            'approved_at', 'created_at', 'updated_at'
        ]
    
    def validate(self, attrs):
        # Validate date range
        if attrs.get('start_date') and attrs.get('end_date'):
            if attrs['start_date'] >= attrs['end_date']:
                raise serializers.ValidationError("End date must be after start date")
        
        # Validate budget constraints
        if attrs.get('total_budget') and attrs.get('daily_budget'):
            total_budget = attrs['total_budget']
            daily_budget = attrs['daily_budget']
            
            # Calculate minimum days needed
            min_days = total_budget / daily_budget
            if attrs.get('start_date') and attrs.get('end_date'):
                campaign_days = (attrs['end_date'] - attrs['start_date']).days
                if campaign_days < min_days:
                    raise serializers.ValidationError(
                        f"Total budget requires at least {min_days:.0f} days at current daily budget"
                    )
        
        # Validate bidding strategy requirements
        bidding_strategy = attrs.get('bidding_strategy')
        if bidding_strategy == 'target_cpa' and not attrs.get('target_cpa'):
            raise serializers.ValidationError("Target CPA is required for Target CPA bidding strategy")
        
        if bidding_strategy == 'target_roas' and not attrs.get('target_roas'):
            raise serializers.ValidationError("Target ROAS is required for Target ROAS bidding strategy")
        
        return attrs


class AdGroupSerializer(serializers.ModelSerializer):
    """Serializer for ad groups"""
    
    campaign_name = serializers.CharField(source='campaign.name', read_only=True)
    effective_bid = serializers.ReadOnlyField()
    creatives_count = serializers.SerializerMethodField()
    keywords_count = serializers.SerializerMethodField()
    
    class Meta:
        model = AdGroup
        fields = [
            'id', 'campaign', 'campaign_name', 'name', 'status', 'default_bid',
            'effective_bid', 'keywords', 'negative_keywords', 'impressions',
            'clicks', 'conversions', 'spend', 'revenue', 'creatives_count',
            'keywords_count', 'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'impressions', 'clicks', 'conversions', 'spend', 'revenue',
            'created_at', 'updated_at'
        ]
    
    def get_creatives_count(self, obj):
        return obj.creatives.filter(status='active').count()
    
    def get_keywords_count(self, obj):
        return obj.keywords.filter(status='active').count()


class AdCreativeSerializer(serializers.ModelSerializer):
    """Serializer for ad creatives"""
    
    ad_group_name = serializers.CharField(source='ad_group.name', read_only=True)
    campaign_name = serializers.CharField(source='ad_group.campaign.name', read_only=True)
    
    class Meta:
        model = AdCreative
        fields = [
            'id', 'ad_group', 'ad_group_name', 'campaign_name', 'name',
            'creative_type', 'status', 'headline', 'description', 'call_to_action',
            'image_url', 'video_url', 'thumbnail_url', 'media_assets',
            'destination_url', 'display_url', 'promoted_products', 'merchant_info',
            'impressions', 'clicks', 'conversions', 'spend', 'quality_score',
            'compliance_status', 'review_notes', 'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'impressions', 'clicks', 'conversions', 'spend',
            'quality_score', 'compliance_status', 'review_notes',
            'created_at', 'updated_at'
        ]
    
    def validate(self, attrs):
        creative_type = attrs.get('creative_type')
        
        # Validate required fields based on creative type
        if creative_type == 'text' and not attrs.get('headline'):
            raise serializers.ValidationError("Headline is required for text ads")
        
        if creative_type in ['image', 'video'] and not attrs.get('image_url') and not attrs.get('video_url'):
            raise serializers.ValidationError(f"Media URL is required for {creative_type} ads")
        
        if creative_type == 'carousel' and not attrs.get('media_assets'):
            raise serializers.ValidationError("Media assets are required for carousel ads")
        
        if creative_type == 'product' and not attrs.get('promoted_products'):
            raise serializers.ValidationError("Promoted products are required for product ads")
        
        return attrs


class AdKeywordSerializer(serializers.ModelSerializer):
    """Serializer for ad keywords"""
    
    ad_group_name = serializers.CharField(source='ad_group.name', read_only=True)
    effective_bid = serializers.ReadOnlyField()
    
    class Meta:
        model = AdKeyword
        fields = [
            'id', 'ad_group', 'ad_group_name', 'keyword_text', 'match_type',
            'status', 'bid_amount', 'effective_bid', 'quality_score',
            'impressions', 'clicks', 'conversions', 'spend', 'monthly_searches',
            'competition_level', 'suggested_bid', 'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'impressions', 'clicks', 'conversions', 'spend',
            'quality_score', 'monthly_searches', 'competition_level',
            'suggested_bid', 'created_at', 'updated_at'
        ]


class AdAudienceSegmentSerializer(serializers.ModelSerializer):
    """Serializer for audience segments"""
    
    created_by_name = serializers.CharField(source='created_by.business_name', read_only=True)
    
    class Meta:
        model = AdAudienceSegment
        fields = [
            'id', 'created_by', 'created_by_name', 'name', 'description',
            'segment_type', 'criteria', 'size_estimate', 'avg_ctr',
            'avg_conversion_rate', 'is_active', 'last_refreshed',
            'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'size_estimate', 'avg_ctr', 'avg_conversion_rate',
            'last_refreshed', 'created_at', 'updated_at'
        ]


class AdImpressionSerializer(serializers.ModelSerializer):
    """Serializer for ad impressions"""
    
    creative_name = serializers.CharField(source='creative.name', read_only=True)
    placement_name = serializers.CharField(source='placement.name', read_only=True)
    customer_name = serializers.CharField(source='customer.full_name', read_only=True)
    
    class Meta:
        model = AdImpression
        fields = [
            'id', 'creative', 'creative_name', 'placement', 'placement_name',
            'customer', 'customer_name', 'impression_id', 'page_url',
            'referrer_url', 'country', 'region', 'city', 'device_type',
            'browser', 'os', 'viewable', 'view_duration', 'scroll_depth',
            'bid_amount', 'cost', 'served_at'
        ]
        read_only_fields = [
            'id', 'impression_id', 'viewable', 'view_duration',
            'scroll_depth', 'served_at'
        ]


class AdClickSerializer(serializers.ModelSerializer):
    """Serializer for ad clicks"""
    
    creative_name = serializers.CharField(source='creative.name', read_only=True)
    impression_id_display = serializers.CharField(source='impression.impression_id', read_only=True)
    
    class Meta:
        model = AdClick
        fields = [
            'id', 'impression', 'impression_id_display', 'creative',
            'creative_name', 'click_id', 'destination_url', 'click_position',
            'time_to_click', 'is_valid', 'fraud_score', 'fraud_reason',
            'cost', 'clicked_at'
        ]
        read_only_fields = [
            'id', 'click_id', 'is_valid', 'fraud_score', 'fraud_reason',
            'clicked_at'
        ]


class AdConversionSerializer(serializers.ModelSerializer):
    """Serializer for ad conversions"""
    
    creative_name = serializers.CharField(source='creative.name', read_only=True)
    click_id_display = serializers.CharField(source='click.click_id', read_only=True)
    order_number = serializers.CharField(source='order.order_number', read_only=True)
    
    class Meta:
        model = AdConversion
        fields = [
            'id', 'click', 'click_id_display', 'creative', 'creative_name',
            'conversion_type', 'conversion_value', 'attribution_model',
            'time_to_conversion', 'order', 'order_number', 'transaction_id',
            'conversion_data', 'is_verified', 'verification_method',
            'converted_at'
        ]
        read_only_fields = [
            'id', 'is_verified', 'verification_method', 'converted_at'
        ]


class AdBudgetSpendSerializer(serializers.ModelSerializer):
    """Serializer for daily budget tracking"""
    
    campaign_name = serializers.CharField(source='campaign.name', read_only=True)
    budget_utilization = serializers.ReadOnlyField()
    
    class Meta:
        model = AdBudgetSpend
        fields = [
            'id', 'campaign', 'campaign_name', 'spend_date', 'daily_budget',
            'total_spend', 'budget_utilization', 'impressions', 'clicks',
            'conversions', 'revenue', 'budget_exhausted_at',
            'is_budget_exceeded', 'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'total_spend', 'impressions', 'clicks', 'conversions',
            'revenue', 'budget_exhausted_at', 'is_budget_exceeded',
            'created_at', 'updated_at'
        ]


class AdReportingDataSerializer(serializers.ModelSerializer):
    """Serializer for reporting data"""
    
    campaign_name = serializers.CharField(source='campaign.name', read_only=True)
    
    class Meta:
        model = AdReportingData
        fields = [
            'id', 'campaign', 'campaign_name', 'aggregation_level',
            'granularity', 'dimension_values', 'report_date', 'report_hour',
            'impressions', 'clicks', 'conversions', 'spend', 'revenue',
            'ctr', 'cpc', 'cpa', 'roas', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']


# Request/Response serializers
class CampaignCreateRequestSerializer(serializers.ModelSerializer):
    """Serializer for campaign creation requests"""
    
    class Meta:
        model = AdCampaign
        fields = [
            'advertiser', 'name', 'description', 'campaign_type',
            'start_date', 'end_date', 'bidding_strategy',
            'daily_budget', 'total_budget', 'default_bid', 'max_bid',
            'target_cpa', 'target_roas', 'target_keywords',
            'target_demographics', 'target_locations', 'target_devices',
            'target_schedule', 'exclude_keywords', 'audience_targeting',
            'is_evergreen', 'auto_pause_low_performance',
            'enable_dynamic_ads', 'enable_audience_expansion'
        ]


class CampaignPerformanceSerializer(serializers.Serializer):
    """Serializer for campaign performance data"""
    
    campaign_id = serializers.UUIDField()
    campaign_name = serializers.CharField()
    impressions = serializers.IntegerField()
    clicks = serializers.IntegerField()
    conversions = serializers.IntegerField()
    spend = serializers.DecimalField(max_digits=12, decimal_places=2)
    revenue = serializers.DecimalField(max_digits=12, decimal_places=2)
    ctr = serializers.DecimalField(max_digits=5, decimal_places=2)
    cpc = serializers.DecimalField(max_digits=8, decimal_places=4)
    cpa = serializers.DecimalField(max_digits=8, decimal_places=2)
    roas = serializers.DecimalField(max_digits=8, decimal_places=2)
    quality_score = serializers.DecimalField(max_digits=4, decimal_places=2)


class AuctionRequestSerializer(serializers.Serializer):
    """Serializer for ad auction requests"""
    
    placement_id = serializers.UUIDField()
    user_context = serializers.DictField()
    page_context = serializers.DictField()
    device_context = serializers.DictField()
    
    def validate_user_context(self, value):
        required_fields = ['session_id', 'device_type']
        for field in required_fields:
            if field not in value:
                raise serializers.ValidationError(f"Missing required field: {field}")
        return value
    
    def validate_page_context(self, value):
        if 'page_url' not in value:
            raise serializers.ValidationError("page_url is required in page_context")
        return value


class AuctionResponseSerializer(serializers.Serializer):
    """Serializer for ad auction responses"""
    
    auction_id = serializers.UUIDField()
    creative = AdCreativeSerializer()
    bid_amount = serializers.DecimalField(max_digits=8, decimal_places=4)
    clearing_price = serializers.DecimalField(max_digits=8, decimal_places=4)
    request_id = serializers.CharField()


class ImpressionTrackingSerializer(serializers.Serializer):
    """Serializer for impression tracking"""
    
    impression_id = serializers.CharField()
    viewable = serializers.BooleanField(default=True)
    view_duration = serializers.IntegerField(default=0)
    scroll_depth = serializers.DecimalField(max_digits=5, decimal_places=2, default=0.00)


class ClickTrackingSerializer(serializers.Serializer):
    """Serializer for click tracking"""
    
    impression_id = serializers.CharField()
    click_position = serializers.DictField(default=dict)
    time_to_click = serializers.IntegerField(default=0)
    destination_url = serializers.URLField(required=False)


class ConversionTrackingSerializer(serializers.Serializer):
    """Serializer for conversion tracking"""
    
    click_id = serializers.CharField()
    conversion_type = serializers.ChoiceField(choices=AdConversion.CONVERSION_TYPES)
    conversion_value = serializers.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    order_id = serializers.UUIDField(required=False)
    transaction_id = serializers.CharField(max_length=100, required=False)
    custom_data = serializers.DictField(default=dict)
    attribution_model = serializers.CharField(default='last_click')
    verification_method = serializers.CharField(default='automatic')


class CampaignReportRequestSerializer(serializers.Serializer):
    """Serializer for campaign report requests"""
    
    campaign_id = serializers.UUIDField()
    start_date = serializers.DateTimeField()
    end_date = serializers.DateTimeField()
    granularity = serializers.ChoiceField(
        choices=['hourly', 'daily', 'weekly', 'monthly'],
        default='daily'
    )
    include_demographics = serializers.BooleanField(default=False)
    include_devices = serializers.BooleanField(default=False)
    include_creatives = serializers.BooleanField(default=False)
    
    def validate(self, attrs):
        start_date = attrs['start_date']
        end_date = attrs['end_date']
        
        if start_date >= end_date:
            raise serializers.ValidationError("end_date must be after start_date")
        
        # Limit report range to 90 days
        if (end_date - start_date).days > 90:
            raise serializers.ValidationError("Report range cannot exceed 90 days")
        
        return attrs


class CampaignReportResponseSerializer(serializers.Serializer):
    """Serializer for campaign report responses"""
    
    campaign_id = serializers.UUIDField()
    campaign_name = serializers.CharField()
    period = serializers.CharField()
    total_impressions = serializers.IntegerField()
    total_clicks = serializers.IntegerField()
    total_conversions = serializers.IntegerField()
    total_spend = serializers.DecimalField(max_digits=12, decimal_places=2)
    total_revenue = serializers.DecimalField(max_digits=12, decimal_places=2)
    ctr = serializers.DecimalField(max_digits=5, decimal_places=2)
    cpc = serializers.DecimalField(max_digits=8, decimal_places=4)
    cpa = serializers.DecimalField(max_digits=8, decimal_places=2)
    avg_order_value = serializers.DecimalField(max_digits=8, decimal_places=2)
    roas = serializers.DecimalField(max_digits=8, decimal_places=2)
    time_series = serializers.ListField(child=serializers.DictField())
    demographics = serializers.DictField(required=False)
    devices = serializers.DictField(required=False)
    creatives = serializers.ListField(child=serializers.DictField(), required=False)


class BidOptimizationRequestSerializer(serializers.Serializer):
    """Serializer for bid optimization requests"""
    
    campaign_id = serializers.UUIDField()
    optimization_goal = serializers.ChoiceField(
        choices=['maximize_clicks', 'maximize_conversions', 'target_cpa', 'target_roas'],
        default='maximize_conversions'
    )
    target_value = serializers.DecimalField(max_digits=8, decimal_places=2, required=False)
    apply_recommendations = serializers.BooleanField(default=False)
    
    def validate(self, attrs):
        optimization_goal = attrs['optimization_goal']
        
        if optimization_goal in ['target_cpa', 'target_roas'] and not attrs.get('target_value'):
            raise serializers.ValidationError(f"target_value is required for {optimization_goal}")
        
        return attrs


class BidOptimizationResponseSerializer(serializers.Serializer):
    """Serializer for bid optimization responses"""
    
    campaign_id = serializers.UUIDField()
    optimization_date = serializers.DateTimeField()
    bidding_strategy = serializers.CharField()
    keyword_recommendations = serializers.ListField(child=serializers.DictField())
    ad_group_recommendations = serializers.ListField(child=serializers.DictField())
    overall_recommendations = serializers.ListField(child=serializers.DictField())


class AdAnalyticsSerializer(serializers.Serializer):
    """Serializer for ads analytics dashboard"""
    
    total_campaigns = serializers.IntegerField()
    active_campaigns = serializers.IntegerField()
    total_spend = serializers.DecimalField(max_digits=12, decimal_places=2)
    total_revenue = serializers.DecimalField(max_digits=12, decimal_places=2)
    total_impressions = serializers.BigIntegerField()
    total_clicks = serializers.BigIntegerField()
    total_conversions = serializers.IntegerField()
    overall_ctr = serializers.DecimalField(max_digits=5, decimal_places=2)
    overall_cpc = serializers.DecimalField(max_digits=8, decimal_places=4)
    overall_cpa = serializers.DecimalField(max_digits=8, decimal_places=2)
    overall_roas = serializers.DecimalField(max_digits=8, decimal_places=2)
    campaign_performance = serializers.ListField(child=serializers.DictField())
    placement_performance = serializers.ListField(child=serializers.DictField())
    device_breakdown = serializers.DictField()
    hourly_performance = serializers.ListField(child=serializers.DictField())


class KeywordSuggestionRequestSerializer(serializers.Serializer):
    """Serializer for keyword suggestion requests"""
    
    seed_keywords = serializers.ListField(
        child=serializers.CharField(max_length=200),
        max_length=10
    )
    match_types = serializers.ListField(
        child=serializers.ChoiceField(choices=AdKeyword.MATCH_TYPES),
        default=['broad']
    )
    max_suggestions = serializers.IntegerField(min_value=1, max_value=100, default=25)
    include_search_volume = serializers.BooleanField(default=True)
    include_competition = serializers.BooleanField(default=True)


class KeywordSuggestionResponseSerializer(serializers.Serializer):
    """Serializer for keyword suggestion responses"""
    
    keyword_text = serializers.CharField()
    match_type = serializers.CharField()
    monthly_searches = serializers.IntegerField()
    competition_level = serializers.CharField()
    suggested_bid = serializers.DecimalField(max_digits=8, decimal_places=4)
    relevance_score = serializers.DecimalField(max_digits=4, decimal_places=2)